"""
build_numbers.py -- single source of truth for every number the manuscript may cite.

Reads only the committed analysis outputs under analysis/final/ and the campaign data
under data/, and writes paper/numbers.csv with one row per citable number:

    claim_id, description, value, value_raw, unit, source_file, source_script, commit

Nothing here is typed by hand: every `value` is read out of a file produced by a script,
and every row names that file and that script. The `commit` column records the repository
HEAD at generation time -- the state the numbers were extracted from.

paper/emit_macros.py then turns numbers.csv into numbers.tex and numbers.json, so no
number is ever typed into prose.

Run order:  python paper/build_numbers.py  &&  python paper/emit_macros.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FINAL = os.path.join(REPO, "analysis", "final")
RCA = "analysis/final/run_confirmatory_analysis.py"

ROWS = []


def commit_hash() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "UNKNOWN"


COMMIT = commit_hash()


def add(claim_id, description, value, source_file, source_script, unit="", fmt=None):
    """Record one citable number. `value` is whatever the source file holds."""
    if isinstance(value, (np.bool_, bool)):
        shown = "yes" if bool(value) else "no"
        raw = str(bool(value)).lower()
    elif isinstance(value, (int, np.integer)):
        shown = str(int(value))
        raw = str(int(value))
    elif isinstance(value, (float, np.floating)):
        if value != value:
            shown, raw = "undefined", "nan"
        else:
            shown = fmt % value if fmt else ("%g" % value)
            raw = repr(float(value))
    else:
        shown = str(value)
        raw = str(value)
    ROWS.append({
        "claim_id": claim_id, "description": description, "value": shown,
        "value_raw": raw, "unit": unit, "source_file": source_file,
        "source_script": source_script, "commit": COMMIT,
    })


def protocol_and_topology_numbers():
    """Method-section constants, read from the code and data that produced the campaign.

    These are protocol parameters rather than results, but the manuscript cites them, so
    they are extracted here rather than typed into prose. Sources are the runner's own
    configuration objects, the graph files, and the run records themselves -- never a
    literal copied from documentation.
    """
    import ast
    import glob as _glob
    import importlib.util
    import sys

    if REPO not in sys.path:          # the runner's modules import each other by package
        sys.path.insert(0, REPO)

    F_GRAPH = "data/graphs/{hr,sn}_CANONICAL.json"
    S_SELF = "paper/build_numbers.py"

    def load(rel, name):
        spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, rel))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    # ---- fault parameters, from the dataclass the runner instantiates -------
    fc = load("faultinjection/fault_config.py", "_fc")
    spec = fc.FaultSpec(fault_type=fc.FaultType.LATENCY)
    add("fault_latency_delay_ms", "Injected network delay for latency faults",
        int(spec.latency_ms), "faultinjection/fault_config.py", S_SELF, "ms")
    add("fault_latency_jitter_ms", "Jitter around the injected delay",
        int(spec.latency_jitter_ms), "faultinjection/fault_config.py", S_SELF, "ms")
    add("fault_kill_signal", "Signal used for kill faults", "SIGKILL",
        "faultinjection/fault_config.py", S_SELF)

    # ---- degradation thresholds, from the single rule the runner uses -------
    mc = load("measurement/metrics_collector.py", "_mc")
    add("threshold_degradation_factor", "Relative p95 threshold for flagging a service "
        "as latency-degraded", float(mc.DEGRADATION_FACTOR),
        "measurement/metrics_collector.py", S_SELF, "x", "%.1f")
    add("threshold_degradation_floor_ms", "Absolute p95 rise required alongside the "
        "relative threshold", float(mc.DEGRADATION_FLOOR_MS),
        "measurement/metrics_collector.py", S_SELF, "ms", "%.1f")
    add("threshold_error_rate_abs", "Absolute error-rate rise for flagging a service",
        float(mc.ERROR_RATE_ABS_THRESHOLD), "measurement/metrics_collector.py",
        S_SELF, "", "%.2f")

    # ---- hybrid metric weights: inherited, not a priori (Deviation 10) -----
    # FIXED_WEIGHTS were carried over from the withdrawn analysis, where an empirical
    # search chose them (centrality/metric_constants.py CHANGELOG). The preregistered
    # cross-arch protocol was not executed.
    wk = load("centrality/metric_constants.py", "_wk")
    for field, cid, desc in (
            ("w_in", "hybrid_w_in", "Hybrid metric weight on in-degree centrality"),
            ("w_out", "hybrid_w_out",
             "Hybrid metric weight on fan-out-scaled out-degree centrality"),
            ("w_btw", "hybrid_w_btw", "Hybrid metric weight on betweenness centrality")):
        add(cid, desc + " (inherited from an empirical search in the withdrawn analysis; "
            "not a priori; not re-tuned on campaign data; Deviation 10)",
            float(getattr(wk.FIXED_WEIGHTS, field)), "centrality/metric_constants.py",
            S_SELF, "", "%.1f")
    lock = os.path.join(REPO, "centrality", "output", "tuned_weights.lock.json")
    lock_exists = os.path.isfile(lock)
    add("hybrid_weights_lockfile_exists", "Whether the cross-arch weight lockfile exists "
        "(it would exist only if the preregistered tuning protocol had been run)",
        lock_exists, "centrality/output/tuned_weights.lock.json", S_SELF)
    # A weight search on campaign data would leave output beside that data or beside the
    # final analysis: a file named for weights/tuning/grids/optimisation, or a table with
    # weight columns. Look in both places.
    search_out = []
    for d in ("data/campaign", "analysis/final"):
        for f in _glob.glob(os.path.join(REPO, d, "**", "*"), recursive=True):
            if not os.path.isfile(f):
                continue
            if re.search(r"weight|tuned|grid|optimi", os.path.basename(f), re.I):
                search_out.append(f)
            elif f.endswith(".csv"):
                with open(f, encoding="utf-8", errors="replace") as fh:
                    header = fh.readline().strip().split(",")
                if {"w_in", "w_out", "w_btw"} & set(header):
                    search_out.append(f)
    add("hybrid_weights_reoptimised_on_campaign", "Whether the hybrid metric's weights "
        "were re-optimised on campaign data", lock_exists or bool(search_out),
        "check: centrality/output/tuned_weights.lock.json absent AND no file under "
        "data/campaign/ or analysis/final/ whose name matches weight|tuned|grid|optimi or "
        "whose CSV header has a w_in/w_out/w_btw column", S_SELF)

    # ---- run protocol, from the campaign runner's RunArgs -------------------
    src = open(os.path.join(REPO, "tools", "run_campaign.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    ra = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "RunArgs":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant):
                    ra[stmt.targets[0].id] = stmt.value.value
    for key, cid, desc, unit in (
            ("warmup", "protocol_warmup_s", "Warm-up before the baseline window", "s"),
            ("fault_duration", "protocol_fault_duration_s", "Fault hold duration", "s"),
            ("max_wait", "protocol_recovery_cap_s",
             "Recovery probe cap, beyond which a run is censored", "s"),
            ("confirm", "protocol_confirm_s",
             "Confirmation period a recovered state must hold", "s"),
            ("lag", "protocol_probe_lag_s",
             "Lag applied to the probe window, to avoid partially written spans", "s"),
            ("min_traces", "protocol_min_traces",
             "Minimum traces before a probe sample may vote for recovery", "traces"),
            ("users", "protocol_load_users", "Concurrent load-generator users", "users"),
            ("cooldown", "protocol_cooldown_s", "Cooldown after each run", "s")):
        if key in ra:
            v = ra[key]
            add(cid, desc, int(v) if float(v).is_integer() else float(v),
                "tools/run_campaign.py", S_SELF, unit)

    # ---- baseline window length, measured from the run records themselves ---
    runs = pd.read_csv(os.path.join(FINAL, "run_level_data.csv"))
    lens = []
    for rf in _glob.glob(os.path.join(REPO, "data", "campaign", "runs", "*.json")):
        r = json.load(open(rf, encoding="utf-8"))
        w = r.get("baseline_window_us")
        if w:
            lens.append((w[1] - w[0]) / 1e6)
    if lens:
        vals = sorted(set(round(v, 3) for v in lens))
        add("protocol_baseline_window_s", "Baseline measurement window, as actually "
            "recorded in every run", float(vals[0]),
            "data/campaign/runs/*.json", S_SELF, "s", "%.0f")
        add("protocol_baseline_window_distinct", "Distinct baseline window lengths across "
            "the campaign", len(vals), "data/campaign/runs/*.json", S_SELF, "values")

    # ---- dependency graph provenance and topology --------------------------
    manifest = load("sdg/hotel_expected_services.py", "_hm")
    expected_edges = set(manifest.HOTEL_EXPECTED_EDGES)
    for app, lab, gf in (("socialnetwork", "sn", "sn_CANONICAL.json"),
                         ("hotelreservation", "hr", "hr_CANONICAL.json")):
        g = json.load(open(os.path.join(REPO, "data", "graphs", gf), encoding="utf-8"))
        meta = g["graph"]
        add(f"graph_{lab}_nodes", f"Services in the reconstructed {app} dependency graph",
            len(g["nodes"]), f"data/graphs/{gf}", S_SELF, "services")
        add(f"graph_{lab}_edges", f"Observed call edges in the {app} dependency graph",
            len(g["edges"]), f"data/graphs/{gf}", S_SELF, "edges")
        add(f"graph_{lab}_traces_examined", f"Traces examined to reconstruct the {app} "
            f"graph", int(meta["traces_examined"]), f"data/graphs/{gf}", S_SELF, "traces")
        add(f"graph_{lab}_spans_examined", f"Spans examined to reconstruct the {app} graph",
            int(meta["spans_examined"]), f"data/graphs/{gf}", S_SELF, "spans")
    add("dsb_commit", "DeathStarBench commit the benchmarks were built from",
        json.load(open(os.path.join(REPO, "data", "graphs", "hr_CANONICAL.json"),
                       encoding="utf-8"))["graph"]["deathstarbench"]["short"],
        "data/graphs/hr_CANONICAL.json", S_SELF)

    # Hotel Reservation: observed graph against the published architecture manifest.
    hr = json.load(open(os.path.join(REPO, "data", "graphs", "hr_CANONICAL.json"),
                        encoding="utf-8"))
    observed = {(e["source"], e["target"]) for e in hr["edges"]}
    recovered = expected_edges & observed
    missed = expected_edges - observed
    extra = observed - expected_edges
    add("hr_manifest_expected_edges", "Call edges the published Hotel Reservation "
        "architecture implies", len(expected_edges), "sdg/hotel_expected_services.py",
        S_SELF, "edges")
    add("hr_manifest_edges_recovered", "Manifest edges recovered by trace reconstruction",
        len(recovered), F_GRAPH, S_SELF, "edges")
    add("hr_manifest_edges_missed", "Manifest edges never observed under this workload",
        len(missed), F_GRAPH, S_SELF, "edges")
    add("hr_manifest_edges_missed_names", "Which manifest edges were never observed",
        "; ".join("%s->%s" % e for e in sorted(missed)), F_GRAPH, S_SELF)
    add("hr_manifest_edges_extra", "Observed edges the manifest does not list",
        "; ".join("%s->%s" % e for e in sorted(extra)) or "none", F_GRAPH, S_SELF)
    add("hr_expected_services_manifest", "Services the published architecture lists",
        len(manifest.HOTEL_EXPECTED_SERVICES), "sdg/hotel_expected_services.py",
        S_SELF, "services")
    ucallers = sorted(s for s, t in observed if t == "user")
    add("hr_user_observed_callers", "Observed callers of the Hotel Reservation user "
        "service", "; ".join(ucallers) or "none", F_GRAPH, S_SELF)
    add("hr_user_observed_caller_count", "Number of observed callers of user",
        len(ucallers), F_GRAPH, S_SELF, "callers")


def main():
    conf = pd.read_csv(os.path.join(FINAL, "confirmatory_family_kill.csv"))
    repl = pd.read_csv(os.path.join(FINAL, "replication_family_latency.csv"))
    expl = pd.read_csv(os.path.join(FINAL, "exploratory_family.csv"))
    h1b = pd.read_csv(os.path.join(FINAL, "h1b_hybrid_metric.csv"))
    sat = pd.read_csv(os.path.join(FINAL, "ancestor_saturation.csv"))
    cps = pd.read_csv(os.path.join(FINAL, "compose_post_service.csv"))
    powr = pd.read_csv(os.path.join(FINAL, "power_table.csv"))
    degen = pd.read_csv(os.path.join(FINAL, "degenerate_predictors.csv"))
    integ = pd.read_csv(os.path.join(FINAL, "integrity_checks.csv"))
    devs = pd.read_csv(os.path.join(FINAL, "deviations.csv"))
    runs = pd.read_csv(os.path.join(FINAL, "run_level_data.csv"))
    svc = pd.read_csv(os.path.join(FINAL, "service_level_data.csv"))
    loo = pd.read_csv(os.path.join(FINAL, "leave_one_out.csv"))
    exact = pd.read_csv(os.path.join(FINAL, "exact_p_supplement.csv"))
    sn_ranks = pd.read_csv(os.path.join(FINAL, "sn_predictor_ranks.csv"))

    F_CONF, F_REPL = "analysis/final/confirmatory_family_kill.csv", "analysis/final/replication_family_latency.csv"
    F_EXPL, F_H1B = "analysis/final/exploratory_family.csv", "analysis/final/h1b_hybrid_metric.csv"
    F_SAT, F_CPS = "analysis/final/ancestor_saturation.csv", "analysis/final/compose_post_service.csv"
    F_POW, F_DEG = "analysis/final/power_table.csv", "analysis/final/degenerate_predictors.csv"
    F_INT, F_DEV = "analysis/final/integrity_checks.csv", "analysis/final/deviations.csv"
    F_RUN, F_SVC = "analysis/final/run_level_data.csv", "analysis/final/service_level_data.csv"
    F_LOO, F_EX = "analysis/final/leave_one_out.csv", "analysis/final/exact_p_supplement.csv"
    S_LOO, S_EX = "analysis/final/leave_one_out.py", "analysis/final/exact_p_supplement.py"

    # ---------------------------------------------------------- campaign -----
    add("campaign_runs_total", "Total fault-injection runs in the final campaign",
        len(runs), F_RUN, RCA, "runs")
    add("campaign_architectures", "Distinct architectures under test",
        runs.app.nunique(), F_RUN, RCA)
    add("campaign_cells", "Distinct (architecture, service, fault type) cells",
        len(runs.groupby(["app", "service", "fault_type"])), F_RUN, RCA, "cells")
    add("campaign_reps_per_cell", "Repetitions per cell (balanced design)",
        int(runs.groupby(["app", "service", "fault_type"]).size().unique()[0]),
        F_RUN, RCA, "repetitions")
    add("campaign_fault_types", "Fault types injected", runs.fault_type.nunique(), F_RUN, RCA)
    add("campaign_runs_failed", "Runs with telemetry failure",
        int((~runs.telemetry_ok).sum()), F_RUN, RCA, "runs")
    add("campaign_runs_censored", "Right-censored recovery observations",
        int(runs.recovery_censored.sum()), F_RUN, RCA, "runs")
    add("campaign_censoring_rate_pct", "Censoring rate",
        100.0 * runs.recovery_censored.mean(), F_RUN, RCA, "%", "%.1f")
    add("campaign_gateway_runs", "Runs faulting a gateway service (excluded by design)",
        int(runs.is_gateway.sum()), F_RUN, RCA, "runs")
    for app, lab in (("socialnetwork", "sn"), ("hotelreservation", "hr")):
        d = runs[runs.app == app]
        add(f"{lab}_runs", f"Runs on {app}", len(d), F_RUN, RCA, "runs")
        add(f"{lab}_services", f"Services in the {app} analysis set",
            d.service.nunique(), F_RUN, RCA, "services")
    ts = pd.to_datetime(runs.timestamp, format="mixed", utc=True)
    add("campaign_start_utc", "First run timestamp (UTC)",
        ts.min().strftime("%Y-%m-%d %H:%M"), F_RUN, RCA)
    add("campaign_end_utc", "Last run timestamp (UTC)",
        ts.max().strftime("%Y-%m-%d %H:%M"), F_RUN, RCA)
    add("campaign_duration_hours", "Elapsed wall-clock time, first to last run",
        (ts.max() - ts.min()).total_seconds() / 3600.0, F_RUN, RCA, "hours", "%.1f")
    add("integrity_checks_total", "Pre-analysis integrity checks run",
        len(integ), F_INT, RCA, "checks")
    add("integrity_checks_passed", "Pre-analysis integrity checks passed",
        int(integ.passed.sum()), F_INT, RCA, "checks")

    # --------------------------------------------------------- primary -------
    pr = conf[(conf.architecture == "socialnetwork") &
              (conf.predictor == "ancestor_count") &
              (conf.outcome == "ancestor_affected_count")].iloc[0]
    add("primary_rho", "Primary test: Spearman rho, SN, ancestor_count vs "
        "ancestor_affected_count, kill faults", pr.spearman_rho, F_CONF, RCA, "", "%.3f")
    add("primary_rho_full", "Primary test: Spearman rho, full precision",
        pr.spearman_rho, F_CONF, RCA, "", "%.6f")
    add("primary_ci_lo", "Primary test: 95% CI lower bound", pr.ci_lo, F_CONF, RCA, "", "%.3f")
    add("primary_ci_hi", "Primary test: 95% CI upper bound", pr.ci_hi, F_CONF, RCA, "", "%.3f")
    add("primary_ci_method", "Primary test: CI method", pr.ci_method, F_CONF, RCA)
    add("primary_n_services", "Primary test: services correlated",
        int(pr.n_services), F_CONF, RCA, "services")
    add("primary_p_locked", "Primary test: raw p as locked (10,000 Monte-Carlo permutations)",
        pr.p_permutation, F_CONF, RCA, "", "%.4f")
    add("primary_p_bh_locked", "Primary test: BH-adjusted p as locked",
        pr.p_bh_adjusted, F_CONF, RCA, "", "%.4f")
    add("primary_significant", "Primary test: significant after BH-FDR at q=0.05",
        bool(pr.significant_after_fdr), F_CONF, RCA)
    ex = exact[exact.is_primary_test].iloc[0]
    add("primary_p_exact", "Primary test: raw p by exact enumeration (supplementary)",
        ex.p_exact_supplementary, F_EX, S_EX, "", "%.6f")
    add("primary_p_exact_arrangements", "Primary test: distinct arrangements enumerated",
        int(ex.exact_distinct_arrangements), F_EX, S_EX, "arrangements")
    add("primary_p_bh_exact", "Primary test: BH-adjusted p with exact p substituted "
        "(supplementary)", ex.p_bh_with_all_available_exact, F_EX, S_EX, "", "%.4f")
    add("primary_significant_exact", "Primary test: significant after BH-FDR using exact p",
        bool(ex.significant_after_fdr_with_exact), F_EX, S_EX)
    add("exact_tests_refined", "Confirmatory tests refined to an exact p (supplementary)",
        int(exact.p_exact_supplementary.notna().sum()), F_EX, S_EX, "tests")

    # ---------------------------------------------------------- families -----
    for tag, df, fn in (("conf", conf, F_CONF), ("repl", repl, F_REPL)):
        name = "confirmatory (kill)" if tag == "conf" else "replication (latency)"
        add(f"{tag}_family_size", f"Tests in the {name} family", len(df), fn, RCA, "tests")
        add(f"{tag}_family_defined", f"Tests with a defined p in the {name} family",
            int(df.p_permutation.notna().sum()), fn, RCA, "tests")
        add(f"{tag}_family_significant", f"Tests significant after BH-FDR, {name} family",
            int(df.significant_after_fdr.sum()), fn, RCA, "tests")
        b = df.nsmallest(1, "p_permutation").iloc[0]
        add(f"{tag}_best_raw_p", f"Smallest raw p in the {name} family",
            b.p_permutation, fn, RCA, "", "%.4f")
        add(f"{tag}_best_bh_p", f"BH-adjusted p of the smallest-raw-p test, {name} family",
            b.p_bh_adjusted, fn, RCA, "", "%.4f")
        add(f"{tag}_best_predictor", f"Predictor of the smallest-raw-p test, {name} family",
            b.predictor, fn, RCA)
    add("fdr_q", "False discovery rate controlled at", float(conf.fdr_q.iloc[0]),
        F_CONF, RCA, "", "%.2f")

    # ------------------------------------------------- T_rec, both families --
    # T_rec tests sit inside the 44-test families above. With no censoring, Spearman is
    # the primary T_rec test (deviation 6); Cox and log-rank are reported alongside and
    # are not separately FDR-corrected. Hotel Reservation is directional only.
    def pfmt(v):
        return "%.4f" if v != v or v >= 1e-4 else "%.2e"

    for tag, df, fn in (("conf", conf, F_CONF), ("repl", repl, F_REPL)):
        name = "confirmatory (kill)" if tag == "conf" else "replication (latency)"
        t = df[df.outcome == "T_rec"]
        add(f"trec_{tag}_tests", f"T_rec tests in the {name} family", len(t), fn, RCA,
            "tests")
        add(f"trec_{tag}_significant", f"T_rec tests significant after BH-FDR, {name} "
            f"family", int(t.significant_after_fdr.sum()), fn, RCA, "tests")
        add(f"trec_{tag}_logrank_undefined", f"T_rec tests with no log-rank p (fewer than "
            f"two distinct predictor terciles), {name} family",
            int(t.logrank_p.isna().sum()), fn, RCA, "tests")
        for pred, short in (("ancestor_count", "ancestor"),
                            ("hybrid_criticality", "hybrid")):
            for _, r in t[t.predictor == pred].iterrows():
                lab = "sn" if r.architecture == "socialnetwork" else "hr"
                k = f"trec_{tag}_{lab}_{short}"
                what = f"T_rec vs {pred}, {r.architecture_label}, {name}"
                add(f"{k}_rho", f"{what}: Spearman rho", r.spearman_rho, fn, RCA, "",
                    "%.3f")
                add(f"{k}_p", f"{what}: raw permutation p", r.p_permutation, fn, RCA, "",
                    pfmt(r.p_permutation))
                add(f"{k}_bh_p", f"{what}: BH-adjusted p", r.p_bh_adjusted, fn, RCA, "",
                    pfmt(r.p_bh_adjusted))
                if pd.notna(r.logrank_p):
                    add(f"{k}_logrank_p", f"{what}: log-rank p across predictor terciles",
                        r.logrank_p, fn, RCA, "", pfmt(r.logrank_p))
                if pred != "ancestor_count":
                    continue
                for lvl in ("run", "service"):
                    unit = ("run level, SE clustered by service" if lvl == "run"
                            else "service level")
                    add(f"{k}_cox_{lvl}_hr", f"{what}: Cox hazard ratio per unit of "
                        f"{pred} ({unit})", r[f"cox_{lvl}_hr"], fn, RCA, "", "%.3f")
                    add(f"{k}_cox_{lvl}_ci_lo", f"{what}: Cox hazard ratio 95% CI lower "
                        f"({unit})", r[f"cox_{lvl}_ci_lo"], fn, RCA, "", "%.3f")
                    add(f"{k}_cox_{lvl}_ci_hi", f"{what}: Cox hazard ratio 95% CI upper "
                        f"({unit})", r[f"cox_{lvl}_ci_hi"], fn, RCA, "", "%.3f")
                    add(f"{k}_cox_{lvl}_p", f"{what}: Cox p ({unit})", r[f"cox_{lvl}_p"],
                        fn, RCA, "", pfmt(r[f"cox_{lvl}_p"]))

    # ------------------------------------------------------- exploratory -----
    add("expl_attempted", "Exploratory tests attempted", len(expl), F_EXPL, RCA, "tests")
    add("expl_testable", "Exploratory tests with a defined p",
        int(expl.p_permutation.notna().sum()), F_EXPL, RCA, "tests")
    add("expl_undefined", "Exploratory tests undefined (outcome constant, not null)",
        int(expl.p_permutation.isna().sum()), F_EXPL, RCA, "tests")
    add("expl_significant", "Exploratory tests significant after their own BH-FDR",
        int(expl.significant_after_fdr.sum()), F_EXPL, RCA, "tests")
    for _, r in expl[expl.significant_after_fdr].iterrows():
        k = f"expl_sig_{r.predictor}"
        add(f"{k}_rho", f"Exploratory: {r.outcome} vs {r.predictor}, {r.fault_type}, "
            f"{r.architecture}: rho", r.spearman_rho, F_EXPL, RCA, "", "%.3f")
        add(f"{k}_bh_p", f"Exploratory: {r.outcome} vs {r.predictor}, {r.fault_type}, "
            f"{r.architecture}: BH-adjusted p", r.p_bh_adjusted, F_EXPL, RCA, "", "%.4f")

    # --------------------------------------------------------------- H1b -----
    for _, r in h1b.iterrows():
        lab = "sn" if r.architecture == "socialnetwork" else "hr"
        k = f"h1b_{lab}_{r.fault_type}"
        add(f"{k}_rho", f"H1b hybrid_criticality vs ancestor_affected_count, "
            f"{r.architecture_label}, {r.fault_type}: rho",
            r.spearman_rho, F_H1B, RCA, "", "%.3f")
        add(f"{k}_ci_lo", f"H1b {r.architecture_label} {r.fault_type}: CI lower",
            r.ci_lo, F_H1B, RCA, "", "%.3f")
        add(f"{k}_ci_hi", f"H1b {r.architecture_label} {r.fault_type}: CI upper",
            r.ci_hi, F_H1B, RCA, "", "%.3f")
        add(f"{k}_p", f"H1b {r.architecture_label} {r.fault_type}: raw p",
            r.p_permutation, F_H1B, RCA, "", "%.4f")
        add(f"{k}_bh_p", f"H1b {r.architecture_label} {r.fault_type}: BH-adjusted p",
            r.p_bh_adjusted, F_H1B, RCA, "", "%.4f")
    add("h1b_all_negative", "H1b: hybrid metric rho <= 0 in every architecture-by-fault cell",
        bool(h1b.anti_predictive_rho_le_0.all()), F_H1B, RCA)
    add("h1b_any_distinguishable", "H1b: any cell distinguishable from zero after FDR",
        bool(h1b.distinguishable_from_zero_after_fdr.any()), F_H1B, RCA)
    add("h1b_cells", "H1b cells tested (2 architectures x 2 fault types)",
        len(h1b), F_H1B, RCA, "cells")

    # -------------------------------------------------------- saturation -----
    for _, r in sat.iterrows():
        lab = "sn" if r.architecture == "socialnetwork" else "hr"
        add(f"saturation_{lab}_{r.fault_type}_run",
            f"Ancestor saturation, {r.architecture_label}, {r.fault_type}, run level",
            r.ancestor_saturation_run_level, F_SAT, RCA, "", "%.3f")
        add(f"saturation_{lab}_{r.fault_type}_service",
            f"Ancestor saturation, {r.architecture_label}, {r.fault_type}, service level",
            r.ancestor_saturation_service_level, F_SAT, RCA, "", "%.3f")
        add(f"saturation_{lab}_{r.fault_type}_tautological",
            f"{r.architecture_label} {r.fault_type}: tautological at the analysis unit",
            bool(r.tautological_at_analysis_unit), F_SAT, RCA)

    # ------------------------------------------------- compose-post-service --
    for _, r in cps.iterrows():
        k = f"composepost_{r.fault_type}"
        add(f"{k}_mean", f"compose-post-service measured ancestor_affected_count, mean "
            f"over {int(r.n_reps)} {r.fault_type} reps",
            r.ancestor_affected_mean, F_CPS, RCA, "", "%.1f")
        add(f"{k}_min", f"compose-post-service ancestor_affected_count, min, {r.fault_type}",
            int(r.ancestor_affected_min), F_CPS, RCA)
        add(f"{k}_max", f"compose-post-service ancestor_affected_count, max, {r.fault_type}",
            int(r.ancestor_affected_max), F_CPS, RCA)
        add(f"{k}_reps", f"compose-post-service repetitions, {r.fault_type}",
            int(r.n_reps), F_CPS, RCA, "runs")
    r0 = cps.iloc[0]
    add("composepost_rank_ancestor_count", "compose-post-service rank by ancestor_count "
        "(1 = highest) among the 11 SN services", int(r0.rank_ancestor_count), F_CPS, RCA)
    add("composepost_rank_hybrid", "compose-post-service rank by hybrid_criticality "
        "(1 = highest) among the 11 SN services", int(r0.rank_hybrid_criticality), F_CPS, RCA)
    add("composepost_set_size", "Services in the SN analysis set used for ranking",
        int(r0.n_services_in_analysis_set), F_CPS, RCA, "services")
    add("composepost_ancestor_count", "compose-post-service graph ancestor_count",
        int(r0.ancestor_count), F_CPS, RCA)
    add("composepost_descendants", "compose-post-service graph descendant count",
        int(r0.n_descendants), F_CPS, RCA)
    add("composepost_out_degree", "compose-post-service out-degree (direct callees)",
        int(r0.out_degree_raw), F_CPS, RCA)
    add("composepost_hybrid", "compose-post-service hybrid_criticality score",
        r0.hybrid_criticality, F_CPS, RCA, "", "%.3f")

    # --------------------------------------------------- leave-one-out -------
    l = loo[loo.fault_type == "kill"]
    lo = l[~l.service_excluded.str.startswith("NONE")]
    add("loo_rho_min", "Leave-one-out: minimum rho across the 11 exclusions (SN, kill)",
        lo.rho.min(), F_LOO, S_LOO, "", "%.3f")
    add("loo_rho_max", "Leave-one-out: maximum rho across the 11 exclusions (SN, kill)",
        lo.rho.max(), F_LOO, S_LOO, "", "%.3f")
    add("loo_n_exclusions", "Leave-one-out: recomputations performed per fault type",
        len(lo), F_LOO, S_LOO, "recomputations")
    us = lo[lo.service_excluded == "user-service"].iloc[0]
    add("loo_userservice_rho", "Leave-one-out: rho with user-service excluded",
        us.rho, F_LOO, S_LOO, "", "%.3f")
    add("loo_userservice_delta", "Leave-one-out: change in rho from excluding user-service",
        float(us.delta_rho_vs_full_set), F_LOO, S_LOO, "", "%+.3f")
    other = lo[lo.service_excluded != "user-service"]
    nxt = other.loc[other.delta_rho_vs_full_set.astype(float).abs().idxmax()]
    add("loo_second_largest_service", "Leave-one-out: service with the second largest swing",
        nxt.service_excluded, F_LOO, S_LOO)
    add("loo_second_largest_delta", "Leave-one-out: second largest change in rho",
        float(nxt.delta_rho_vs_full_set), F_LOO, S_LOO, "", "%+.3f")
    add("loo_swing_ratio", "Leave-one-out: user-service swing divided by the next largest",
        abs(float(us.delta_rho_vs_full_set)) / abs(float(nxt.delta_rho_vs_full_set)),
        F_LOO, S_LOO, "x", "%.1f")

    # user-service departure, from the run-level data
    ud = runs[(runs.app == "socialnetwork") & (runs.service == "user-service") &
              (runs.fault_type == "kill")]
    add("userservice_ancestor_count", "user-service graph ancestor_count",
        int(ud.n_ancestors.iloc[0]), F_RUN, RCA)
    add("userservice_measured", "user-service measured ancestor_affected_count "
        "(identical in every kill repetition)",
        int(ud.ancestor_affected_count.unique()[0]), F_RUN, RCA)
    add("userservice_runs_departing", "user-service kill runs where measured < graph ancestors",
        int((ud.ancestor_affected_count < ud.n_ancestors).sum()), F_RUN, RCA, "runs")

    # ------------------------------------------------------------- power -----
    for _, r in powr.iterrows():
        lab = "sn" if r.architecture == "socialnetwork" else "hr"
        add(f"power_{lab}_n", f"{r.architecture_label}: services in the analysis set",
            int(r.n_services_actual), F_POW, RCA, "services")
        add(f"power_{lab}_n_prereg", f"{r.architecture_label}: services preregistered",
            int(r.n_services_preregistered), F_POW, RCA, "services")
        add(f"power_{lab}_n_matches", f"{r.architecture_label}: n matches preregistration",
            bool(r.n_matches_prereg), F_POW, RCA)
        add(f"power_{lab}_levels", f"{r.architecture_label}: distinct ancestor_count levels",
            int(r.ancestor_count_levels_actual), F_POW, RCA, "levels")
        add(f"power_{lab}_levels_match", f"{r.architecture_label}: levels match preregistration",
            bool(r.levels_match_prereg), F_POW, RCA)
        add(f"power_{lab}_ceiling", f"{r.architecture_label}: best attainable rho, "
            f"untied outcome", r.best_attainable_rho_untied_outcome, F_POW, RCA, "", "%.3f")
        add(f"power_{lab}_ceiling_prereg", f"{r.architecture_label}: preregistered ceiling rho",
            r.best_attainable_rho_preregistered, F_POW, RCA, "", "%.3f")
        add(f"power_{lab}_ceiling_matches", f"{r.architecture_label}: ceiling reproduces "
            f"the preregistered value", bool(r.untied_ceiling_matches_prereg), F_POW, RCA)
        add(f"power_{lab}_ceiling_p", f"{r.architecture_label}: exact p at the ceiling",
            r.best_attainable_p_untied_outcome, F_POW, RCA, "", "%.4f")
        add(f"power_{lab}_ceiling_p_asymptotic", f"{r.architecture_label}: asymptotic p at "
            f"the ceiling (NOT for inference)",
            r.best_attainable_p_asymptotic_NOT_FOR_INFERENCE, F_POW, RCA, "", "%.4f")
    add("power_hr_prereg_stated_p", "Preregistration section 7.2's stated Hotel Reservation "
        "ceiling p (the asymptotic value)",
        float(powr[powr.architecture == "hotelreservation"].prereg_stated_p.iloc[0]),
        F_POW, RCA, "", "%.3f")

    # -------------------------------------------------------- degenerate -----
    add("degenerate_pairs", "Predictor-architecture pairs that are degenerate",
        int((~degen.testable).sum()), F_DEG, RCA, "pairs")
    add("testable_pairs", "Predictor-architecture pairs that are testable",
        int(degen.testable.sum()), F_DEG, RCA, "pairs")
    add("total_predictor_pairs", "Predictor-architecture pairs considered",
        len(degen), F_DEG, RCA, "pairs")
    for _, r in degen[~degen.testable].iterrows():
        lab = "sn" if r.architecture == "socialnetwork" else "hr"
        add(f"degenerate_{lab}_predictor", f"Degenerate predictor on {r.architecture}",
            r.predictor, F_DEG, RCA)
        add(f"degenerate_{lab}_value", f"Constant value of {r.predictor} on {r.architecture}",
            r.value_if_constant, F_DEG, RCA, "", "%.6f")

    # -------------------------------------------- constant-outcome evidence --
    for col in ("descendant_affected_count", "unrelated_affected_count"):
        add(f"{col}_distinct_values", f"Distinct service-median values of {col} across all "
            f"architectures and fault types", int(svc[col].nunique()), F_SVC, RCA, "values")
        add(f"{col}_constant_at", f"Constant value of {col} at the service level",
            float(svc[col].unique()[0]) if svc[col].nunique() == 1 else float("nan"),
            F_SVC, RCA, "", "%.0f")
    # Run level is NOT identically zero, though the service-level median is. Both are
    # recorded, because the run-level exceptions bound how strongly the "descendants do
    # not degrade" claim can be stated.
    for col, tag in (("descendant_affected_count", "descendant"),
                     ("unrelated_affected_count", "unrelated")):
        nz = runs[runs[col] > 0]
        add(f"{tag}_affected_runs_nonzero",
            f"Runs (of 180) in which at least one {tag} service degraded",
            int(len(nz)), F_RUN, RCA, "runs")
        add(f"{tag}_affected_runs_zero",
            f"Runs (of 180) in which no {tag} service degraded",
            int(len(runs) - len(nz)), F_RUN, RCA, "runs")
        add(f"{tag}_affected_runs_zero_pct",
            f"Percentage of runs with no {tag} service degraded",
            100.0 * (len(runs) - len(nz)) / len(runs), F_RUN, RCA, "%", "%.1f")
        add(f"{tag}_affected_max_in_any_run",
            f"Largest {col} observed in any single run",
            int(runs[col].max()), F_RUN, RCA)
        if len(nz) == 1:
            e = nz.iloc[0]
            add(f"{tag}_affected_exception_run",
                f"The single run with a nonzero {col}",
                f"{e.app}/{e.service}/{e.fault_type}/rep{int(e.repetition)}", F_RUN, RCA)

    # -------------------------------------------------------- deviations -----
    add("deviations_total", "Deviations from the preregistration, total",
        len(devs), F_DEV, RCA, "deviations")
    add("deviations_runs_invalidated", "Campaign runs invalidated across all deviations",
        int(devs.runs_invalidated.sum()), F_DEV, RCA, "runs")
    add("deviations_precampaign", "Deviations found before any campaign data existed",
        int(devs.stage.str.contains("pre-launch").sum()), F_DEV, RCA, "deviations")
    log = os.path.join(REPO, "_quarantine", "QUARANTINE_LOG.md")
    nums = set()
    if os.path.isfile(log):
        for line in open(log, encoding="utf-8"):
            m = re.match(r"^##\s+(?:Item\s+)?(\d+)[.\s—-]", line)
            if m:
                nums.add(int(m.group(1)))
    add("quarantine_items", "Numbered items in the quarantine log",
        len(nums), "_quarantine/QUARANTINE_LOG.md", "hand-maintained log", "items")

    # ------------------------------------------------- replication overlap ---
    ident = []
    for app in ("socialnetwork", "hotelreservation"):
        k = svc[(svc.app == app) & (svc.fault_type == "kill")].sort_values("service")
        l = svc[(svc.app == app) & (svc.fault_type == "latency")].sort_values("service")
        ident.append(np.array_equal(k.ancestor_affected_count.to_numpy(),
                                    l.ancestor_affected_count.to_numpy()))
    add("replication_primary_identical", "Median ancestor_affected_count identical between "
        "kill and latency in every architecture", bool(all(ident)), F_SVC, RCA)

    # ----------------------------------------------- fault invariance -------
    from scipy import stats as _st
    same_tot = same_n = 0
    for app, lab in (("socialnetwork", "sn"), ("hotelreservation", "hr")):
        k = svc[(svc.app == app) & (svc.fault_type == "kill")].sort_values("service")
        l = svc[(svc.app == app) & (svc.fault_type == "latency")].sort_values("service")
        add(f"trec_rho_between_faults_{lab}", f"Spearman rho between kill and latency "
            f"median T_rec across {app} services",
            float(_st.spearmanr(k.T_rec.to_numpy(), l.T_rec.to_numpy()).statistic),
            F_SVC, RCA, "", "%.3f")
        s = n = 0
        for svc_name in sorted(runs[runs.app == app].service.unique()):
            a = sorted(runs[(runs.app == app) & (runs.service == svc_name) &
                            (runs.fault_type == "kill")].ancestor_affected_count)
            b = sorted(runs[(runs.app == app) & (runs.service == svc_name) &
                            (runs.fault_type == "latency")].ancestor_affected_count)
            n += 1
            s += int(a == b)
        add(f"fault_invariant_services_{lab}", f"{app} services whose full set of five "
            f"per-run ancestor_affected_count values is identical under kill and latency",
            s, F_RUN, RCA, "services")
        add(f"fault_invariant_services_total_{lab}", f"{app} services compared",
            n, F_RUN, RCA, "services")
        same_tot += n
        same_n += s
    add("fault_invariant_services_all", "Services (both architectures) whose per-run "
        "ancestor_affected_count values are identical under both fault types",
        same_n, F_RUN, RCA, "services")
    add("fault_invariant_services_all_total", "Services compared across both architectures",
        same_tot, F_RUN, RCA, "services")
    add("trec_median_s", "Median recovery time across all 180 runs",
        float(runs.T_rec.median()), F_RUN, RCA, "s", "%.2f")
    add("trec_min_s", "Minimum recovery time observed",
        float(runs.T_rec.min()), F_RUN, RCA, "s", "%.2f")
    add("trec_max_s", "Maximum recovery time observed",
        float(runs.T_rec.max()), F_RUN, RCA, "s", "%.2f")

    # ------------------------------------------------------ SN rank table ----
    add("sn_analysis_set_size", "Services in the Social Network analysis set",
        int(sn_ranks.in_analysis_set.sum()), "analysis/final/sn_predictor_ranks.csv", RCA,
        "services")

    protocol_and_topology_numbers()

    df = pd.DataFrame(ROWS)
    dupes = df[df.claim_id.duplicated(keep=False)]
    if not dupes.empty:
        raise SystemExit("duplicate claim_id:\n%s" % dupes.claim_id.tolist())
    df.to_csv(os.path.join(HERE, "numbers.csv"), index=False)
    print("wrote paper/numbers.csv with %d rows at commit %s" % (len(df), COMMIT))


if __name__ == "__main__":
    main()
