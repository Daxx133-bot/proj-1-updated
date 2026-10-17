"""
check_docx_numbers.py -- audit every numeric token in paper/manuscript.docx. Fixes nothing.

Each token is classified, in this order, as one of:

  section number      in a heading, or written as §n / §n.m
  table/figure number in "Table N", "Tables N and M", "Figure N", or a caption label
  reference number    [n] where n is a rendered reference
  deviation number    in "Deviation N" / "deviations N, M and K" / "amendment N" (a label)
  year                a four-digit integer from 1900 to 2100
  numbers.csv value   equal to a numbers.csv value, allowing display rounding: the token
                      matches if some numeric value_raw, formatted to the token's number of
                      decimals, gives the token; string values (dates, names, hashes) are
                      matched as whole substrings before tokenising
  table cell          a cell of a rendered table whose text is identical to the same cell of
                      the paper/tables/*.csv file named by the table's caption
  UNMATCHED           none of the above

Every UNMATCHED token is written to paper/number_audit.txt with its sentence (prose) or its
table row (tables) and the section it sits in. A match is evidence that a number has a
traced source, not proof that it is attached to the right claim: small integers match many
values.

Run: python paper/check_docx_numbers.py
"""
from __future__ import annotations

import collections
import csv
import os
import re
import sys

import docx
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DOCX = os.path.join(HERE, "manuscript.docx")
OUT = os.path.join(HERE, "number_audit.txt")

NUMBER = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?(?![\w])")
MENTION = re.compile(r"\b(?:Tables?|Figures?)\s+\d+(?:\s*(?:,|and)\s*\d+)*")
CAPTION = re.compile(r"^(?:Table|Figure)\s+\d+\.")
DEVIATION = re.compile(r"\b(?:[Dd]eviations?|[Aa]mendments?)\s+\d+(?:\s*(?:,|and)\s*\d+)*")
SECTION = re.compile(r"§\s*\d+(?:\.\d+)*")
REFNUM = re.compile(r"\[\d+\]")
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(`*\[])")


def norm(s):
    return s.replace("−", "-").replace(" ", " ").replace(" ", " ")


def load_numbers():
    df = pd.read_csv(os.path.join(HERE, "numbers.csv"), dtype=str, keep_default_na=False)
    nums, strings = [], set()
    for v, raw in zip(df["value"], df["value_raw"]):
        try:
            nums.append(float(raw))
        except ValueError:
            if re.search(r"\d", v):
                strings.add(v)
                m = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})$", v)
                if m:
                    strings.update(m.groups())
    return nums, sorted(strings, key=len, reverse=True)


def numeric_match(tok, nums):
    t = tok.replace(",", "")
    try:
        tv = float(t)
    except ValueError:
        return False
    d = len(t.split(".")[1]) if "." in t else 0
    target = format(tv, ".%df" % d)
    for r in nums:
        if r != r:
            continue
        if abs(r - tv) < 1e-12 or format(r, ".%df" % d) == target:
            return True
    return False


def spans(regex, text):
    return [m.span() for m in regex.finditer(text)]


def inside(pos, ss):
    return any(a <= pos < b for a, b in ss)


def classify_text(text, is_heading, nums, strings, nref):
    """Yield (token, category) for one sentence or heading."""
    text = norm(text)
    masked = text
    out = []
    for s in strings:
        if s in masked:
            out.append((s, "numbers.csv value (string)"))
            masked = masked.replace(s, " " * len(s))
    if is_heading:
        for m in NUMBER.finditer(masked):
            out.append((m.group(0), "section number"))
        return out
    sec, men, dev, ref = (spans(SECTION, masked), spans(MENTION, masked),
                          spans(DEVIATION, masked), spans(REFNUM, masked))
    cap = spans(CAPTION, masked)
    for m in NUMBER.finditer(masked):
        tok, pos = m.group(0), m.start()
        if inside(pos, sec):
            cat = "section number"
        elif inside(pos, men) or inside(pos, cap):
            cat = "table/figure number"
        elif inside(pos, ref) and tok.isdigit() and 1 <= int(tok) <= nref:
            cat = "reference number"
        elif inside(pos, dev):
            cat = "deviation number"
        elif re.fullmatch(r"\d{4}", tok) and 1900 <= int(tok) <= 2100:
            cat = "year"
        elif numeric_match(tok, nums):
            cat = "numbers.csv value"
        else:
            cat = "UNMATCHED"
        out.append((tok, cat))
    return out


def table_sources():
    rows = list(csv.reader(open(os.path.join(HERE, "tables", "tables_index.csv"),
                                encoding="utf-8", newline="")))
    h = rows[0]
    return {r[h.index("shows")]: os.path.join(HERE, "tables", r[h.index("table")] + ".csv")
            for r in rows[1:]}


def main():
    d = docx.Document(DOCX)
    nums, strings = load_numbers()
    shows = table_sources()
    nref = 0
    body = d.element.body
    counts = collections.Counter()
    unmatched = []
    section = ""
    last_caption = ""
    pmap = {p._p: p for p in d.paragraphs}
    tmap = {t._tbl: t for t in d.tables}

    for el in body.iterchildren():
        if el in pmap:
            p = pmap[el]
            txt = p.text.strip()
            if not txt:
                continue
            heading = p.style.name.startswith("Heading") or p.style.name == "Title"
            if heading:
                section = txt
                if txt == "References":
                    pass
            if CAPTION.match(txt):
                last_caption = txt
            if re.match(r"^\[\d+\] ", txt):
                nref += 1
            for sent in ([txt] if heading else SENT.split(txt)):
                for tok, cat in classify_text(sent, heading, nums, strings, nref):
                    counts[cat] += 1
                    if cat == "UNMATCHED":
                        unmatched.append((section, tok, sent))
        elif el in tmap:
            t = tmap[el]
            cap = re.sub(r"^Table\s+\d+\.\s*", "", last_caption)
            src = shows.get(cap)
            srows = (list(csv.reader(open(src, encoding="utf-8", newline="")))
                     if src and os.path.isfile(src) else None)
            for i, row in enumerate(t.rows):
                cells = [c.text for c in row.cells]
                for j, ct in enumerate(cells):
                    toks = [m.group(0) for m in NUMBER.finditer(norm(ct))]
                    if not toks:
                        continue
                    same = (srows is not None and i < len(srows) and j < len(srows[i])
                            and srows[i][j] == ct)
                    for tok in toks:
                        cat = "table cell" if same else (
                            "numbers.csv value" if numeric_match(tok, nums) else "UNMATCHED")
                        counts[cat] += 1
                        if cat == "UNMATCHED":
                            unmatched.append((section + " / " + last_caption.split(".")[0],
                                              tok, " | ".join(cells)))

    L = ["number_audit.txt -- written by paper/check_docx_numbers.py from paper/manuscript.docx",
         "Nothing was changed. A match means the number has a traced source of the kind",
         "named, not that it is attached to the right claim; small integers match many values.",
         "", "Tokens by category:"]
    for cat in ("numbers.csv value", "numbers.csv value (string)", "table cell",
                "section number", "table/figure number", "deviation number", "year",
                "reference number", "UNMATCHED"):
        L.append("  %-28s %6d" % (cat, counts[cat]))
    L += ["", "UNMATCHED tokens (%d), each with its sentence or table row:" % len(unmatched), ""]
    for i, (sec, tok, ctx) in enumerate(unmatched, 1):
        L.append("%3d. [%s] token %s" % (i, sec, tok))
        L.append("     %s" % ctx)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote paper/number_audit.txt: %d tokens, %d unmatched"
          % (sum(counts.values()), len(unmatched)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
