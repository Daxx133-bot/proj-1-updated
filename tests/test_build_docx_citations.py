"""Unit tests for the name-year citation rules in paper/build_docx.py.

TEST FIXTURES ONLY. Every reference below is fictional ("Alpha", "Example title ...") and
exists only to exercise the formatting rules. None is a real work and none may be copied
into paper/references.csv.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "paper"))

import build_docx as bd  # noqa: E402


def ref(authors, year, title="Example title", **kw):
    e = {"authors": authors, "year": year, "title": title, "venue": "Example Venue",
         "volume": "", "issue": "", "pages": "", "doi": "", "status": "VERIFIED"}
    e.update(kw)
    return e


REFS = {
    "one": ref("Alpha, A.", "2010"),
    "two": ref("Alpha, A.; Beta, B.", "2005"),
    "three": ref("Alpha, A.; Beta, B.; Gamma, C.", "2012"),
    "four": ref("Delta, D.; Beta, B.; Gamma, C.; Alpha, A.", "2001"),
    "same_a": ref("Omega, O.", "2015", title="Example title A"),
    "same_b": ref("Omega, O.", "2015", title="Example title B"),
}


def cite(text, refs=REFS):
    return bd.resolve_citations(text, refs, [])


def test_author_count_rules():
    assert cite("[@one]") == "(Alpha, 2010)"
    assert cite("[@two]") == "(Alpha & Beta, 2005)"
    assert cite("[@three]") == "(Alpha, Beta & Gamma, 2012)"
    assert cite("[@four]") == "(Delta et al., 2001)"


def test_several_keys_are_chronological_and_semicolon_separated():
    assert cite("[@one; @four; @two]") == "(Delta et al., 2001; Alpha & Beta, 2005; Alpha, 2010)"


def test_same_author_and_year_get_letter_suffixes():
    assert cite("[@same_b; @same_a]") == "(Omega, 2015a; Omega, 2015b)"


def test_unknown_or_unverified_keys_stay_visible():
    assert cite("[@missing]") == "[@missing]"
    assert cite("[@one; @missing]") == "[@one; @missing]"
    assert cite("[CITATION NEEDED: anything]") == "[CITATION NEEDED: anything]"


def test_reference_format_includes_volume_issue_pages_doi():
    e = ref("Alpha, A. B.; Beta, C.", "2010", title="Example title.", volume="12",
            issue="3", pages="45-67", doi="10.0000/example")
    assert bd.format_reference(e, "2010") == \
        "Alpha AB, Beta C. 2010. Example title. Example Venue 12(3):45-67. DOI 10.0000/example."


def test_only_verified_rows_load(tmp_path):
    p = tmp_path / "refs.csv"
    p.write_text("key,authors,title,venue,year,volume,issue,pages,doi,status,verified_by_user\n"
                 "a,\"Alpha, A.\",T,V,2010,,,,,VERIFIED,yes\n"
                 "b,\"Beta, B.\",T,V,2011,,,,,UNVERIFIED,\n", encoding="utf-8")
    assert set(bd.load_refs(str(p))) == {"a"}


def test_reference_without_doi_shows_url():
    e = ref("Alpha, A.", "2010", title="Example report", venue="Example Technical Report",
            url="https://example.org/report")
    assert bd.format_reference(e, "2010") == \
        "Alpha A. 2010. Example report. Example Technical Report. Available at https://example.org/report."
