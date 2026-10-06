"""
run_pilot.py — small, instrumented pilot. NOT the full campaign.

Runs (service x kill x repetition) for a handful of services against ONE already-running
stack, using the corrected recovery probe. Writes one JSON per run plus a summary CSV
into data/pilot/.

Everything measured here comes from Jaeger and the Docker API. Nothing is estimated.
If telemetry is empty the run is recorded as telemetry_ok=False and the metrics are left
as nulls -- never as zeros, which is the conflation that hid the earlier outage.

Usage:
    python tools/run_pilot.py --app hotelreservation --services frontend,geo --reps 2
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
from dataclasses import replace
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from faultinjection.fault_config import FaultType, DEFAULT_SPECS  # noqa: E402
from infra.docker_utils import find_docker_executable  # noqa: E402
from measurement.metrics_collector import (  # noqa: E402
    collect_baseline_metrics, collect_fault_window_metrics, compute_blast_radius,
    get_traces_in_window,
)
from measurement.blast_radius import classify_affected, is_gateway  # noqa: E402
from measurement.recovery_probe import probe_recovery  # noqa: E402
import networkx as nx  # noqa: E402

APPS = {
    "socialnetwork": {
        "jaeger": "http://localhost:16686",
        "gateway": "nginx-web-server",
        "url": "http://localhost:8080",
        "locustfile": ROOT / "infra" / "_locustfile_baseline.py",
        "graph": ROOT / "data" / "graphs" / "sn_CANONICAL.json",
        "compose_dir": ROOT.parent / "DeathStarBench" / "socialNetwork",
        # Graph/Jaeger service name -> docker compose service name, where they differ.
        # A service's name in a trace is whatever it reports to Jaeger, which need not
        # match the compose service that runs it. The Social Network gateway reports
        # itself as "nginx-web-server" but is the compose service "nginx-thrift".
        # Everything that talks to Jaeger uses the graph name; everything that talks to
        # Docker must use the compose name. Conflating them made the stack-completeness
        # check declare "nginx-web-server" permanently missing.
        "compose_aliases": {"nginx-web-server": "nginx-thrift"},
    },
    "hotelreservation": {
        "jaeger": "http://localhost:16687",
        "gateway": "frontend",
        "url": "http://localhost:5000",
        "locustfile": ROOT / "infra" / "_locustfile_hotel.py",
        "graph": ROOT / "data" / "graphs" / "hr_CANONICAL.json",
        "compose_dir": ROOT.parent / "DeathStarBench" / "hotelReservation",
        # Every Hotel Reservation graph name equals its compose service name.
        "compose_aliases": {},
    },
}


class RunLock:
    """Refuse to start if another runner instance is live.

    A double-launch silently corrupts runs: two processes inject faults into the same
    stack while each other's load generator and recovery probe are active. That happened
    during the 2026-09-24 pilot and cost 3 runs
    (see _quarantine/QUARANTINE_LOG.md item 9).
    """

    def __init__(self, path: Path):
        self.path = path

    def __enter__(self):
        if self.path.exists():
            holder = self.path.read_text(encoding="utf-8").strip()
            raise SystemExit(
                f"[REFUSED] another runner appears to be active (lock held by {holder}). "
                f"If you are certain it is dead, delete {self.path} and retry."
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(f"pid={os.getpid()} started={datetime.now(timezone.utc).isoformat()}",
                             encoding="utf-8")
        return self

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)
        return False


def graph_services(path: Path) -> list[str]:
    return [n["id"] for n in json.loads(path.read_text(encoding="utf-8"))["nodes"]]


def load_graph(path: Path) -> "nx.DiGraph":
    return nx.node_link_graph(json.loads(path.read_text(encoding="utf-8")), edges="edges")


def compose_service(app: str, graph_service: str) -> str:
    """Translate a graph/Jaeger service name into its docker compose service name.

    Identity for all but the Social Network gateway; see `compose_aliases` in APPS.
    """
    return APPS[app].get("compose_aliases", {}).get(graph_service, graph_service)


def container_for(service: str, docker_exe: str) -> str:
    """Resolve a compose service name to its running container, by LABEL not by substring.

    Docker Compose stamps every container with `com.docker.compose.service`, which is an
    exact value. Matching on that is authoritative. Matching on the container NAME is not,
    and got this badly wrong:

        container_for("reservation") -> "hotelreservation-geo-1"

    because the compose project is called "hotelReservation", so the project prefix
    "hotel*reservation*-" contains the substring "reservation" -- every container in the
    project matched, and `min(key=len)` then picked the shortest, which was `geo`. The
    2026-09-26 campaign therefore SIGKILLed `geo` while recording the run as a
    `reservation` fault, and restored `reservation` afterwards, leaving `geo` dead for the
    two runs that followed. See _quarantine/QUARANTINE_LOG.md item 12.

    Raises rather than guessing. An ambiguous match previously resolved silently to the
    shortest name; there is no circumstance in which quietly faulting a different service
    than the one being recorded is better than stopping.
    """
    res = subprocess.run(
        [docker_exe, "ps",
         "--filter", f"label=com.docker.compose.service={service}",
         "--format", "{{.Names}}\t{{.Label \"com.docker.compose.service\"}}"],
        capture_output=True, text=True, check=True)

    matches = []
    for line in res.stdout.strip().splitlines():
        if not line.strip():
            continue
        name, _, label = line.partition("\t")
        # Belt and braces: --filter label=k=v is an exact match, but verify it anyway so a
        # future Docker change in filter semantics cannot reintroduce fuzzy matching.
        if label.strip() == service:
            matches.append(name.strip())

    if not matches:
        raise SystemExit(
            f"[FAIL] no running container has compose label "
            f"com.docker.compose.service={service}. The stack is not up, or this service "
            f"is not running.")
    if len(matches) > 1:
        raise SystemExit(
            f"[FAIL] {len(matches)} running containers claim to be compose service "
            f"'{service}': {matches}. Refusing to guess which one to fault.")
    return matches[0]


def start_load(cfg: dict, duration: int, users: int) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "locust", "-f", str(cfg["locustfile"]),
         "--host", cfg["url"], "--headless", "--users", str(users),
         "--spawn-rate", "10", "--run-time", f"{duration}s", "--only-summary",
         "--loglevel", "ERROR"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(ROOT),
    )


def persist_spans(jaeger_url: str, services: list[str], start_us: int, end_us: int,
                  out_path: Path, label: str) -> dict:
    """Write the raw Jaeger traces for a window to a gzipped JSON file.

    Preregistration v3 §9.6. The pilot stored only aggregates, so when the per-service
    percentile definition turned out to be wrong (§6.1) the affected runs could not be
    recomputed -- Jaeger's in-memory storage was long gone. Persisting the spans makes a
    definitional change replayable offline instead of a re-run.

    Traces are deduplicated by traceID: Jaeger returns the same trace once per service it
    touches, so a naive dump stores each trace N times.
    """
    seen: dict[str, dict] = {}
    for svc in services:
        for tr in get_traces_in_window(jaeger_url, svc, start_us, end_us):
            tid = tr.get("traceID")
            if tid and tid not in seen:
                seen[tid] = tr
    payload = {
        "label": label,
        "window_start_us": start_us,
        "window_end_us": end_us,
        "queried_services": services,
        "trace_count": len(seen),
        "traces": list(seen.values()),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_path, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh)
    return {"path": str(out_path.relative_to(ROOT)).replace(chr(92), "/"),
            "trace_count": len(seen),
            "bytes": out_path.stat().st_size}


def one_run(app: str, service: str, rep: int, cfg: dict, args,
            fault_type: FaultType = FaultType.KILL) -> dict:
    docker_exe = find_docker_executable()
    # `service` is the graph/Jaeger name throughout this function, because that is what
    # Jaeger queries and the graph both use. Docker operations need the compose name.
    compose_svc = compose_service(app, service)
    container = container_for(compose_svc, docker_exe)
    services = graph_services(cfg["graph"])
    G = load_graph(cfg["graph"])
    t0 = time.time()

    print(f"\n{'='*70}\n  {app} / {service} / {fault_type.value} / rep {rep}"
          f"   (container: {container})\n{'='*70}")

    load = start_load(cfg, args.warmup + args.fault_duration + int(args.max_wait) + 60,
                      args.users)
    try:
        print(f"  [WARMUP] {args.warmup}s")
        time.sleep(args.warmup)

        print("  [BASELINE] collecting")
        baseline_end_us = int(time.time() * 1_000_000)
        baseline_start_us = baseline_end_us - args.warmup * 1_000_000
        baseline = collect_baseline_metrics(cfg["jaeger"], services,
                                            window_seconds=args.warmup)
        gw_base = baseline.get(cfg["gateway"], {})
        base_traces = int(gw_base.get("trace_count", 0))
        print(f"  [BASELINE] gateway p95={gw_base.get('p95_ms')}ms "
              f"traces={base_traces}")

        # The netem / stress rule must expire exactly when the fault window closes,
        # otherwise the "removal" instant used as the T_rec reference would be recorded
        # while the fault is still active. DEFAULT_SPECS ships 60 s; align it to the
        # window actually being run.
        spec = replace(DEFAULT_SPECS[fault_type],
                       duration_seconds=args.fault_duration)
        fault_start_us = int(time.time() * 1_000_000)
        cmd = spec.pumba_command(container)
        print(f"  [FAULT] {' '.join(cmd)}")
        fault_proc = None
        if fault_type == FaultType.KILL:
            # SIGKILL is instantaneous; run it synchronously.
            subprocess.run(cmd, check=True, timeout=60, capture_output=True)
        else:
            # `pumba netem` and `pumba stress` BLOCK for their whole --duration. Running
            # them synchronously would let the rule expire while we were still waiting,
            # so the fault window would be over before we started measuring it and the
            # recorded "removal" instant would land long after the real one. Launch in
            # the background and let the window below be the authority on timing.
            # (faultinjection/fault_runner.py::inject_fault does the same.)
            fault_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)

        print(f"  [FAULT] holding {args.fault_duration}s")
        time.sleep(args.fault_duration)
        fault_end_us = int(time.time() * 1_000_000)

        fault_m = collect_fault_window_metrics(cfg["jaeger"], cfg["gateway"],
                                               fault_start_us, fault_end_us)
        fault_traces = int(fault_m.get("trace_count", 0))
        down_n, down_list = compute_blast_radius(cfg["jaeger"], services, service,
                                                 baseline, fault_start_us, fault_end_us)
        print(f"  [FAULT] gateway p95={fault_m.get('p95_ms')}ms traces={fault_traces} "
              f"downstream={down_n}")

        # v3 §9.6: keep the raw spans for this fault window so any later change to a
        # metric definition can be replayed rather than re-run.
        # Both windows are kept. The blast-radius rule compares a fault-window
        # per-service percentile against its BASELINE counterpart, so storing only the
        # fault window would leave the comparison half-replayable -- which is the exact
        # gap that made the Q3 fix unverifiable against the pilot runs.
        spans_meta = None
        if getattr(args, "persist_spans", True):
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            base = (f"spans_{app}_{service}_{fault_type.value}_rep{rep}_{stamp}")
            spans_meta = {
                w: persist_spans(cfg["jaeger"], services, a, b,
                                 Path(args.spans_dir) / f"{base}_{w}.json.gz", label=w)
                for w, a, b in (("baseline_window", baseline_start_us, baseline_end_us),
                                ("fault_window", fault_start_us, fault_end_us))
            }
            for w, m in spans_meta.items():
                print(f"  [SPANS] {w}: {m['trace_count']} traces -> "
                      f"{m['path']} ({m['bytes'] / 1e6:.1f} MB)")

        restart_t0 = time.time()
        if fault_type == FaultType.KILL:
            print("  [RESTORE] docker compose up -d")
            subprocess.run([docker_exe, "compose", "up", "-d", compose_svc],
                           cwd=str(cfg["compose_dir"]), capture_output=True, timeout=180)
        else:
            # The rule expires with the pumba process. Wait for it so the removal instant
            # below is the real one, rather than a guess.
            print(f"  [RESTORE] waiting for {fault_type.value} rule to expire...")
            if fault_proc is not None:
                try:
                    fault_proc.wait(timeout=args.fault_duration + 60)
                except subprocess.TimeoutExpired:
                    fault_proc.kill()
                    print("  [WARNING] pumba did not exit; killed it")
        restart_s = round(time.time() - restart_t0, 2)

        # Amendment (b): the instant the fault was lifted. T_rec counts from here.
        fault_removal_us = int(time.time() * 1_000_000)
        fault_removal_offset_s = round((fault_removal_us - fault_start_us) / 1e6, 2)

        print(f"  [RECOVERY] probing (poll={args.poll}s, max_wait={args.max_wait}s)")
        rec = probe_recovery(
            cfg["jaeger"], cfg["gateway"], services, baseline, fault_start_us,
            reference_us=fault_removal_us,
            poll_interval_s=args.poll, max_wait_s=args.max_wait,
            tolerance=0.10, confirm_seconds=args.confirm,
            lag_s=args.lag, min_traces=args.min_traces,
        )
        if rec.recovered:
            print(f"  [RECOVERY] recovered at {rec.recovery_time_s}s")
        else:
            print(f"  [RECOVERY] CENSORED at {rec.observed_until_s}s "
                  f"(blocked on {rec.blocking_indicator})")

        # A `pumba netem` rule is supposed to expire with its --duration, but it does not
        # always: on 2026-09-26 a delay applied to compose-post-service survived its own
        # run and stayed active for the 10 SN latency runs that followed, inflating their
        # baselines ~60x and systematically UNDER-counting ancestor_affected_count by 2
        # (the two ancestors were already degraded before the fault). The stack teardown
        # cleared it, so nothing in the run records revealed it.
        #
        # Recreating the container removes any residual qdisc unconditionally. It happens
        # AFTER the fault window and AFTER the recovery probe, so it cannot influence this
        # run's measurements -- it exists to guarantee the NEXT run starts clean. Kill runs
        # already got a fresh container by necessity.
        fault_cleanup = None
        if fault_type != FaultType.KILL:
            print(f"  [CLEANUP] force-recreating {compose_svc} to clear any residual rule")
            cu = subprocess.run(
                [docker_exe, "compose", "up", "-d", "--force-recreate", compose_svc],
                cwd=str(cfg["compose_dir"]), capture_output=True, text=True, timeout=300)
            fault_cleanup = {"performed": True, "returncode": cu.returncode,
                             "stderr_tail": cu.stderr.strip()[-300:]}
            if cu.returncode != 0:
                print(f"  [WARNING] cleanup recreate failed: {cu.stderr.strip()[-200:]}")

        cls = classify_affected(G, service, down_list)
        print(f"  [BLAST] ancestors={cls['ancestor_affected_count']}/{cls['n_ancestors']} "
              f"descendants={cls['descendant_affected_count']}/{cls['n_descendants']} "
              f"unrelated={cls['unrelated_affected_count']}")

        return {
            "app": app, "service": service, "fault_type": fault_type.value,
            "repetition": rep,
            **cls,
            "is_gateway": is_gateway(G, service),
            "excluded_from_correlation": is_gateway(G, service),
            "fault_removal_offset_s": fault_removal_offset_s,
            "raw_spans": spans_meta,
            "fault_cleanup": fault_cleanup,
            "baseline_window_us": [baseline_start_us, baseline_end_us],
            "fault_window_us": [fault_start_us, fault_end_us],
            # Per-service baseline for EVERY service, not just the gateway. This is what
            # the blast-radius rule actually compares against; storing only the gateway's
            # made the classification unauditable after the fact.
            "baseline_per_service": baseline,
            "recovery_measured_from": rec.measured_from,
            "recovery_min_traces": rec.min_traces,
            "recovery_lag_s": rec.lag_s,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "container": container,
            "baseline_p95_ms": gw_base.get("p95_ms"),
            "baseline_p99_ms": gw_base.get("p99_ms"),
            "baseline_error_rate": gw_base.get("error_rate"),
            "baseline_trace_count": base_traces,
            "fault_p95_ms": fault_m.get("p95_ms"),
            "fault_p99_ms": fault_m.get("p99_ms"),
            "fault_error_rate": fault_m.get("error_rate"),
            "fault_trace_count": fault_traces,
            "telemetry_ok": base_traces > 0 and fault_traces > 0,
            "downstream_affected_count": down_n,
            "downstream_affected_services": ",".join(down_list),
            "recovery_time_s": rec.recovery_time_s,
            "recovery_censored": rec.censored,
            "recovery_observed_until_s": rec.observed_until_s,
            "recovery_first_ok_at_s": rec.first_ok_at_s,
            "recovery_blocking_indicator": rec.blocking_indicator,
            "recovery_poll_interval_s": args.poll,
            "container_restart_time_s": restart_s,
            "wall_clock_s": round(time.time() - t0, 2),
            "recovery_samples": rec.samples,
        }
    finally:
        load.terminate()
        try:
            load.wait(timeout=15)
        except subprocess.TimeoutExpired:
            load.kill()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True, choices=list(APPS))
    ap.add_argument("--services", required=True, help="comma-separated")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--warmup", type=int, default=60)
    ap.add_argument("--fault-duration", type=int, default=30)
    ap.add_argument("--poll", type=float, default=1.0)
    ap.add_argument("--max-wait", type=float, default=180.0)
    ap.add_argument("--confirm", type=float, default=5.0)
    ap.add_argument("--fault-type", default="kill", choices=["kill", "latency", "cpu"])
    ap.add_argument("--lag", type=float, default=5.0,
                    help="amendment (e): seconds to lag each probe window")
    ap.add_argument("--min-traces", type=int, default=20,
                    help="amendment (e): minimum traces for a sample to vote for recovery")
    ap.add_argument("--users", type=int, default=25)
    ap.add_argument("--cooldown", type=int, default=20)
    ap.add_argument("--no-persist-spans", dest="persist_spans",
                    action="store_false",
                    help="v3 §9.6: skip writing raw spans (not recommended)")
    ap.add_argument("--spans-dir", default=str(ROOT / "data" / "spans"),
                    help="where gzipped raw spans are written")
    args = ap.parse_args()

    cfg = APPS[args.app]
    out_dir = ROOT / "data" / "pilot"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    with RunLock(out_dir / ".runner.lock"):
        for service in [s.strip() for s in args.services.split(",")]:
            for rep in range(1, args.reps + 1):
                res = one_run(args.app, service, rep, cfg, args,
                              FaultType(args.fault_type))
                results.append(res)
                stamp = res["timestamp"].replace(":", "-").replace("+00:00", "Z")
                (out_dir / f"pilot_{args.app}_{service}_{args.fault_type}_rep{rep}_{stamp}.json").write_text(
                    json.dumps(res, indent=2), encoding="utf-8")
                print(f"  [COOLDOWN] {args.cooldown}s")
                time.sleep(args.cooldown)

    print(f"\n{'='*70}\n  PILOT SUMMARY: {args.app}\n{'='*70}")
    for r in results:
        rt = "CENSORED" if r["recovery_censored"] else f"{r['recovery_time_s']}s"
        print(f"  {r['service']:<22} rep{r['repetition']}  "
              f"telemetry_ok={str(r['telemetry_ok']):<5}  "
              f"base_traces={r['baseline_trace_count']:<5} fault_traces={r['fault_trace_count']:<5} "
              f"recovery={rt:<10} restart={r['container_restart_time_s']}s  "
              f"wall={r['wall_clock_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
