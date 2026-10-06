"""
audit_baseline_sanity.py -- was each run's BASELINE actually a steady state?

A pre-analysis gate, of the same kind as audit_run_topology.py. The baseline window is
fault-free by construction, so within one application every run's baseline should look
alike. When one does not, something was wrong with the system before the fault was even
injected, and every ratio computed from that baseline is distorted.

This exists because of a real incident (2026-09-26): a `pumba netem delay` applied to
`compose-post-service` did not expire with its --duration. It stayed active for the 10
Social Network latency runs that followed, inflating their gateway baseline p95 from ~55 ms
to ~3100-4050 ms. The distortion was systematic, not random: because the faulted service's
ancestors were ALREADY degraded in the baseline, their fault-window p95 failed to reach 2x
that inflated baseline, and `ancestor_affected_count` -- the primary outcome -- came out
lower by exactly 2 in most of those runs. Nothing in the per-run records looked anomalous
on its own; only the cross-run comparison exposed it.

Method: robust outlier detection per (app) on the gateway baseline p95, using the median
and the median absolute deviation, plus an absolute ratio-to-median cut. No distributional
assumption, and the median is not dragged by the contaminated runs themselves.

Usage:
    python tools/audit_baseline_sanity.py [--ratio 3.0]
"""

from __future__ import annotations

import argparse
import glob
import json
import statistics as stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_runs() -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(ROOT / "data" / "campaign" / "runs" / "*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        d["_file"] = Path(f).name
        out.append(d)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratio", type=float, default=3.0,
                    help="flag a run whose baseline p95 exceeds this multiple of the "
                         "app median (default 3.0)")
    args = ap.parse_args()

    runs = load_runs()
    if not runs:
        print("SOURCE NOT FOUND: no campaign runs on disk")
        return 1

    flagged = []
    print("=" * 100)
    print("BASELINE SANITY GATE")
    print("=" * 100)
    for app in sorted({r["app"] for r in runs}):
        sub = [r for r in runs if r["app"] == app and r.get("baseline_p95_ms") is not None]
        vals = [r["baseline_p95_ms"] for r in sub]
        med = stat.median(vals)
        mad = stat.median([abs(v - med) for v in vals]) or 1e-9
        print(f"\n{app}:  n={len(sub)}  median={med:.2f} ms  MAD={mad:.3f} ms  "
              f"min={min(vals):.2f}  max={max(vals):.2f}")
        bad = [r for r in sub if r["baseline_p95_ms"] > args.ratio * med]
        if not bad:
            print(f"  no run exceeds {args.ratio:g}x the median")
            continue
        print(f"  {len(bad)} run(s) exceed {args.ratio:g}x the median "
              f"({args.ratio * med:.1f} ms):")
        for r in sorted(bad, key=lambda x: x["timestamp"]):
            rob = (r["baseline_p95_ms"] - med) / mad
            print(f"    {r['timestamp'][11:19]}  {r['service']:<24}{r['fault_type']:<9}"
                  f"rep{r['repetition']}  baseline_p95={r['baseline_p95_ms']:.1f} ms  "
                  f"({r['baseline_p95_ms'] / med:.0f}x median, {rob:.0f} MAD)")
            flagged.append(r)

    print()
    print("=" * 100)
    print(f"VERDICT: {len(flagged)} of {len(runs)} runs have a non-steady-state baseline")
    print("=" * 100)
    if flagged:
        print("  These runs must NOT be analysed. A distorted baseline distorts every ratio")
        print("  computed against it, and the distortion is directional: an inflated")
        print("  baseline makes the fault look smaller, so degradation is UNDER-counted.")
        print("  Quarantine them, reset them in the manifest, and collect them again.")
    else:
        print("  Every baseline is consistent with its application's steady state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
