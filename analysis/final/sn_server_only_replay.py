"""
sn_server_only_replay.py -- POST-HOC SENSITIVITY REPLAY. NOT PART OF THE PREREGISTERED
CONFIRMATORY FAMILY. NO STORED OUTCOME IS OVERWRITTEN.

Why this exists (Deviation 11)
------------------------------
measurement/metrics_collector.select_spans chooses a service's own SERVER spans by the
`span.kind` tag. No Social Network span carries that tag (the C++ Jaeger client does not
emit it), so for every Social Network sample the function fell back to ALL of the
service's spans -- client spans included -- while the run records still labelled the
scope "service_server_spans:<svc>". About half of the spans used were `*_client` spans,
which measure a callee's latency as seen by the caller: the re-attribution the per-service
metric was designed to exclude.

This script replays the blast-radius rule for all 110 Social Network campaign runs from
their persisted spans, with per-service latency restricted to spans whose operation name
ends in `_server`. It was specified AFTER the confirmatory results were known. It is
therefore exploratory: it is not FDR-corrected, carries no inferential weight, and does
not change the preregistered verdict in either direction. p-values are nominal.

What is held identical to the campaign
--------------------------------------
* Degradation rule: measurement.metrics_collector.latency_degraded (2.0x relative AND
  +1.0 ms absolute), imported, not copied.
* Error-rate rule: fault error rate > baseline error rate + ERROR_RATE_ABS_THRESHOLD
  (0.05), computed by measurement.metrics_collector.compute_error_rate, which attributes
  errors over all of a service's own spans and never consulted span.kind. Unchanged.
* Classification: measurement.blast_radius.classify_affected (ancestor / descendant /
  unrelated relative to the faulted service in the canonical graph).
* Service skipping as in compute_blast_radius: the faulted service, infrastructure names,
  and services with no traces in the fault window.
* nginx-web-server (the SN gateway) reports HTTP operation names such as
  "/wrk2-api/post/compose" rather than "*_server" names. It keeps the existing handling
  (metrics_collector.select_spans, i.e. all of its spans). Only the 11 Thrift services
  change rule.

Emulating the live Jaeger query
-------------------------------
The runner queried Jaeger once per service (`/api/traces?service=X&limit=500`); the
persisted file for a window is the de-duplicated union of those queries. To recover what
each live query saw, the replay takes the traces containing a span from X and, where more
than 500 exist, keeps the 500 with the latest start time (Jaeger's in-memory store returns
the most recent traces first). This cannot be exact: traces whose spans reached Jaeger
after the live query are present in the persisted file but were not seen live. The replay
is therefore validated before it is used (below), and every Social Network difference is
reported against BOTH the stored value and an existing-rule replay of the same bytes, so a
difference caused by the rule change can be told apart from one caused by replaying.

Validation
----------
1. The 70 Hotel Reservation runs (whose spans DO carry span.kind) are replayed with the
   existing rule. Their stored ancestor/descendant/unrelated counts must reproduce exactly
   or this script writes nothing and exits 1.
2. The 110 Social Network runs are also replayed with the existing rule, as a control.

What cannot be replayed
-----------------------
Recovery-probe windows were not persisted, so Social Network T_rec cannot be replayed
under the server-only rule. T_rec values remain as stored.

Inputs : data/spans/*.json.gz                (all latency and error measurements)
         data/graphs/{sn,hr}_CANONICAL.json  (ancestor/descendant sets, ancestor_count)
         data/campaign/runs/*.json           (read ONLY for each run's span-file paths and
                                              its stored A/D/U counts, for comparison;
                                              no stored metric is used in the replay)
Outputs: analysis/final/sn_server_only_replay.csv        (one row per run)
         analysis/final/sn_server_only_replay_tests.csv  (service-level Spearman tests)
         analysis/final/sn_server_only_replay.md

Run: python analysis/final/sn_server_only_replay.py
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys
from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from analysis.final.exact_p_supplement import exact_p  # noqa: E402
from measurement.blast_radius import classify_affected  # noqa: E402
from measurement.metrics_collector import (  # noqa: E402
    DEGRADATION_FACTOR,
    DEGRADATION_FLOOR_MS,
    ERROR_RATE_ABS_THRESHOLD,
    compute_error_rate,
    compute_latency_percentiles,
    latency_degraded,
    select_spans,
    span_service_map,
)

RUNS = os.path.join(REPO, "data", "campaign", "runs")
GRAPHS = {"socialnetwork": os.path.join(REPO, "data", "graphs", "sn_CANONICAL.json"),
          "hotelreservation": os.path.join(REPO, "data", "graphs", "hr_CANONICAL.json")}
OUT_DIR = os.path.join(REPO, "analysis", "final")
OUT_CSV = os.path.join(OUT_DIR, "sn_server_only_replay.csv")
OUT_TESTS = os.path.join(OUT_DIR, "sn_server_only_replay_tests.csv")
OUT_MD = os.path.join(OUT_DIR, "sn_server_only_replay.md")

JAEGER_LIMIT = 500                    # get_traces_in_window's default, used by the runner
SN_GATEWAY = "nginx-web-server"
# compute_blast_radius skips these substrings (metrics_collector.compute_blast_radius).
INFRA = ("jaeger", "mongo", "redis", "memcached")
LABEL = "POST-HOC SENSITIVITY REPLAY -- exploratory, not preregistered, not FDR-corrected"


def load_graph(app: str) -> nx.DiGraph:
    with open(GRAPHS[app], encoding="utf-8") as fh:
        return nx.node_link_graph(json.load(fh), edges="edges")


def load_traces(rel: str) -> list[dict]:
    with gzip.open(os.path.join(REPO, rel), "rt", encoding="utf-8") as fh:
        return json.load(fh)["traces"]


def live_query(traces: list[dict], service: str) -> list[dict]:
    """Emulate Jaeger /api/traces?service=X&limit=500 over a persisted window."""
    sub = [t for t in traces if service in span_service_map(t).values()]
    if len(sub) <= JAEGER_LIMIT:
        return sub
    return sorted(sub, key=lambda t: min(s["startTime"] for s in t["spans"]))[-JAEGER_LIMIT:]


def p95_existing(traces: list[dict], service: str) -> float:
    """The campaign's own rule: metrics_collector.compute_latency_percentiles."""
    return compute_latency_percentiles(traces, service=service)["p95_ms"]


def p95_server_only(traces: list[dict], service: str) -> float:
    """Server-only rule: own spans whose operation name ends in "_server".

    The gateway keeps the existing handling (select_spans). Percentile arithmetic is the
    same as compute_latency_percentiles: durations in microseconds / 1000, np.percentile.
    """
    if service == SN_GATEWAY:
        spans = select_spans(traces, service)
    else:
        spans = []
        for t in traces:
            pmap = span_service_map(t)
            spans.extend(s for s in t.get("spans", [])
                         if pmap.get(s.get("processID")) == service
                         and str(s.get("operationName", "")).endswith("_server"))
    if not spans:
        return 0.0
    return float(np.percentile([float(s.get("duration", 0)) / 1000.0 for s in spans], 95))


def replay_run(rec: dict, G: nx.DiGraph, p95_fn) -> list[str]:
    """Return the affected set for one run under the given per-service p95 rule."""
    base_tr = load_traces(rec["raw_spans"]["baseline_window"]["path"])
    fault_tr = load_traces(rec["raw_spans"]["fault_window"]["path"])
    faulted = rec["service"]
    affected = []
    for svc in sorted(G.nodes()):
        if svc == faulted or any(i in svc.lower() for i in INFRA):
            continue
        f_sub = live_query(fault_tr, svc)
        if not f_sub:
            continue
        b_sub = live_query(base_tr, svc)
        b_p95 = p95_fn(b_sub, svc) if b_sub else 0.0
        b_err = compute_error_rate(b_sub, service=svc) if b_sub else 0.0
        if latency_degraded(b_p95, p95_fn(f_sub, svc)):
            affected.append(svc)
            continue
        if compute_error_rate(f_sub, service=svc) > b_err + ERROR_RATE_ABS_THRESHOLD:
            affected.append(svc)
    return affected


def adu(G: nx.DiGraph, faulted: str, affected: list[str]) -> dict:
    c = classify_affected(G, faulted, affected)
    return {"A": c["ancestor_affected_count"], "D": c["descendant_affected_count"],
            "U": c["unrelated_affected_count"],
            "A_set": c["ancestor_affected_services"],
            "D_set": c["descendant_affected_services"],
            "U_set": c["unrelated_affected_services"]}


def run_records(app: str) -> list[dict]:
    recs = []
    for f in sorted(glob.glob(os.path.join(RUNS, "run_%s_*.json" % app))):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        d["_file"] = os.path.basename(f)
        recs.append(d)
    return recs


def stored_adu(d: dict) -> tuple[int, int, int]:
    return (d["ancestor_affected_count"], d["descendant_affected_count"],
            d["unrelated_affected_count"])


def validate_hr() -> tuple[int, int, list[str]]:
    G = load_graph("hotelreservation")
    recs = run_records("hotelreservation")
    bad = []
    for d in recs:
        r = adu(G, d["service"], replay_run(d, G, p95_existing))
        if (r["A"], r["D"], r["U"]) != stored_adu(d):
            bad.append("%s: replay %d/%d/%d, stored %d/%d/%d"
                       % ((d["_file"], r["A"], r["D"], r["U"]) + stored_adu(d)))
    return len(recs), len(recs) - len(bad), bad


def service_tests(df: pd.DataFrame, G: nx.DiGraph) -> pd.DataFrame:
    """ancestor_count vs median ancestor_affected_count over the 11 non-gateway services."""
    services = sorted(n for n in G.nodes() if G.in_degree(n) != 0)
    anc_count = {s: len(nx.ancestors(G, s)) for s in services}
    rows = []
    for fault in ("kill", "latency"):
        sub = df[df.fault_type == fault]
        for source, col in (("stored", "stored_A"),
                            ("replay_existing_rule", "existing_A"),
                            ("replay_server_only", "server_only_A")):
            med = sub.groupby("service")[col].median()
            x = np.array([anc_count[s] for s in services], dtype=float)
            y = np.array([float(med[s]) for s in services], dtype=float)
            rho, p, n_dis, method = exact_p(x, y)
            rows.append({"label": LABEL, "fault_type": fault, "source": source,
                         "predictor": "ancestor_count",
                         "outcome": "median ancestor_affected_count",
                         "n_services": len(services), "spearman_rho": rho,
                         "p_exact_two_sided": p, "distinct_arrangements": n_dis,
                         "p_method": method})
    return pd.DataFrame(rows)


def main() -> int:
    n_hr, ok_hr, bad_hr = validate_hr()
    print("HR validation (existing rule): %d of %d runs reproduce stored A/D/U" % (ok_hr, n_hr))
    if bad_hr:
        for b in bad_hr:
            print("  MISMATCH", b)
        print("VALIDATION FAILED: nothing written.")
        return 1

    G = load_graph("socialnetwork")
    rows = []
    for d in run_records("socialnetwork"):
        ex = adu(G, d["service"], replay_run(d, G, p95_existing))
        so = adu(G, d["service"], replay_run(d, G, p95_server_only))
        st = stored_adu(d)
        rows.append({
            "label": LABEL, "run_file": d["_file"], "service": d["service"],
            "fault_type": d["fault_type"], "repetition": d["repetition"],
            "n_ancestors": len(nx.ancestors(G, d["service"])),
            "stored_A": st[0], "stored_D": st[1], "stored_U": st[2],
            "stored_affected": d.get("downstream_affected_services", ""),
            "existing_A": ex["A"], "existing_D": ex["D"], "existing_U": ex["U"],
            "server_only_A": so["A"], "server_only_D": so["D"], "server_only_U": so["U"],
            "server_only_A_set": so["A_set"], "server_only_D_set": so["D_set"],
            "server_only_U_set": so["U_set"],
            "existing_replay_matches_stored": (ex["A"], ex["D"], ex["U"]) == st,
            "server_only_differs_from_stored": (so["A"], so["D"], so["U"]) != st,
            "server_only_differs_from_existing_replay":
                (so["A"], so["D"], so["U"]) != (ex["A"], ex["D"], ex["U"]),
        })
    df = pd.DataFrame(rows).sort_values(["fault_type", "service", "repetition"])
    tests = service_tests(df, G)
    df.to_csv(OUT_CSV, index=False)
    tests.to_csv(OUT_TESTS, index=False)
    write_md(df, tests, G, n_hr, ok_hr)
    print("wrote", os.path.relpath(OUT_CSV, REPO), os.path.relpath(OUT_TESTS, REPO),
          os.path.relpath(OUT_MD, REPO))
    return 0


def write_md(df: pd.DataFrame, tests: pd.DataFrame, G: nx.DiGraph, n_hr: int,
             ok_hr: int) -> None:
    L = []
    A = L.append
    A("# Social Network server-only span replay")
    A("")
    A("**%s.** Generated by `analysis/final/sn_server_only_replay.py`; every value below "
      "is computed by that script from `data/spans/` and `data/graphs/`. No stored "
      "outcome was overwritten. Recorded as Deviation 11." % LABEL)
    A("")
    A("## Rule replayed")
    A("")
    A("Per-service latency for the 11 Social Network Thrift services uses only spans whose "
      "operation name ends in `_server`. `nginx-web-server` reports HTTP operation names "
      "rather than `*_server` names, so it keeps the existing handling (all of its spans). "
      "Degradation rule unchanged: %.1fx relative and +%.1f ms absolute on p95, or error "
      "rate above baseline + %.2f. Error rate is attributed over all of a service's own "
      "spans, as in the campaign. Classification as in "
      "`measurement.blast_radius.classify_affected`."
      % (DEGRADATION_FACTOR, DEGRADATION_FLOOR_MS, ERROR_RATE_ABS_THRESHOLD))
    A("")
    A("## Validation")
    A("")
    A("* Hotel Reservation, existing rule: **%d of %d** runs reproduce the stored "
      "ancestor/descendant/unrelated counts exactly." % (ok_hr, n_hr))
    n_ex = int(df.existing_replay_matches_stored.sum())
    A("* Social Network, existing rule (control): **%d of %d** runs reproduce the stored "
      "counts." % (n_ex, len(df)))
    for _, r in df[~df.existing_replay_matches_stored].iterrows():
        A("  * not reproduced: %s %s rep %d -- stored %d/%d/%d, existing-rule replay "
          "%d/%d/%d" % (r.service, r.fault_type, r.repetition, r.stored_A, r.stored_D,
                        r.stored_U, r.existing_A, r.existing_D, r.existing_U))
    A("* Why replay is not bit-exact at the metric level: the persisted windows are the "
      "union of per-service Jaeger queries made after the fault window, so they contain "
      "traces that reached Jaeger after the live query, and the 500-trace query limit is "
      "re-applied by start time rather than observed. Outcome-level agreement is the "
      "validation criterion.")
    A("")
    A("## (i) Runs whose A/D/U differs from the stored value under the server-only rule")
    A("")
    diff = df[df.server_only_differs_from_stored]
    A("%d of %d runs differ from the stored value; %d of %d differ from the existing-rule "
      "replay of the same bytes." % (len(diff), len(df),
                                     int(df.server_only_differs_from_existing_replay.sum()),
                                     len(df)))
    A("")
    A("| cell | rep | stored A/D/U | existing-rule replay | server-only replay | "
      "server-only affected (A; D; U) |")
    A("|---|---:|---|---|---|---|")
    for _, r in diff.iterrows():
        A("| %s / %s | %d | %d/%d/%d | %d/%d/%d | %d/%d/%d | %s; %s; %s |"
          % (r.service, r.fault_type, r.repetition, r.stored_A, r.stored_D, r.stored_U,
             r.existing_A, r.existing_D, r.existing_U, r.server_only_A, r.server_only_D,
             r.server_only_U, r.server_only_A_set or "-", r.server_only_D_set or "-",
             r.server_only_U_set or "-"))
    A("")
    A("## (ii) and (iv) Primary test under the replay")
    A("")
    A("`ancestor_count` vs the median `ancestor_affected_count` over 5 repetitions, 11 "
      "non-gateway Social Network services, exact two-sided permutation p "
      "(`exact_p_supplement.exact_p`). Nominal, not FDR-corrected.")
    A("")
    A("| fault | source | rho | exact p | arrangements |")
    A("|---|---|---:|---:|---:|")
    for _, t in tests.iterrows():
        A("| %s | %s | %.6f | %.8f | %s |" % (t.fault_type, t.source, t.spearman_rho,
                                              t.p_exact_two_sided,
                                              format(int(t.distinct_arrangements), ",")))
    A("")
    A("## (iii) user-service ancestors")
    A("")
    anc = sorted(nx.ancestors(G, "user-service"))
    A("`user-service` has %d graph ancestors: %s." % (len(anc), ", ".join(anc)))
    A("")
    A("| fault | rep | stored A | server-only A | server-only ancestors affected |")
    A("|---|---:|---:|---:|---|")
    us = df[df.service == "user-service"]
    for _, r in us.iterrows():
        A("| %s | %d | %d | %d | %s |" % (r.fault_type, r.repetition, r.stored_A,
                                          r.server_only_A, r.server_only_A_set or "-"))
    for fault in ("kill", "latency"):
        s = us[us.fault_type == fault]
        A("")
        A("* %s: median ancestors affected, stored %s of %d; server-only %s of %d."
          % (fault, format(s.stored_A.median(), "g"), len(anc),
             format(s.server_only_A.median(), "g"), len(anc)))
    A("")
    A("## Not replayable")
    A("")
    A("Recovery-probe windows were not persisted, so Social Network T_rec cannot be "
      "replayed under the server-only rule. Stored T_rec values stand as collected, "
      "measured under the all-spans fallback.")
    A("")
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
