"""
sn_span_composition.py -- POST-HOC DESCRIPTIVE COUNT (Deviation 11). NO HYPOTHESIS TEST.

Counts, per architecture, how many per-service latency samples in the persisted spans fell
back to all of a service's spans in measurement.metrics_collector.select_spans (no span in
that service's sample carries a span.kind tag), and what kind of operation the selected
spans are by name (`*_server`, `*_client`, other). Also counts how the run records label
the scope of their per-service baseline samples.

A "sample" is one service in one persisted window (baseline or fault) of one run, with the
service's spans selected by select_spans over every trace in that window that contains a
span from the service.

Inputs : data/spans/*.json.gz, data/campaign/runs/*.json (baseline_per_service.scope only)
Output : analysis/final/sn_span_composition.csv

Run: python analysis/final/sn_span_composition.py
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from measurement.metrics_collector import _span_kind, select_spans  # noqa: E402

LABEL = "POST-HOC DESCRIPTIVE -- not preregistered, no hypothesis test (Deviation 11)"


def main() -> int:
    acc = {}
    for f in sorted(glob.glob(os.path.join(REPO, "data", "spans", "*.json.gz"))):
        app = "socialnetwork" if "_socialnetwork_" in os.path.basename(f) \
            else "hotelreservation"
        a = acc.setdefault(app, {"span_files": 0, "samples": 0, "samples_fallback": 0,
                                 "spans_selected": 0, "spans_selected_server_named": 0,
                                 "spans_selected_client_named": 0})
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            traces = json.load(fh)["traces"]
        a["span_files"] += 1
        services = sorted({p["serviceName"] for t in traces
                           for p in t["processes"].values()} - {""})
        for svc in services:
            if "jaeger" in svc:
                continue
            mine = [s for t in traces for s in t["spans"]
                    if t["processes"].get(s["processID"], {}).get("serviceName") == svc]
            if not mine:
                continue
            a["samples"] += 1
            if not any(_span_kind(s) is not None for s in mine):
                a["samples_fallback"] += 1
            sel = select_spans(traces, svc)
            a["spans_selected"] += len(sel)
            a["spans_selected_server_named"] += sum(
                1 for s in sel if s["operationName"].endswith("_server"))
            a["spans_selected_client_named"] += sum(
                1 for s in sel if s["operationName"].endswith("_client"))

    for f in sorted(glob.glob(os.path.join(REPO, "data", "campaign", "runs", "*.json"))):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        a = acc[d["app"]]
        for v in d["baseline_per_service"].values():
            a["record_baseline_samples"] = a.get("record_baseline_samples", 0) + 1
            if str(v.get("scope", "")).startswith("service_server_spans:"):
                a["record_baseline_labelled_server_spans"] = \
                    a.get("record_baseline_labelled_server_spans", 0) + 1

    rows = []
    for app, a in acc.items():
        a = dict(a)
        a["fraction_selected_client_named"] = (
            a["spans_selected_client_named"] / a["spans_selected"] if a["spans_selected"]
            else float("nan"))
        rows.append({"label": LABEL, "architecture": app, **a})
    out = os.path.join(REPO, "analysis", "final", "sn_span_composition.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(pd.DataFrame(rows).drop(columns="label").to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
