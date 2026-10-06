"""
check_threshold_floor.py -- is the 2x relative degradation threshold meaningful at the
per-service scale?

Background
----------
The blast-radius rule flags a service when

    p95(service, fault) > DEGRADATION_FACTOR * p95(service, baseline)

with DEGRADATION_FACTOR = 2.0 and, BEFORE amendment 1 (2026-09-26), no absolute floor.
This script is what established that the floor was needed, and is kept as the standing
check on it. That threshold was safe while "a service's p95"
was the END-TO-END trace p95 (tens of milliseconds for every service): sub-millisecond
noise could never produce a 2x move.

The Q3 fix (v3 §6.1) made percentiles per-service, which is correct -- and which moved many
services into the 0.02-0.60 ms range, where a purely multiplicative threshold has no
physical meaning. This script measures that directly from persisted baseline spans.

The fix is `DEGRADATION_FLOOR_MS` (currently 1.0 ms), required as a SECOND condition
alongside the 2x factor. Re-running this script after collecting more baseline windows
checks that the floor still clears the observed baseline-only drift.

Two questions, both answered from logged data only:

  1. How many services have a baseline per-service p95 below 1 ms?
  2. For services measured in more than one BASELINE window -- i.e. with no fault present
     at all -- does baseline-to-baseline variation already exceed the 2x threshold? If it
     does, the rule produces false "degraded" verdicts by construction.

Usage:
    python tools/check_threshold_floor.py
"""

from __future__ import annotations

import glob
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from measurement.metrics_collector import (  # noqa: E402
    DEGRADATION_FACTOR,
    DEGRADATION_FLOOR_MS,
    compute_latency_percentiles,
    span_service_map,
)

INFRA = ("jaeger", "mongo", "redis", "memcached", "consul")
SUB_MS = 1.0
# Jaeger stores span durations in whole microseconds. Percentiles are no longer rounded
# before comparison (amendment 1), but 0.01 ms remains the granularity at which these
# values were historically stored and displayed, so it is the reference scale here.
QUANTUM_MS = 0.01


def baseline_windows() -> list[tuple[str, str, Path]]:
    """(app, run_id, baseline span file) for every run that persisted one."""
    out = []
    for f in sorted(glob.glob(str(ROOT / "data" / "campaign" / "runs" / "*.json")) +
                    glob.glob(str(ROOT / "data" / "pilot" / "pilot_*.json"))):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        rs = d.get("raw_spans")
        if isinstance(rs, dict) and "baseline_window" in rs:
            out.append((d["app"], Path(f).name, ROOT / rs["baseline_window"]["path"]))
    return out


def per_service_p95(span_file: Path) -> dict[str, float]:
    with gzip.open(span_file, "rt", encoding="utf-8") as fh:
        traces = json.load(fh)["traces"]
    svcs = sorted({s for t in traces for s in span_service_map(t).values()
                   if s and not any(i in s.lower() for i in INFRA)})
    out = {}
    for s in svcs:
        sub = [t for t in traces if s in span_service_map(t).values()]
        out[s] = compute_latency_percentiles(sub, service=s)["p95_ms"]
    return out


def main() -> int:
    wins = baseline_windows()
    if not wins:
        print("SOURCE NOT FOUND: no run has persisted baseline spans yet")
        return 1

    obs: dict[tuple[str, str], list[float]] = {}
    for app, _run, f in wins:
        for svc, p95 in per_service_p95(f).items():
            obs.setdefault((app, svc), []).append(p95)

    print("=" * 92)
    print(f"BASELINE per-service p95, across {len(wins)} fault-free baseline windows")
    print("=" * 92)
    print(f"{'app':<17}{'service':<24}{'n':>3}{'min':>8}{'max':>8}"
          f"{'max/min':>9}{'quanta':>8}  note")
    print("-" * 92)

    sub_ms = 0
    self_tripping = []
    for (app, svc), v in sorted(obs.items()):
        lo, hi = min(v), max(v)
        ratio = (hi / lo) if lo > 0 else float("inf")
        quanta = lo / QUANTUM_MS if lo > 0 else 0
        notes = []
        if lo < SUB_MS:
            sub_ms += 1
            notes.append("sub-ms")
        if len(v) > 1 and ratio > DEGRADATION_FACTOR:
            self_tripping.append((app, svc, lo, hi, ratio))
            notes.append(f"BASELINE ALONE EXCEEDS {DEGRADATION_FACTOR:g}x")
        print(f"{app[:15]:<17}{svc:<24}{len(v):>3}{lo:>8.2f}{hi:>8.2f}"
              f"{ratio:>9.2f}{quanta:>8.1f}  {', '.join(notes)}")

    print()
    print(f"  services with baseline per-service p95 < {SUB_MS:g} ms : "
          f"{sub_ms} of {len(obs)}")
    print(f"  services whose BASELINE-only variation already exceeds the "
          f"{DEGRADATION_FACTOR:g}x threshold: {len(self_tripping)}")
    for app, svc, lo, hi, ratio in self_tripping:
        print(f"    {app:<17}{svc:<24}{lo:.2f} -> {hi:.2f} ms  ({ratio:.2f}x) "
              f"with NO fault present")

    print()
    print("=" * 92)
    print("VERDICT")
    print("=" * 92)
    if self_tripping:
        print("  The purely multiplicative threshold is NOT SAFE at this scale. At least one")
        print("  service exceeds it between two fault-free windows, so the rule will report")
        print("  'degraded' for services nothing happened to. Any count built on it -- and")
        print("  ancestor_affected_count is the PRIMARY outcome -- is contaminated.")
        print()
        print("  The error-rate branch of the same rule already carries an absolute floor")
        print("  (+0.05 absolute). The latency branch needs the equivalent.")
    else:
        print("  No baseline-only violation observed in this sample. Note that absence of")
        print("  evidence here is weak: it depends on how many baseline windows exist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
