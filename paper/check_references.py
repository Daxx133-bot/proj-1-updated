"""
check_references.py -- fill bibliographic fields in paper/references.csv from Crossref.

For every row with a DOI whose status is not VERIFIED, this fetches
https://api.crossref.org/works/<doi> (polite User-Agent, one request per second) and sets
authors, title, venue, year, volume, issue and pages from the Crossref response only --
never from anything else in the row, and never from memory. Status becomes AUTO_MATCHED if
the DOI resolves and DOI_NOT_FOUND if Crossref returns 404.

It never sets VERIFIED and never touches verified_by_user: an AUTO_MATCHED row says only
that the DOI resolves to the metadata shown, not that it is the work the author meant. A
person checks the printed table and marks a row VERIFIED by hand. paper/build_docx.py
renders only VERIFIED rows. Rows with no DOI are left for manual entry.

Needs internet access. If Crossref cannot be reached, nothing is written.

Run: python paper/check_references.py
"""
from __future__ import annotations

import csv
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "references.csv")
API = "https://api.crossref.org/works/"
USER_AGENT = ("microservice-failure-analysis/check_references.py "
              "(+https://github.com/Daxx133-bot/proj-1-updated)")
PAUSE_S = 1.0
FILLED = ["authors", "title", "venue", "year", "volume", "issue", "pages"]


def clean(s):
    """Crossref titles can carry JATS/HTML markup and entities."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def initials(given):
    parts = [p for p in re.split(r"[\s\-]+", given or "") if p]
    return " ".join(p[0].upper() + "." for p in parts)


def authors_of(msg):
    out = []
    for a in msg.get("author", []):
        if a.get("family"):
            ini = initials(a.get("given", ""))
            out.append("%s, %s" % (clean(a["family"]), ini) if ini else clean(a["family"]))
        elif a.get("name"):
            out.append(clean(a["name"]))
    return "; ".join(out)


def year_of(msg):
    for k in ("issued", "published-print", "published-online", "published", "created"):
        parts = (msg.get(k) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0]:
            return str(parts[0][0])
    return ""


def fields_from(msg):
    """The bibliographic fields, taken from a Crossref 'message' object and nothing else."""
    first = lambda v: clean(v[0]) if isinstance(v, list) and v else clean(v or "")
    return {"authors": authors_of(msg), "title": first(msg.get("title")),
            "venue": first(msg.get("container-title")), "year": year_of(msg),
            "volume": clean(msg.get("volume", "")), "issue": clean(msg.get("issue", "")),
            "pages": clean(msg.get("page", ""))}


def fetch(doi):
    """Return (http_status, message or None). Raises URLError if the network is down."""
    url = API + urllib.parse.quote(doi, safe="/")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.load(r)["message"]
    except urllib.error.HTTPError as e:
        return e.code, None


def main():
    with open(REFS, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        cols, rows = reader.fieldnames, list(reader)

    report = []
    first_request = True
    for row in rows:
        doi = row.get("doi", "").strip()
        if not doi or row.get("status", "").strip() == "VERIFIED":
            report.append((row["key"], doi or "(none)", "", "", "",
                           row.get("status", "")))
            continue
        if not first_request:
            time.sleep(PAUSE_S)
        first_request = False
        try:
            code, msg = fetch(doi)
        except urllib.error.URLError as e:
            print("NO INTERNET ACCESS (or Crossref unreachable): %s. Nothing written." % e)
            return 2
        if code == 200 and msg is not None:
            if msg.get("DOI", "").lower() != doi.lower():
                print("WARNING: %s requested %s, Crossref answered %s"
                      % (row["key"], doi, msg.get("DOI")))
            row.update(fields_from(msg))
            row["status"] = "AUTO_MATCHED"
        elif code == 404:
            for f in FILLED:
                row[f] = ""
            row["status"] = "DOI_NOT_FOUND"
        else:
            print("Crossref returned HTTP %d for %s; row left unchanged." % (code, doi))
        first_author = row["authors"].split(";")[0].split(",")[0] if row["authors"] else ""
        report.append((row["key"], doi, row["title"], row["year"], first_author,
                       row["status"]))

    with open(REFS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print("key | DOI | Crossref title | Crossref year | first author | status")
    for r in report:
        print(" | ".join(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
