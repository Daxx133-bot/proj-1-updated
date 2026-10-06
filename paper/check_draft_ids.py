"""
check_draft_ids.py -- verify the drafting markers in paper/draft/*.md.

Three checks:

  1. Every %[id:x] marker names a claim_id that exists in paper/numbers.csv. A dangling
     marker is a hard error: it means a number in the prose has no source.
  2. For each marker, the value numbers.csv holds appears somewhere in the preceding run of
     prose. This catches a number being edited in the text without its id being updated, or
     an id being attached to the wrong number. Reported as a warning, because many markers
     legitimately attach to a qualitative statement ("no run was censored", "equals the
     predictor for every service") rather than to a printed digit.
  3. Numeric tokens in a paragraph that carries no marker of any kind are listed, so that an
     untraced number cannot slip through unnoticed.

Markers of the form %[fig:...], %[tbl:...] and %[prereg:...] are recognised and skipped:
CLAIMS_LEDGER.md records those as deliberate exemptions for pilot-derived values, values
carried in a table file, and design decisions that have no number.

Run: python paper/check_draft_ids.py
"""
from __future__ import annotations

import os
import re
import sys

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, "draft")
NUMBERS = os.path.join(HERE, "numbers.csv")

MARKER = re.compile(r"%\[id:([a-z0-9_]+)\]")
OTHER_MARKER = re.compile(r"%\[(?:fig|prereg|src|tbl):[^\]]*\]")
NUMBER = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?(?![\w])")
SECTION_REF = re.compile(r"(?:§|Section |Table |Figure )\s*\d+(?:\.\d+)?")

# Numerals that are structural rather than measurements: section, table and figure numbers,
# ordinary small-integer enumeration in prose, and calendar years.
ALLOWED_BARE = {str(i) for i in range(0, 14)} | {
    "2026", "1.0", "2.0", "0.05", "1.4", "2.4", "2.5", "25", "10", "95", "99",
}


def main() -> int:
    df = pd.read_csv(NUMBERS, dtype=str).fillna("")
    values = dict(zip(df.claim_id, df.value))

    files = sorted(f for f in os.listdir(DRAFT)
                   if f.endswith(".md") and not f.startswith("outline_"))
    dangling, mismatched, untraced = [], [], []
    total, cited = 0, set()

    for fn in files:
        text = open(os.path.join(DRAFT, fn), encoding="utf-8").read()
        body = "\n".join(l for l in text.splitlines() if not l.startswith(">"))
        body = body.replace("−", "-")        # prose uses the Unicode minus sign

        for m in MARKER.finditer(body):
            total += 1
            cid = m.group(1)
            cited.add(cid)
            if cid not in values:
                dangling.append((fn, cid))
                continue
            val = values[cid].replace(",", "")
            if not re.match(r"^[-+]?[\d.]+$", val):
                continue                          # yes/no/textual value, nothing to match
            window = body[max(0, m.start() - 320):m.start()]
            seen = [t.replace(",", "") for t in NUMBER.findall(window)]
            hit = False
            for t in seen:
                if t == val:
                    hit = True
                    break
                try:
                    if abs(float(t) - float(val)) < 1e-9:
                        hit = True
                        break
                except ValueError:
                    pass
            if not hit:
                mismatched.append((fn, cid, values[cid], seen[-6:]))

        for para in re.split(r"\n\s*\n", body):
            stripped = para.lstrip()
            if not stripped or stripped.startswith(("|", "#", "```")):
                continue
            if MARKER.search(para) or OTHER_MARKER.search(para):
                continue
            clean = SECTION_REF.sub(" ", para)
            for tok in NUMBER.findall(clean):
                if tok.replace(",", "") in ALLOWED_BARE:
                    continue
                untraced.append((fn, tok, " ".join(para.split())[:90]))

    print("draft files checked : %d (%s)" % (len(files), ", ".join(files)))
    print("id markers found    : %d" % total)
    print("distinct ids cited  : %d of %d in numbers.csv" % (len(cited), len(values)))

    ok = True
    if dangling:
        ok = False
        print("\nFAIL: %d marker(s) name an id absent from numbers.csv:" % len(dangling))
        for fn, cid in dangling:
            print("   %s: %s" % (fn, cid))
    if mismatched:
        print("\nREVIEW: %d marker(s) whose value is not printed in the preceding prose."
              % len(mismatched))
        print("        Expected where the marker backs a qualitative statement; check the "
              "rest.")
        for fn, cid, val, seen in mismatched:
            print("   %-22s %-38s = %-10s nearby: %s" % (fn, cid, val, seen))
    if untraced:
        print("\nFAIL: %d numeric token(s) in a paragraph with no marker of any kind:"
              % len(untraced))
        ok = False
        for fn, tok, line in untraced:
            print("   %s: %s in \"%s\"" % (fn, tok, line))

    print("\n%s" % ("OK: every id marker resolves and every numeric paragraph is traced."
                   if ok else "DRAFT ID CHECK FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
