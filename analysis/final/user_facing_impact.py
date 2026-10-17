"""
user_facing_impact.py -- POST-HOC DESCRIPTIVE ANALYSIS. NOT PREREGISTERED. NO TEST IS ADDED
TO ANY FAMILY.

What "user-facing impact" means here
------------------------------------
The quantity is `delta_error_rate` under kill faults, as stored in the run records:

    delta_error_rate = fault_error_rate - baseline_error_rate

`fault_error_rate` is END-TO-END at the gateway: over the traces Jaeger returned for the
gateway in the fault window, the fraction in which ANY span carried an error
(metrics_collector.collect_fault_window_metrics -> compute_error_rate(traces)).
`baseline_error_rate` uses the GATEWAY'S OWN SPANS (collect_baseline_metrics ->
compute_error_rate(traces, service=gateway)). The two scopes differ. The baseline is 0.0 in
all 90 kill runs, which this script checks, so the difference has no numerical effect:
delta_error_rate equals the fault-window gateway error rate.

Parts
-----
(a) The 8 exploratory delta_error_rate kill tests already reported in
    analysis/final/exploratory_family.csv for hybrid_criticality, out_degree,
    ancestor_count and descendant_count in each architecture: rho, raw p, BH p. They are
    recomputed here by calling the producing functions of run_confirmatory_analysis.py in
    the order its main() calls them, so the seeded resampling stream is consumed
    identically and the Monte-Carlo p-values and the BH adjustment over the 66 testable
    exploratory tests reproduce. Nothing is written by those functions.
(b) Median, minimum and maximum gateway error rate under kill, per faulted service.
(c) The request-mix weight share per service: the Locust task weights in infra/, summed
    over the request types whose persisted baseline traces pass through the service, over
    the total weight. Request types are matched to Jaeger root operations by path and
    method. Plus the descriptive rank correlation between gateway error and weight share.
(d) hybrid_criticality split into its three weighted terms (in-degree, fan-out-scaled
    out-degree, betweenness), with each term's descriptive rank correlation with gateway
    error on Social Network.

Rank correlations in (c) and (d) are descriptive: Spearman's rho with no p-value.

Inputs : data/campaign/runs/*.json, data/spans/*.json.gz (baseline windows of kill runs),
         data/graphs/{sn,hr}_CANONICAL.json, infra/_locustfile_baseline.py,
         infra/_locustfile_hotel.py (task weights, paths and methods)
Outputs: analysis/final/user_facing_impact.csv               (per service)
         analysis/final/user_facing_impact_tests.csv         (part a, 8 rows)
         analysis/final/user_facing_impact_correlations.csv  (parts c and d)
         analysis/final/user_facing_impact_endpoints.csv     (request type x service)
         analysis/final/user_facing_impact.md

Run: python analysis/final/user_facing_impact.py
"""
from __future__ import annotations

import ast
import collections
import glob
import gzip
import json
import os
import sys

import networkx as nx
import pandas as pd
from scipy import stats

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

import analysis.final.run_confirmatory_analysis as rca  # noqa: E402
from centrality.compute_centrality import compute_all_centralities  # noqa: E402
from centrality.hybrid_weight_optimizer import compute_hybrid  # noqa: E402
from centrality.metric_constants import FIXED_WEIGHTS  # noqa: E402

OUT = os.path.join(REPO, "analysis", "final")
LABEL = "POST-HOC DESCRIPTIVE -- not preregistered; no test added to any family"
APPS = {"socialnetwork": ("sn_CANONICAL.json", "infra/_locustfile_baseline.py"),
        "hotelreservation": ("hr_CANONICAL.json", "infra/_locustfile_hotel.py")}
TEST_PREDICTORS = ["hybrid_criticality", "out_degree", "ancestor_count", "descendant_count"]


def load_graph(app):
    with open(os.path.join(REPO, "data", "graphs", APPS[app][0]), encoding="utf-8") as fh:
        return nx.node_link_graph(json.load(fh), edges="edges")


def gateway(G):
    gws = [n for n in G.nodes() if G.in_degree(n) == 0]
    if len(gws) != 1:
        raise SystemExit("expected one gateway, found %s" % gws)
    return gws[0]


def locust_tasks(rel):
    """[(task name, weight, HTTP method, path)] read from a locustfile's AST."""
    tree = ast.parse(open(os.path.join(REPO, rel), encoding="utf-8").read())
    tasks = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        weight = None
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and getattr(dec.func, "id", "") == "task":
                weight = int(dec.args[0].value)
        if weight is None:
            continue
        for call in ast.walk(node):
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and call.func.attr in ("get", "post", "put", "delete")
                    and call.args and isinstance(call.args[0], ast.Constant)):
                tasks.append((node.name, weight, call.func.attr.upper(), call.args[0].value))
                break
    return tasks


def part_a():
    """Replay main()'s calls in order; return the 8 requested exploratory rows."""
    runs = rca.load_runs()
    preds = rca.load_predictors()
    rca.integrity_checks(runs, preds)
    pairs, _ = rca.testable_pairs(preds, runs)
    rca.run_family("confirmatory", "kill", rca.CONFIRMATORY_OUTCOMES, pairs, runs, preds,
                   with_survival=True)
    rca.run_family("replication", "latency", rca.CONFIRMATORY_OUTCOMES, pairs, runs, preds,
                   with_survival=True)
    expl = rca.run_exploratory(pairs, runs, preds)
    sub = expl[(expl.outcome == "delta_error_rate") & (expl.fault_type == "kill") &
               (expl.predictor.isin(TEST_PREDICTORS))]
    keep = ["architecture", "predictor", "n_services", "spearman_rho", "p_permutation",
            "p_method", "p_bh_adjusted", "significant_after_fdr", "family_size"]
    out = sub[keep].rename(columns={"family_size": "bh_family_size"}).copy()
    out.insert(0, "label", LABEL)
    return out.sort_values(["architecture", "predictor"]), expl


def main() -> int:
    tests, _ = part_a()

    runs, kill_runs = [], 0
    for f in sorted(glob.glob(os.path.join(REPO, "data", "campaign", "runs", "*.json"))):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        if d["fault_type"] == "kill":
            runs.append(d)
    kill_runs = len(runs)
    base_zero = sum(1 for d in runs if d["baseline_error_rate"] == 0.0)

    svc_rows, ep_rows, corr_rows = [], [], []
    for app in APPS:
        G = load_graph(app)
        gw = gateway(G)
        tasks = locust_tasks(APPS[app][1])
        total_w = sum(t[1] for t in tasks)

        # request type -> traces, and traces passing through each service (baseline windows)
        n_ep = collections.Counter()
        n_ep_svc = collections.Counter()
        for d in runs:
            if d["app"] != app:
                continue
            with gzip.open(os.path.join(REPO, d["raw_spans"]["baseline_window"]["path"]),
                           "rt", encoding="utf-8") as fh:
                traces = json.load(fh)["traces"]
            for t in traces:
                pm = {k: v["serviceName"] for k, v in t["processes"].items()}
                roots = [s for s in t["spans"] if not s.get("references")]
                if not roots or pm.get(roots[0]["processID"]) != gw:
                    continue
                op = roots[0]["operationName"]
                n_ep[op] += 1
                for s in set(pm.values()):
                    n_ep_svc[(op, s)] += 1

        def task_for(op):
            for name, w, method, path in tasks:
                if op == path or op == "HTTP %s %s" % (method, path):
                    return name, w
            return None, 0

        for op in sorted(n_ep):
            name, w = task_for(op)
            for s in sorted(n for n in G.nodes() if n != gw):
                if n_ep_svc[(op, s)]:
                    ep_rows.append({"label": LABEL, "architecture": app, "root_operation": op,
                                    "locust_task": name, "task_weight": w,
                                    "total_weight": total_w, "service": s,
                                    "traces_of_type": n_ep[op],
                                    "traversal_fraction": n_ep_svc[(op, s)] / n_ep[op]})

        cent = compute_hybrid(compute_all_centralities(G), FIXED_WEIGHTS).set_index("service")
        for s in sorted(n for n in G.nodes() if n != gw):
            errs = [d["fault_error_rate"] for d in runs if d["app"] == app and d["service"] == s]
            share_w = sum(task_for(op)[1] for op in n_ep if n_ep_svc[(op, s)])
            c = cent.loc[s]
            svc_rows.append({
                "label": LABEL, "architecture": app, "gateway": gw, "service": s,
                "kill_runs": len(errs),
                "gateway_error_median": float(pd.Series(errs).median()),
                "gateway_error_min": float(min(errs)), "gateway_error_max": float(max(errs)),
                "weight_share_numerator": share_w, "weight_share_denominator": total_w,
                "weight_share": share_w / total_w,
                "descendant_count": len(nx.descendants(G, s)),
                "ancestor_count": len(nx.ancestors(G, s)),
                "out_degree_raw": int(G.out_degree(s)),
                "hybrid_criticality": float(c.hybrid_criticality),
                "hybrid_term_in_degree": FIXED_WEIGHTS.w_in * float(c.in_degree),
                "hybrid_term_fanout_out_degree": FIXED_WEIGHTS.w_out * float(c.out_degree)
                * float(c.fan_out_weight),
                "hybrid_term_betweenness": FIXED_WEIGHTS.w_btw * float(c.betweenness),
            })

    svc = pd.DataFrame(svc_rows)
    for app in APPS:
        g = svc[svc.architecture == app]
        cols = [("weight_share", "request-mix weight share")]
        if app == "socialnetwork":
            cols += [("hybrid_criticality", "hybrid_criticality (all three terms)"),
                     ("hybrid_term_in_degree", "hybrid term: weighted in-degree"),
                     ("hybrid_term_fanout_out_degree",
                      "hybrid term: weighted fan-out-scaled out-degree"),
                     ("hybrid_term_betweenness", "hybrid term: weighted betweenness")]
        for col, what in cols:
            corr_rows.append({
                "label": LABEL, "architecture": app, "x": col, "x_description": what,
                "y": "gateway_error_median", "n_services": len(g),
                "x_distinct_values": int(g[col].round(12).nunique()),
                "spearman_rho_descriptive": float(stats.spearmanr(
                    g[col], g.gateway_error_median).statistic)})
    corr = pd.DataFrame(corr_rows)
    ep = pd.DataFrame(ep_rows)

    svc.to_csv(os.path.join(OUT, "user_facing_impact.csv"), index=False)
    tests.to_csv(os.path.join(OUT, "user_facing_impact_tests.csv"), index=False)
    corr.to_csv(os.path.join(OUT, "user_facing_impact_correlations.csv"), index=False)
    ep.to_csv(os.path.join(OUT, "user_facing_impact_endpoints.csv"), index=False)
    write_md(svc, tests, corr, ep, kill_runs, base_zero)
    print("kill runs %d, baseline error 0.0 in %d" % (kill_runs, base_zero))
    print(tests.drop(columns="label").to_string(index=False))
    return 0


def write_md(svc, tests, corr, ep, kill_runs, base_zero):
    L = ["# User-facing impact under kill faults", "",
         "**%s.** Generated by `analysis/final/user_facing_impact.py`; every value below is "
         "computed by that script. Correlations in parts (c) and (d) are descriptive "
         "(Spearman's rho, no p-value)." % LABEL, "",
         "## Quantity", "",
         "`delta_error_rate = fault_error_rate - baseline_error_rate`. The fault-window error "
         "rate is end-to-end at the gateway (a trace counts as an error if any of its spans "
         "errored). The baseline error rate uses the gateway's own spans. The scopes differ, "
         "but the baseline error rate is 0.0 in %d of the %d kill runs, so the difference has "
         "no numerical effect: `delta_error_rate` equals the fault-window gateway error rate."
         % (base_zero, kill_runs), "",
         "## (a) Exploratory delta_error_rate kill tests (as already reported)", "",
         "BH adjustment is over the %d testable tests of the exploratory family. Hotel "
         "Reservation is directional only." % int(tests.bh_family_size.iloc[0]), "",
         "| architecture | predictor | n | rho | raw p | p method | BH p |",
         "|---|---|---:|---:|---:|---|---:|"]
    for _, r in tests.iterrows():
        L.append("| %s | %s | %d | %.3f | %.4f | %s | %.4f |" % (
            r.architecture, r.predictor, r.n_services, r.spearman_rho, r.p_permutation,
            r.p_method, r.p_bh_adjusted))
    L += ["", "## (b), (c) Gateway error rate under kill, weight share, structure", "",
          "Weight share: Locust task weights of the request types whose baseline traces pass "
          "through the service, over the total weight. See "
          "`user_facing_impact_endpoints.csv` for each request type's traversal fraction.", "",
          "| architecture | service | median gateway error | min | max | weight share | "
          "descendants | ancestors |", "|---|---|---:|---:|---:|---|---:|---:|"]
    for _, r in svc.sort_values(["architecture", "gateway_error_median"],
                                ascending=[False, False]).iterrows():
        L.append("| %s | %s | %.4f | %.4f | %.4f | %d/%d = %.3f | %d | %d |" % (
            r.architecture, r.service, r.gateway_error_median, r.gateway_error_min,
            r.gateway_error_max, r.weight_share_numerator, r.weight_share_denominator,
            r.weight_share, r.descendant_count, r.ancestor_count))
    L += ["", "## (d) hybrid_criticality terms, Social Network", "",
          "Weighted terms; they sum to hybrid_criticality (rounded to 6 decimals there).", "",
          "| service | median gateway error | in-degree term | fan-out-scaled out-degree term "
          "| betweenness term | hybrid_criticality |", "|---|---:|---:|---:|---:|---:|"]
    for _, r in svc[svc.architecture == "socialnetwork"].sort_values(
            "gateway_error_median", ascending=False).iterrows():
        L.append("| %s | %.4f | %.6f | %.6f | %.6f | %.6f |" % (
            r.service, r.gateway_error_median, r.hybrid_term_in_degree,
            r.hybrid_term_fanout_out_degree, r.hybrid_term_betweenness, r.hybrid_criticality))
    L += ["", "## Descriptive rank correlations with median gateway error", "",
          "| architecture | x | distinct x values | rho (descriptive) |", "|---|---|---:|---:|"]
    for _, r in corr.iterrows():
        L.append("| %s | %s | %d of %d | %.3f |" % (r.architecture, r.x_description,
                                                    r.x_distinct_values, r.n_services,
                                                    r.spearman_rho_descriptive))
    L.append("")
    with open(os.path.join(OUT, "user_facing_impact.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())
