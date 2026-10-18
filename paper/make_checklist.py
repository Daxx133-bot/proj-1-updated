"""
make_checklist.py -- write paper/submission/SUBMISSION_CHECKLIST.md.

Each PeerJ Computer Science requirement is checked against the files the build wrote and
marked PASS or TO DO. A requirement that is met outside these files (an entry in the
submission system, an upload) is TO DO until a person does it. The checklist then lists
every [TO FILL] placeholder with its file and line (paragraph number for .docx files).
Writes no prose for the paper.

Run after build_docx.py and check_docx_numbers.py: python paper/make_checklist.py
"""
from __future__ import annotations

import os
import re
import sys
import tempfile

import docx
from docx.oxml.ns import qn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_docx as bd  # noqa: E402

HERE = bd.HERE
SUB = bd.SUB
OUT = os.path.join(SUB, "SUBMISSION_CHECKLIST.md")
AUDIT = os.path.join(HERE, "number_audit.txt")
TITLE_MAX = 250
PLACEHOLDER = re.compile(r"\[TO FILL[^\]]*\]")


def doc_text(path):
    return [p.text for p in docx.Document(path).paragraphs]


def main():
    rows = []

    def req(name, ok, detail=""):
        rows.append((name, "PASS" if ok else "TO DO", detail))

    man = os.path.join(SUB, "manuscript.docx")
    d = docx.Document(man)
    body = d.element.body
    text = "\n".join(p.text for p in d.paragraphs)
    sect = d.sections[0]

    req("Manuscript supplied as .docx", os.path.isfile(man), "paper/submission/manuscript.docx")
    req("Title under %d characters" % TITLE_MAX, len(bd.COVER["title"]) < TITLE_MAX,
        "%d characters" % len(bd.COVER["title"]))
    req("Continuous line numbering",
        sect._sectPr.find(qn("w:lnNumType")) is not None, "")
    req("US Letter page, 2.5 cm margins",
        abs(sect.page_width.inches - 8.5) < 0.01 and abs(sect.page_height.inches - 11) < 0.01
        and abs(sect.left_margin.cm - 2.5) < 0.01, "")
    req("Figures and tables not embedded in the manuscript",
        not d.tables and not body.findall(".//" + qn("w:drawing")),
        "%d tables, %d drawings" % (len(d.tables), len(body.findall(".//" + qn("w:drawing")))))

    # Re-run the builder into a scratch directory for its abstract word count and cited keys.
    real_out, real_sub = bd.OUT, bd.SUB
    with tempfile.TemporaryDirectory() as tmp:
        bd.OUT, bd.SUB = os.path.join(tmp, "manuscript.docx"), os.path.join(tmp, "sub")
        b = bd.Builder()
        b.build()
    bd.OUT, bd.SUB = real_out, real_sub
    req("Abstract with Background, Methods, Results, Conclusions headings, at most %d words"
        % bd.ABSTRACT_MAX_WORDS,
        b.abstract_words <= bd.ABSTRACT_MAX_WORDS
        and all(h in text for h in bd.ABSTRACT_PARTS), "%d words" % b.abstract_words)

    figs = sorted(f for f in os.listdir(SUB) if re.fullmatch(r"Figure \d+\.(png|pdf)", f))
    nfig = len([f for f in figs if f.endswith(".png")])
    req("Each figure supplied as a separate file (PNG and PDF)",
        nfig > 0 and len(figs) == 2 * nfig, "%d figures" % nfig)
    req("Figure legends supplied", os.path.isfile(os.path.join(SUB, "figure_legends.docx")))
    tbls = [f for f in os.listdir(SUB) if re.fullmatch(r"Table \d+\.docx", f)]
    req("Each table supplied as a separate .docx with a title", len(tbls) > 0,
        "%d tables" % len(tbls))

    missing = [f for f in bd.SUPPLEMENTARY if not os.path.isfile(os.path.join(SUB, f))]
    req("Supplementary data files named in table footnotes supplied", not missing,
        ", ".join(missing) or ", ".join(bd.SUPPLEMENTARY))

    refs = bd.load_refs()
    req("Every reference in the list is cited in the text", set(refs) == set(b.cited),
        "%d listed, %d cited" % (len(refs), len(b.cited)))
    nolink = [k for k, r in refs.items() if not (r.get("doi") or r.get("url"))]
    req("Every reference has a DOI or URL", not nolink, ", ".join(nolink))
    leftover = [s for s in ("%[", "[CITATION NEEDED", "[UNRESOLVED", "[TO WRITE")
                if s in text]
    req("No drafting markers, unresolved citations or [TO WRITE] in the manuscript",
        not leftover, ", ".join(leftover))

    unmatched = None
    if os.path.isfile(AUDIT):
        for line in open(AUDIT, encoding="utf-8"):
            m = re.match(r"\s+UNMATCHED\s+(\d+)", line)
            if m:
                unmatched = int(m.group(1))
    req("Number audit: every number traced to numbers.csv (0 unmatched)", unmatched == 0,
        "paper/number_audit.txt, %s unmatched" % unmatched)

    def placeholders_in(name):
        return [p for p in doc_text(os.path.join(SUB, name)) if PLACEHOLDER.search(p)]

    req("Cover page: authors, affiliations, corresponding author",
        not placeholders_in("cover_page.docx"), "cover_page.docx has [TO FILL]")
    req("Cover letter", os.path.isfile(os.path.join(SUB, "cover_letter.docx"))
        and not placeholders_in("cover_letter.docx"), "cover_letter.docx has [TO FILL]")
    for heading in ("Funding", "Acknowledgments", "Data Availability", "AI-Use Statement"):
        i = text.find("\n" + heading + "\n")
        nxt = text[i + len(heading) + 2:].split("\n", 1)[0] if i >= 0 else ""
        label = heading if heading.endswith("Statement") else heading + " statement"
        req(label, i >= 0 and not PLACEHOLDER.search(nxt),
            "section missing" if i < 0 else "has [TO FILL]" if PLACEHOLDER.search(nxt)
            else "")
    req("Code licence (LICENSE) and data licence (LICENSE-DATA) in the repository",
        all(os.path.isfile(os.path.join(bd.REPO, f)) for f in ("LICENSE", "LICENSE-DATA")))
    req("Raw data archived with a DOI (Zenodo)", "Zenodo (DOI: [TO FILL" not in text,
        "Data Availability names a Zenodo DOI to fill")
    for name in ("Preregistration uploaded as supplementary material "
                 "(_audit/preregistration_versions/PREREGISTRATION_v3_LOCKED.md)",
                 "Competing interests declared in the submission system",
                 "Author contributions declared in the submission system",
                 "All authors listed and ORCIDs entered in the submission system"):
        req(name, False, "done at submission")

    todo = []
    for fn in sorted(os.listdir(bd.DRAFT)):
        if fn.endswith(".md") and not fn.startswith("outline_"):
            for n, line in enumerate(open(os.path.join(bd.DRAFT, fn), encoding="utf-8"), 1):
                for m in PLACEHOLDER.finditer(line):
                    todo.append(("paper/draft/%s:%d" % (fn, n), m.group(0)))
    for n, line in enumerate(open(os.path.join(HERE, "build_docx.py"), encoding="utf-8"), 1):
        for m in PLACEHOLDER.finditer(line):
            todo.append(("paper/build_docx.py:%d (COVER)" % n, m.group(0)))
    for fn in sorted(f for f in os.listdir(SUB) if f.endswith(".docx")):
        for n, p in enumerate(doc_text(os.path.join(SUB, fn)), 1):
            for m in PLACEHOLDER.finditer(p):
                todo.append(("paper/submission/%s, paragraph %d" % (fn, n), m.group(0)))

    L = ["# Submission checklist: PeerJ Computer Science", "",
         "Written by `paper/make_checklist.py`. PASS means the build output meets the "
         "requirement; TO DO means a person still has to act.", "",
         "| Requirement | Status | Detail |", "|---|---|---|"]
    L += ["| %s | %s | %s |" % r for r in rows]
    L += ["", "## [TO FILL] placeholders (%d)" % len(todo), "",
          "Drafts and `build_docx.py` are the sources; the `.docx` rows are where each one "
          "appears after the build.", "", "| Location | Placeholder |", "|---|---|"]
    L += ["| %s | `%s` |" % t for t in todo]
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote paper/submission/SUBMISSION_CHECKLIST.md: %d PASS, %d TO DO, %d [TO FILL]"
          % (sum(r[1] == "PASS" for r in rows), sum(r[1] == "TO DO" for r in rows),
             len(todo)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
