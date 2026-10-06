"""
build_all.py -- regenerate every artifact under paper/ in dependency order, then index them.

    build_numbers.py   analysis/final/*.csv        -> numbers.csv
    emit_macros.py     numbers.csv                 -> numbers.tex, numbers.json
    make_tables.py     analysis/final/*.csv        -> tables/*.csv, tables/*.md
    make_figures.py    analysis/final/*.csv, spans -> figures/*.png, *.pdf, *_data.csv
    check_ledger.py    CLAIMS_LEDGER.md + numbers.csv -> pass/fail

Finally writes paper/INDEX.csv, one row per file under paper/, naming the script that
produced it. A failing ledger check fails the build.

Run: python paper/build_all.py
"""
from __future__ import annotations

import os
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

STEPS = ["build_numbers.py", "emit_macros.py", "make_tables.py", "make_figures.py",
         "check_ledger.py"]

PRODUCER = {
    "numbers.csv": "paper/build_numbers.py",
    "numbers.tex": "paper/emit_macros.py",
    "numbers.json": "paper/emit_macros.py",
    "INDEX.csv": "paper/build_all.py",
    "CLAIMS_LEDGER.md": "hand-written, validated by paper/check_ledger.py",
}


def main() -> int:
    for step in STEPS:
        print("\n=== %s ===" % step)
        r = subprocess.run([sys.executable, os.path.join(HERE, step)], cwd=REPO)
        if r.returncode != 0:
            print("\nBUILD FAILED at %s" % step)
            return r.returncode

    rows = []
    for root, _, files in os.walk(HERE):
        for fn in sorted(files):
            if fn.endswith((".pyc",)) or "__pycache__" in root:
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, REPO).replace("\\", "/")
            base = os.path.relpath(full, HERE).replace("\\", "/")
            if fn.endswith(".py"):
                produced_by = "source"
            elif base.startswith("tables/"):
                produced_by = "paper/make_tables.py"
            elif base.startswith("figures/"):
                produced_by = "paper/make_figures.py"
            elif base.startswith("draft/"):
                produced_by = ("hand-written, markers validated by "
                               "paper/check_draft_ids.py")
            else:
                produced_by = PRODUCER.get(fn, "unknown")
            rows.append({"file": rel, "produced_by": produced_by,
                         "bytes": os.path.getsize(full)})
    df = pd.DataFrame(rows).sort_values("file")
    df.to_csv(os.path.join(HERE, "INDEX.csv"), index=False)
    print("\nwrote paper/INDEX.csv (%d files)" % len(df))
    unknown = df[df.produced_by == "unknown"]
    if not unknown.empty:
        print("WARNING: no producer recorded for:\n%s" % unknown.file.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
