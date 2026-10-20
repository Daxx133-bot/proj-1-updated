# Submission checklist: PeerJ Computer Science

Written by `paper/make_checklist.py`. PASS means the build output meets the requirement; TO DO means a person still has to act.

| Requirement | Status | Detail |
|---|---|---|
| Manuscript supplied as .docx | PASS | paper/submission/manuscript.docx |
| Title under 250 characters | PASS | 102 characters |
| Continuous line numbering | PASS |  |
| US Letter page, 2.5 cm margins | PASS |  |
| Figures and tables not embedded in the manuscript | PASS | 0 tables, 0 drawings |
| Abstract with Background, Methods, Results, Conclusions headings, at most 500 words | PASS | 380 words |
| Each figure supplied as a separate file (PNG and PDF) | PASS | 4 figures |
| Figure legends supplied | PASS |  |
| Each table supplied as a separate .docx with a title | PASS | 10 tables |
| Supplementary data files named in table footnotes supplied | PASS | Supplementary_recovery_time_raw.csv |
| Every reference in the list is cited in the text | PASS | 15 listed, 15 cited |
| Every reference has a DOI or URL | PASS |  |
| No drafting markers, unresolved citations or [TO WRITE] in the manuscript | PASS |  |
| Number audit: every number traced to numbers.csv (0 unmatched) | PASS | paper/number_audit.txt, 0 unmatched |
| Cover page: authors, affiliations, corresponding author | TO DO | cover_page.docx has [TO FILL] |
| Cover letter | TO DO | cover_letter.docx has [TO FILL] |
| Funding statement | PASS |  |
| Competing Interests statement | PASS |  |
| Data Availability statement | TO DO | has [TO FILL] |
| AI-Use Statement | PASS |  |
| Code licence (LICENSE) and data licence (LICENSE-DATA) in the repository | PASS |  |
| Raw data archived with a DOI (Zenodo) | TO DO | Data Availability names a Zenodo DOI to fill |
| Preregistration uploaded as supplementary material (_audit/preregistration_versions/PREREGISTRATION_v3_LOCKED.md) | TO DO | done at submission |
| Competing interests declared in the submission system | TO DO | answer in FORM_ANSWERS.md |
| Funding declared in the submission system | TO DO | answer in FORM_ANSWERS.md |
| Author contributions declared in the submission system | TO DO | draft in FORM_ANSWERS.md, awaiting [Guide to confirm] |
| All authors listed and ORCIDs entered in the submission system | TO DO | done at submission |

## Placeholders (10)

Drafts and `build_docx.py` are the sources; the `.docx` rows are where each one appears after the build.

| Location | Placeholder |
|---|---|
| paper/draft/cover_letter.md:8 | `[TO FILL: date]` |
| paper/draft/cover_letter.md:49 | `[TO FILL: corresponding author name and email]` |
| paper/draft/data_availability.md:5 | `[TO FILL]` |
| paper/build_docx.py:101 | `[TO FILL: corresponding author name and email]` |
| paper/submission/FORM_ANSWERS.md:7 | `[Guide to confirm]` |
| paper/submission/FORM_ANSWERS.md:21 | `[TO FILL]` |
| paper/submission/cover_letter.docx, paragraph 1 | `[TO FILL: date]` |
| paper/submission/cover_letter.docx, paragraph 13 | `[TO FILL: corresponding author name and email]` |
| paper/submission/cover_page.docx, paragraph 4 | `[TO FILL: corresponding author name and email]` |
| paper/submission/manuscript.docx, paragraph 169 | `[TO FILL]` |
