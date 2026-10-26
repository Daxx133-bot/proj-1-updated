"""
verify_candidates.py -- verify candidate references against Crossref and add the accepted ones
to paper/references.csv.

For each candidate below, this fetches https://api.crossref.org/works/<DOI> (polite
User-Agent, one request per second). A candidate is ACCEPTED only if the Crossref record's
title matches the expected title after case, punctuation and whitespace are ignored; the
Crossref title is also tried with its subtitle appended, since Crossref stores subtitles
separately. If the DOI lookup fails or the title differs, it queries
https://api.crossref.org/works?query.bibliographic=<expected title>&rows=3 and accepts only an
exact title match. Anything else is REJECTED.

Authors, title, venue, year, volume, issue, pages and DOI are filled from the Crossref record
only, never from this file or from memory. The expected titles below are used for matching and
nothing else; the stored title is the Crossref title that matched, with its subtitle when that
is how it matched. Accepted rows are appended to paper/references.csv with status VERIFIED; keys
already present are left alone.

Needs internet access. If Crossref cannot be reached, nothing is written.

Run: python paper/verify_candidates.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_references import REFS, USER_AGENT, clean, fetch, fields_from  # noqa: E402

PAUSE_S = 1.0
CHECKED_ON = "2026-10-26"
VERIFIED_BY = "Crossref metadata, %s" % CHECKED_ON
SEARCH = "https://api.crossref.org/works?query.bibliographic=%s&rows=3"

# key, DOI, expected title, where it fits in the paper
CANDIDATES = [
    ("albert2000", "10.1038/35019019", "Error and attack tolerance of complex networks",
     "Related Work A: removing central nodes in networks"),
    ("motter2002", "10.1103/PhysRevE.66.065102", "Cascade-based attacks on complex networks",
     "Related Work A: cascading failures and node load"),
    ("bonacich1987", "10.1086/228631", "Power and Centrality: A Family of Measures",
     "Methods: eigenvector centrality"),
    ("brin1998", "10.1016/S0169-7552(98)00110-X",
     "The anatomy of a large-scale hypertextual Web search engine", "Methods: PageRank"),
    ("lengauer1979", "10.1145/357062.357071",
     "A fast algorithm for finding dominators in a flowgraph", "Methods: dominator subtree size"),
    ("jamshidi2018", "10.1109/MS.2018.2141039",
     "Microservices: The Journey So Far and Challenges Ahead",
     "Introduction: microservices background"),
    ("soldani2018", "10.1016/j.jss.2018.09.082",
     "The pains and gains of microservices: A Systematic grey literature review",
     "Introduction: operational difficulties"),
    ("gunawi2016", "10.1145/2987550.2987583",
     "Why Does the Cloud Stop Computing? Lessons from Hundreds of Service Outages",
     "Introduction: outages in cloud services"),
    ("huang2017", "10.1145/3102980.3103005",
     "Gray Failure: The Achilles' Heel of Cloud-Scale Systems",
     "Related Work / Discussion: partial (slow) failures, latency faults"),
    ("basiri2019", "10.1109/ICSE-SEIP.2019.00012", "Automating Chaos Experiments in Production",
     "Related Work B"),
    ("meiklejohn2021", "10.1145/3472883.3487005", "Service-level fault injection testing",
     "Related Work B: fault injection for microservices"),
    ("heinrich2017", "10.1145/3053600.3053653",
     "Performance Engineering for Microservices: Research Challenges and Directions",
     "Introduction / Related Work"),
    ("ma2018", "10.1109/COMPSAC.2018.10207",
     "Using Service Dependency Graph to Analyze and Test Microservices",
     "Related Work A/C: service dependency graphs"),
    ("chen2002", "10.1109/DSN.2002.1029005",
     "Pinpoint: problem determination in large, dynamic Internet services",
     "Related Work D: tracing-based problem determination"),
    ("lin2018", "10.1007/978-3-030-03596-9_1",
     "Microscope: Pinpoint Performance Issues with Causal Graphs in Micro-service Environments",
     "Related Work D: root cause with graphs"),
    ("gan2019seer", "10.1145/3297858.3304004",
     "Seer: Leveraging Big Data to Navigate the Complexity of Performance Debugging in Cloud "
     "Microservices", "Related Work D"),
    ("soldani2022", "10.1145/3501297",
     "Anomaly Detection and Failure Root Cause Analysis in (Micro)Service-Based Cloud "
     "Applications: A Survey", "Related Work D: survey"),
    ("efron1987", "10.1080/01621459.1987.10478410", "Better Bootstrap Confidence Intervals",
     "Methods: BCa intervals"),
    ("cox1972", "10.1111/j.2517-6161.1972.tb00899.x", "Regression Models and Life-Tables",
     "Methods: Cox model"),
    ("phipson2010", "10.2202/1544-6115.1585",
     "Permutation P-values Should Never Be Zero: Calculating Exact P-values When Permutations "
     "Are Randomly Drawn", "Methods: permutation p-values"),
]


def norm(s):
    """Title key: lower case, letters and digits only."""
    return re.sub(r"[^a-z0-9]+", "", clean(s).lower())


def titles_of(msg):
    """The Crossref title alone, and with each subtitle appended."""
    t = clean((msg.get("title") or [""])[0])
    out = [t]
    for sub in msg.get("subtitle") or []:
        sep = " " if t.endswith(("?", "!", ":")) else ": "
        out.append(t + sep + clean(sub))
    return out


def matching_title(msg, expected):
    for t in titles_of(msg):
        if norm(t) == norm(expected):
            return t
    return None


def pub_year(msg):
    """Publication year from Crossref's issue dates. The record's creation date is not a
    publication date, so when no issue date exists the year comes from the conference
    acronym in Crossref's event field (e.g. DSN-02), and the second value says so."""
    for k in ("issued", "published-print", "published-online", "published"):
        parts = (msg.get(k) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0]:
            return str(parts[0][0]), ""
    acr = (msg.get("event") or {}).get("acronym", "")
    m = re.search(r"(\d{2})$", acr)
    if m:
        yy = int(m.group(1))
        return str(1900 + yy if yy > 50 else 2000 + yy),             "year from the Crossref event acronym %s (no issue date in Crossref)" % acr
    return "", "no issue date in Crossref"


def search(title):
    url = SEARCH % urllib.parse.quote(title)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["message"].get("items", [])


def main():
    with open(REFS, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        cols, rows = reader.fieldnames, list(reader)
    have = {r["key"] for r in rows}

    report, added = [], []
    for i, (key, doi, expected, _where) in enumerate(CANDIDATES):
        if key in have:
            report.append((key, expected, "(already in references.csv)", "", "", "SKIPPED"))
            continue
        if i:
            time.sleep(PAUSE_S)
        try:
            code, msg = fetch(doi)
            got = matching_title(msg, expected) if code == 200 and msg else None
            how = "DOI"
            if got is None:
                time.sleep(PAUSE_S)
                for item in search(expected):
                    got = matching_title(item, expected)
                    if got:
                        msg, how = item, "title search"
                        break
        except urllib.error.URLError as e:
            print("NO INTERNET ACCESS (or Crossref unreachable): %s. Nothing written." % e)
            return 2
        if got is None:
            shown = titles_of(msg)[0] if code == 200 and msg else "(DOI lookup HTTP %s)" % code
            report.append((key, expected, shown, "", "", "REJECTED"))
            continue
        f = fields_from(msg)
        f["year"], year_note = pub_year(msg)
        row = {c: "" for c in cols}
        row.update(f)
        row.update({"key": key, "title": got, "doi": clean(msg.get("DOI", "")).lower(), "url": "",
                    "status": "VERIFIED", "verified_by_user": VERIFIED_BY})
        if how != "DOI":
            row["verified_by_user"] += " (matched by title search)"
        if year_note:
            row["verified_by_user"] += "; " + year_note
        added.append(row)
        first = f["authors"].split(";")[0].split(",")[0] if f["authors"] else ""
        report.append((key, expected, got, f["year"], first, "ACCEPTED (%s)" % how))

    if added:
        with open(REFS, "a", encoding="utf-8", newline="") as fh:
            csv.DictWriter(fh, fieldnames=cols, lineterminator="\n").writerows(added)

    print("key | expected title | Crossref title | year | first author | result")
    for r in report:
        print(" | ".join(r))
    print("accepted %d, rejected %d, skipped %d"
          % (sum(r[5].startswith("ACCEPTED") for r in report),
             sum(r[5] == "REJECTED" for r in report),
             sum(r[5] == "SKIPPED" for r in report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
