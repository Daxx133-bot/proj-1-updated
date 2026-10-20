"""
build_ieee.py -- the IEEE Access manuscript, from paper/draft_ieee/*.md.

Outputs (paper/ieee/)
  manuscript_ieee.docx   two-column manuscript, plain Word styles
  manuscript_ieee.pdf    the same document exported by Microsoft Word (skipped, with a note,
                         where Word is not available)
  ieee_checks.txt        the results of the checks below

No paper/ieee/template.docx exists, so the layout imitates IEEE Access: US Letter, two
columns, Times New Roman 10 pt, single spacing, justified; a full-width title block,
abstract and index terms; IEEE heading numbering (I., A.); figures and tables placed after
the paragraph that first cites them, numbered by first mention, with "Fig. N." captions
below figures and "TABLE I" captions above tables; numbered display equations; Algorithm 1;
numeric citations [n] numbered by first appearance, with ranges written [a]-[c]; an IEEE
reference list with DOIs; page numbers and a running head. [TO FILL] placeholders are
highlighted in yellow.

Every paragraph goes through the shared pipeline of paper/build_docx.py (markers stripped,
inline markdown rendered); only numbering and citation style differ. Draft table and figure
numbers resolve through the map in paper/draft_ieee/floats.md. A table fits one column when
it is at most three columns wide, spans both columns when it fits the text width at 6.5 pt or
larger, and otherwise takes a landscape page; tables of one or two rows and ten or more
columns, and the supplementary recovery-time table, are shown transposed.

Checks (written to ieee_checks.txt; the build fails if one fails):
  number audit   paper/check_docx_numbers.py's classification on the docx; table cells must
                 equal their source CSV cells; 0 unmatched
  floats         every figure and table appears once, numbered in order of first mention, after
                 the paragraph that first cites it
  references     every VERIFIED reference cited, numbered by first appearance, listed in order
  abstract       one paragraph, at most 250 words
  pronouns       no first-person or gendered third-person pronoun in the text
  layout (PDF)   page count, content past the margins, tables wider than their column

Run after build_all.py's earlier steps: python paper/build_ieee.py
"""
from __future__ import annotations

import collections
import copy
import csv
import os
import re
import sys

import docx
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_docx as bd  # noqa: E402
import check_docx_numbers as cdn  # noqa: E402

HERE, REPO = bd.HERE, bd.REPO
DRAFT = os.path.join(HERE, "draft_ieee")
OUTDIR = os.path.join(HERE, "ieee")
DOCX_OUT = os.path.join(OUTDIR, "manuscript_ieee.docx")
PDF_OUT = os.path.join(OUTDIR, "manuscript_ieee.pdf")
REPORT = os.path.join(OUTDIR, "ieee_checks.txt")

ORDER = ["introduction.md", "related_work.md", "problem.md", "methodology.md", "results.md",
         "discussion.md", "threats.md", "conclusion.md", "acknowledgment.md"]
TAIL = ["appendix.md", "biographies.md"]          # after the references
INDEX_TERMS = ("Distributed tracing, failure propagation, fault injection, graph centrality, "
               "microservices, preregistration")
ABSTRACT_MAX = 250

PAGE_W, PAGE_H = Inches(8.5), Inches(11)
MARGINS = {"top_margin": Inches(0.75), "bottom_margin": Inches(1.0),
           "left_margin": Inches(0.625), "right_margin": Inches(0.625)}
LAND_MARGINS = {"top_margin": Inches(0.625), "bottom_margin": Inches(0.625),
                "left_margin": Inches(0.75), "right_margin": Inches(0.75)}
COL_GAP = Inches(0.25)
TEXT_W_CM, LAND_W_CM = 7.25 * 2.54, 9.5 * 2.54
COL_W_CM = (7.25 - 0.25) / 2 * 2.54
FIG_MAX_H = Cm(9.5)
BODY_PT, SMALL_PT, CAPTION_PT, REF_PT = 10, 9, 8, 8
CELL_PAD_TWIPS = 28
KEEP_ROWS = 13
PAD = 6.5
TRANSPOSE = {"tbl_trec_supplementary"}
FORCE_LAND = {"tbl_trec_supplementary"}
MONO_COLS = {"tbl_commands": {"command"}}
# Fixed column fractions of the text width, for tables Word's autofit lays out badly.
COL_FRACTIONS = {"tbl_commands": (0.15, 0.60, 0.25)}
SHORT_TITLE = bd.COVER["title"].split("? ")[0] + "?"
PLACEHOLDER = re.compile(r"\[(?:TO FILL[^\]]*|Guide to confirm)\]")
ZWSP = "​"
PPR_SEQ = ["w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr",
           "w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd",
           "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
           "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi",
           "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing",
           "w:mirrorIndents", "w:suppressOverlap", "w:jc", "w:textDirection",
           "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId",
           "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange"]
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII",
         "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]
DRAFT_MENTION = re.compile(r"\b(Tables?|Figures?)\s+(\d+)((?:\s*(?:,|and)\s*\d+)*)")
RENDERED_MENTION = re.compile(
    r"\b(Tables?|Figures?|Figs?\.)\s+([IVXLC]+|\d+)((?:\s*(?:,|and)\s*(?:[IVXLC]+|\d+))*)")
FIG_CAPTION = re.compile(r"^Fig\. (\d+)\. ")
TAB_LABEL = re.compile(r"^TABLE ([IVXLC]+)$")
NUMERIC_CITE = re.compile(r"\[\d+\](?:\s*[–-]\s*\[\d+\])?")
ALGO_NUMBER = re.compile(r"\bAlgorithm\s+\d+")
PRONOUN = re.compile(r"\b(we|We|WE|our|Our|ours|us|Us|he|He|she|She|his|His|her|Her)\b|"
                     r"(?<!Section )(?<!Table )(?<!TABLE )(?<![A-Za-z.\-])I(?=\s+[a-z])")


# ── helpers ───────────────────────────────────────────────────────────────────

_plain_add_runs = bd.add_runs
_plain_blocks = bd.blocks


def add_runs(par, text, size=None):
    pos = 0
    for m in PLACEHOLDER.finditer(text):
        _plain_add_runs(par, text[pos:m.start()])
        par.add_run(m.group(0)).font.highlight_color = WD_COLOR_INDEX.YELLOW
        pos = m.end()
    _plain_add_runs(par, text[pos:])
    if size:
        for r in par.runs:
            r.font.size = Pt(size)


def add_field(par, instr, placeholder=""):
    def fld(kind):
        e = OxmlElement("w:fldChar")
        e.set(qn("w:fldCharType"), kind)
        return e
    par.add_run()._r.append(fld("begin"))
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = " %s " % instr
    par.add_run()._r.append(it)
    par.add_run()._r.append(fld("separate"))
    par.add_run(placeholder)
    par.add_run()._r.append(fld("end"))


def insert_ppr(pPr, el):
    tag = el.tag.split("}")[1]
    pPr.insert_element_before(el, *PPR_SEQ[PPR_SEQ.index("w:" + tag) + 1:])


def border(sides, sz="6", space="1"):
    b = OxmlElement("w:pBdr")
    for side in sides:
        e = OxmlElement("w:" + side)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), sz)
        e.set(qn("w:space"), space)
        e.set(qn("w:color"), "000000")
        b.append(e)
    return b


def tiny_paragraph():
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    sp = OxmlElement("w:spacing")
    for k, v in (("w:before", "0"), ("w:after", "0"), ("w:line", "20"),
                 ("w:lineRule", "exact")):
        sp.set(qn(k), v)
    pPr.append(sp)
    rPr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "2")
    rPr.append(sz)
    pPr.append(rPr)
    p.append(pPr)
    return p


def configure(section, landscape, cols):
    section.orientation = WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
    section.page_width, section.page_height = ((PAGE_H, PAGE_W) if landscape
                                               else (PAGE_W, PAGE_H))
    for side, v in (LAND_MARGINS if landscape else MARGINS).items():
        setattr(section, side, v)
    section.header_distance = section.footer_distance = Inches(0.4)
    sp = section._sectPr
    for e in sp.findall(qn("w:lnNumType")):
        sp.remove(e)
    c = sp.find(qn("w:cols"))
    if c is None:
        c = OxmlElement("w:cols")
        sp.find(qn("w:pgMar")).addnext(c)
    c.set(qn("w:num"), str(cols))
    c.set(qn("w:space"), str(int(COL_GAP.twips)))


def wrap_points(s):
    return s.replace("_", "_" + ZWSP)


def clean(s):
    return s.replace(ZWSP, "")


def width_needed(rows, pt, mono=()):
    total = 0.0
    for j in range(len(rows[0])):
        cw = (0.0212 if j in mono else 0.0168) * pt
        pieces = [t for r in rows for t in re.split(r"\s+|(?<=[_/-])", r[j]) if t]
        total += max((len(t) for t in pieces), default=1) * cw + 0.15
    return total


def ieee_blocks(text):
    """build_docx.blocks, plus ```algorithm fences and $$ display equations."""
    algos = []

    def keep(m):
        algos.append(m.group(1).strip("\n").splitlines())
        return "\n@@ALGO%d@@\n" % (len(algos) - 1)
    text = re.sub(r"```algorithm\n(.*?)\n```", keep, text, flags=re.S)
    out = []
    for kind, t in _plain_blocks(text):
        m = re.fullmatch(r"@@ALGO(\d+)@@", t.strip()) if kind == "p" else None
        if m:
            out.append(("algo", algos[int(m.group(1))]))
        elif kind == "p" and t.strip().startswith("$$") and t.strip().endswith("$$"):
            out.append(("eq", t.strip()[2:-2].strip()))
        else:
            out.append((kind, t))
    return out


def read(name):
    with open(os.path.join(DRAFT, name), encoding="utf-8") as fh:
        return fh.read()


def float_map():
    m = {}
    for line in read("floats.md").splitlines():
        r = bd.REF_MAP_ROW.match(line)
        if r:
            m[(r.group(1), int(r.group(2)))] = r.group(3)
    return m


# ── IEEE references ───────────────────────────────────────────────────────────

def ieee_authors(entry):
    names = []
    for a in entry["authors"].split(";"):
        sur, _, ini = a.strip().partition(",")
        names.append(("%s %s" % (ini.strip(), sur.strip())).strip())
    if len(names) > 6:
        return names[0] + " et al."
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + ", and " + names[-1]


def ieee_reference(entry):
    a, t, v, y = ieee_authors(entry), entry["title"].rstrip("."), entry["venue"], entry["year"]
    pages = entry.get("pages", "").replace("-", "–")
    if entry.get("volume"):
        s = '%s, "%s," *%s*, vol. %s' % (a, t, v, entry["volume"])
        if entry.get("issue"):
            s += ", no. %s" % entry["issue"]
        if pages:
            s += ", pp. %s" % pages
        s += ", %s" % y
    elif v.startswith("Proceedings of the "):
        s = '%s, "%s," in *Proc. %s*, %s' % (a, t, v[len("Proceedings of the "):], y)
        s += ", pp. %s" % pages if pages else ""
    elif "Report" in v:
        s = '%s, "%s," %s, %s' % (a, t, v, y)
    else:
        s = '%s, "%s," in *%s*, %s' % (a, t, v, y)
        s += ", pp. %s" % pages if pages else ""
    if entry.get("doi"):
        s += ", doi: %s." % entry["doi"]
    elif entry.get("url"):
        s += ". [Online]. Available: %s" % entry["url"]
    else:
        s += "."
    return s


# ── build ─────────────────────────────────────────────────────────────────────

class IEEEBuilder(bd.Builder):
    def __init__(self):
        super().__init__()
        self.draft_map = float_map()
        self.doc = Document()
        bd.style_document(self.doc, line_numbers=False)
        st = self.doc.styles
        normal = st["Normal"]
        normal.font.size = Pt(BODY_PT)
        pf = normal.paragraph_format
        pf.line_spacing, pf.space_after = 1.0, Pt(0)
        pf.first_line_indent = Inches(0.15)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for name, size, caps, bold, italic in (("Title", 20, False, True, False),
                                               ("Heading 1", 10, True, True, False),
                                               ("Heading 2", 10, False, False, True),
                                               ("Heading 3", 10, False, False, True)):
            h = st[name]
            h.font.size, h.font.all_caps = Pt(size), caps
            h.font.bold, h.font.italic = bold, italic
            h.paragraph_format.keep_with_next = True
            h.paragraph_format.first_line_indent = Inches(0)
            h.paragraph_format.space_before = Pt(8 if name == "Heading 1" else 5)
            h.paragraph_format.space_after = Pt(3)
            h.paragraph_format.alignment = (WD_ALIGN_PARAGRAPH.CENTER if name == "Heading 1"
                                            else WD_ALIGN_PARAGRAPH.LEFT)
        st["Title"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        cap = st["Caption"]
        cap.font.name, cap.font.size = bd.FONT, Pt(CAPTION_PT)
        cap.font.bold, cap.font.italic = False, False
        cap.font.color.rgb = RGBColor(0, 0, 0)
        rf = cap.element.get_or_add_rPr().get_or_add_rFonts()
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            rf.attrib.pop(qn(a), None)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(a), bd.FONT)
        cap.paragraph_format.first_line_indent = Inches(0)
        cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        cap.paragraph_format.space_after = Pt(6)
        for name, size in (("Abstract", SMALL_PT), ("Reference", REF_PT),
                           ("Equation", BODY_PT), ("Algorithm", 7.5),
                           ("Biography", SMALL_PT)):
            s = st.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            s.base_style = normal
            s.font.size = Pt(size)
            s.paragraph_format.first_line_indent = Inches(0)
        ref = st["Reference"].paragraph_format
        ref.alignment = WD_ALIGN_PARAGRAPH.LEFT
        ref.left_indent, ref.first_line_indent, ref.space_after = Inches(0.3), Inches(-0.3), Pt(1)
        st["Algorithm"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        st["Algorithm"].paragraph_format.left_indent = Inches(0.15)
        st["Algorithm"].paragraph_format.first_line_indent = Inches(-0.15)
        eq = st["Equation"].paragraph_format
        eq.alignment = WD_ALIGN_PARAGRAPH.LEFT
        eq.space_before = eq.space_after = Pt(3)
        eq.tab_stops.add_tab_stop(Inches(1.75), WD_TAB_ALIGNMENT.CENTER)
        eq.tab_stops.add_tab_stop(Inches(3.5), WD_TAB_ALIGNMENT.RIGHT)
        self.mode = "span"
        self.floats = []
        self.unplaced = []
        self.cite_order = []
        self.eq_no = 0
        self.algo_no = 0
        self.table_no = 0
        self.fixed_tables = set()       # 1-based indices of tables Word must not autofit

    # numbering and citations -------------------------------------------------
    def renumber(self, text):
        def sub(m):
            word, first, rest = m.group(1), int(m.group(2)), m.group(3) or ""
            kind = "Table" if word.startswith("Table") else "Figure"
            plural = word.endswith("s")
            nums = [first] + [int(x) for x in re.findall(r"\d+", rest)]
            new = []
            for n in nums:
                f = self.resolve(kind, n)
                if f is None:
                    new.append("%d [UNRESOLVED %s %d]" % (n, kind, n))
                else:
                    k = self.number[f][1]
                    new.append(ROMAN[k] if kind == "Table" else str(k))
            if kind == "Figure":
                before = text[:m.start()].rstrip()
                start = not before or before[-1] in ".!?"
                word = ("Figures" if plural else "Figure") if start else \
                       ("Figs." if plural else "Fig.")
            seps = re.findall(r"\s*(?:,|and)\s*", rest)
            out = word + " " + new[0]
            for sep, v in zip(seps, new[1:]):
                out += sep + v
            return out
        return DRAFT_MENTION.sub(sub, text)

    def cite(self, text):
        def sub(m):
            parts = [p.strip() for p in m.group(1).split(";")]
            if not all(p.startswith("@") and p[1:] in self.refs for p in parts):
                return m.group(0)
            nums = []
            for p in parts:
                k = p[1:]
                if k not in self.cite_order:
                    self.cite_order.append(k)
                nums.append(self.cite_order.index(k) + 1)
            nums = sorted(set(nums))
            groups, run = [], [nums[0]]
            for n in nums[1:]:
                if n == run[-1] + 1:
                    run.append(n)
                else:
                    groups.append(run)
                    run = [n]
            groups.append(run)
            out = []
            for g in groups:
                if len(g) >= 3:
                    out.append("[%d]–[%d]" % (g[0], g[-1]))
                else:
                    out.extend("[%d]" % n for n in g)
            return ", ".join(out)
        return bd.CITE.sub(sub, text)

    def render(self, text):
        return self.cite(self.renumber(bd.MARKER.sub("", text).strip()))

    # sections ---------------------------------------------------------------
    def section_break(self, start, landscape, cols):
        body = self.doc.element.body
        sent = body.find(qn("w:sectPr"))
        carrier = tiny_paragraph()
        sent.addprevious(carrier)
        insert_ppr(carrier.find(qn("w:pPr")), copy.deepcopy(sent))
        for tag in ("w:headerReference", "w:footerReference", "w:titlePg", "w:type"):
            for e in sent.findall(qn(tag)):
                sent.remove(e)
        t = OxmlElement("w:type")
        t.set(qn("w:val"), start)
        sent.insert(0, t)
        configure(self.doc.sections[-1], landscape, cols)

    def goto(self, mode):
        cur = self.mode
        if mode == cur:
            return
        if mode == "land":
            if cur == "two":
                self.section_break("continuous", False, 1)
            self.section_break("nextPage", True, 1)
        else:
            self.section_break("nextPage" if cur == "land" else "continuous", False,
                               2 if mode == "two" else 1)
        self.mode = mode

    # floats -----------------------------------------------------------------
    def table_plan(self, f):
        base = os.path.splitext(os.path.basename(f))[0]
        rows = bd.read_csv_rows(os.path.join(REPO, f))
        transposed = base in TRANSPOSE or (len(rows) - 1 <= 2 and len(rows[0]) >= 10)
        if transposed:
            rows = [list(col) for col in zip(*rows)]
            shown = [[bd.header_with_unit(r[0])] + r[1:] for r in rows]
        else:
            shown = [[bd.header_with_unit(h) for h in rows[0]]] + rows[1:]
        mono = {j for j, h in enumerate(rows[0]) if h in MONO_COLS.get(base, ())}
        longest = max(len(c) for r in shown for c in r)
        ncols = len(shown[0])
        if base not in FORCE_LAND and longest <= 300:
            if ncols <= 3 and not mono and width_needed(shown, 8) <= COL_W_CM:
                return rows, transposed, "two", 8, mono
            for pt in (7.5, 7, 6.5):
                if width_needed(shown, pt, mono) <= TEXT_W_CM:
                    return rows, transposed, "span", pt, mono
        for pt in (8, 7.5, 7):
            if width_needed(shown, pt, mono) <= LAND_W_CM:
                return rows, transposed, "land", pt, mono
        return rows, transposed, "land", 6.5, mono

    def place_new(self, before):
        new = [f for f in self.number if f not in before]
        for f in new:
            kind, n = self.number[f]
            if kind == "Figure":
                self.goto("span")
                self.add_figure(n, f)
            else:
                rows, transposed, mode, pt, mono = self.table_plan(f)
                self.goto(mode)
                self.add_table(n, f, rows, transposed, pt, mono,
                               keep_together=mode != "land" and len(rows) <= KEEP_ROWS)
        if new:
            self.goto("two")

    def add_figure(self, n, f):
        base = os.path.splitext(os.path.basename(f))[0]
        png = os.path.join(REPO, os.path.splitext(f)[0] + ".png")
        w, h = Image.open(png).size
        width = Cm(TEXT_W_CM * (0.72 if w / h < 1.4 else 0.95))
        if width * h / w > FIG_MAX_H:
            width = int(FIG_MAX_H * w / h)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Inches(0)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(6)
        p.add_run().add_picture(png, width=width)
        c = self.doc.add_paragraph(style="Caption")
        c.add_run("Fig. %d. " % n)
        add_runs(c, self.fig_caps.get(base, base) + ".")
        self.floats.append(("Fig. %d" % n, "Figure", f, False))

    def add_table(self, n, f, rows, transposed, pt, mono, keep_together=False):
        base = os.path.splitext(os.path.basename(f))[0]
        label = "TABLE %s" % ROMAN[n]
        p = self.doc.add_paragraph(label, style="Caption")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(0)
        p = self.doc.add_paragraph(style="Caption")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(self.tbl_caps.get(base, base))
        r.font.small_caps = True
        t = self.doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.style = "Table Grid"
        t.autofit = base not in COL_FRACTIONS
        self.table_no += 1
        if base in COL_FRACTIONS:
            self.fixed_tables.add(self.table_no)
            for j, frac in enumerate(COL_FRACTIONS[base]):
                for c in t.columns[j].cells:
                    c.width = Cm(frac * TEXT_W_CM)
        tblPr = t._tbl.tblPr
        tblW = tblPr.find(qn("w:tblW"))
        tblW.set(qn("w:type"), "pct")
        tblW.set(qn("w:w"), "5000")
        mar = OxmlElement("w:tblCellMar")
        for side in ("left", "right"):
            e = OxmlElement("w:" + side)
            e.set(qn("w:w"), str(CELL_PAD_TWIPS))
            e.set(qn("w:type"), "dxa")
            mar.append(e)
        tblPr.insert_element_before(mar, "w:tblLook", "w:tblCaption", "w:tblDescription")
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                head = (j == 0) if transposed else (i == 0)
                text = bd.header_with_unit(val) if head else val
                cell = t.cell(i, j)
                cell.text = ""
                par = cell.paragraphs[0]
                par.alignment = WD_ALIGN_PARAGRAPH.LEFT
                par.paragraph_format.first_line_indent = Inches(0)
                par.paragraph_format.line_spacing = 1.0
                par.paragraph_format.space_after = Pt(0)
                run = par.add_run(text if (j in mono and not head) else wrap_points(text))
                run.font.size = Pt(pt - 0.5 if (j in mono and not head) else pt)
                if j in mono and not head:
                    run.font.name = "Courier New"
                run.bold = head or (transposed and i == 0)
                if keep_together:
                    par.paragraph_format.keep_with_next = True
        if keep_together:
            for row in t.rows:
                row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        hdr = OxmlElement("w:tblHeader")
        hdr.set(qn("w:val"), "true")
        t.rows[0]._tr.get_or_add_trPr().append(hdr)
        notes = [bd.TABLE_NOTE] + ([bd.TABLE_FOOTNOTES[base]] if base in bd.TABLE_FOOTNOTES
                                   else [])
        for k, note in enumerate(notes):
            p = self.doc.add_paragraph(note, style="Caption")
            p.runs[0].font.size = Pt(7)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = keep_together and k < len(notes) - 1
        self.floats.append((label, "Table", f, transposed))

    # text -------------------------------------------------------------------
    def paragraph(self, text, style=None):
        before = set(self.number)
        add_runs(self.doc.add_paragraph(style=style), self.render(text))
        self.place_new(before)

    def equation(self, text):
        self.eq_no += 1
        p = self.doc.add_paragraph(style="Equation")
        add_runs(p, "\t" + bd.MARKER.sub("", text).strip() + "\t(%d)" % self.eq_no)

    def algorithm(self, lines):
        self.algo_no += 1
        first = True
        for k, line in enumerate(lines):
            p = self.doc.add_paragraph(style="Algorithm")
            p.paragraph_format.keep_with_next = k < len(lines) - 1
            if first:
                head, _, rest = line.partition(":")
                p.add_run(head + ":").bold = True
                add_runs(p, rest)
                insert_ppr(p._p.get_or_add_pPr(), border(("top", "bottom")))
                first = False
            else:
                add_runs(p, line)
                if k == len(lines) - 1:
                    insert_ppr(p._p.get_or_add_pPr(), border(("bottom",)))

    def draft(self, name):
        for kind, text in ieee_blocks(read(name)):
            if kind.startswith("h"):
                h = self.doc.add_heading(bd.MARKER.sub("", text).strip(), level=int(kind[1]))
                h.paragraph_format.first_line_indent = Inches(0)
            elif kind == "eq":
                self.equation(text)
            elif kind == "algo":
                self.algorithm(text)
            elif name == "biographies.md":
                add_runs(self.doc.add_paragraph(style="Biography"), self.render(text))
            else:
                self.paragraph(text, style={"quote": "Quote", "li": "List Bullet"}.get(kind))

    def title_block(self):
        doc = self.doc
        sec = doc.sections[0]
        configure(sec, landscape=False, cols=1)
        sec.different_first_page_header_footer = True
        hp = sec.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hp.paragraph_format.first_line_indent = Inches(0)
        r = hp.add_run(SHORT_TITLE)
        r.italic, r.font.size = True, Pt(8)
        for footer in (sec.footer, sec.first_page_footer):
            fp = footer.paragraphs[0]
            fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_field(fp, "PAGE", "1")
        doc.add_heading(bd.COVER["title"], level=0)
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Inches(0)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for i, (name, aff) in enumerate(bd.COVER["authors"]):
            r = p.add_run(("" if i == 0 else " AND " if i == len(bd.COVER["authors"]) - 1
                           else ", ") + name.upper())
            r.font.size = Pt(11)
            p.add_run(str(aff)).font.superscript = True
        for n, aff in enumerate(bd.COVER["affiliations"], 1):
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Inches(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.add_run(str(n)).font.superscript = True
            r = p.add_run(aff)
            r.font.size = Pt(8)
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Inches(0)
        p.paragraph_format.space_after = Pt(8)
        add_runs(p, "Corresponding author: " + bd.COVER["corresponding"], size=8)

    def abstract(self):
        paras = [t for k, t in ieee_blocks(read("abstract.md")) if k == "p"]
        assert len(paras) == 1, "the abstract must be one paragraph"
        p = self.doc.add_paragraph(style="Abstract")
        p.add_run("ABSTRACT ").bold = True
        text = self.render(paras[0])
        add_runs(p, text, size=SMALL_PT)
        self.abstract_words = len(re.sub(r"[*`]", "", text).split())
        p = self.doc.add_paragraph(style="Abstract")
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(10)
        p.add_run("INDEX TERMS ").bold = True
        p.add_run(INDEX_TERMS)
        insert_ppr(p._p.get_or_add_pPr(), border(("bottom",), sz="4", space="4"))

    def build_ieee(self):
        bd.add_runs = _plain_add_runs
        self.title_block()
        before = set(self.number)
        self.abstract()
        self.place_new(before)
        self.goto("two")
        for name in ORDER:
            self.draft(name)
        self.doc.add_heading("References", level=1)
        for i, k in enumerate(self.cite_order, 1):
            p = self.doc.add_paragraph(style="Reference")
            add_runs(p, "[%d]\t%s" % (i, ieee_reference(self.refs[k])))
        for name in TAIL:
            self.draft(name)
        self.unplaced = sorted(f for f in set(self.draft_map.values()) if f not in self.number)
        self.cited = list(self.cite_order)
        for p in self.doc.paragraphs:               # inline code at 9 pt beside 10 pt text
            for r in p.runs:
                if r.font.name == "Courier New":
                    r.font.size = Pt(9)
            if p.style.name == "Biography":
                p.paragraph_format.space_after = Pt(4)
        cp = self.doc.core_properties
        cp.author, cp.title, cp.comments = "", "", "built by paper/build_ieee.py"
        os.makedirs(OUTDIR, exist_ok=True)
        self.doc.save(DOCX_OUT)


def word_finalize(docx_path, pdf_path, fixed=()):
    """Fit tables, save, export the PDF and measure each table against its column or page.
    Returns (pages, geometry) or (None, []) where Word is not available."""
    try:
        import win32com.client
    except ImportError:
        return None, []
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    geometry = []
    try:
        d = word.Documents.Open(os.path.abspath(docx_path), False, False)
        for i in range(1, d.Tables.Count + 1):
            if i not in fixed:
                d.Tables(i).AutoFitBehavior(1)
                d.Tables(i).AutoFitBehavior(2)
        d.Repaginate()
        for i in range(1, d.Tables.Count + 1):
            t = d.Tables(i)
            x = t.Range.Information(5)
            row = t.Rows(1)
            w = sum(row.Cells(k).Width for k in range(1, row.Cells.Count + 1))
            ps = t.Range.Sections(1).PageSetup
            left, right = ps.LeftMargin, ps.PageWidth - ps.RightMargin
            if ps.TextColumns.Count > 1:
                cw, gap = ps.TextColumns(1).Width, ps.TextColumns(1).SpaceAfter
                if x < left + cw:
                    right = left + cw
                else:
                    left = left + cw + gap
            geometry.append((i, ps.TextColumns.Count, x - CELL_PAD_TWIPS / 20.0, w, left,
                             right))
        d.Save()
        d.ExportAsFixedFormat(OutputFileName=os.path.abspath(pdf_path), ExportFormat=17,
                              OpenAfterExport=False, OptimizeFor=0, CreateBookmarks=1,
                              DocStructureTags=True)
        pages = d.ComputeStatistics(2)
        d.Close(False)
    finally:
        word.Quit()
    return pages, geometry


# ── checks ────────────────────────────────────────────────────────────────────

def ieee_key(s):
    s = NUMERIC_CITE.sub("", s)
    s = re.sub(r"\bTables?\s+[IVXLC]+\b", "#REF#", s)
    return cdn.key(s)


def draft_sentence_ids():
    """check_docx_numbers.draft_sentence_ids, pointed at the IEEE drafts."""
    saved = (bd.DRAFT, bd.SECTIONS, bd.TRAILING, bd.COVER_LETTER, bd.blocks)
    try:
        bd.DRAFT = DRAFT
        bd.SECTIONS = [("", f, None) for f in ["abstract.md"] + ORDER + TAIL]
        bd.TRAILING = []
        bd.COVER_LETTER = "abstract.md"
        bd.blocks = ieee_blocks
        return cdn.draft_sentence_ids()
    finally:
        bd.DRAFT, bd.SECTIONS, bd.TRAILING, bd.COVER_LETTER, bd.blocks = saved


def audit(docx_path, b, L):
    nums, strings, by_id = cdn.load_numbers()
    sent_ids = draft_sentence_ids()
    nref = len(b.cite_order)
    counts = collections.Counter()
    flagged = []
    d = docx.Document(docx_path)
    pmap = {p._p: p for p in d.paragraphs}
    tmap = {t._tbl: t for t in d.tables}
    sources = {lab: (os.path.join(REPO, f), tr) for lab, kind, f, tr in b.floats
               if kind == "Table"}
    section, label = "title block", None
    for el in d.element.body.iterchildren():
        if el in pmap:
            p = pmap[el]
            txt, st = clean(p.text).strip(), p.style.name
            if not txt:
                continue
            heading = st.startswith("Heading")
            if heading:
                section = txt
            if TAB_LABEL.match(txt):
                label = txt
                counts["table/figure number"] += 0
                continue
            if section == "title block" and st != "Abstract":
                if txt.endswith(bd.AFFILIATION) and txt[:-len(bd.AFFILIATION)].strip().isdigit():
                    counts["affiliation marker"] += 1
                    txt = bd.AFFILIATION
                txt = re.sub(r"(?<=[A-Za-z])\d(?=$| AND|,)", "", txt)
            if st == "Abstract":
                txt = re.sub(r"^(ABSTRACT|INDEX TERMS)\s+", "", txt)
            if section == "References" and not heading:
                counts["reference entry"] += len(cdn.NUMBER.findall(cdn.norm(txt)))
                continue
            if st == "Equation":
                body, _, eqn = txt.rpartition("(")
                counts["equation number"] += 1
                for tok in cdn.NUMBER.findall(cdn.norm(body)):
                    cat = "equation constant" if tok in ("0", "1") else "UNMATCHED"
                    counts[cat] += 1
                    if cat == "UNMATCHED":
                        flagged.append((cat, section, tok, txt))
                continue
            for m in ALGO_NUMBER.finditer(txt):
                counts["algorithm number"] += 1
            for sent in ([txt] if heading or st == "Title" else cdn.SENT.split(txt)):
                marked = [by_id[i] for i in sent_ids.get(ieee_key(sent), ()) if i in by_id]
                for tok, cat in cdn.classify_text(ALGO_NUMBER.sub("Algorithm", sent),
                                                  heading or st == "Title", nums,
                                                  strings, nref, marked):
                    counts[cat] += 1
                    if cat in ("UNMATCHED", "WEAK MATCH"):
                        flagged.append((cat, section, tok, sent))
        elif el in tmap:
            src, transposed = sources.get(label, (None, False))
            srows = list(csv.reader(open(src, encoding="utf-8", newline=""))) if src else None
            for i, row in enumerate(tmap[el].rows):
                for j, c in enumerate(row.cells):
                    ct = clean(c.text)
                    toks = cdn.NUMBER.findall(cdn.norm(ct))
                    if not toks:
                        continue
                    a, bb = (j, i) if transposed else (i, j)
                    head = (j == 0) if transposed else (i == 0)
                    same = (srows is not None and a < len(srows) and bb < len(srows[a])
                            and srows[a][bb] == ct)
                    cat = "table header" if head else "table cell" if same else "UNMATCHED"
                    counts[cat] += len(toks)
                    if cat == "UNMATCHED":
                        flagged.append((cat, label, ct, ""))
    L.append("Number audit: " + ", ".join("%s %d" % kv for kv in sorted(counts.items())))
    for cat, sec, tok, sent in flagged:
        L.append("  %s [%s] %s | %s" % (cat, sec, tok, sent[:150]))
    return counts["UNMATCHED"]


def check_floats(docx_path, b, L):
    d = docx.Document(docx_path)
    seen, problems, first_cite = [], [], {}
    body_index = -1
    for p in d.paragraphs:
        txt, st = clean(p.text).strip(), p.style.name
        lab = None
        if st == "Caption":
            m = FIG_CAPTION.match(txt) or TAB_LABEL.match(txt)
            if m:
                lab = ("Figure" if txt.startswith("Fig") else "Table", m.group(1))
        if lab:
            seen.append(lab)
            if lab[0] == "Table" and lab in [x for x in seen[:-1]]:
                pass
            if first_cite.get(lab) != body_index:
                problems.append("%s %s is not directly after the paragraph that first cites "
                                "it" % lab)
            continue
        if not txt or st in ("Caption", "Equation", "Algorithm") or \
                st.lower().startswith(("title", "heading")):
            continue
        body_index += 1
        for mm in RENDERED_MENTION.finditer(txt):
            k = "Table" if mm.group(1).startswith("Table") else "Figure"
            for n in [mm.group(2)] + re.findall(r"[IVXLC]+|\d+", mm.group(3) or ""):
                first_cite.setdefault((k, n), body_index)
    for kind, conv in (("Figure", str), ("Table", lambda i: ROMAN[i])):
        got = [n for k, n in seen if k == kind]
        want = [conv(i) for i in range(1, len(got) + 1)]
        if got != want:
            problems.append("%s order %s, expected %s" % (kind, got, want))
    dup = [x for x, c in collections.Counter(seen).items() if c > 1]
    if dup:
        problems.append("appear more than once: %s" % dup)
    if b.unplaced:
        problems.append("never cited, not placed: %s" % b.unplaced)
    L.append("Floats: %d figures and %d tables, each once, numbered by first mention, after "
             "the paragraph that first cites it; problems: %d"
             % (sum(k == "Figure" for k, _ in seen), sum(k == "Table" for k, _ in seen),
                len(problems)))
    for x in problems:
        L.append("  " + x)
    return not problems


def check_references(docx_path, b, L):
    d = docx.Document(docx_path)
    text = " ".join(p.text for p in d.paragraphs
                    if p.style.name not in ("Reference",))
    order = []
    for m in re.finditer(r"\[(\d+)\](?:\s*[–-]\s*\[(\d+)\])?", text):
        a = int(m.group(1))
        z = int(m.group(2)) if m.group(2) else a
        for n in range(a, z + 1):
            if n not in order:
                order.append(n)
    listed = [p for p in d.paragraphs if p.style.name == "Reference"]
    ok_order = order == list(range(1, len(order) + 1))
    ok = (ok_order and len(listed) == len(b.refs) and set(b.cite_order) == set(b.refs))
    L.append("References: %d VERIFIED, %d cited, %d listed; numbered by first appearance: %s"
             % (len(b.refs), len(set(b.cite_order)), len(listed),
                "yes" if ok_order else "no (%s)" % order[:20]))
    return ok


def check_pronouns_and_abstract(docx_path, b, L):
    d = docx.Document(docx_path)
    hits = []
    for p in d.paragraphs:
        if p.style.name == "Reference":
            continue
        for m in PRONOUN.finditer(p.text):
            hits.append((m.group(0), p.text[max(0, m.start() - 40):m.end() + 40]))
    L.append("First-person and gendered pronouns: %d" % len(hits))
    for w, ctx in hits[:20]:
        L.append("  %s | %s" % (w, ctx))
    L.append("Abstract: one paragraph, %d words (limit %d)" % (b.abstract_words, ABSTRACT_MAX))
    return not hits, b.abstract_words <= ABSTRACT_MAX


def check_layout(pdf_path, geometry, floats, L):
    import pdfplumber
    issues = []
    labels = [lab for lab, kind, _, _ in floats if kind == "Table"]
    for (i, ncol, x, w, left, right), lab in zip(geometry, labels):
        if x + w > right + 2 or x < left - PAD:
            issues.append("%s is wider than its %s" % (lab, "column" if right - left < 300
                                                       else "page"))
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        for no, page in enumerate(pdf.pages, 1):
            W, H = page.width, page.height
            lm = 0.75 * 72 if W > H else 0.625 * 72
            words = [w for w in page.extract_words() if 30 < w["top"] < H - 40]
            over = [w["text"] for w in words if w["x1"] > W - lm + 2 or w["x0"] < lm - 2]
            rules = [e for e in page.edges if e["x1"] > W - lm + PAD or e["x0"] < lm - PAD]
            if over or rules:
                issues.append("page %d: content past the margin (%s)"
                              % (no, ", ".join(over[:4]) or "table rules"))
    L.append("Layout: %d pages; problems: %d" % (n, len(issues)))
    for x in issues:
        L.append("  " + x)
    return n


def main():
    b = IEEEBuilder()
    b.build_ieee()
    pages, geometry = word_finalize(DOCX_OUT, PDF_OUT, b.fixed_tables)
    L = ["ieee_checks.txt -- written by paper/build_ieee.py",
         "IEEE manuscript: paper/ieee/manuscript_ieee.docx%s"
         % (" and .pdf (%d pages in Word)" % pages if pages else
            "; PDF not exported (Microsoft Word not available)"), ""]
    unmatched = audit(DOCX_OUT, b, L)
    ok_floats = check_floats(DOCX_OUT, b, L)
    ok_refs = check_references(DOCX_OUT, b, L)
    ok_pron, ok_abs = check_pronouns_and_abstract(DOCX_OUT, b, L)
    if pages:
        check_layout(PDF_OUT, geometry, b.floats, L)
    todo = [m.group(0) for p in docx.Document(DOCX_OUT).paragraphs
            for m in PLACEHOLDER.finditer(p.text)]
    L.append("Placeholders (highlighted): %d: %s" % (len(todo), "; ".join(todo)))
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))
    failed = [name for name, ok in (("number audit", unmatched == 0), ("floats", ok_floats),
                                    ("references", ok_refs), ("pronouns", ok_pron),
                                    ("abstract", ok_abs)) if not ok]
    if failed:
        print("IEEE BUILD FAILED: %s" % ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
