"""
audit_run_topology.py -- did every expected application service appear during each run?

The campaign's health check verifies that Jaeger answers and the gateway answers. It does
NOT verify that all application services are up, so a stack that has silently lost a
service still passes, and runs against that degraded topology get marked `done` with
invalid outcomes.

This script detects that after the fact, from the persisted BASELINE spans: the baseline
window is fault-free by construction, so every application service that receives traffic in
normal operation must appear in it. A service missing from a baseline window was absent or
dead before the fault was even injected.

Usage:
    python tools/audit_run_topology.py
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

from measurement.metrics_collector import span_service_map  # noqa: E402
from tools.run_pilot import APPS  # noqa: E402

INFRA = ("jaeger", "mongo", "redis", "memcached", "consul")


def expected(app: str) -> set[str]:
    G = nx.node_link_graph(
        json.loads(APPS[app]["graph"].read_text(encoding="utf-8")), edges="edges")
    return set(G.nodes())


def main() -> int:
    files = sorted(glob.glob(str(ROOT / "data" / "campaign" / "runs" / "*.json")))
    if not files:
        print("SOURCE NOT FOUND: no campaign runs on disk")
        return 1

    exp = {app: expected(app) for app in APPS}
    bad = []
    print("=" * 104)
    print("PER-RUN TOPOLOGY AUDIT (from fault-free baseline windows)")
    print("=" * 104)
    print(f"{'app':<16}{'service':<24}{'fault':<9}{'time':<10}{'traces':>7}  missing from baseline")
    print("-" * 104)
    for f in files:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        rs = d.get("raw_spans") or {}
        if "baseline_window" not in rs:
            continue
        with gzip.open(ROOT / rs["baseline_window"]["path"], "rt", encoding="utf-8") as fh:
            tr = json.load(fh)["traces"]
        present = {s for t in tr for s in span_service_map(t).values()
                   if s and not any(i in s.lower() for i in INFRA)}
        missing = sorted(exp[d["app"]] - present)
        if missing:
            bad.append((Path(f).name, d, missing))
        print(f"{d['app'][:14]:<16}{d['service']:<24}{d['fault_type']:<9}"
              f"{d['timestamp'][11:19]:<10}{len(tr):>7}  "
              f"{', '.join(missing) if missing else '-'}")

    print()
    print("=" * 104)
    print(f"VERDICT: {len(bad)} of {len(files)} runs ran against an INCOMPLETE topology")
    print("=" * 104)
    for name, d, missing in bad:
        rec = "CENSORED" if d.get("recovery_censored") else f"{d.get('recovery_time_s')}s"
        print(f"  {d['app']}|{d['service']}|{d['fault_type']}|{d['repetition']}")
        print(f"    missing: {missing}")
        print(f"    recorded A/D/U = {d.get('ancestor_affected_count')}/"
              f"{d.get('descendant_affected_count')}/{d.get('unrelated_affected_count')}"
              f"   T_rec = {rec}")
        print(f"    file: {name}")
    if bad:
        print()
        print("  These runs are INVALID. A missing service cannot be flagged as degraded,")
        print("  and its absence also removes load from the services that call it, so both")
        print("  blast radius and T_rec are affected. Neither is recoverable by")
        print("  recomputation -- the traffic that would have existed was never generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
