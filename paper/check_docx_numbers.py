"""
check_docx_numbers.py -- audit every numeric token in paper/manuscript.docx. Fixes nothing.

Each token is classified, in this order, as one of:

  URL                 a web address (its digits are not numbers of the paper)
  section number      in a heading, or written as §n / §n.m
  table/figure number in "Table N", "Tables N and M", "Figure N", "Fig. N", or a caption label
  reference number    [n] where n is a rendered reference
  deviation number    in "Deviation N" / "deviations N, M and K" / "amendment N" (a label)
  year                a four-digit integer from 1900 to 2100
  numbers.csv value   a token of absolute value 10 or more that equals some numbers.csv
                      value, allowing display rounding (some numeric value_raw, formatted to
                      the token's number of decimals, gives the token); string values
                      (dates, names, hashes) are matched as whole substrings first
  marked in sentence  a token of absolute value below 10 that equals the value of an id
                      whose %[id:...] marker sits in the same sentence of the draft
  WEAK MATCH          a token of absolute value below 10 that equals some numbers.csv value,
                      but not the value of any id marked in its sentence. Small numbers match
                      many unrelated values, so such a match is not evidence of a source.
  table cell          a data cell of paper/submission/Table N.docx whose text is identical
                      to the same cell of the paper/tables/*.csv file named by its title
  table header        a token in a table's header row (column names with units)
  reference entry     a token in the manuscript's reference list (volume, issue, pages,
                      DOI, year), which is rendered from paper/references.csv
  UNMATCHED           none of the above

The docx carries no markers, so the ids marked in each sentence are recovered from the
prose drafts: each draft paragraph is normalised the way paper/build_docx.py renders it,
split into sentences with the same rule used here, and keyed by its text. A docx sentence
with no draft counterpart (a caption, a placeholder) has no marked ids.

Audited files: paper/manuscript.docx, paper/submission/figure_legends.docx and every
paper/submission/Table N.docx. UNMATCHED and WEAK MATCH tokens are written to paper/number_audit.txt with their sentence
(prose) or table row (tables) and the section they sit in.

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
sys.path.insert(0, HERE)
import build_docx as bd  # noqa: E402  (same rendering rules as the build)

DOCX = os.path.join(HERE, "manuscript.docx")
OUT = os.path.join(HERE, "number_audit.txt")

NUMBER = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?(?![\w])")
MENTION = re.compile(r"\b(?:Tables?|Figures?|Figs?\.)\s+\d+(?:\s*(?:,|and)\s*\d+)*")
CAPTION = re.compile(r"^(?:Table|Figure)\s+\d+\.")
DEVIATION = re.compile(r"\b(?:[Dd]eviations?|[Aa]mendments?)\s+\d+(?:\s*(?:,|and)\s*\d+)*")
SECTION = re.compile(r"§\s*\d+(?:\.\d+)*")
REFNUM = re.compile(r"\[\d+\]")
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(`*\[])")
PH = re.compile("(\\d+)")
SMALL = 10.0


def norm(s):
    return s.replace("−", "-").replace(" ", " ").replace(" ", " ")


CITATION = re.compile(r"\[@[^\]]+\]|\((?:[A-Z][^()]*?, (?:19|20)\d\d[a-z]?(?:; )?)+\)")
URL = re.compile(r"https?://\S+")


def key(s):
    """Sentence key shared by the draft side and the docx side. Citations are dropped,
    since the draft writes [@key] where the docx shows (Author, Year)."""
    s = norm(s)
    s = MENTION.sub("#REF#", s)
    s = CITATION.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def unformat(s):
    """Drop the markdown that build_docx renders as run formatting."""
    s = re.sub(r"</?su[bp]>", "", s)
    return s.replace("**", "").replace("`", "").replace("*", "")


def draft_sentence_ids():
    """{normalised sentence text: set of ids marked in that sentence}."""
    out = collections.defaultdict(set)
    for _, prose, _ in bd.SECTIONS + bd.TRAILING:
        if not (prose and os.path.isfile(os.path.join(bd.DRAFT, prose))):
            continue
        for kind, raw in bd.blocks(bd.read(prose)):
            if kind not in ("p", "quote", "li"):
                continue
            ids = []

            def ph(m):
                body = m.group(0).strip()[2:-1]
                ids.append(body[3:] if body.startswith("id:") else None)
                return "%d" % (len(ids) - 1)

            s = bd.MARKER.sub(ph, raw).strip()
            s = re.sub("([.!?])((?:\\d+)+)", r"\2\1", s)
            s = unformat(s)
            # Placeholders were moved in front of sentence-final punctuation above, so they
            # cannot block a sentence boundary.
            for sent in SENT.split(s):
                marked = {ids[int(i)] for i in PH.findall(sent) if ids[int(i)]}
                out[key(PH.sub("", sent))] |= marked
    return out


def load_numbers():
    df = pd.read_csv(os.path.join(HERE, "numbers.csv"), dtype=str, keep_default_na=False)
    nums, strings, by_id = [], set(), {}
    for cid, v, raw in zip(df["claim_id"], df["value"], df["value_raw"]):
        try:
            nums.append(float(raw))
            by_id[cid] = float(raw)
        except ValueError:
            if re.search(r"\d", v):
                strings.add(v)
                m = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})$", v)
                if m:
                    strings.update(m.groups())
    return nums, sorted(strings, key=len, reverse=True), by_id


def numeric_match(tok, values):
    t = tok.replace(",", "")
    try:
        tv = float(t)
    except ValueError:
        return False
    d = len(t.split(".")[1]) if "." in t else 0
    target = format(tv, ".%df" % d)
    for r in values:
        if r != r:
            continue
        if abs(r - tv) < 1e-12 or format(r, ".%df" % d) == target:
            return True
    return False


def spans(regex, text):
    return [m.span() for m in regex.finditer(text)]


def inside(pos, ss):
    return any(a <= pos < b for a, b in ss)


def classify_text(text, is_heading, nums, strings, nref, marked_values):
    """Yield (token, category) for one sentence or heading."""
    text = norm(text)
    masked = text
    out = []
    for s in strings:
        if s in masked:
            out.append((s, "numbers.csv value (string)"))
            masked = masked.replace(s, " " * len(s))
    for u in URL.findall(masked):
        out.append((u, "URL"))
        masked = masked.replace(u, " " * len(u))
    if is_heading:
        for m in NUMBER.finditer(masked):
            out.append((m.group(0), "section number"))
        return out
    sec, men, dev, ref = (spans(SECTION, masked), spans(MENTION, masked),
                          spans(DEVIATION, masked), spans(REFNUM, masked))
    cap = spans(CAPTION, masked)
    for m in NUMBER.finditer(masked):
        tok, pos = m.group(0), m.start()
        val = float(tok.replace(",", ""))
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
        elif abs(val) < SMALL:
            if numeric_match(tok, marked_values):
                cat = "marked in sentence"
            elif numeric_match(tok, nums):
                cat = "WEAK MATCH"
            else:
                cat = "UNMATCHED"
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


def audited_files():
    sub = os.path.join(HERE, "submission")
    files = [("manuscript", DOCX)]
    legends = os.path.join(sub, "figure_legends.docx")
    if os.path.isfile(legends):
        files.append(("figure_legends.docx", legends))
    tables = ([f for f in os.listdir(sub) if re.fullmatch(r"Table \d+\.docx", f)]
              if os.path.isdir(sub) else [])
    for f in sorted(tables, key=lambda f: int(re.findall(r"\d+", f)[0])):
        files.append((f, os.path.join(sub, f)))
    return files


def audit_file(label, path, nums, strings, by_id, sent_ids, shows, counts, flagged):
    d = docx.Document(path)
    section = "" if label == "manuscript" else label
    last_caption = ""
    nref = 0
    pmap = {p._p: p for p in d.paragraphs}
    tmap = {t._tbl: t for t in d.tables}

    for el in d.element.body.iterchildren():
        if el in pmap:
            p = pmap[el]
            txt = p.text.strip()
            if not txt:
                continue
            heading = p.style.name.startswith("Heading") or p.style.name == "Title"
            if heading and label == "manuscript":
                section = txt
            if CAPTION.match(txt):
                last_caption = txt
            if label == "manuscript" and section == "References" and not heading:
                for m in NUMBER.finditer(norm(txt)):
                    counts["reference entry"] += 1
                continue
            for sent in ([txt] if heading else SENT.split(txt)):
                marked = [by_id[i] for i in sent_ids.get(key(sent), ()) if i in by_id]
                for tok, cat in classify_text(sent, heading, nums, strings, nref, marked):
                    counts[cat] += 1
                    if cat in flagged:
                        flagged[cat].append((section, tok, sent))
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
                        cat = ("table header" if i == 0 else
                               "table cell" if same else "UNMATCHED")
                        counts[cat] += 1
                        if cat == "UNMATCHED":
                            flagged[cat].append((section, tok, " | ".join(cells)))


def write_report(counts, flagged, files):
    L = ["number_audit.txt -- written by paper/check_docx_numbers.py",
         "Audited: " + ", ".join(f for f, _ in files),
         "Nothing was changed. A match means the number has a traced source of the kind",
         "named, not that it is attached to the right claim. Tokens below 10 count as sourced",
         "only if an id marked in the same draft sentence carries that value.",
         "", "Tokens by category:"]
    for cat in ("numbers.csv value", "numbers.csv value (string)", "URL", "marked in sentence",
                "table cell", "table header", "reference entry", "section number",
                "table/figure number",
                "deviation number", "year", "reference number", "WEAK MATCH", "UNMATCHED"):
        L.append("  %-28s %6d" % (cat, counts[cat]))
    for cat in ("UNMATCHED", "WEAK MATCH"):
        L += ["", "%s tokens (%d), each with its sentence or table row:"
              % (cat, len(flagged[cat])), ""]
        for i, (sec, tok, ctx) in enumerate(flagged[cat], 1):
            L.append("%3d. [%s] token %s" % (i, sec, tok))
            L.append("     %s" % ctx)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    nums, strings, by_id = load_numbers()
    sent_ids = draft_sentence_ids()
    shows = table_sources()
    counts = collections.Counter()
    flagged = {"UNMATCHED": [], "WEAK MATCH": []}
    files = audited_files()
    for label, path in files:
        audit_file(label, path, nums, strings, by_id, sent_ids, shows, counts, flagged)
    write_report(counts, flagged, files)
    print("wrote paper/number_audit.txt: %d tokens, %d unmatched, %d weak matches"
          % (sum(counts.values()), len(flagged["UNMATCHED"]), len(flagged["WEAK MATCH"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
