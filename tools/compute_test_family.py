"""
compute_test_family.py -- derive the confirmatory test-family size from the graphs.

The BH-FDR family size must not be typed by hand: a predictor that is constant within an
architecture's analysis set has an undefined Spearman rho, and counting it would inflate
the family and weaken the correction for every real test. This script counts only the
(predictor, architecture) pairs that can actually be tested, reading
data/analysis/predictor_table.csv (itself produced by tools/build_predictor_table.py).

Usage: python tools/compute_test_family.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.build_predictor_table import PREDICTORS  # noqa: E402

TABLE = ROOT / "data" / "analysis" / "predictor_table.csv"
OUTCOMES = ["ancestor_affected_count", "T_rec"]          # confirmatory outcomes
CONFIRMATORY_FAULT = "kill"
REPLICATION_FAULT = "latency"


def main() -> int:
    if not TABLE.exists():
        print(f"SOURCE NOT FOUND: {TABLE} -- run tools/build_predictor_table.py first")
        return 1
    df = pd.read_csv(TABLE)
    df = df[df["in_analysis_set"]]

    print("=" * 84)
    print("TESTABLE (predictor x architecture) PAIRS")
    print("=" * 84)
    print(f"{'predictor':<26}" + "".join(f"{a[:16]:>18}" for a in sorted(df.architecture.unique())))
    print("-" * 84)

    testable = 0
    dead = []
    for p in PREDICTORS:
        cells = []
        for a in sorted(df.architecture.unique()):
            lv = df[df.architecture == a][p].nunique()
            ok = lv >= 2
            testable += ok
            if not ok:
                dead.append((p, a))
            cells.append(f"{('levels=' + str(lv)) if ok else 'CONSTANT -> drop':>18}")
        print(f"{p:<26}" + "".join(cells))

    n_arch = df.architecture.nunique()
    print()
    print(f"  predictors                      : {len(PREDICTORS)}")
    print(f"  architectures                   : {n_arch}")
    print(f"  naive pairs                     : {len(PREDICTORS) * n_arch}")
    print(f"  dropped as constant             : {len(dead)}  {dead}")
    print(f"  testable pairs                  : {testable}")

    conf = testable * len(OUTCOMES)
    print()
    print("=" * 84)
    print("FAMILY SIZES")
    print("=" * 84)
    print(f"  confirmatory family ({CONFIRMATORY_FAULT} faults):")
    print(f"    {testable} testable pairs x {len(OUTCOMES)} outcomes {OUTCOMES} = {conf} tests")
    print(f"    -> Benjamini-Hochberg at q=0.05 across all {conf}")
    print(f"  replication family ({REPLICATION_FAULT} faults):")
    print(f"    same structure = {conf} tests, corrected SEPARATELY at q=0.05")
    print()
    print(f"  If instead both fault types were pooled into ONE confirmatory family:")
    print(f"    {conf * 2} tests -- every per-test threshold roughly halves.")
    print()
    print("  Rationale for splitting rather than pooling: the hypothesis is about how a")
    print("  service FAILING propagates, and kill is the canonical failure. Latency is a")
    print("  preregistered replication under a different failure mode with a different")
    print("  primary indicator (delta-p95 rather than error rate), so it is a separate")
    print("  question rather than 44 more tests of the same one. This split is declared")
    print("  BEFORE any campaign data exists and may not be revised afterwards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
