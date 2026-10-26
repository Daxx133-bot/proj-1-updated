"""
build_all.py -- regenerate every artifact under paper/ in dependency order, then index them.

    build_numbers.py   analysis/final/*.csv        -> numbers.csv
    emit_macros.py     numbers.csv                 -> numbers.tex, numbers.json
    make_tables.py     analysis/final/*.csv        -> tables/*.csv, tables/*.md
    make_figures.py    analysis/final/*.csv, spans -> figures/*.png, *.pdf, *_data.csv
    check_ledger.py    CLAIMS_LEDGER.md + numbers.csv -> pass/fail
    build_docx.py      draft/*.md, tables, figures, references.csv -> manuscript.docx,
                       submission/ (manuscript copy, figures, legends, tables, cover
                       page, cover letter)
    check_docx_numbers.py  manuscript.docx + numbers.csv -> number_audit.txt (report only)
    build_latex.py     latex/main.tex, latex/sections/*.tex, numbers.csv, tables, figures,
                       references.csv -> latex/manuscript_ieee.pdf, latex/generated/,
                       latex/overleaf_upload.zip, latex/latex_checks.txt (IEEE Access
                       manuscript, compiled with LaTeX; fails the build if a check fails)
    make_checklist.py  submission/, number_audit.txt -> submission/SUBMISSION_CHECKLIST.md,
                       submission/FORM_ANSWERS.md

Finally writes paper/INDEX.csv, one row per file under paper/, naming the script that
produced it. A failing ledger check fails the build. The number audit never fails the
build; its findings are in number_audit.txt.

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
         "check_ledger.py", "build_docx.py", "check_docx_numbers.py", "make_checklist.py",
         "build_latex.py"]

PRODUCER = {
    "numbers.csv": "paper/build_numbers.py",
    "numbers.tex": "paper/emit_macros.py",
    "numbers.json": "paper/emit_macros.py",
    "INDEX.csv": "paper/build_all.py",
    "CLAIMS_LEDGER.md": "hand-written, validated by paper/check_ledger.py",
    "manuscript.docx": "paper/build_docx.py",
    "number_audit.txt": "paper/check_docx_numbers.py",
    "SUBMISSION_CHECKLIST.md": "paper/make_checklist.py",
    "FORM_ANSWERS.md": "paper/make_checklist.py",
    "manuscript.pdf": ("exported from manuscript.docx by Microsoft Word, for reading only; "
                       "not part of the submission"),
    "references.csv": ("keys and DOIs hand-entered; bibliographic fields from Crossref via "
                       "paper/check_references.py or paper/verify_candidates.py; only "
                       "VERIFIED rows are rendered"),
    "deviations_short.csv": ("hand-written short labels for the deviations table; read by "
                             "paper/make_tables.py"),
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
            elif base.startswith("latex/build/"):
                continue                            # LaTeX intermediate files, not tracked
            elif base.startswith("latex/generated/") or base in (
                    "latex/manuscript_ieee.pdf", "latex/overleaf_upload.zip",
                    "latex/latex_checks.txt"):
                produced_by = "paper/build_latex.py"
            elif base.startswith("latex/"):
                produced_by = ("hand-written; numbers as \\val{claim_id}, checked by "
                               "paper/build_latex.py")
            elif base.startswith("review/"):
                produced_by = "paper/build_review_pdf.py (run separately; needs Microsoft Word)"
            elif base.startswith("submission/") and fn not in PRODUCER:
                produced_by = "paper/build_docx.py"
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
