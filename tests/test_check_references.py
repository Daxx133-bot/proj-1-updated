"""Unit tests for paper/check_references.py field extraction.

TEST FIXTURE ONLY. The Crossref-shaped record below is fictional and exists only to
exercise the parsing rules; it is not a real work.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "paper"))

import check_references as cr  # noqa: E402

FICTIONAL = {
    "DOI": "10.0000/example",
    "title": ["An <i>Example</i> Title &amp; More"],
    "container-title": ["Example Venue"],
    "author": [{"family": "Alpha", "given": "Ann-Marie B"}, {"name": "Example Consortium"}],
    "issued": {"date-parts": [[2010, 5]]},
    "volume": "12", "issue": "3", "page": "45-67",
}


def test_fields_come_only_from_the_crossref_record():
    f = cr.fields_from(FICTIONAL)
    assert f == {"authors": "Alpha, A. M. B.; Example Consortium",
                 "title": "An Example Title & More", "venue": "Example Venue",
                 "year": "2010", "volume": "12", "issue": "3", "pages": "45-67"}


def test_missing_fields_stay_empty():
    f = cr.fields_from({"title": ["T"], "issued": {"date-parts": [[None]]}})
    assert f["year"] == "" and f["venue"] == "" and f["authors"] == ""
