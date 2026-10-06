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
        "verdict": h1b.h1b_verdict,
    })
    emit("tbl_h1b", h,
         "H1b: hybrid_criticality vs ancestor_affected_count in all four "
         "architecture-by-fault cells", "analysis/final/h1b_hybrid_metric.csv", RCA)

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

    # ---- 7. deviations ------------------------------------------------------
    d = devs.sort_values("n")[["n", "date", "title", "stage", "what_happened",
                               "what_changed", "outcome_affected", "runs_invalidated",
                               "runs_disposition", "record", "detected_by"]]
    emit("tbl_deviations", d,
         "Every deviation from the preregistration, ready for the deviations section",
         "analysis/final/deviations.csv", RCA)

    pd.DataFrame(INDEX).to_csv(os.path.join(OUT, "tables_index.csv"), index=False)
    print("wrote %d tables (csv + md) and tables_index.csv" % len(INDEX))


if __name__ == "__main__":
    main()
