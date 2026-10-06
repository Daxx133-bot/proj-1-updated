"""
check_ledger.py -- verify paper/CLAIMS_LEDGER.md against paper/numbers.csv.

Two failure modes matter and both are hard errors:

  1. The ledger cites a claim_id that does not exist in numbers.csv -- a dangling citation,
     which would let a manuscript claim point at nothing.
  2. Every claim marked SUPPORTED cites at least one id, or says in the entry why it has no
     numbers.csv id (pilot-derived evidence, for instance).

Backticked tokens that look like file paths, column names or code identifiers are ignored:
only tokens matching a claim_id already present in numbers.csv, or looking like one and
absent from it, are considered.

Run: python paper/check_ledger.py
"""
from __future__ import annotations

import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "CLAIMS_LEDGER.md")
NUMBERS = os.path.join(HERE, "numbers.csv")

# A claim_id is lowercase words joined by underscores. Paths, dotted names and anything
# with uppercase are not claim_ids.
CANDIDATE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")


def data_column_names() -> set:
    """Column names across the analysis outputs. These look like claim_ids but are not."""
    final = os.path.join(os.path.dirname(HERE), "analysis", "final")
    cols = set()
    for fn in os.listdir(final):
        if fn.endswith(".csv"):
            try:
                cols |= set(pd.read_csv(os.path.join(final, fn), nrows=0).columns)
            except Exception:
                pass
    return cols


def main() -> int:
    ids = set(pd.read_csv(NUMBERS).claim_id)
    columns = data_column_names() - ids
    text = open(LEDGER, encoding="utf-8").read()

    ticked = re.findall(r"`([^`]+)`", text)
    cited, dangling = set(), set()
    for tok in ticked:
        tok = tok.strip()
        if "/" in tok or "." in tok or " " in tok:
            continue
        if tok in ids:
            cited.add(tok)
        elif tok in columns:
            continue          # a data column name, not a citation
        elif CANDIDATE.match(tok):
            dangling.add(tok)

    # Claim entries: lines like "**1.2 SUPPORTED** -- ..." up to the next blank-line block.
    entries = re.findall(r"\*\*(\d+\.\d+) (SUPPORTED[^*]*|POST-HOC|UNSUPPORTED)\*\*(.*?)"
                         r"(?=\n\*\*\d+\.\d+ |\n---|\Z)", text, flags=re.S)
    missing_support = []
    for num, mark, body in entries:
        if not mark.startswith("SUPPORTED"):
            continue
        body_ids = [t for t in re.findall(r"`([^`]+)`", body) if t in ids]
        excused = "no numbers.csv id" in body or "No supporting id" in body
        if not body_ids and not excused:
            missing_support.append(num)

    print("claim ids in numbers.csv : %d" % len(ids))
    print("claim ids cited by ledger: %d" % len(cited))
    print("ledger claim entries     : %d" % len(entries))
    marks = {}
    for _, m, _ in entries:
        key = m.split(",")[0].strip()
        marks[key] = marks.get(key, 0) + 1
    for k in sorted(marks):
        print("   %-12s %d" % (k, marks[k]))
    uncited = sorted(ids - cited)
    print("ids defined but not cited: %d" % len(uncited))

    ok = True
    if dangling:
        ok = False
        print("\nFAIL: ledger cites %d id(s) absent from numbers.csv:" % len(dangling))
        for d in sorted(dangling):
            print("   %s" % d)
    if missing_support:
        ok = False
        print("\nFAIL: SUPPORTED claims with no cited id and no stated exemption: %s"
              % ", ".join(missing_support))
    print("\n%s" % ("OK: every cited id resolves and every SUPPORTED claim is backed."
                    if ok else "LEDGER CHECK FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
