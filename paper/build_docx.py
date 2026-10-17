"""
build_docx.py -- assemble paper/manuscript.docx from paper/draft/*.md. Writes no prose.

Sections, in order: abstract, 1 introduction, 2 related work, 3 method, 4 results,
5 discussion, 6 threats to validity, 7 audit and deviations, 8 conclusion, data
availability, AI-use statement, references, appendix. A section with a prose draft is rendered from it. A section that has only an
outline file, or no file at all, gets its heading followed by the visible placeholder
[TO WRITE]; nothing is generated to fill it.

Rendering rules
  * Every %[...] drafting marker is removed. "> **Drafting note" blockquotes are removed.
  * Tables (paper/tables/*.csv) and figures (paper/figures/*.png) are inserted after the
    paragraph that first mentions them, numbered in order of first mention, and every
    in-text "Table N" / "Figure N" is renumbered to match. The draft numbers are resolved to
    files through the reference map in the results draft's drafting note. Captions come from
    paper/tables/tables_index.csv and paper/figures/figures_index.csv. A table or figure the
    text never mentions is appended, numbered, before the references.
  * Citations are written [@key]. A key is resolved only if paper/references.csv has that
    key with status VERIFIED; it is then numbered in order of first citation. Any other
    [@key], and any [CITATION NEEDED: ...], stays as visible text.
  * Section headings keep the numbers the drafts give them; nothing is renumbered, because
    the prose cross-references those numbers.
  * Plain single-column layout: Times New Roman 12 pt, 1.5 line spacing; tables in 8 pt.

Run: python paper/build_docx.py
"""
from __future__ import annotations

import csv
import os
import re
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, "draft")
OUT = os.path.join(HERE, "manuscript.docx")
REFS = os.path.join(HERE, "references.csv")
FONT = "Times New Roman"

# (heading used when there is no prose, prose draft, outline draft)
SECTIONS = [
    ("Abstract", None, "outline_abstract.md"),
    ("1. Introduction", None, "outline_intro.md"),
    ("2. Related Work", None, "outline_related_work.md"),
    ("3. Method", "method.md", None),
    ("4. Results", "results.md", None),
    ("5. Discussion", None, "outline_discussion.md"),
    ("6. Threats to Validity", "limitations.md", None),
    ("7. Audit and Deviations", "audit_disclosure.md", None),
    ("8. Conclusion", None, "outline_conclusion.md"),
    ("Data Availability", None, None),
    ("AI-use statement", None, None),
]
# Rendered after the references.
TRAILING = [("Appendix", None, None)]

MARKER = re.compile(r"\s*%\[[^\]]*\]")
REF_MAP_ROW = re.compile(r"^>\s*\|\s*(Table|Figure)\s+(\d+)\s*\|\s*`([^`]+)`\s*\|")
MENTION = re.compile(r"\b(Tables?|Figures?)\s+(\d+)((?:\s*(?:,|and)\s*\d+)*)")
CITE = re.compile(r"\[@([A-Za-z0-9_:\-]+)\]")
INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|<sub>.*?</sub>|<sup>.*?</sup>|\*[^*\s][^*]*\*)")


def read(name):
    with open(os.path.join(DRAFT, name), encoding="utf-8") as fh:
        return fh.read()


def outline_heading(name, default):
    """The outline's own title, minus its ' — ... outline' suffix."""
    if not name or not os.path.isfile(os.path.join(DRAFT, name)):
        return default
    first = read(name).splitlines()[0].lstrip("# ").strip()
    return re.split(r"\s+[—-]\s+", first)[0] or default


def draft_reference_map():
    """{('Table', n): file, ('Figure', n): file} from the results draft's drafting note."""
    m = {}
    for line in read("results.md").splitlines():
        r = REF_MAP_ROW.match(line)
        if r:
            m[(r.group(1), int(r.group(2)))] = r.group(3)
    return m


def blocks(text):
    """Split a draft into (kind, text) blocks, dropping drafting-note blockquotes."""
    out, para, quote = [], [], []

    def flush():
        if para:
            out.append(("p", " ".join(s.strip() for s in para)))
            para.clear()

    lines = text.splitlines() + [""]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> ").rstrip())
                i += 1
            if "Drafting note" not in quote[0]:
                out.append(("quote", " ".join(q for q in quote if q)))
            continue
        h = re.match(r"^(#{1,3})\s+(.*)", line)
        if h:
            flush()
            out.append(("h%d" % len(h.group(1)), h.group(2).strip()))
        elif not line.strip():
            flush()
        else:
            para.append(line)
        i += 1
    return out


def load_refs():
    if not os.path.isfile(REFS):
        return {}
    with open(REFS, encoding="utf-8", newline="") as fh:
        return {r["key"]: r for r in csv.DictReader(fh)
                if r.get("status", "").strip() == "VERIFIED"}


def read_csv_rows(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


def captions(index_file, key_col):
    rows = read_csv_rows(index_file)
    head = rows[0]
    k, s = head.index(key_col), head.index("shows")
    return {r[k]: r[s] for r in rows[1:]}


def set_base_style(doc):
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    st.paragraph_format.line_spacing = 1.5
    st.paragraph_format.space_after = Pt(6)
    for name, size in (("Title", 16), ("Heading 1", 14), ("Heading 2", 12), ("Heading 3", 12)):
        h = doc.styles[name]
        h.font.name = FONT
        h.font.size = Pt(size)
        h.font.bold = True
        h.font.color.rgb = RGBColor(0, 0, 0)
        h.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)


def add_runs(par, text):
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            par.add_run(piece[2:-2]).bold = True
        elif piece.startswith("`") and piece.endswith("`"):
            r = par.add_run(piece[1:-1])
            r.font.name = "Courier New"
            r.font.size = Pt(11)
        elif piece.startswith("<sub>"):
            par.add_run(piece[5:-6]).font.subscript = True
        elif piece.startswith("<sup>"):
            par.add_run(piece[5:-6]).font.superscript = True
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            par.add_run(piece[1:-1]).italic = True
        else:
            par.add_run(piece)


class Builder:
    def __init__(self):
        self.doc = Document()
        set_base_style(self.doc)
        self.draft_map = draft_reference_map()
        self.tbl_caps = captions(os.path.join(HERE, "tables", "tables_index.csv"), "table")
        self.fig_caps = captions(os.path.join(HERE, "figures", "figures_index.csv"), "figure")
        self.number = {}          # file -> (kind, new number)
        self.counter = {"Table": 0, "Figure": 0}
        self.refs = load_refs()
        self.ref_order = []
        self.placed = set()

    def resolve(self, kind, n):
        f = self.draft_map.get((kind, n))
        if f is None:
            return None
        if f not in self.number:
            self.counter[kind] += 1
            self.number[f] = (kind, self.counter[kind])
        return f

    def renumber(self, text):
        """Rewrite Table/Figure mentions to first-mention numbers; return text, files."""
        files = []

        def sub(m):
            word, first, rest = m.group(1), int(m.group(2)), m.group(3) or ""
            kind = "Table" if word.startswith("Table") else "Figure"
            nums = [first] + [int(x) for x in re.findall(r"\d+", rest)]
            new = []
            for n in nums:
                f = self.resolve(kind, n)
                if f is None:
                    new.append("%d [UNRESOLVED %s %d]" % (n, kind, n))
                else:
                    files.append(f)
                    new.append(str(self.number[f][1]))
            seps = re.findall(r"\s*(?:,|and)\s*", rest)
            out = word + " " + new[0]
            for sep, v in zip(seps, new[1:]):
                out += sep + v
            return out

        return MENTION.sub(sub, text), files

    def cite(self, text):
        def sub(m):
            key = m.group(1)
            if key not in self.refs:
                return m.group(0)
            if key not in self.ref_order:
                self.ref_order.append(key)
            return "[%d]" % (self.ref_order.index(key) + 1)
        return CITE.sub(sub, text)

    def paragraph(self, text, style=None):
        text = MARKER.sub("", text).strip()
        text, files = self.renumber(text)
        text = self.cite(text)
        par = self.doc.add_paragraph(style=style)
        add_runs(par, text)
        for f in files:
            if f not in self.placed:
                self.place(f)

    def place(self, f):
        kind, n = self.number[f]
        base = os.path.splitext(os.path.basename(f))[0]
        if kind == "Table":
            path = os.path.join(os.path.dirname(HERE), f)
            rows = read_csv_rows(path)
            cap = self.doc.add_paragraph()
            cap.add_run("Table %d. " % n).bold = True
            cap.add_run(self.tbl_caps.get(base, base))
            t = self.doc.add_table(rows=len(rows), cols=len(rows[0]))
            t.style = "Table Grid"
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    cell = t.cell(i, j)
                    cell.text = ""
                    r = cell.paragraphs[0].add_run(val)
                    r.font.size = Pt(8)
                    r.bold = i == 0
                    cell.paragraphs[0].paragraph_format.line_spacing = 1.0
        else:
            png = os.path.join(os.path.dirname(HERE),
                               os.path.splitext(f)[0] + ".png")
            self.doc.add_picture(png, width=Inches(6.0))
            self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap = self.doc.add_paragraph()
            cap.add_run("Figure %d. " % n).bold = True
            cap.add_run(self.fig_caps.get(base, base))
        self.placed.add(f)

    def to_write(self, heading):
        self.doc.add_heading(heading, level=1)
        r = self.doc.add_paragraph().add_run("[TO WRITE]")
        r.bold = True
        r.font.color.rgb = RGBColor(0xC0, 0, 0)

    def build(self):
        self.doc.add_heading("[TITLE TO WRITE]", level=0)
        for heading, prose, outline in SECTIONS:
            if prose and os.path.isfile(os.path.join(DRAFT, prose)):
                for kind, text in blocks(read(prose)):
                    if kind.startswith("h"):
                        self.doc.add_heading(MARKER.sub("", text).strip(),
                                             level=int(kind[1]))
                    elif kind == "quote":
                        self.paragraph(text, style="Quote")
                    else:
                        self.paragraph(text)
            else:
                self.to_write(outline_heading(outline, heading))

        leftover = [f for f in sorted(set(self.draft_map.values())) if f not in self.placed]
        if leftover:
            self.doc.add_heading("Tables and figures not referenced in the text", level=1)
            for f in leftover:
                kind = "Table" if "/tables/" in f else "Figure"
                self.counter[kind] += 1
                self.number[f] = (kind, self.counter[kind])
                self.place(f)

        self.doc.add_heading("References", level=1)
        if not self.ref_order:
            r = self.doc.add_paragraph().add_run(
                "[TO WRITE: no reference in paper/references.csv has status VERIFIED]")
            r.bold = True
            r.font.color.rgb = RGBColor(0xC0, 0, 0)
        for i, key in enumerate(self.ref_order, 1):
            e = self.refs[key]
            self.doc.add_paragraph("[%d] %s (%s). %s. %s.%s" % (
                i, e["authors"], e["year"], e["title"], e["venue"],
                (" doi:%s" % e["doi"]) if e.get("doi") else ""))

        for heading, prose, outline in TRAILING:
            self.to_write(outline_heading(outline, heading))

        cp = self.doc.core_properties
        cp.author, cp.title, cp.comments = "", "", "built by paper/build_docx.py"
        self.doc.save(OUT)
        return {"tables": self.counter["Table"], "figures": self.counter["Figure"],
                "references": len(self.ref_order),
                "order": [(self.number[f], f) for f in sorted(
                    self.number, key=lambda f: (self.number[f][0], self.number[f][1]))]}


def main():
    info = Builder().build()
    print("wrote paper/manuscript.docx: %d tables, %d figures, %d verified references"
          % (info["tables"], info["figures"], info["references"]))
    for (kind, n), f in info["order"]:
        print("  %s %d <- %s" % (kind, n, f))
    todo = [outline_heading(o, h) for h, p, o in SECTIONS + TRAILING
            if not (p and os.path.isfile(os.path.join(DRAFT, p)))]
    print("  [TO WRITE]: %s" % "; ".join(todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
