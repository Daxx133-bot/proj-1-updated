"""
analyze_live_spans.py -- replay the blast-radius rule over a run's persisted raw spans
under BOTH metric definitions, old and new.

This is what the Q3 validation could not do against the 2026-09-24 pilot runs: those runs
stored only aggregates, so the corrected per-service p95 was unrecoverable. Runs written
after the v3 change persist the baseline window's and the fault window's spans (deduped,
gzipped), so both definitions can be computed from the same bytes and compared directly.

OLD definition (the bug): "service X's p95" = p95 of ROOT-span durations over every trace
                          that TOUCHES X. Every service on a slow path inherits the same
                          end-to-end number. Error rate: a trace counts as errored if ANY
                          span in it errored.
NEW definition (v3 §6.1): p95 over the SERVER spans X itself emitted; error rate over X's
                          own spans, denominated by traces X appears in.

Nothing is injected or simulated here -- this reads files.

Usage:
    python tools/analyze_live_spans.py                 # newest HR search latency runs
    python tools/analyze_live_spans.py <run.json> ...
"""

from __future__ import annotations

import glob
import gzip
import json
import sys
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from measurement.metrics_collector import (  # noqa: E402
    DEGRADATION_FACTOR,
    DEGRADATION_FLOOR_MS,
    ERROR_RATE_ABS_THRESHOLD,
    compute_error_rate,
    compute_latency_percentiles,
    latency_degraded,
    span_service_map,
)
from tools.run_pilot import APPS  # noqa: E402

INFRA = ("jaeger", "mongo", "redis", "memcached", "consul")


def load_spans(rel: str) -> list[dict]:
    with gzip.open(ROOT / rel, "rt", encoding="utf-8") as fh:
        return json.load(fh)["traces"]


def touching(traces: list[dict], service: str) -> list[dict]:
    """Emulate Jaeger's /api/traces?service=X -- every trace containing a span from X."""
    return [t for t in traces if service in span_service_map(t).values()]


def app_services(traces: list[dict]) -> list[str]:
    return sorted({s for t in traces for s in span_service_map(t).values()
                   if s and not any(i in s.lower() for i in INFRA)})


def measure(traces: list[dict], svc: str, per_service: bool) -> dict:
    sub = touching(traces, svc)
    if not sub:
        return {"n_traces": 0, "p95": None, "err": None}
    kw = {"service": svc} if per_service else {}
    lat = compute_latency_percentiles(sub, **kw)
    return {"n_traces": len(sub), "n_spans": lat["count"],
            "p95": lat["p95_ms"], "err": compute_error_rate(sub, **kw)}


def flagged(base: dict, fault: dict) -> tuple[bool, str]:
    """The blast-radius rule, returning the reason it fired.

    Delegates to measurement.latency_degraded so this replay cannot drift away from what
    the runner actually applied.
    """
    if fault["n_traces"] == 0:
        return False, "no traffic in fault window (idle)"
    bp, fp = base["p95"], fault["p95"]
    if latency_degraded(bp, fp):
        return True, (f"p95 {fp:.3f} > {DEGRADATION_FACTOR:g}x{bp:.3f} "
                      f"and +{fp - bp:.3f} >= {DEGRADATION_FLOOR_MS:g}ms")
    if bp and bp > 0 and fp is not None and fp > DEGRADATION_FACTOR * bp:
        # Relative condition met, absolute floor not. Name it: under the pre-amendment
        # rule this service WOULD have been counted.
        return False, (f"BELOW FLOOR: {fp:.3f} is {fp / bp:.2f}x{bp:.3f} but only "
                       f"+{fp - bp:.3f} ms (< {DEGRADATION_FLOOR_MS:g} ms)")
    be, fe = (base["err"] or 0.0), (fault["err"] or 0.0)
    if fe > be + ERROR_RATE_ABS_THRESHOLD:
        return True, f"err {fe:.3f} > {be:.3f}+{ERROR_RATE_ABS_THRESHOLD}"
    return False, "within tolerance"


def analyse(run_path: Path) -> dict:
    d = json.loads(run_path.read_text(encoding="utf-8"))
    spans = d.get("raw_spans")
    if not isinstance(spans, dict) or "baseline_window" not in spans:
        print(f"  SKIP {run_path.name}: no persisted baseline+fault spans "
              f"(written before the v3 change)")
        return {}

    base_tr = load_spans(spans["baseline_window"]["path"])
    fault_tr = load_spans(spans["fault_window"]["path"])
    faulted = d["service"]
    G = nx.node_link_graph(
        json.loads(Path(ROOT / APPS[d["app"]]["graph"].relative_to(ROOT))
                   .read_text(encoding="utf-8")), edges="edges")
    anc, desc = nx.ancestors(G, faulted), nx.descendants(G, faulted)

    def relation(s: str) -> str:
        return ("FAULTED" if s == faulted else "ANCESTOR" if s in anc
                else "DESCENDANT" if s in desc else "UNRELATED")

    print("=" * 112)
    print(f"{run_path.name}")
    print(f"  app={d['app']}  faulted={faulted}  fault={d['fault_type']}  "
          f"rep={d['repetition']}")
    print(f"  baseline spans file: {spans['baseline_window']['trace_count']} traces   "
          f"fault spans file: {spans['fault_window']['trace_count']} traces")
    print(f"  ancestors={sorted(anc)}  descendants={sorted(desc)}")
    print("=" * 112)

    services = app_services(base_tr) or app_services(fault_tr)
    rows = []
    print(f"{'service':<15}{'rel':<11}"
          f"{'OLD base':>10}{'OLD fault':>11}{'OLD flag':>10}   "
          f"{'NEW base':>10}{'NEW fault':>11}{'NEW flag':>10}")
    print("-" * 112)
    old_set, new_set = set(), set()
    for s in services:
        ob, of = measure(base_tr, s, False), measure(fault_tr, s, False)
        nb, nf = measure(base_tr, s, True), measure(fault_tr, s, True)
        of_flag, of_why = flagged(ob, of)
        nf_flag, nf_why = flagged(nb, nf)
        if s != faulted:
            if of_flag:
                old_set.add(s)
            if nf_flag:
                new_set.add(s)
        rows.append({"service": s, "relation": relation(s),
                     "old_base_p95": ob["p95"], "old_fault_p95": of["p95"],
                     "old_flagged": of_flag, "old_reason": of_why,
                     "new_base_p95": nb["p95"], "new_fault_p95": nf["p95"],
                     "new_flagged": nf_flag, "new_reason": nf_why,
                     "new_base_err": nb["err"], "new_fault_err": nf["err"],
                     "fault_traces": of["n_traces"], "fault_spans": nf.get("n_spans")})
        fmt = lambda v: ("     -" if v is None else
                         (f"{v:10.3f}" if v < 1.0 else f"{v:10.2f}"))
        print(f"{s:<15}{relation(s):<11}"
              f"{fmt(ob['p95'])}{fmt(of['p95'])}{('YES' if of_flag else '.'):>10}   "
              f"{fmt(nb['p95'])}{fmt(nf['p95'])}{('YES' if nf_flag else '.'):>10}")

    print()
    print(f"  OLD flagged set ({len(old_set)}): {sorted(old_set)}")
    print(f"  NEW flagged set ({len(new_set)}): {sorted(new_set)}")
    gone = sorted(old_set - new_set)
    stayed = sorted(new_set)
    added = sorted(new_set - old_set)
    print(f"  dropped by the fix  : {gone}")
    print(f"  still flagged       : {stayed}")
    print(f"  newly flagged       : {added}")

    def adu(names):
        c = {"ANCESTOR": 0, "DESCENDANT": 0, "UNRELATED": 0}
        for n in names:
            c[relation(n)] += 1
        return f"{c['ANCESTOR']}/{c['DESCENDANT']}/{c['UNRELATED']}"

    print(f"  A/D/U  OLD={adu(old_set)}   NEW={adu(new_set)}")
    print(f"  (the run itself recorded A/D/U = {d.get('ancestor_affected_count')}/"
          f"{d.get('descendant_affected_count')}/{d.get('unrelated_affected_count')} "
          f"and flagged {sorted(x for x in d.get('downstream_affected_services','').split(',') if x)})")

    if stayed:
        print()
        print("  WHY each still-flagged service fires under the CORRECTED definition:")
        for r in rows:
            if r["service"] in new_set:
                print(f"    {r['service']:<15} {r['relation']:<11} "
                      f"own-span p95 {r['new_base_p95']:.2f} -> {r['new_fault_p95']:.2f} ms "
                      f"({(r['new_fault_p95'] / r['new_base_p95']):.2f}x), "
                      f"err {r['new_base_err']:.3f} -> {r['new_fault_err']:.3f}  "
                      f"[{r['new_reason']}]")
    print()
    return {"run": run_path.name, "old": sorted(old_set), "new": sorted(new_set),
            "rows": rows}


def main(argv: list[str]) -> int:
    if argv:
        paths = [Path(a) for a in argv]
    else:
        paths = [Path(p) for p in sorted(glob.glob(str(
            ROOT / "data" / "pilot" / "pilot_hotelreservation_search_latency_*.json")))]
    if not paths:
        print("SOURCE NOT FOUND: no matching run files")
        return 1

    out = [analyse(p) for p in paths]
    out = [o for o in out if o]
    if len(out) > 1:
        print("=" * 112)
        print("REPRODUCIBILITY ACROSS REPS")
        print("=" * 112)
        for o in out:
            print(f"  {o['run'][:70]:<72} NEW={o['new']}")
        sets = {tuple(o["new"]) for o in out}
        print(f"  identical NEW flagged set across {len(out)} reps: "
              f"{'YES' if len(sets) == 1 else 'NO -- ' + str(sets)}")

    dest = ROOT / "_audit" / "Q3_LIVE_VALIDATION.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n[WROTE] {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
