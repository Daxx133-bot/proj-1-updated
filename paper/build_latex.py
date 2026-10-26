"""
build_latex.py -- build the IEEE Access manuscript from paper/latex/ with LaTeX.

The hand-written text lives in paper/latex/main.tex and paper/latex/sections/*.tex. It types
no result: every number is written \\val{claim_id}, which prints the value of that row of
paper/numbers.csv, and claims that print no number carry a %[id:claim_id] comment. This
script writes everything else into paper/latex/generated/ and then compiles:

  values.tex       one \\val entry per row of paper/numbers.csv
  tables/*.tex     one float per paper/tables/tbl_ieee_*.csv, caption from tables_index.csv
  figures/*.pdf    copied from paper/figures/
  references.bib   the VERIFIED rows of paper/references.csv, fields exactly as stored

It compiles with pdflatex and BibTeX (TinyTeX in %APPDATA%\\TinyTeX, or pdflatex on the
PATH) into paper/latex/build/, copies the PDF to paper/latex/manuscript_ieee.pdf, writes an
Overleaf-ready paper/latex/overleaf_upload.zip, and runs these checks, written to
paper/latex/latex_checks.txt:

  * the LaTeX log has no undefined reference or citation;
  * every VERIFIED reference is cited and every citation is VERIFIED;
  * every \\val and %[id:...] names a row of numbers.csv;
  * the hand-written source contains no digit outside \\val, labels, references and a short
    list of allowed forms (p95, H1, S1, WSL2 and the like), each listed with its reason;
  * the abstract has at most 250 words;
  * no banned phrase and no first-person or gendered pronoun in the rendered text;
  * no sentence shares eight consecutive words with the README, the claims ledger, the
    audit records or the preregistration.

It exits non-zero if any check fails. Run: python paper/build_latex.py
"""
from __future__ import annotations

import csv
import glob
import os
import re
import shutil
import subprocess
import sys
import zipfile

import pdfplumber

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LTX = os.path.join(HERE, "latex")
GEN = os.path.join(LTX, "generated")
BUILD = os.path.join(LTX, "build")
PDF_OUT = os.path.join(LTX, "manuscript_ieee.pdf")
ZIP_OUT = os.path.join(LTX, "overleaf_upload.zip")
REPORT = os.path.join(LTX, "latex_checks.txt")
NUMBERS = os.path.join(HERE, "numbers.csv")
REFS = os.path.join(HERE, "references.csv")
TABLES = os.path.join(HERE, "tables")
FIGURES = os.path.join(HERE, "figures")
ABSTRACT_MAX = 250

sys.path.insert(0, HERE)
from emit_macros import tex_escape  # noqa: E402

# ── tables ───────────────────────────────────────────────────────────────────
# Column layout of each table. "wide" tables span both columns. Header cells of columns
# that are not paragraph columns are wrapped onto lines of at most `wrap` characters.
TABLE_LAYOUT = {
    "tbl_ieee_testbed": dict(wide=True, size="footnotesize",
                             spec=r"p{3.3cm}p{9.6cm}p{4.6cm}"),
    "tbl_ieee_commands": dict(wide=True, size="footnotesize",
                              spec=r"p{2.9cm}p{11.9cm}p{2.7cm}", mono={"Command"}),
    "tbl_ieee_predictors_sn": dict(wide=True, size="scriptsize", spec="l" + "r" * 13, wrap=11,
                                   fit=True),
    "tbl_ieee_predictors_hr": dict(wide=True, size="scriptsize", spec="l" + "r" * 13, wrap=11,
                                   fit=True),
    "tbl_ieee_primary": dict(wide=True, size="scriptsize",
                             spec=r"lllrrllrp{2.3cm}rlp{2.0cm}", wrap=12),
    "tbl_ieee_families": dict(wide=True, size="footnotesize",
                              spec=r"llrrrrrp{5.0cm}", wrap=14),
    "tbl_ieee_h2": dict(wide=True, size="footnotesize", spec=r"lllrrlrrlp{2.6cm}", wrap=12),
    "tbl_ieee_power": dict(wide=False, size="footnotesize", spec=r"p{3.9cm}p{2.0cm}p{1.9cm}"),
    "tbl_ieee_trec": dict(wide=True, size="scriptsize", spec="lll" + "r" * 10, wrap=11,
                          fit=True),
    "tbl_ieee_weights": dict(wide=True, size="scriptsize", spec="lll" + "r" * 9, wrap=11),
    "tbl_ieee_deviations": dict(wide=True, size="footnotesize",
                                spec=r"rlp{6.4cm}rp{6.6cm}", wrap=10),
}
# Notes printed under single tables.
TABLE_NOTES = {
    "tbl_ieee_trec": ("Not estimable: the Cox fit did not converge or showed separation "
                      "because the predictor takes few distinct values; raw estimates are in "
                      "supplementary file S2."),
}

# ── checks ───────────────────────────────────────────────────────────────────
BANNED = {
    "delve": r"\bdelv(e|es|ed|ing)\b", "crucial": r"\bcrucial", "pivotal": r"\bpivotal",
    "notably": r"\bnotably\b", "furthermore": r"\bfurthermore\b", "moreover": r"\bmoreover\b",
    "in conclusion": r"\bin conclusion\b",
    "it is important/worth noting": r"\bit is (important|worth) (noting|to note)|\bworth noting\b",
    "underscores": r"\bunderscor", "highlights the importance": r"\bhighlights? the importance",
    "landscape": r"\blandscape", "robust": r"\brobust", "seamless": r"\bseamless",
    "leverage": r"\bleverag", "comprehensive": r"\bcomprehensive",
    "in today's": r"\bin today'?s", "plays a vital role": r"\bplays? a vital role",
    "not only...but also": r"\bnot only\b[^.]*\bbut also\b", "rather than": r"\brather than\b",
    "anti-predictive": r"anti-predictive", "least consequential/impactful":
    r"least (consequential|impactful)", "never degrade": r"never degrade",
    "predicts blast radius": r"predicts blast radius",
    "approaches significance": r"approach(es|ing) significance",
}
PRONOUN = re.compile(r"\b(we|We|WE|our|Our|ours|us|Us|he|He|she|She|his|His|her|Her)\b|"
                     r"(?<!Section )(?<!Table )(?<!TABLE )(?<![A-Za-z.\-])I(?=\s+[a-z])")
# Digits the hand-written source may contain, each with its reason.
ALLOWED_DIGITS = [
    (r"\bp9[59]\b", "percentile names p95 and p99"),
    (r"\b95\\%", "the conventional 95% confidence level"),
    (r"\bH1b?\b|\bH2\b", "hypothesis labels"),
    (r"\bS[1-3]\b", "supplementary file names S1 to S3"),
    (r"\bWSL2\b", "product name"),
    (r"\bCC BY \d\.\d\b", "licence name and version"),
    (r"\bDeviations?~?\s*\d+(?:(?:,\s*|\s+and\s+)\d+)*", "deviation numbers, the labels of "
     "analysis/final/deviations.csv"),
]
MATH_DIGITS = {"0", "1", "1.0"}     # constants in equations: zero, one, a perfect correlation
OVERLAP_N = 8


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# ── generated inputs ─────────────────────────────────────────────────────────

def value_tex(v):
    """Display form of a numbers.csv value: thousands grouped, a true minus sign, arrows."""
    if re.fullmatch(r"\d{4,}", v):
        v = "{:,}".format(int(v))
    v = tex_escape(v)
    if re.fullmatch(r"-\d[\d.,]*", v):
        v = r"\ensuremath{-}" + v[1:]
    return v.replace("->", r"$\rightarrow$")


def gen_values(numbers):
    lines = ["% AUTO-GENERATED by paper/build_latex.py from paper/numbers.csv. Do not edit.",
             r"\makeatletter"]
    for r in numbers:
        lines.append(r"\@namedef{val@%s}{%s}%% %s" % (r["claim_id"], value_tex(r["value"]),
                                                      r["source_file"]))
    lines.append(r"\makeatother")
    write(os.path.join(GEN, "values.tex"), "\n".join(lines) + "\n")


def cell_tex(s, mono=False):
    """Table markup (*italic*, <sub>, Unicode symbols) to LaTeX."""
    s = s or ""
    if mono:
        s = tex_escape(s).replace("--", "-{}-")
        return r"\texttt{%s}" % s
    s = tex_escape(s)
    s = re.sub(r"\*([^*]+)\*", r"\\textit{\1}", s)
    s = re.sub(r"<sub>(.*?)</sub>", r"\\textsubscript{\1}", s)
    s = re.sub(r"(?<![\w$])-(\d)", r"\\textminus{}\1", s)
    s = re.sub(r"(\d\.\d+)e([+-])0*(\d+)",
               lambda m: r"$%s\times10^{%s%s}$" % (m.group(1), "-" if m.group(2) == "-" else "",
                                                   m.group(3)), s)
    s = s.replace("<", r"$<$").replace(">", r"$>$")
    for a, b in (("ρ", r"$\rho$"), ("≤", r"$\leq$"), ("−", r"\textminus{}"), ("×", r"$\times$")):
        s = s.replace(a, b)
    return s


def caption_tex(s):
    s = cell_tex(s)
    return re.sub(r"(?<![\w\\])([XY])(?![\w])", r"$\1$", s)


def head_tex(h, wrap):
    t = cell_tex(h)
    if not wrap or len(h) <= wrap:
        return t
    words, lines, cur = h.split(" "), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > wrap:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    return r"\makecell[lb]{%s}" % r"\\".join(cell_tex(x) for x in lines)


def gen_tables(captions):
    for name, lay in TABLE_LAYOUT.items():
        rows = read_csv(os.path.join(TABLES, name + ".csv"))
        with open(os.path.join(TABLES, name + ".csv"), encoding="utf-8", newline="") as fh:
            head = next(csv.reader(fh))
        mono = lay.get("mono", set())
        paragraph = [c.startswith("p") for c in re.findall(r"p\{[^}]*\}|[lrc]", lay["spec"])]
        env = "table*" if lay["wide"] else "table"
        out = [r"\begin{%s}[!t]" % env, r"\centering",
               r"\caption{%s}" % caption_tex(captions[name]), r"\label{tab:%s}" % name,
               "\\" + lay["size"], r"\setlength{\tabcolsep}{3pt}",
               r"\resizebox{\textwidth}{!}{%" if lay.get("fit") else "",
               r"\begin{tabular}{%s}" % lay["spec"], r"\toprule"]
        out.append(" & ".join(r"\textbf{%s}" % (cell_tex(h) if paragraph[i]
                                                 else head_tex(h, lay.get("wrap")))
                              for i, h in enumerate(head)) + r" \\")
        out.append(r"\midrule")
        for r in rows:
            out.append(" & ".join(cell_tex(r[h], h in mono) for h in head) + r" \\")
        out += [r"\bottomrule", r"\end{tabular}" + ("}" if lay.get("fit") else "")]
        if name in TABLE_NOTES:
            out.append(r"\par\smallskip\parbox{\linewidth}{\scriptsize %s}"
                       % cell_tex(TABLE_NOTES[name]))
        out.append(r"\end{%s}" % env)
        write(os.path.join(GEN, "tables", name + ".tex"), "\n".join(out) + "\n")


def bib_escape(s):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#"),
                 ("_", r"\_"), ("$", r"\$")):
        s = s.replace(a, b)
    return s


def bib_type(r):
    v = r["venue"]
    if "Technical Report" in v:
        return "techreport", "institution"
    if re.search(r"Proceedings|Conference|Symposium|NOMS|Lecture Notes|Software Engineering "
                 r"\(Springer\)", v):
        return "inproceedings", "booktitle"
    return "article", "journal"


def gen_bib(refs):
    out = ["% AUTO-GENERATED by paper/build_latex.py from the VERIFIED rows of "
           "paper/references.csv. Do not edit."]
    for r in refs:
        typ, venue_field = bib_type(r)
        authors = " and ".join(a.strip() for a in r["authors"].split(";") if a.strip())
        f = [("author", bib_escape(authors)), ("title", "{%s}" % bib_escape(r["title"])),
             (venue_field, bib_escape(r["venue"])), ("year", r["year"])]
        if r["volume"]:
            f.append(("volume", r["volume"]))
        if r["issue"]:
            f.append(("number", r["issue"]))
        if r["pages"]:
            f.append(("pages", r["pages"].replace("-", "--")))
        if r["doi"]:
            f.append(("note", "doi: " + bib_escape(r["doi"])))
        elif r["url"]:
            f.append(("url", r["url"]))
        out.append("@%s{%s,\n%s\n}" % (typ, r["key"], ",\n".join(
            "  %s = {%s}" % (k, v) for k, v in f)))
    write(os.path.join(GEN, "references.bib"), "\n\n".join(out) + "\n")


def gen_figures(names):
    os.makedirs(os.path.join(GEN, "figures"), exist_ok=True)
    for n in names:
        shutil.copyfile(os.path.join(FIGURES, n + ".pdf"), os.path.join(GEN, "figures", n + ".pdf"))


# ── source scanning ──────────────────────────────────────────────────────────

def sources():
    return [os.path.join(LTX, "main.tex")] + sorted(glob.glob(os.path.join(LTX, "sections",
                                                                           "*.tex")))


def strip_comments(t):
    return re.sub(r"(?<!\\)%.*", "", t)


def source_text():
    return {p: open(p, encoding="utf-8").read() for p in sources()}


def used(texts, pattern):
    out = []
    for p, t in texts.items():
        out += re.findall(pattern, t)
    return out


def stray_digits(texts):
    """Digits in the hand-written source that do not come from \\val."""
    def math_ok(m):
        """Digits inside math may be the constants 0, 1 and 1.0 only."""
        s = re.sub(r"\\val\{[^}]*\}", " ", m.group(0))
        for a, _ in ALLOWED_DIGITS:
            s = re.sub(a, " ", s)
        toks = re.findall(r"\d+(?:\.\d+)?", s)
        return m.group(0) if [x for x in toks if x not in MATH_DIGITS] else " "

    hits = []
    for p, t in texts.items():
        t = strip_comments(t)
        if "\\begin{document}" in t:                       # the preamble defines, never states
            t = t.split("\\begin{document}", 1)[1]
        t = re.sub(r"\$[^$]*\$", math_ok, t)
        t = re.sub(r"\\begin\{(equation|align)\*?\}.*?\\end\{(equation|align)\*?\}", math_ok,
                   t, flags=re.S)
        t = re.sub(r"\\(val|ref|label|cite|input|includegraphics|begin|end|url|"
                   r"bibliography|bibliographystyle|setlength|hspace|vspace|textsubscript)\*?"
                   r"(\[[^\]]*\]|\{[^{}]*\})*", " ", t)
        t = re.sub(r"\[(!?[htbp]+|width=[^\]]*)\]", " ", t)
        t = re.sub(r"[0-9.]+\\(columnwidth|textwidth|linewidth)", " ", t)
        for a, _ in ALLOWED_DIGITS:
            t = re.sub(a, " ", t)
        for m in re.finditer(r"\d", t):
            ctx = t[max(0, m.start() - 50):m.end() + 30].replace("\n", " ")
            hits.append((os.path.relpath(p, REPO), ctx))
    return hits


def prose_text(texts, values):
    """The running text as a reader sees it, from the source: values substituted, captions
    kept, tables, algorithms and equations left out, commands removed. The style and overlap
    checks run on this, because text extracted from a two-column PDF interleaves the columns
    and mixes in table cells and the reference list."""
    out = []
    for p, t in texts.items():
        t = strip_comments(t)
        if "\\begin{document}" in t:
            t = t.split("\\begin{document}", 1)[1].split("\\bibliographystyle", 1)[0]
        t = re.sub(r"\\begin\{(algorithm|tabular|equation|align)\*?\}.*?\\end\{\1\*?\}", " ",
                   t, flags=re.S)
        t = re.sub(r"\\(input|includegraphics|label|url)(\[[^\]]*\])?\{[^}]*\}", " ", t)
        t = re.sub(r"\\val\{([^}]+)\}", lambda m: values.get(m.group(1), ""), t)
        t = re.sub(r"\\cite\{[^}]*\}", "[1]", t)
        t = re.sub(r"\\ref\{[^}]*\}", "1", t)
        t = re.sub(r"\\(begin|end)\{[^}]*\}(\[[^\]]*\])?", " ", t)
        t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
        out.append(re.sub(r"[{}$~\\]", " ", t))
    return re.sub(r"\s+", " ", " ".join(out))


def abstract_words(texts, values):
    main = strip_comments(texts[os.path.join(LTX, "main.tex")])
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", main, re.S)
    body = re.sub(r"\\val\{([^}]+)\}", lambda k: values.get(k.group(1), "X"), m.group(1))
    body = re.sub(r"\\[a-zA-Z]+\*?(\{[^{}]*\})?", " ", body)
    body = re.sub(r"[{}$~]", " ", body)
    return len(body.split())


# ── compile ──────────────────────────────────────────────────────────────────

def tex_bin(name):
    cand = os.path.join(os.environ.get("APPDATA", ""), "TinyTeX", "bin", "windows", name + ".exe")
    if os.path.isfile(cand):
        return cand
    found = shutil.which(name)
    if not found:
        raise SystemExit("%s not found: install TinyTeX or TeX Live" % name)
    return found


def run(cmd):
    r = subprocess.run(cmd, cwd=LTX, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


def compile_pdf():
    os.makedirs(BUILD, exist_ok=True)
    pdflatex = [tex_bin("pdflatex"), "-interaction=nonstopmode", "-halt-on-error",
                "-output-directory=build", "main.tex"]
    codes = [run(pdflatex), run([tex_bin("bibtex"), "build/main"]), run(pdflatex), run(pdflatex)]
    log = open(os.path.join(BUILD, "main.log"), encoding="utf-8", errors="replace").read()
    return codes, log


def pdf_text(path):
    with pdfplumber.open(path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return pages


def overlap(text):
    files = (["README.md", "paper/CLAIMS_LEDGER.md"]
             + sorted(glob.glob(os.path.join(REPO, "_audit", "*.md")))
             + sorted(glob.glob(os.path.join(REPO, "PREREGISTRATION*.md")))
             + sorted(glob.glob(os.path.join(REPO, "_audit", "preregistration_versions",
                                             "PREREGISTRATION*.md"))))
    tok = lambda s: re.findall(r"[a-z0-9]+(?:['\-][a-z0-9]+)*",  # noqa: E731
                               s.lower().replace("\u2019", "'"))
    grams = {}
    for f in files:
        p = f if os.path.isabs(f) else os.path.join(REPO, f)
        w = tok(open(p, encoding="utf-8").read())
        for i in range(len(w) - OVERLAP_N + 1):
            grams.setdefault(tuple(w[i:i + OVERLAP_N]), os.path.relpath(p, REPO))
    hits, n = [], 0
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text):
        n += 1
        w = tok(s)
        for i in range(len(w) - OVERLAP_N + 1):
            g = tuple(w[i:i + OVERLAP_N])
            if g in grams:
                hits.append((grams[g], " ".join(g), s[:160]))
                break
    return n, hits


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    numbers = read_csv(NUMBERS)
    values = {r["claim_id"]: r["value"] for r in numbers}
    refs = [r for r in read_csv(REFS) if r["status"].strip() == "VERIFIED"]
    captions = {r["table"]: r["shows"] for r in read_csv(os.path.join(TABLES,
                                                                        "tables_index.csv"))}
    texts = source_text()
    figs = sorted(set(used(texts, r"generated/figures/([\w]+)\.pdf")))

    gen_values(numbers)
    gen_tables(captions)
    gen_bib(refs)
    gen_figures(figs)
    codes, log = compile_pdf()
    ok_compile = os.path.isfile(os.path.join(BUILD, "main.pdf")) and codes[-1] == 0
    if ok_compile:
        shutil.copyfile(os.path.join(BUILD, "main.pdf"), PDF_OUT)

    L, failed = [], []

    def check(name, ok, detail=()):
        L.append("%s: %s" % (name, "ok" if ok else "FAILED"))
        L.extend("  " + d for d in detail)
        if not ok:
            failed.append(name)

    check("Compile (pdflatex, bibtex, pdflatex, pdflatex exit codes %s)" % codes, ok_compile)
    undefined = re.findall(r"(?:Citation|Reference) `[^']+' on page \d+ undefined", log)
    check("Undefined references and citations: %d" % len(undefined), not undefined,
          sorted(set(undefined))[:20])
    overfull = re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\)", log)
    big = [x for x in overfull if float(x) > 1.0]
    check("Overfull boxes over 1 pt: %d (largest %s pt)"
          % (len(big), max((float(x) for x in big), default=0)), not big)

    cited = []
    for c in used(texts, r"\\cite\{([^}]+)\}"):
        cited += [k.strip() for k in c.split(",")]
    keys = [r["key"] for r in refs]
    check("References: %d VERIFIED, %d cited" % (len(keys), len(set(cited))),
          set(cited) == set(keys),
          ["not cited: %s" % ", ".join(sorted(set(keys) - set(cited)))] * bool(
              set(keys) - set(cited)) +
          ["cited but not VERIFIED: %s" % ", ".join(sorted(set(cited) - set(keys)))] * bool(
              set(cited) - set(keys)))

    bare = {p: strip_comments(t) for p, t in texts.items()}
    ids = set(used(bare, r"\\val\{([^}]+)\}")) | set(
        i.strip() for g in used(texts, r"%\[id:([^\]]+)\]") for i in g.split(","))
    unknown = sorted(i for i in ids if i not in values)
    check("Claim ids: %d used, %d unknown" % (len(ids), len(unknown)), not unknown, unknown)

    stray = stray_digits(texts)
    check("Digits typed into the source: %d" % len(stray), not stray,
          ["%s: ...%s..." % h for h in stray[:40]])

    words = abstract_words(texts, values)
    check("Abstract: %d words (limit %d)" % (words, ABSTRACT_MAX), words <= ABSTRACT_MAX)

    prose = prose_text(texts, values)
    L.append("Words in the running text (captions included, tables excluded): %d"
             % len(prose.split()))
    bhits = [(n, prose[max(0, m.start() - 50):m.end() + 30]) for n, rx in BANNED.items()
             for m in re.finditer(rx, prose, re.I)]
    check("Banned phrases: %d" % len(bhits), not bhits, ["%s: ...%s..." % h for h in bhits[:20]])
    phits = [prose[max(0, m.start() - 50):m.end() + 30] for m in PRONOUN.finditer(prose)]
    check("First-person and gendered pronouns: %d" % len(phits), not phits, phits[:20])
    n, ohits = overlap(prose)
    check("Overlap: %d sentences, %d sharing %d words with the repository's own records"
          % (n, len(ohits), OVERLAP_N), not ohits, ["%s | %s | %s" % h for h in ohits[:20]])
    if ok_compile:
        L.append("Pages: %d" % len(pdf_text(PDF_OUT)))
    L.append("Tables: %d; figures: %d" % (len(TABLE_LAYOUT), len(figs)))

    with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sources():
            z.write(p, os.path.relpath(p, LTX))
        for p in sorted(glob.glob(os.path.join(GEN, "**", "*"), recursive=True)):
            if os.path.isfile(p):
                z.write(p, os.path.relpath(p, LTX))

    write(REPORT, "\n".join(L) + "\n")
    print("\n".join(L))
    print("wrote %s, %s and %s" % tuple(os.path.relpath(p, REPO) for p in
                                        (PDF_OUT, ZIP_OUT, REPORT)))
    if failed:
        print("FAILED: %s" % "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
