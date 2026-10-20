"""
build_review_pdf.py -- a journal-style review copy of the manuscript for internal feedback.
It is not the journal submission format and writes nothing to paper/submission/ or
paper/manuscript.docx.

Outputs (paper/review/)
  Manuscript_review_copy.docx  Word document with plain styles, for comments and tracked changes
  Manuscript_review_copy.pdf   the same document exported by Microsoft Word
  review_checks.txt            the results of the checks below

Layout, set out like a published article: A4, Times New Roman throughout (code
identifiers included), 10.5 pt body,
single spacing, justified; a full-width title block (title, authors, affiliation,
corresponding author) and abstract in a box, followed by the keywords; the body in two
columns; numbered headings; a running header with the short title and page numbers in the
footer; references at 9 pt. No line numbers. [TO FILL] placeholders are highlighted.

Figures and tables follow the paragraph that first cites them, numbered as in the
submission, with captions below figures and above tables. Figures span both columns. A
table goes in one column when it is at most three columns wide, across both columns when it
fits the text width at 6.5 pt or larger, and otherwise on a landscape page. Tables of one or
two rows and ten or more columns are shown transposed so that they fit a column. Appendix A
holds the unrounded recovery-time estimates (paper/tables/tbl_trec_supplementary.csv),
transposed, on a landscape page. The deviations table is already in the body, so there is no
Appendix B. Table cells carry zero-width spaces after underscores so long identifiers can
wrap; the checks ignore them.

Every body paragraph goes through paper/build_docx.py's own pipeline (markers stripped,
mentions renumbered, citations rendered), so the text is the submission text. The keywords
are the one addition; they are not part of the submission manuscript.

Checks, written to review_checks.txt (the build fails if a hard check fails):
  text identity  the body paragraphs of the review docx equal the submission manuscript's, in
                 order, and each appears in order in the PDF's text layer (running header and
                 page numbers excluded)
  number audit   paper/check_docx_numbers.py's classification applied to the review docx;
                 table cells must equal their source CSV cells; 0 unmatched
  floats         every figure and table appears once, numbered in order, directly after the
                 paragraph that first cites it
  references     every VERIFIED reference is cited and listed
  layout         page count; text or table rules past the page margins; a table wider than
                 its column or page (measured by Word); a heading last in a column or on a
                 page; a figure whose caption is not below it on the same page (reported only)

Requires Microsoft Word on Windows (via pywin32) for the table autofit and the PDF export.
Run after build_all.py: python paper/build_review_pdf.py
"""
from __future__ import annotations

import collections
import copy
import csv
import os
import re
import sys
import unicodedata

import docx
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_docx as bd  # noqa: E402
import check_docx_numbers as cdn  # noqa: E402

HERE, REPO = bd.HERE, bd.REPO
OUTDIR = os.path.join(HERE, "review")
DOCX_OUT = os.path.join(OUTDIR, "Manuscript_review_copy.docx")
PDF_OUT = os.path.join(OUTDIR, "Manuscript_review_copy.pdf")
REPORT = os.path.join(OUTDIR, "review_checks.txt")

PAGE_W, PAGE_H, MARGIN = Cm(21.0), Cm(29.7), Cm(2.0)
COL_GAP = Cm(0.6)
TEXT_W_CM, LAND_W_CM = 17.0, 25.7
COL_W_CM = (TEXT_W_CM - 0.6) / 2
FIG_MAX_H = Cm(10.0)
BODY_PT, ABSTRACT_PT, CAPTION_PT, REF_PT, KEYWORD_PT = 10.5, 10, 9, 9, 9.5
CELL_PAD_TWIPS = 28                       # 0.05 cm left and right in table cells
SHORT_TITLE = bd.COVER["title"].split("? ")[0] + "?"
KEYWORDS = ("microservices; fault injection; graph centrality; failure propagation; "
            "distributed tracing; preregistration")
REVIEW_NOTE = "Review copy for internal feedback, not the journal submission format"
PLACEHOLDER = re.compile(r"\[(?:TO FILL[^\]]*|Guide to confirm)\]")
ZWSP = "​"
PAD = 6.5                                 # pt tolerance for table rules at the margins
KEEP_ROWS = 13                            # tables up to this many rows are kept in one piece
APPENDIX_A = {"heading": "Appendix A. Supplementary recovery-time estimates",
              "label": "Table A1",
              "file": "paper/tables/tbl_trec_supplementary.csv"}
CAPTION_LABEL = re.compile(r"^(Table|Figure) (A?\d+)\. ")
MENTION = re.compile(r"\b(Tables?|Figures?|Figs?\.)\s+(\d+)((?:\s*(?:,|and)\s*\d+)*)")
# Child order of w:pPr (ECMA-376), for inserting borders and shading in the right place.
PPR_SEQ = ["w:pStyle", "w:keepNext", "w:keepLines", "w:pageBreakBefore", "w:framePr",
           "w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr", "w:shd",
           "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
           "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi",
           "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing",
           "w:mirrorIndents", "w:suppressOverlap", "w:jc", "w:textDirection",
           "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId",
           "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange"]


# ── docx helpers ──────────────────────────────────────────────────────────────

_plain_add_runs = bd.add_runs


def add_runs_highlighted(par, text):
    """build_docx.add_runs, with [TO FILL] placeholders highlighted in yellow."""
    pos = 0
    for m in PLACEHOLDER.finditer(text):
        _plain_add_runs(par, text[pos:m.start()])
        par.add_run(m.group(0)).font.highlight_color = WD_COLOR_INDEX.YELLOW
        pos = m.end()
    _plain_add_runs(par, text[pos:])


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


def border(sides, sz="6", space="4"):
    b = OxmlElement("w:pBdr")
    for side in sides:
        e = OxmlElement("w:" + side)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), sz)
        e.set(qn("w:space"), space)
        e.set(qn("w:color"), "000000")
        b.append(e)
    return b


def box(p_el):
    """Border and light shading; Word joins adjacent boxed paragraphs into one box."""
    pPr = p_el.get_or_add_pPr()
    insert_ppr(pPr, border(("top", "left", "bottom", "right"), space="6"))
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F2F2F2")
    insert_ppr(pPr, shd)
    ind = OxmlElement("w:ind")             # keeps the border inside the page margins
    ind.set(qn("w:left"), "160")
    ind.set(qn("w:right"), "160")
    insert_ppr(pPr, ind)


def tiny_paragraph():
    """An empty 1 pt paragraph to carry a section break where no paragraph precedes it."""
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
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, MARGIN)
    section.header_distance = section.footer_distance = Cm(1.0)
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


def width_needed(rows, pt):
    """Rough minimum table width in cm: the longest unbreakable piece of each column."""
    cw = 0.0168 * pt
    total = 0.0
    for j in range(len(rows[0])):
        pieces = [t for r in rows for t in re.split(r"\s+|(?<=[_/-])", r[j]) if t]
        total += max((len(t) for t in pieces), default=1) * cw + 0.15
    return total


# ── build ─────────────────────────────────────────────────────────────────────

class ReviewBuilder(bd.Builder):
    def __init__(self):
        super().__init__()
        self.doc = Document()
        bd.style_document(self.doc, line_numbers=False)
        st = self.doc.styles
        normal = st["Normal"]
        normal.font.size = Pt(BODY_PT)
        normal.paragraph_format.line_spacing = 1.0
        normal.paragraph_format.space_after = Pt(4)
        normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for name in ("Heading 1", "Heading 2", "Heading 3"):
            pf = st[name].paragraph_format
            pf.keep_with_next, pf.space_before, pf.space_after = True, Pt(10), Pt(4)
        st["Title"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap = st["Caption"]
        cap.font.name, cap.font.size = bd.FONT, Pt(CAPTION_PT)
        cap.font.bold, cap.font.italic = False, False
        cap.font.color.rgb = RGBColor(0, 0, 0)
        rf = cap.element.get_or_add_rPr().get_or_add_rFonts()
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            rf.attrib.pop(qn(a), None)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(a), bd.FONT)
        cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        cap.paragraph_format.line_spacing = 1.0
        cap.paragraph_format.space_after = Pt(6)
        for name, size in (("Keywords", KEYWORD_PT), ("Reference", REF_PT)):
            s = st.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            s.base_style = normal
            s.font.size = Pt(size)
        ref = st["Reference"].paragraph_format
        ref.alignment = WD_ALIGN_PARAGRAPH.LEFT
        ref.left_indent, ref.first_line_indent, ref.space_after = Cm(0.4), Cm(-0.4), Pt(2)
        self.mode = "span"          # "span" (one column), "two" (two columns) or "land"
        self.floats = []            # (label, kind, file, transposed) in document order
        self.unplaced = []

    # sections ---------------------------------------------------------------
    def section_break(self, start, landscape, cols):
        """End the current section and start a new one. The break sits on its own 1 pt
        paragraph: Word stretches a justified line that ends in a section break."""
        body = self.doc.element.body
        sent = body.find(qn("w:sectPr"))
        carrier = tiny_paragraph()
        sent.addprevious(carrier)
        insert_ppr(carrier.find(qn("w:pPr")), copy.deepcopy(sent))
        # The new section inherits the first section's header and footer.
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
                self.section_break("continuous", False, 1)    # balances the columns
            self.section_break("nextPage", True, 1)
        else:
            self.section_break("nextPage" if cur == "land" else "continuous", False,
                               2 if mode == "two" else 1)
        self.mode = mode

    # floats -----------------------------------------------------------------
    def table_plan(self, f, transposed=None, force_land=False):
        rows = bd.read_csv_rows(os.path.join(REPO, f))
        if transposed is None:
            transposed = len(rows) - 1 <= 2 and len(rows[0]) >= 10
        if transposed:
            rows = [list(col) for col in zip(*rows)]
            shown = [[bd.header_with_unit(r[0])] + r[1:] for r in rows]
        else:
            shown = [[bd.header_with_unit(h) for h in rows[0]]] + rows[1:]
        longest = max(len(c) for r in shown for c in r)
        ncols = len(shown[0])
        if not force_land and longest <= 300:
            if ncols <= 3 and width_needed(shown, 8) <= COL_W_CM:
                return rows, transposed, "two", 8
            for pt in (7.5, 7, 6.5):
                if width_needed(shown, pt) <= TEXT_W_CM:
                    return rows, transposed, "span", pt
        for pt in (8, 7.5, 7):
            if width_needed(shown, pt) <= LAND_W_CM:
                return rows, transposed, "land", pt
        return rows, transposed, "land", 6.5

    def place_new(self, before):
        new = [f for f in self.number if f not in before]
        for f in new:
            kind, n = self.number[f]
            if kind == "Figure":
                self.goto("span")
                self.add_figure("Figure %d" % n, f)
            else:
                rows, transposed, mode, pt = self.table_plan(f)
                self.goto(mode)
                self.add_table("Table %d" % n, f, rows, transposed, pt,
                               keep_together=mode != "land" and len(rows) <= KEEP_ROWS)
        if new:
            self.goto("two")

    def add_figure(self, label, f):
        base = os.path.splitext(os.path.basename(f))[0]
        png = os.path.join(REPO, os.path.splitext(f)[0] + ".png")
        w, h = Image.open(png).size
        width = Cm(TEXT_W_CM)
        if width * h / w > FIG_MAX_H:
            width = int(FIG_MAX_H * w / h)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(6)
        p.add_run().add_picture(png, width=width)
        c = self.doc.add_paragraph(style="Caption")
        c.add_run(label + ". ").bold = True
        c.add_run(self.fig_caps.get(base, base))
        self.floats.append((label, "Figure", f, False))

    def add_table(self, label, f, rows, transposed, pt, caption=None, keep_together=False):
        base = os.path.splitext(os.path.basename(f))[0]
        ncols = len(rows[0])
        c = self.doc.add_paragraph(style="Caption")
        c.paragraph_format.keep_with_next = True
        c.paragraph_format.space_before = Pt(6)
        c.add_run(label + ". ").bold = True
        c.add_run(caption or self.tbl_caps.get(base, base))
        t = self.doc.add_table(rows=len(rows), cols=ncols)
        t.style = "Table Grid"
        t.autofit = True
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
                par.paragraph_format.line_spacing = 1.0
                par.paragraph_format.space_after = Pt(0)
                r = par.add_run(wrap_points(text))
                r.font.size = Pt(pt)
                r.bold = head or (transposed and i == 0)
        if keep_together:
            # Keep a column or full-width table in one piece: no row splits, and every
            # row kept with the next.
            for row in t.rows:
                cs = OxmlElement("w:cantSplit")
                row._tr.get_or_add_trPr().append(cs)
            for row in t.rows:                  # the last row stays with the notes
                for cell in row.cells:
                    for par in cell.paragraphs:
                        par.paragraph_format.keep_with_next = True
        trPr = t.rows[0]._tr.get_or_add_trPr()
        hdr = OxmlElement("w:tblHeader")
        hdr.set(qn("w:val"), "true")
        trPr.append(hdr)
        notes = [bd.TABLE_NOTE] + ([bd.TABLE_FOOTNOTES[base]] if base in bd.TABLE_FOOTNOTES
                                   else [])
        for k, note in enumerate(notes):
            p = self.doc.add_paragraph(note, style="Caption")
            p.runs[0].font.size = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = keep_together and k < len(notes) - 1
        self.floats.append((label, "Table", f, transposed))

    # text -------------------------------------------------------------------
    def paragraph(self, text, style=None):
        before = set(self.number)
        super().paragraph(text, style)
        self.place_new(before)

    def abstract(self):
        body = self.doc.element.body
        old = set(body.iterchildren())
        before = set(self.number)
        super().abstract()
        for el in body.iterchildren():
            if el not in old and el.tag == qn("w:p"):
                box(el)
                for r in el.iter(qn("w:r")):
                    rPr = r.get_or_add_rPr()
                    if rPr.find(qn("w:sz")) is None and \
                            el.find(qn("w:pPr") + "/" + qn("w:pStyle")) is None:
                        sz = OxmlElement("w:sz")
                        sz.set(qn("w:val"), str(int(ABSTRACT_PT * 2)))
                        rPr.append(sz)
        self.place_new(before)

    def title_block(self):
        doc = self.doc
        sec = doc.sections[0]
        configure(sec, landscape=False, cols=1)
        sec.different_first_page_header_footer = True
        hp = sec.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = hp.add_run(SHORT_TITLE)
        r.italic, r.font.size = True, Pt(9)
        insert_ppr(hp._p.get_or_add_pPr(), border(("bottom",), sz="4", space="1"))
        for footer in (sec.footer, sec.first_page_footer):
            fp = footer.paragraphs[0]
            fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_field(fp, "PAGE", "1")

        doc.add_heading(bd.COVER["title"], level=0)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for i, (name, aff) in enumerate(bd.COVER["authors"]):
            r = p.add_run(("" if i == 0 else ", ") + name)
            r.font.size = Pt(11)
            p.add_run(str(aff)).font.superscript = True
        for n, aff in enumerate(bd.COVER["affiliations"], 1):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(str(n)).font.superscript = True
            r = p.add_run(" " + aff)
            r.italic, r.font.size = True, Pt(9.5)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_runs_highlighted(p, "Corresponding author: " + bd.COVER["corresponding"])
        for r in p.runs:
            r.font.size = Pt(9.5)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(REVIEW_NOTE)
        r.italic, r.font.size = True, Pt(8.5)

    def build_review(self):
        bd.add_runs = add_runs_highlighted
        try:
            self.title_block()
            for heading, prose, outline in bd.SECTIONS:
                if prose == bd.ABSTRACT_FILE:
                    self.abstract()
                    p = self.doc.add_paragraph(style="Keywords")
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p.paragraph_format.space_before = Pt(6)
                    p.paragraph_format.space_after = Pt(10)
                    p.add_run("Keywords: ").bold = True
                    p.add_run(KEYWORDS)
                    self.goto("two")
                elif bd.has_prose(prose):
                    for kind, text in bd.blocks(bd.read(prose)):
                        if kind.startswith("h"):
                            self.doc.add_heading(bd.MARKER.sub("", text).strip(),
                                                 level=int(kind[1]))
                        else:
                            self.paragraph(text, style={"quote": "Quote",
                                                        "li": "List Bullet"}.get(kind))
                else:
                    self.to_write(bd.outline_heading(outline, heading))

            self.doc.add_heading("References", level=1)
            years = bd.year_suffixes(self.refs, list(self.refs))
            for k in sorted(self.refs, key=lambda k: (bd.surnames(self.refs[k])[0].lower(),
                                                      years[k], self.refs[k]["title"])):
                self.doc.add_paragraph(bd.format_reference(self.refs[k], years[k]),
                                       style="Reference")

            rows, transposed, _, pt = self.table_plan(APPENDIX_A["file"], transposed=True,
                                                      force_land=True)
            self.goto("land")
            self.doc.add_heading(APPENDIX_A["heading"], level=1)
            self.add_table(APPENDIX_A["label"], APPENDIX_A["file"], rows, transposed,
                           min(pt, 6.5))
        finally:
            bd.add_runs = _plain_add_runs

        # Times New Roman throughout: the submission sets code identifiers in Courier New.
        for rf in self.doc.element.body.iter(qn("w:rFonts")):
            if rf.get(qn("w:ascii")) == "Courier New":
                for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                    rf.set(qn(a), bd.FONT)
                sz = rf.getparent().find(qn("w:sz"))
                if sz is not None:
                    rf.getparent().remove(sz)

        self.unplaced = sorted(f for f in set(self.draft_map.values()) if f not in self.number)
        cp = self.doc.core_properties
        cp.author, cp.title, cp.comments = "", "", "built by paper/build_review_pdf.py"
        os.makedirs(OUTDIR, exist_ok=True)
        self.doc.save(DOCX_OUT)


def word_finalize(docx_path, pdf_path):
    """Fit tables to their column or page, save, export the PDF, and measure each table
    against the column or page it sits in."""
    import win32com.client
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    geometry = []
    try:
        d = word.Documents.Open(os.path.abspath(docx_path), False, False)
        for t in d.Tables:
            t.AutoFitBehavior(1)      # fit to contents
            t.AutoFitBehavior(2)      # then to the column or page width
        d.Repaginate()
        for i in range(1, d.Tables.Count + 1):
            t = d.Tables(i)
            x = t.Range.Information(5)            # wdHorizontalPositionRelativeToPage
            row = t.Rows(1)
            w = sum(row.Cells(k).Width for k in range(1, row.Cells.Count + 1))
            ps = t.Range.Sections(1).PageSetup
            left, right = ps.LeftMargin, ps.PageWidth - ps.RightMargin
            ncol = ps.TextColumns.Count
            if ncol > 1:
                cw, gap = ps.TextColumns(1).Width, ps.TextColumns(1).SpaceAfter
                if x < left + cw:
                    right = left + cw
                else:
                    left = left + cw + gap
            geometry.append((i, ncol, x - CELL_PAD_TWIPS / 20.0, w, left, right))
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

def nfkc_compact(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", clean(s)))


def kind_of(style):
    return style if style.startswith("Heading") else "body"


def body_paragraphs(path, review):
    """(heading level or 'body', text) from Abstract to the end of References. In the review
    copy, captions, table notes, keywords, images and the appendix are left out."""
    out, started = [], not review
    for p in docx.Document(path).paragraphs:
        t, st = clean(p.text).strip(), p.style.name
        if review:
            if not started:
                if st == "Heading 1" and t == "Abstract":
                    started = True
                else:
                    continue
            if st == "Heading 1" and t.startswith("Appendix"):
                break
            if st in ("Caption", "Keywords"):
                continue
        elif st == "Title":
            continue
        if t:
            out.append((kind_of(st), t))
    return out


def check_identity(review_docx, pdf_path, L):
    sub = body_paragraphs(bd.OUT, review=False)
    rev = body_paragraphs(review_docx, review=True)
    diffs = [(i, sub[i] if i < len(sub) else None, rev[i] if i < len(rev) else None)
             for i in range(max(len(sub), len(rev)))
             if (sub[i] if i < len(sub) else None) != (rev[i] if i < len(rev) else None)]
    L.append("Text identity, docx: %d submission paragraphs, %d review paragraphs, "
             "%d differences" % (len(sub), len(rev), len(diffs)))
    for i, a, b in diffs[:10]:
        L.append("  paragraph %d\n    submission: %r\n    review:     %r" % (i, a, b))

    import pdfplumber
    m = MARGIN.pt
    stream, body_started = [], False
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(extra_attrs=["size"], use_text_flow=True)
            if not body_started:
                body_started = any(w["text"] == "Abstract" and w["size"] > 13 for w in words)
                if not body_started:
                    continue
            for w in words:
                if w["bottom"] < m - 1 or w["top"] > page.height - m + 1:
                    continue        # running header, page number
                stream.append(w["text"])
    S = nfkc_compact("".join(stream))
    pos, missing = 0, []
    for _, t in sub:
        k = S.find(nfkc_compact(t), pos)
        if k < 0:
            missing.append(t)
        else:
            pos = k + len(nfkc_compact(t))
    L.append("Text identity, PDF text layer: %d of %d submission paragraphs found in order"
             % (len(sub) - len(missing), len(sub)))
    for t in missing[:10]:
        L.append("  not found: %s" % t[:160])
    return not diffs and not missing


def audit_review(review_docx, sources, L):
    nums, strings, by_id = cdn.load_numbers()
    sent_ids = cdn.draft_sentence_ids()
    counts = collections.Counter()
    flagged = []
    d = docx.Document(review_docx)
    pmap = {p._p: p for p in d.paragraphs}
    tmap = {t._tbl: t for t in d.tables}
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
            m = CAPTION_LABEL.match(txt)
            if m:
                label = "%s %s" % m.groups()
            if section == "title block":
                if txt.endswith(bd.AFFILIATION) and txt[:-len(bd.AFFILIATION)].strip().isdigit():
                    counts["affiliation marker"] += 1
                    txt = bd.AFFILIATION
                txt = re.sub(r"(?<=[A-Za-z])\d$|(?<=[A-Za-z])\d(?=,)", "", txt)  # author marks
            if section == "References" and not heading:
                counts["reference entry"] += len(cdn.NUMBER.findall(cdn.norm(txt)))
                continue
            for sent in ([txt] if heading or st == "Title" else cdn.SENT.split(txt)):
                marked = [by_id[i] for i in sent_ids.get(cdn.key(sent), ()) if i in by_id]
                for tok, cat in cdn.classify_text(sent, heading or st == "Title", nums,
                                                  strings, 0, marked):
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
                    a, b = (j, i) if transposed else (i, j)
                    head = (j == 0) if transposed else (i == 0)
                    same = (srows is not None and a < len(srows) and b < len(srows[a])
                            and srows[a][b] == ct)
                    cat = "table header" if head else "table cell" if same else "UNMATCHED"
                    counts[cat] += len(toks)
                    if cat == "UNMATCHED":
                        flagged.append((cat, label, ct, ""))
    L.append("Number audit (review docx): " + ", ".join(
        "%s %d" % (k, v) for k, v in sorted(counts.items())))
    for cat, sec, tok, sent in flagged:
        L.append("  %s [%s] %s | %s" % (cat, sec, tok, sent[:140]))
    return counts["UNMATCHED"]


def check_floats(review_docx, b, L):
    d = docx.Document(review_docx)
    seen, problems, first_cite = [], [], {}
    body_index = -1
    for p in d.paragraphs:
        txt, st = clean(p.text).strip(), p.style.name
        m = CAPTION_LABEL.match(txt) if st == "Caption" else None
        if m:
            kind, num = m.groups()
            seen.append((kind, num))
            if not num.startswith("A") and first_cite.get((kind, num)) != body_index:
                problems.append("%s %s is not directly after the paragraph that first "
                                "cites it" % (kind, num))
            continue
        if not txt or st in ("Caption", "Keywords") or \
                st.lower().startswith(("title", "heading")):
            continue
        body_index += 1
        for mm in MENTION.finditer(txt):
            k = "Table" if mm.group(1).startswith("Table") else "Figure"
            for n in [mm.group(2)] + re.findall(r"\d+", mm.group(3) or ""):
                first_cite.setdefault((k, n), body_index)
    for kind in ("Figure", "Table"):
        got = [n for k, n in seen if k == kind and not n.startswith("A")]
        want = [str(i) for i in range(1, len(got) + 1)]
        if got != want:
            problems.append("%s order %s, expected %s" % (kind, got, want))
    dup = [x for x, c in collections.Counter(seen).items() if c > 1]
    if dup:
        problems.append("appear more than once: %s" % dup)
    if b.unplaced:
        problems.append("never cited, not placed: %s" % b.unplaced)
    nfig = sum(1 for k, n in seen if k == "Figure")
    ntab = sum(1 for k, n in seen if k == "Table" and not n.startswith("A"))
    L.append("Floats: %d figures and %d tables in the body, each once, in citation order, "
             "directly after the paragraph that first cites it; appendix tables: %s; "
             "problems: %d" % (nfig, ntab, [k + " " + n for k, n in seen
                                            if n.startswith("A")], len(problems)))
    for x in problems:
        L.append("  " + x)
    return not problems


def check_references(review_docx, b, L):
    d = docx.Document(review_docx)
    listed, inside = 0, False
    for p in d.paragraphs:
        if p.style.name == "Heading 1":
            inside = p.text.strip() == "References"
            continue
        if inside and p.text.strip():
            listed += 1
    ok = listed == len(b.refs) and set(b.cited) == set(b.refs)
    L.append("References: %d VERIFIED, %d listed, %d cited" % (len(b.refs), listed,
                                                               len(b.cited)))
    return ok


def check_layout(review_docx, pdf_path, geometry, floats, L):
    import pdfplumber
    headings = {nfkc_compact(p.text) for p in docx.Document(review_docx).paragraphs
                if p.style.name.startswith("Heading") and p.text.strip()}
    m = MARGIN.pt
    issues = []
    labels = [lab for lab, kind, _, _ in floats if kind == "Table"]
    for (i, ncol, x, w, left, right), lab in zip(geometry, labels):
        if x + w > right + 2 or x < left - PAD:
            issues.append("%s is wider than its %s (%.0f pt over)"
                          % (lab, "column" if ncol > 1 and right - left < 300 else "page",
                             x + w - right))
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        for no, page in enumerate(pdf.pages, 1):
            W, H = page.width, page.height
            words = [w for w in page.extract_words(use_text_flow=True)
                     if w["bottom"] > m - 1 and w["top"] < H - m + 1]
            over = [w["text"] for w in words if w["x1"] > W - m + 2 or w["x0"] < m - 2]
            rules = [e for e in page.edges if e["x1"] > W - m + PAD or e["x0"] < m - PAD]
            if over or rules:
                issues.append("page %d: content past the page margin (%s)"
                              % (no, ", ".join(over[:5]) or "table rules"))
            mid = W / 2
            columns = {"page": words} if W > H else {
                "left column": [w for w in words if w["x1"] <= mid + 1],
                "right column": [w for w in words if w["x0"] >= mid - 1]}
            for where, ws in columns.items():
                lines = collections.OrderedDict()
                for w in sorted(ws, key=lambda w: (round(w["top"]), w["x0"])):
                    lines.setdefault(round(w["top"]), []).append(w["text"])
                if not lines:
                    continue
                last = " ".join(lines[max(lines)])
                if nfkc_compact(last) in headings:
                    issues.append("page %d: heading '%s' is the last line of the %s"
                                  % (no, last, where))
                if CAPTION_LABEL.match(last) and last.startswith("Table"):
                    issues.append("page %d: a table title is the last line of the %s"
                                  % (no, where))
            for img in page.images:
                below = [w for w in words if w["top"] > img["bottom"] - 1
                         and w["text"] == "Figure"]
                if not below:
                    issues.append("page %d: a figure without its caption below it" % no)
    L.append("Layout: %d pages; problems: %d" % (n, len(issues)))
    for x in issues:
        L.append("  " + x)
    return n, issues


def main():
    b = ReviewBuilder()
    b.build_review()
    pages, geometry = word_finalize(DOCX_OUT, PDF_OUT)
    sources = {label: (os.path.join(REPO, f), tr) for label, kind, f, tr in b.floats
               if kind == "Table"}
    L = ["review_checks.txt -- written by paper/build_review_pdf.py",
         "Review copy: paper/review/Manuscript_review_copy.pdf (%d pages in Word) and .docx"
         % pages, ""]
    ok_text = check_identity(DOCX_OUT, PDF_OUT, L)
    unmatched = audit_review(DOCX_OUT, sources, L)
    ok_floats = check_floats(DOCX_OUT, b, L)
    ok_refs = check_references(DOCX_OUT, b, L)
    n, issues = check_layout(DOCX_OUT, PDF_OUT, geometry, b.floats, L)
    todo = [m.group(0) for p in docx.Document(DOCX_OUT).paragraphs
            for m in PLACEHOLDER.finditer(p.text)]
    L.append("Placeholders (highlighted): %s" % ("; ".join(todo) or "none"))
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))
    failed = [name for name, ok in (("text identity", ok_text),
                                    ("number audit", unmatched == 0),
                                    ("floats", ok_floats), ("references", ok_refs)) if not ok]
    if failed:
        print("REVIEW BUILD FAILED: %s" % ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
