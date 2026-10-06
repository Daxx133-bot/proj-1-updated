"""
run_campaign.py -- resumable, crash-isolated runner for the full 180-run campaign.

Implements Preregistration v3 §9. This is the process that runs unattended for 8-11 hours,
so its failure modes matter more than its happy path.

Design
------
* MANIFEST-DRIVEN. Every (app, service, fault_type, repetition) combination is enumerated
  up front into data/campaign/manifest.json with a status. The manifest -- not the
  filesystem, not this process's memory -- is the single source of truth for what has run.

* RESUMABLE. A combination marked `done` or `censored` is never run again. Re-launching
  after a crash, a laptop sleep or a Ctrl-C continues from where it stopped. The manifest
  is written atomically (temp file + os.replace) after every status change, so an
  interruption mid-write cannot corrupt it.

* CRASH-ISOLATED. Any exception from a single run is caught, logged with a full traceback,
  and the combination is marked `failed`; the stack is then restored and the campaign
  moves to the next combination. One bad run never aborts the campaign.

  The one case that DOES stop the campaign is an unrecoverable stack: if escalating
  recovery (compose up -> restart -> down+up) cannot bring the application back to a
  healthy state, every subsequent run would produce garbage, so the process stops with a
  clear message and a manifest that can be resumed once the machine is fixed. Continuing
  in that state would generate 100 plausible-looking but meaningless rows, which is the
  exact failure this project is recovering from.

* SINGLE STACK. RunLock (reused from run_pilot) refuses a second concurrent runner. A
  double-launch corrupted 3 SN pilot runs (_quarantine/QUARANTINE_LOG.md item 9), and one
  stack at a time is also a hard memory constraint (_audit/MEMORY_CEILING.md).

* BALANCED ORDERING. Runs are ordered repetition-major: every combination gets its 1st
  repetition before any gets its 2nd. If the campaign is interrupted at any point the
  partial dataset is as close to balanced as it can be, rather than complete for the
  first few services and empty for the rest. Prior batches were unbalanced precisely on
  the services carrying the headline claims (v3 §8).

* APPEND-ONLY PROGRESS LOG at data/campaign/progress.log, one line per completed run, so
  progress can be checked by reading a file without touching the process.

Status values
-------------
  pending   not yet attempted
  running   claimed by a runner; a `running` entry found at startup means the previous
            process died mid-run, and it is reset to `pending`
  done      completed, telemetry_ok, recovery observed
  censored  completed, telemetry_ok, did NOT recover within max-wait. This is a LEGITIMATE
            OBSERVATION, not a failure. It is never re-run to obtain a number.
  failed    exception, or telemetry_ok=False. Re-runnable with --retry-failed.

Usage
-----
    python tools/run_campaign.py --build-manifest      # enumerate, write manifest, exit
    python tools/run_campaign.py --dry-run             # show what would run, touch nothing
    python tools/run_campaign.py                       # run / resume the campaign
    python tools/run_campaign.py --retry-failed        # reset `failed` to `pending` first
    python tools/run_campaign.py --status              # print progress and exit
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from faultinjection.fault_config import FaultType  # noqa: E402
from infra.docker_utils import find_docker_executable  # noqa: E402
from measurement.blast_radius import is_gateway  # noqa: E402
from tools.run_pilot import (  # noqa: E402
    APPS,
    RunLock,
    compose_service,
    load_graph,
    one_run,
)

CAMPAIGN_DIR = ROOT / "data" / "campaign"
MANIFEST = CAMPAIGN_DIR / "manifest.json"
PROGRESS_LOG = CAMPAIGN_DIR / "progress.log"
RESULTS_DIR = CAMPAIGN_DIR / "runs"
FAILURES_DIR = CAMPAIGN_DIR / "failures"
LOCK = CAMPAIGN_DIR / ".campaign.lock"

# Preregistration v3 §8. Changing either of these changes the preregistered design.
FAULT_TYPES = ["kill", "latency"]
REPETITIONS = 5

TERMINAL = {"done", "censored"}


def rel(p: Path) -> str:
    """Repo-relative path for display, falling back to absolute when outside the repo."""
    try:
        return str(p.relative_to(ROOT)).replace(chr(92), "/")
    except ValueError:
        return str(p)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Manifest ──────────────────────────────────────────────────────────────────

def enumerate_runs() -> list[dict]:
    """Every (app, service, fault_type, repetition), repetition-major.

    Services come from the canonical graphs with gateways excluded (v3 §4): a gateway has
    ancestor_count 0 by construction and killing it leaves the outcome undefined.
    """
    per_app = {}
    for app, cfg in APPS.items():
        G = load_graph(cfg["graph"])
        per_app[app] = sorted(s for s in G.nodes() if not is_gateway(G, s))

    runs = []
    for rep in range(1, REPETITIONS + 1):
        for app in APPS:
            for fault in FAULT_TYPES:
                for svc in per_app[app]:
                    runs.append({
                        "id": f"{app}|{svc}|{fault}|{rep}",
                        "app": app, "service": svc,
                        "fault_type": fault, "repetition": rep,
                        "status": "pending", "attempts": 0,
                        "result_file": None, "error": None,
                        "updated_at": None,
                    })
    return runs


def build_manifest(force: bool = False) -> dict:
    if MANIFEST.exists() and not force:
        raise SystemExit(
            f"[REFUSED] {rel(MANIFEST)} already exists. Resuming uses it as "
            f"is; pass --force-rebuild only if you intend to discard its history."
        )
    runs = enumerate_runs()
    doc = {
        "created_at": now(),
        "preregistration": "v3 (2026-09-25)",
        "fault_types": FAULT_TYPES,
        "repetitions": REPETITIONS,
        "total_runs": len(runs),
        "ordering": "repetition-major, so an interruption leaves a balanced partial set",
        "runs": runs,
    }
    write_manifest(doc)
    return doc


def load_manifest() -> dict:
    if not MANIFEST.exists():
        raise SystemExit(
            f"[FAIL] no manifest at {rel(MANIFEST)}. "
            f"Run: python tools/run_campaign.py --build-manifest"
        )
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def write_manifest(doc: dict) -> None:
    """Atomic: write a temp file in the same directory, then replace.

    A half-written manifest after a power loss would be worse than no manifest -- the
    campaign would not know what it had already run.
    """
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    os.replace(tmp, MANIFEST)


def counts(doc: dict) -> dict:
    out = {k: 0 for k in ("pending", "running", "done", "censored", "failed")}
    for r in doc["runs"]:
        out[r["status"]] = out.get(r["status"], 0) + 1
    return out


def log_progress(line: str) -> None:
    PROGRESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_LOG, "a", encoding="utf-8") as fh:
        fh.write(line.rstrip() + "\n")
    print(line)


# ── Stack lifecycle ───────────────────────────────────────────────────────────

def compose(app: str, *cmd: str, timeout: int = 600) -> subprocess.CompletedProcess:
    docker = find_docker_executable()
    return subprocess.run([docker, "compose", *cmd],
                          cwd=str(APPS[app]["compose_dir"]),
                          capture_output=True, text=True, timeout=timeout)


def running_services(app: str) -> set[str]:
    """Compose service names with a running container in this app's project."""
    docker = find_docker_executable()
    r = subprocess.run(
        [docker, "ps", "--format", '{{.Label "com.docker.compose.service"}}'],
        cwd=str(APPS[app]["compose_dir"]), capture_output=True, text=True, timeout=120)
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


def missing_services(app: str) -> list[str]:
    """Graph services that have no running container, reported by their GRAPH name.

    The graph is the authority on which services the experiment depends on. Anything in it
    that is not running means the topology under measurement is not the topology being
    reported.

    Graph names are translated to compose names first (`compose_service`): a service's
    identity in a trace is whatever it reports to Jaeger, which need not equal the compose
    service that runs it. Comparing the two directly made the Social Network gateway look
    permanently absent and aborted the campaign on a healthy stack.
    """
    running = running_services(app)
    return sorted(g for g in load_graph(APPS[app]["graph"]).nodes()
                  if compose_service(app, g) not in running)


def preflight_service_names() -> list[str]:
    """Check every graph service maps to a real compose service, before anything starts.

    A mismatch here is a configuration error, and the only sane time to discover it is at
    launch. It was previously discovered 28 minutes into a campaign, when the runner
    switched applications and the stack-completeness check rejected a healthy stack.
    """
    problems = []
    docker = find_docker_executable()
    for app, cfg in APPS.items():
        r = subprocess.run([docker, "compose", "config", "--services"],
                           cwd=str(cfg["compose_dir"]), capture_output=True, text=True,
                           timeout=180)
        if r.returncode != 0:
            problems.append(f"{app}: cannot read compose services: {r.stderr.strip()[-300:]}")
            continue
        declared = {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}
        for g in sorted(load_graph(cfg["graph"]).nodes()):
            cs = compose_service(app, g)
            if cs not in declared:
                problems.append(
                    f"{app}: graph service '{g}' maps to compose service '{cs}', which "
                    f"the compose file does not declare. Add or correct an entry in "
                    f"APPS['{app}']['compose_aliases'].")
    return problems


def stack_healthy(app: str, timeout_s: float = 240.0) -> bool:
    """Healthy = Jaeger answers, the gateway answers, AND every graph service is running.

    The third condition was added after the 2026-09-26 campaign ran two runs against a
    stack that had silently lost `geo`: Jaeger and the gateway both answered perfectly, so
    the first two checks passed and the runs were marked `done` with invalid outcomes. A
    partial stack is not a healthy stack, and the failure is silent precisely because the
    gateway keeps serving. See _quarantine/QUARANTINE_LOG.md item 12.
    """
    cfg = APPS[app]
    deadline = time.time() + timeout_s
    last_missing: list[str] = []
    while time.time() < deadline:
        try:
            j = requests.get(f"{cfg['jaeger']}/api/services", timeout=10)
            if j.ok and (j.json().get("data") or []):
                a = requests.get(cfg["url"], timeout=10)
                if a.status_code < 500:
                    last_missing = missing_services(app)
                    if not last_missing:
                        return True
        except (requests.RequestException, subprocess.SubprocessError):
            pass
        time.sleep(5)
    if last_missing:
        log_progress(f"[{now()}] UNHEALTHY {app}: services not running: {last_missing}")
    return False


def stack_up(app: str) -> bool:
    log_progress(f"[{now()}] STACK UP   {app}")
    r = compose(app, "up", "-d")
    if r.returncode != 0:
        log_progress(f"[{now()}] STACK UP FAILED {app}: {r.stderr[-800:]}")
        return False
    return stack_healthy(app)


def stack_down(app: str) -> None:
    log_progress(f"[{now()}] STACK DOWN {app}")
    compose(app, "down", "-v")


def down_all_stacks() -> None:
    """Bring every application stack down before the first run.

    Necessary, not merely tidy. The two stacks collide on Jaeger's host port and cannot
    both fit under the Docker VM memory ceiling, and this process cannot know what a
    previous process (or a human) left running -- a runner that died between `stack_up`
    and `stack_down` leaves one up. Starting the other on top of it fails in a way that
    looks like a broken application rather than a dirty host.

    `compose down` on a stack that is not running is a no-op, so this is cheap.
    """
    for app in APPS:
        log_progress(f"[{now()}] PRE-CLEAN down {app}")
        try:
            compose(app, "down", "-v", timeout=600)
        except subprocess.SubprocessError as exc:
            log_progress(f"[{now()}] PRE-CLEAN {app} raised {type(exc).__name__}: {exc}")


def restore_stack(app: str) -> bool:
    """Escalating recovery after a failed run. Returns True if the stack is usable.

    Level 1 recreates whatever container the fault removed; level 2 restarts everything;
    level 3 tears the stack down and rebuilds it. Level 3 is slow (~2-4 min) but a run
    against a half-broken stack is worse than the time it costs.
    """
    for level, args_ in enumerate(
            [("up", "-d"), ("restart",), None], start=1):
        log_progress(f"[{now()}] RESTORE L{level} {app}")
        if args_ is None:
            stack_down(app)
            ok = stack_up(app)
        else:
            r = compose(app, *args_)
            ok = r.returncode == 0 and stack_healthy(app)
        if ok:
            log_progress(f"[{now()}] RESTORE OK at L{level} {app}")
            return True
    log_progress(f"[{now()}] RESTORE FAILED {app} -- all levels exhausted")
    return False


# ── Run execution ─────────────────────────────────────────────────────────────

class RunArgs:
    """The knobs one_run expects. Values are Preregistration v3 §8 and §6.4."""

    warmup = 60
    fault_duration = 30
    poll = 1.0
    max_wait = 180.0
    confirm = 5.0
    lag = 5.0
    min_traces = 20
    users = 25
    cooldown = 20
    persist_spans = True
    spans_dir = str(ROOT / "data" / "spans")


def classify_result(res: dict) -> tuple[str, str]:
    """Map a completed run onto a manifest status.

    A censored run is a real observation and is terminal. A run with no telemetry is not
    an observation at all -- v3 §8 requires it be discarded and re-run, never analysed as
    zeros -- so it is `failed`.
    """
    if not res.get("telemetry_ok"):
        return "failed", (f"telemetry_ok=False "
                          f"(baseline_traces={res.get('baseline_trace_count')}, "
                          f"fault_traces={res.get('fault_trace_count')})")
    if res.get("recovery_censored"):
        return "censored", ""
    return "done", ""


def summarise(res: dict) -> str:
    rec = "CENS" if res.get("recovery_censored") else f"{res.get('recovery_time_s')}s"
    return (f"A/D/U={res.get('ancestor_affected_count')}/"
            f"{res.get('descendant_affected_count')}/"
            f"{res.get('unrelated_affected_count')}  "
            f"err={res.get('fault_error_rate')}  "
            f"dp95={round((res.get('fault_p95_ms') or 0) - (res.get('baseline_p95_ms') or 0), 1)}  "
            f"T_rec={rec}")


def execute(entry: dict, doc: dict) -> bool:
    """Run one combination. Returns False only if the stack is unrecoverable."""
    app, svc = entry["app"], entry["service"]
    entry["status"] = "running"
    entry["attempts"] += 1
    entry["updated_at"] = now()
    write_manifest(doc)

    try:
        res = one_run(app, svc, entry["repetition"], APPS[app], RunArgs(),
                      FaultType(entry["fault_type"]))
    except BaseException as exc:                      # noqa: BLE001 - deliberate
        # Deliberately broad: an unattended 8-11h campaign must survive anything a single
        # run can raise, including SystemExit from a helper that calls sys.exit(). The
        # full traceback is written to disk so nothing is lost by catching it here.
        # KeyboardInterrupt is re-raised below so Ctrl-C still stops the campaign.
        if isinstance(exc, KeyboardInterrupt):
            entry["status"] = "pending"
            entry["updated_at"] = now()
            write_manifest(doc)
            raise
        FAILURES_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        tb = FAILURES_DIR / f"{entry['id'].replace('|', '_')}_{stamp}.txt"
        tb.write_text("".join(traceback.format_exception(exc)), encoding="utf-8")
        entry["status"] = "failed"
        entry["error"] = f"{type(exc).__name__}: {exc}"
        entry["updated_at"] = now()
        write_manifest(doc)
        c = counts(doc)
        log_progress(f"[{now()}] FAILED   {entry['id']:<48} {type(exc).__name__}: {exc} "
                     f"| traceback={rel(tb)} "
                     f"| done={c['done']} censored={c['censored']} failed={c['failed']}")
        return restore_stack(app)

    status, note = classify_result(res)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = res["timestamp"].replace(":", "-").replace("+00:00", "Z")
    path = RESULTS_DIR / f"run_{entry['id'].replace('|', '_')}_{stamp}.json"
    path.write_text(json.dumps(res, indent=2), encoding="utf-8")

    entry["status"] = status
    entry["result_file"] = rel(path)
    entry["error"] = note or None
    entry["updated_at"] = now()
    write_manifest(doc)

    c = counts(doc)
    log_progress(f"[{now()}] {status.upper():<8} {entry['id']:<48} {summarise(res)} "
                 f"| done={c['done']} censored={c['censored']} failed={c['failed']} "
                 f"pending={c['pending']}")
    if status == "failed":
        return restore_stack(app)
    return True


# ── Main loop ─────────────────────────────────────────────────────────────────

def print_status(doc: dict) -> None:
    c = counts(doc)
    total = doc["total_runs"]
    finished = c["done"] + c["censored"]
    print(f"manifest  : {rel(MANIFEST)}")
    print(f"created   : {doc['created_at']}   prereg {doc['preregistration']}")
    print(f"progress  : {finished}/{total} terminal "
          f"({100 * finished / total:.1f}%)")
    for k in ("done", "censored", "failed", "running", "pending"):
        print(f"  {k:<9}: {c[k]}")
    if c["failed"]:
        print("\nfailed combinations:")
        for r in doc["runs"]:
            if r["status"] == "failed":
                print(f"  {r['id']:<48} attempts={r['attempts']}  {r['error']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build-manifest", action="store_true")
    ap.add_argument("--force-rebuild", action="store_true",
                    help="with --build-manifest: overwrite an existing manifest")
    ap.add_argument("--status", action="store_true", help="print progress and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would run; start no stack and inject no fault")
    ap.add_argument("--retry-failed", action="store_true",
                    help="reset `failed` entries to `pending` before running")
    ap.add_argument("--only-app", choices=list(APPS))
    ap.add_argument("--max-runs", type=int, default=None,
                    help="stop after this many runs (for a short supervised trial)")
    args = ap.parse_args()

    if args.build_manifest:
        doc = build_manifest(force=args.force_rebuild)
        print(f"[WROTE] {rel(MANIFEST)}  ({doc['total_runs']} runs)")
        by_app = {}
        for r in doc["runs"]:
            by_app[r["app"]] = by_app.get(r["app"], 0) + 1
        for a, n in by_app.items():
            print(f"  {a}: {n}")
        return 0

    doc = load_manifest()

    if args.status:
        print_status(doc)
        return 0

    # A `running` entry at startup means the previous process died mid-run. That run's
    # data is not trustworthy, so it goes back to `pending` rather than being counted.
    reset = [r for r in doc["runs"] if r["status"] == "running"]
    for r in reset:
        r["status"] = "pending"
        r["error"] = "reset: previous runner died while this run was in flight"
    if args.retry_failed:
        for r in doc["runs"]:
            if r["status"] == "failed":
                r["status"] = "pending"
    if reset or args.retry_failed:
        write_manifest(doc)
    if reset:
        print(f"[RESUME] reset {len(reset)} interrupted run(s) to pending")

    todo = [r for r in doc["runs"]
            if r["status"] not in TERMINAL and r["status"] != "failed"
            and (args.only_app is None or r["app"] == args.only_app)]
    if args.max_runs:
        todo = todo[:args.max_runs]

    if args.dry_run:
        print_status(doc)
        print(f"\nwould run {len(todo)} combination(s), in this order:")
        for r in todo[:40]:
            print(f"  {r['id']}")
        if len(todo) > 40:
            print(f"  ... and {len(todo) - 40} more")
        return 0

    if not todo:
        print("[DONE] nothing pending.")
        print_status(doc)
        return 0

    problems = preflight_service_names()
    if problems:
        print("[REFUSED] service-name preflight failed; nothing was started:")
        for pr in problems:
            print(f"  - {pr}")
        return 2

    rc = 0
    current_app = None
    with RunLock(LOCK):
        log_progress(f"[{now()}] CAMPAIGN START  {len(todo)} run(s) to go "
                     f"| {counts(doc)}")
        down_all_stacks()
        try:
            for entry in todo:
                # Re-read status: nothing else writes the manifest while we hold the
                # lock, but this keeps the loop honest if that ever changes.
                if entry["status"] in TERMINAL:
                    continue

                if entry["app"] != current_app:
                    if current_app is not None:
                        stack_down(current_app)
                    if not stack_up(entry["app"]):
                        log_progress(f"[{now()}] ABORT: cannot bring up "
                                     f"{entry['app']}; campaign paused, manifest intact")
                        rc = 2
                        break
                    current_app = entry["app"]

                if not execute(entry, doc):
                    log_progress(f"[{now()}] ABORT: {entry['app']} stack is "
                                 f"unrecoverable; campaign paused, manifest intact. "
                                 f"Fix the machine and re-run this command to resume.")
                    rc = 2
                    break

                time.sleep(RunArgs.cooldown)
        except KeyboardInterrupt:
            log_progress(f"[{now()}] INTERRUPTED by user; manifest intact, resumable")
            rc = 130
        finally:
            if current_app is not None:
                stack_down(current_app)
            log_progress(f"[{now()}] CAMPAIGN STOP  | {counts(doc)}")

    print()
    print_status(doc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
