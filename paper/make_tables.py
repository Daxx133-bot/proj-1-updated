"""
make_tables.py -- table-ready CSVs plus formatted Markdown for the manuscript.

Every table is built from the committed analysis outputs under analysis/final/. Nothing is
typed by hand. Each table is written twice:

    paper/tables/<name>.csv   machine-readable, one row per line, ready for a table package
    paper/tables/<name>.md    the same rows rendered as a Markdown table

paper/tables/tables_index.csv records what each table shows and which file it came from.

Run: python paper/make_tables.py
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FINAL = os.path.join(REPO, "analysis", "final")
OUT = os.path.join(HERE, "tables")
RCA = "analysis/final/run_confirmatory_analysis.py"

INDEX = []


def emit(name, df, shows, source_file, source_script):
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(os.path.join(OUT, name + ".csv"), index=False)
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |",
             "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(r[c]) else str(r[c])
                                       for c in cols) + " |")
    open(os.path.join(OUT, name + ".md"), "w", encoding="utf-8").write(
        "\n".join(lines) + "\n")
    INDEX.append({"table": name, "shows": shows, "source_file": source_file,
                  "source_script": source_script, "rows": len(df)})
    print("  %-28s %d rows" % (name, len(df)))


def f(x, n=3):
    return "" if x is None or (isinstance(x, float) and np.isnan(x)) else format(x, ".%df" % n)


def hr(x):
    """Hazard ratio or interval bound: three decimals, scientific notation outside
    [0.001, 1000) so degenerate fits stay readable."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    return format(x, ".3f") if 0.001 <= abs(x) < 1000 else format(x, ".2e")


def pv(x):
    """p-value to four decimals, '<0.0001' below that."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    return "<0.0001" if x < 0.00005 else format(x, ".4f")


def main():
    preds = pd.read_csv(os.path.join(FINAL, "predictors.csv"))
    svc = pd.read_csv(os.path.join(FINAL, "service_level_data.csv"))
    conf = pd.read_csv(os.path.join(FINAL, "confirmatory_family_kill.csv"))
    repl = pd.read_csv(os.path.join(FINAL, "replication_family_latency.csv"))
    h1b = pd.read_csv(os.path.join(FINAL, "h1b_hybrid_metric.csv"))
    loo = pd.read_csv(os.path.join(FINAL, "leave_one_out.csv"))
    powr = pd.read_csv(os.path.join(FINAL, "power_table.csv"))
    devs = pd.read_csv(os.path.join(FINAL, "deviations.csv"))
    exact = pd.read_csv(os.path.join(FINAL, "exact_p_supplement.csv"))

    # ---- 1/2. predictor tables, per architecture, with the measured outcome --
    for app, tag, label in (("socialnetwork", "sn", "Social Network"),
                            ("hotelreservation", "hr", "Hotel Reservation")):
        p = preds[(preds.architecture == app) & (preds.in_analysis_set)].copy()
        k = svc[(svc.app == app) & (svc.fault_type == "kill")][
            ["service", "ancestor_affected_count", "T_rec"]].rename(
            columns={"ancestor_affected_count": "measured_kill", "T_rec": "T_rec_kill"})
        l = svc[(svc.app == app) & (svc.fault_type == "latency")][
            ["service", "ancestor_affected_count", "T_rec"]].rename(
            columns={"ancestor_affected_count": "measured_latency",
                     "T_rec": "T_rec_latency"})
        t = p.merge(k, on="service").merge(l, on="service").sort_values(
            ["ancestor_count", "service"], ascending=[False, True])
        out = pd.DataFrame({
            "service": t.service,
            "ancestor_count": t.ancestor_count.astype(int),
            "descendant_count": t.descendant_count.astype(int),
            "in_degree_raw": t.in_degree_raw.astype(int),
            "out_degree_raw": t.out_degree_raw.astype(int),
            "hybrid_criticality": t.hybrid_criticality.map(lambda v: f(v, 3)),
            "betweenness": t.betweenness.map(lambda v: f(v, 3)),
            "closeness": t.closeness.map(lambda v: f(v, 3)),
            "pagerank": t.pagerank.map(lambda v: f(v, 3)),
            "eigenvector": t.eigenvector.map(lambda v: f(v, 3)),
            "measured_ancestor_affected_kill": t.measured_kill.map(lambda v: f(v, 1)),
            "measured_ancestor_affected_latency": t.measured_latency.map(lambda v: f(v, 1)),
            "T_rec_kill_s": t.T_rec_kill.map(lambda v: f(v, 2)),
            "T_rec_latency_s": t.T_rec_latency.map(lambda v: f(v, 2)),
        })
        emit("tbl_predictors_%s" % tag,
             out,
             "%s: graph predictors per service with ancestor_count and the measured "
             "service-median outcomes" % label,
             "analysis/final/predictors.csv + service_level_data.csv", RCA)

    # ---- 3. primary results by family -------------------------------------
    rows = []
    for fam, df, fn in (("confirmatory (kill)", conf, "confirmatory_family_kill.csv"),
                        ("replication (latency)", repl, "replication_family_latency.csv")):
        for _, r in df[(df.predictor == "ancestor_count") &
                       (df.outcome == "ancestor_affected_count")].iterrows():
            rows.append({
                "family": fam, "architecture": r.architecture_label,
                "predictor": r.predictor, "outcome": r.outcome,
                "n_services": int(r.n_services), "rho": f(r.spearman_rho, 3),
                "ci_lo": f(r.ci_lo, 3), "ci_hi": f(r.ci_hi, 3), "ci_method": r.ci_method,
                "p_raw": f(r.p_permutation, 4), "p_method": r.p_method,
                "p_bh_adjusted": f(r.p_bh_adjusted, 4),
                "significant_q05": "yes" if r.significant_after_fdr else "no",
                "role": "DIRECTIONAL ONLY (saturated)" if r.hr_directional_only
                        else "confirmatory" if fam.startswith("conf") else "replication",
            })
    prim = pd.DataFrame(rows)
    fam_rows = []
    for fam, df in (("confirmatory (kill)", conf), ("replication (latency)", repl)):
        b = df.nsmallest(1, "p_permutation").iloc[0]
        fam_rows.append({
            "family": fam, "tests": len(df),
            "tests_with_defined_p": int(df.p_permutation.notna().sum()),
            "significant_after_bh_q05": int(df.significant_after_fdr.sum()),
            "smallest_raw_p": f(b.p_permutation, 4),
            "its_bh_adjusted_p": f(b.p_bh_adjusted, 4),
            "smallest_p_test": "%s / %s vs %s" % (b.architecture_label, b.predictor, b.outcome),
        })
    emit("tbl_primary_by_family", prim,
         "The primary predictor-outcome test in each family and architecture",
         "analysis/final/confirmatory_family_kill.csv + replication_family_latency.csv", RCA)
    emit("tbl_family_summary", pd.DataFrame(fam_rows),
         "Family sizes and how many tests survive BH-FDR at q=0.05",
         "analysis/final/confirmatory_family_kill.csv + replication_family_latency.csv", RCA)

    # supplementary exact-p row for the primary test
    ex = exact[exact.is_primary_test].iloc[0]
    emit("tbl_primary_exact_p_supplementary", pd.DataFrame([{
        "label": "SUPPLEMENTARY - not part of the preregistered analysis",
        "test": "Social Network, ancestor_count vs ancestor_affected_count, kill",
        "rho": f(ex.spearman_rho_locked, 6),
        "p_raw_locked_monte_carlo": f(ex.p_locked, 6),
        "p_raw_exact_enumeration": f(ex.p_exact_supplementary, 6),
        "distinct_arrangements": int(ex.exact_distinct_arrangements),
        "p_bh_locked": f(ex.p_bh_locked, 4),
        "p_bh_with_exact": f(ex.p_bh_with_all_available_exact, 4),
        "significant_locked": "no" if not ex.significant_after_fdr_locked else "yes",
        "significant_with_exact": "no" if not ex.significant_after_fdr_with_exact else "yes",
        "verdict": "unchanged",
    }]), "Supplementary: exact-enumeration p for the primary test and its BH-FDR rerun",
        "analysis/final/exact_p_supplement.csv", "analysis/final/exact_p_supplement.py")

    # ---- 4. H1b ------------------------------------------------------------
    h = pd.DataFrame({
        "family": h1b.family, "fault_type": h1b.fault_type,
        "architecture": h1b.architecture_label,
        "n_services": h1b.n_services.astype(int),
        "rho": h1b.spearman_rho.map(lambda v: f(v, 3)),
        "ci_lo": h1b.ci_lo.map(lambda v: f(v, 3)),
        "ci_hi": h1b.ci_hi.map(lambda v: f(v, 3)),
        "p_raw": h1b.p_permutation.map(lambda v: f(v, 4)),
        "p_bh_adjusted": h1b.p_bh_adjusted.map(lambda v: f(v, 4)),
        "rho_le_zero_as_preregistered": h1b.anti_predictive_rho_le_0.map(
            lambda b: "yes" if b else "no"),
        "distinguishable_from_zero_after_fdr": h1b.distinguishable_from_zero_after_fdr.map(
            lambda b: "yes" if b else "no"),
    })
    emit("tbl_h1b", h,
         "hybrid_criticality vs ancestor_affected_count in all four architecture-by-fault "
         "cells (the preregistration's H1b)", "analysis/final/h1b_hybrid_metric.csv",
         RCA)

    # ---- 5. leave-one-out ---------------------------------------------------
    l = loo.copy()
    l = pd.DataFrame({
        "label": "POST-HOC robustness check - NOT part of the preregistered family",
        "fault_type": l.fault_type, "service_excluded": l.service_excluded,
        "n_services": l.n_services.astype(int),
        "rho": l.rho.map(lambda v: f(v, 6)),
        "p_raw_nominal_uncorrected": l.p_permutation_nominal_uncorrected.map(
            lambda v: f(v, 6)),
        "delta_rho_vs_full_set": l.delta_rho_vs_full_set.map(
            lambda v: "" if pd.isna(v) else format(float(v), "+.6f")),
        "p_method": l.p_method,
    })
    emit("tbl_leave_one_out", l,
         "Post-hoc: Social Network primary rho recomputed with each service excluded",
         "analysis/final/leave_one_out.csv", "analysis/final/leave_one_out.py")

    # ---- 6. power -----------------------------------------------------------
    p = pd.DataFrame({
        "architecture": powr.architecture_label,
        "n_services_actual": powr.n_services_actual.astype(int),
        "n_services_preregistered": powr.n_services_preregistered.astype(int),
        "n_matches": powr.n_matches_prereg.map(lambda b: "yes" if b else "NO"),
        "ancestor_count_levels_actual": powr.ancestor_count_levels_actual.astype(int),
        "ancestor_count_levels_preregistered":
            powr.ancestor_count_levels_preregistered.astype(int),
        "levels_match": powr.levels_match_prereg.map(lambda b: "yes" if b else "NO"),
        "ancestor_count_values": powr.ancestor_count_values,
        "ceiling_rho_untied_outcome": powr.best_attainable_rho_untied_outcome.map(
            lambda v: f(v, 3)),
        "ceiling_rho_preregistered": powr.best_attainable_rho_preregistered.map(
            lambda v: f(v, 3)),
        "ceiling_matches_prereg": powr.untied_ceiling_matches_prereg.map(
            lambda b: "yes" if b else "NO"),
        "ceiling_p_exact": powr.best_attainable_p_untied_outcome.map(lambda v: f(v, 4)),
        "ceiling_p_asymptotic_NOT_FOR_INFERENCE":
            powr.best_attainable_p_asymptotic_NOT_FOR_INFERENCE.map(lambda v: f(v, 4)),
        "prereg_section_7_2_states": powr.prereg_stated_p.map(
            lambda v: "" if pd.isna(v) else f(v, 3)),
        "role": powr.role,
    })
    emit("tbl_power", p,
         "Preregistered power table reproduced from the actual analysis sets",
         "analysis/final/power_table.csv", RCA)

    # ---- 6b. recovery time (T_rec) ------------------------------------------
    # Spearman is primary for T_rec (no censoring, deviation 6). Cox and log-rank are
    # secondary and uncorrected. Hazard ratios are per one-unit increase of the predictor.
    # A Cox fit is shown as "not estimable" when it failed (NaN estimate or a "failed: ..."
    # note; the analysis stores no separate convergence flag) or its CI upper bound exceeds
    # COX_CI_HI_MAX. Every raw value stays in tbl_trec_supplementary.
    COX_CI_HI_MAX = 1e6

    def estimable(r, lvl):
        hi, note = r["cox_%s_ci_hi" % lvl], str(r["cox_%s_note" % lvl])
        return not (pd.isna(r["cox_%s_hr" % lvl]) or note.startswith("failed")
                    or hi > COX_CI_HI_MAX)

    rows, raw, changed = [], [], []
    for fam, df in (("confirmatory (kill)", conf), ("replication (latency)", repl)):
        t = df[(df.outcome == "T_rec") &
               (df.predictor.isin(["ancestor_count", "hybrid_criticality"]))]
        for _, r in t.sort_values(["architecture", "predictor"],
                                  ascending=[False, True]).iterrows():
            row = {
                "family": fam, "architecture": r.architecture_label,
                "predictor": r.predictor,
                "spearman_rho": f(r.spearman_rho, 3), "p_raw": f(r.p_permutation, 4),
                "p_bh_adjusted": f(r.p_bh_adjusted, 4)}
            for lvl in ("run", "service"):
                if estimable(r, lvl):
                    row["cox_%s_hr" % lvl] = hr(r["cox_%s_hr" % lvl])
                    row["cox_%s_ci_95" % lvl] = "%s to %s" % (hr(r["cox_%s_ci_lo" % lvl]),
                                                              hr(r["cox_%s_ci_hi" % lvl]))
                    row["cox_%s_p" % lvl] = pv(r["cox_%s_p" % lvl])
                else:
                    for k in ("hr", "ci_95", "p"):
                        row["cox_%s_%s" % (lvl, k)] = "not estimable"
                    changed.append("%s | %s | %s | %s level"
                                   % (fam, r.architecture_label, r.predictor, lvl))
            row["logrank_p"] = "undefined" if pd.isna(r.logrank_p) else f(r.logrank_p, 4)
            rows.append(row)
            raw.append({"family": fam, "architecture": r.architecture_label,
                        "predictor": r.predictor, "spearman_rho": r.spearman_rho,
                        "p_raw": r.p_permutation, "p_bh_adjusted": r.p_bh_adjusted,
                        **{c: r[c] for c in r.index
                           if c.startswith(("cox_run_", "cox_service_", "logrank_"))}})
    emit("tbl_trec", pd.DataFrame(rows),
         "Recovery time: Spearman (primary, BH-corrected within family), Cox and log-rank "
         "(secondary, uncorrected) for ancestor_count and hybrid_criticality. Cox hazard "
         "ratios are per one-unit increase of the predictor, at run level with SEs clustered "
         "by service and at service level; hybrid_criticality spans less than one unit, so "
         "its hazard ratios extrapolate beyond the observed range. Log-rank is undefined "
         "where the predictor has fewer than two distinct terciles",
         "analysis/final/confirmatory_family_kill.csv + replication_family_latency.csv", RCA)
    emit("tbl_trec_supplementary", pd.DataFrame(raw),
         "Supplementary: unrounded recovery-time Spearman, Cox and log-rank estimates and "
         "notes for ancestor_count and hybrid_criticality, as stored by the analysis",
         "analysis/final/confirmatory_family_kill.csv + replication_family_latency.csv", RCA)
    for c in changed:
        print("  tbl_trec not estimable: %s" % c)

    # ---- 7. deviations ------------------------------------------------------
    d = devs.sort_values("n")[["n", "date", "title", "stage", "what_happened",
                               "what_changed", "outcome_affected", "runs_invalidated",
                               "runs_disposition", "record", "detected_by"]]
    emit("tbl_deviations", d,
         "Every deviation from the preregistration, ready for the deviations section",
         "analysis/final/deviations.csv", RCA)

    # ---- 7b. deviations, appendix view (2026-10-20) ---------------------------
    # The columns that summarise each deviation and its consequence. The full record,
    # with the descriptive what_happened / what_changed / record columns, stays in
    # analysis/final/deviations.csv and in tbl_deviations.
    emit("tbl_deviations_appendix",
         devs.sort_values("n")[["n", "date", "title", "stage", "outcome_affected",
                                "runs_invalidated", "runs_disposition"]],
         "Deviations from the preregistered plan: when each arose, what it affected and "
         "what happened to the affected runs", "analysis/final/deviations.csv", RCA)

    testbed_tables()
    ws_table()

    pd.DataFrame(INDEX).to_csv(os.path.join(OUT, "tables_index.csv"), index=False)
    print("wrote %d tables (csv + md) and tables_index.csv" % len(INDEX))


def numbers():
    df = pd.read_csv(os.path.join(HERE, "numbers.csv"), dtype=str, keep_default_na=False)
    return dict(zip(df.claim_id, df.value))


def literal_commands(path):
    """Command lists written literally in a source file, rendered as shell text. A name
    or expression in the list is shown as <name>; docker_exe as docker, sys.executable
    as python."""
    import ast
    src = open(os.path.join(REPO, path), encoding="utf-8").read()
    out = []

    def part(e):
        if isinstance(e, ast.Constant):
            return str(e.value).replace("\t", "\\t")
        if isinstance(e, ast.Name):
            return {"docker_exe": "docker"}.get(e.id, "<%s>" % e.id)
        if isinstance(e, ast.Attribute) and ast.unparse(e) == "sys.executable":
            return "python"
        if isinstance(e, ast.JoinedStr):
            return "".join(str(v.value) if isinstance(v, ast.Constant)
                           else "<%s>" % ast.unparse(v.value) for v in e.values)
        if isinstance(e, ast.Call) and ast.unparse(e.func) == "str" and e.args:
            return part(e.args[0])
        if isinstance(e, ast.Subscript):
            return "<%s>" % ast.unparse(e.slice).strip("'\"")
        return "<%s>" % ast.unparse(e)
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.List) and node.elts and all(
                not isinstance(e, ast.Starred) for e in node.elts):
            toks = [part(e) for e in node.elts]
            out.append(" ".join("'%s'" % t if (" " in t and not t.startswith("<"))
                                else t for t in toks))
    return out


def testbed_tables():
    """Testbed table and the exact command lines the runner issued (2026-10-20)."""
    import sys
    from dataclasses import replace
    sys.path.insert(0, REPO)
    from faultinjection.fault_config import DEFAULT_SPECS, FaultType
    n = numbers()

    rows = [
        ("Host OS", "%s (%s)" % (n["testbed_host_os"], n["testbed_host_os_version"]),
         "measured on %s" % n["testbed_measured_on"]),
        ("Host CPU", "%s, %s cores, %s threads" % (n["testbed_cpu_model"],
                                                   n["testbed_cpu_cores"],
                                                   n["testbed_cpu_logical"]),
         "measured on %s" % n["testbed_measured_on"]),
        ("Host RAM", "%s GB" % n["testbed_host_ram_gb"],
         "recorded %s" % n["testbed_vm_record_date"]),
        ("Docker Desktop", "%s, %s backend" % (n["version_docker_desktop"],
                                               n["testbed_docker_backend"]),
         "version measured on %s; backend recorded %s" % (n["testbed_measured_on"],
                                                          n["testbed_vm_record_date"])),
        ("Docker VM memory", "%s GiB (WSL2 default)" % n["testbed_docker_vm_gib"],
         "recorded %s" % n["testbed_vm_record_date"]),
        ("Docker client / Compose", "%s / %s" % (n["version_docker_client"],
                                                 n["version_docker_compose"]),
         "client recorded 2026-10-18; Compose measured on %s" % n["testbed_measured_on"]),
        ("Containers per stack", "Social Network %s, Hotel Reservation %s"
         % (n["testbed_containers_sn"], n["testbed_containers_hr"]),
         "recorded %s; one stack ran at a time" % n["testbed_vm_record_date"]),
        ("DeathStarBench commit", n["dsb_commit"], "pinned upstream commit"),
        ("Jaeger", "%s all-in-one, %s storage" % (n["version_jaeger"],
                                                  n["testbed_jaeger_storage"]),
         "compose override"),
        ("Pumba", "ghcr.io/alexei-led/pumba (untagged image)",
         "faultinjection/fault_config.py; version not recorded"),
        ("Python", n["version_python"], "README"),
        ("Python libraries", "NumPy %s, pandas %s, SciPy %s, statsmodels %s, NetworkX %s, "
         "matplotlib %s" % (n["version_numpy"], n["version_pandas"], n["version_scipy"],
                            n["version_statsmodels"], n["version_networkx"],
                            n["version_matplotlib"]), "README"),
        ("Locust", "%s; %s users, spawn rate %s users/s, wait %s-%s s between requests"
         % (n["version_locust"], n["protocol_load_users"], n["protocol_spawn_rate"],
            n["protocol_sn_wait_min_s"], n["protocol_sn_wait_max_s"]),
         "runner and locustfiles"),
        ("Request mix, Social Network", "compose post %s, home timeline %s, user timeline %s"
         % (n["protocol_sn_task_weight_compose_post"],
            n["protocol_sn_task_weight_read_home_timeline"],
            n["protocol_sn_task_weight_read_user_timeline"]), "task weights"),
        ("Request mix, Hotel Reservation", "search %s, reservation %s, user %s, "
         "recommendation %s" % (n["protocol_hr_task_weight_hotel_search"],
                                n["protocol_hr_task_weight_make_reservation"],
                                n["protocol_hr_task_weight_get_user"],
                                n["protocol_hr_task_weight_get_recommendations"]),
         "task weights"),
        ("Load before the fault (s)", "%s; the baseline is computed over this window"
         % n["protocol_warmup_s"], "runner"),
        ("Fault hold (s)", n["protocol_fault_duration_s"], "runner"),
        ("Recovery probe (s)", "poll %s, confirmation %s, window lag %s, cap %s"
         % (n["trec_poll_interval_nominal_s"], n["protocol_confirm_s"],
            n["protocol_probe_lag_s"], n["protocol_recovery_cap_s"]), "runner"),
        ("Cooldown (s)", n["protocol_cooldown_s"], "runner"),
    ]
    emit("tbl_testbed", pd.DataFrame(rows, columns=["item", "value", "source"]),
         "Testbed and run protocol. Host values marked measured were queried after the "
         "campaign; all others were recorded before or during it",
         "paper/numbers.csv (testbed_*, version_*, protocol_* ids)", "paper/make_tables.py")

    lists = literal_commands("tools/run_pilot.py")
    pick = lambda *keys: next(c for c in lists if all(k in c for k in keys))  # noqa: E731
    lat = replace(DEFAULT_SPECS[FaultType.LATENCY],
                  duration_seconds=int(n["protocol_fault_duration_s"]))
    cmd = lambda spec: " ".join(["docker"] + spec.pumba_command("<container>")[1:])  # noqa
    rows = [
        ("Load generation", pick("locust", "--users"), "tools/run_pilot.py: start_load"),
        ("Target resolution", pick("ps", "--filter"), "tools/run_pilot.py: container_for"),
        ("Kill fault", cmd(DEFAULT_SPECS[FaultType.KILL]),
         "faultinjection/fault_config.py: pumba_command"),
        ("Latency fault", cmd(lat), "faultinjection/fault_config.py: pumba_command"),
        ("Restore after a kill", next(c for c in lists if c.startswith("docker compose up")
                                      and "--force-recreate" not in c),
         "tools/run_pilot.py: one_run"),
        ("Clean-up after a latency fault", pick("--force-recreate"),
         "tools/run_pilot.py: one_run"),
    ]
    emit("tbl_commands", pd.DataFrame(rows, columns=["step", "command", "source"]),
         "Command lines issued for each run, generated from the runner code (the runner "
         "starts load, resolves the target container, injects the fault and restores the "
         "service)", "tools/run_pilot.py + faultinjection/fault_config.py",
         "paper/make_tables.py")


def ws_table():
    p = os.path.join(FINAL, "weight_sensitivity_summary.csv")
    if not os.path.isfile(p):
        return
    s = pd.read_csv(p)
    rows = []
    for _, r in s.iterrows():
        rows.append({
            "architecture": r.architecture_label, "fault_type": r.fault_type,
            "outcome": r.outcome, "triplets_defined": int(r.triplets_defined),
            "rho_min": f(r.rho_min, 3), "rho_median": f(r.rho_median, 3),
            "rho_max": f(r.rho_max, 3), "rho_positive": int(r.triplets_rho_positive),
            "p_raw_below_05": int(r.triplets_p_raw_below_05),
            "significant_bh_231": int(r.triplets_significant_bh),
            "rho_at_0.4/0.4/0.2": f(r.reported_rho, 3),
            "p_at_0.4/0.4/0.2": f(r.reported_p, 4),
        })
    emit("tbl_weight_sensitivity", pd.DataFrame(rows),
         "Post hoc weight sensitivity of the hybrid metric over 231 weight triplets: "
         "distribution of Spearman rho, counts of positive and significant correlations "
         "(BH within each family of 231), and the values at the reported weights",
         "analysis/final/weight_sensitivity_summary.csv",
         "analysis/final/weight_sensitivity.py")


if __name__ == "__main__":
    main()
