"""
make_figures.py -- the manuscript's figures, as PNG and PDF, with their backing data.

Four figures, each written to paper/figures/ in both formats, each accompanied by the CSV
it was plotted from so that every plotted point is traceable to a file:

  fig_primary_sn        ancestor_count vs measured ancestor_affected_count, Social Network,
                        with the y = x line and user-service labelled
  fig_rank_inversion    ancestor_count rank vs hybrid_criticality rank, all 11 SN services,
                        with compose-post-service highlighted
  fig_leave_one_out     post-hoc: primary rho recomputed with each service excluded
  fig_q3_artifact       the measurement artifact: per-service p95 under the old end-to-end
                        root-span scope versus the corrected own-server-span scope, Hotel
                        Reservation, recomputed here from the persisted pilot spans

paper/figures/figures_index.csv records what each figure shows and its data file.

Run: python paper/make_figures.py
"""
from __future__ import annotations

import glob
import gzip
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FINAL = os.path.join(REPO, "analysis", "final")
OUT = os.path.join(HERE, "figures")
RCA = "analysis/final/run_confirmatory_analysis.py"

FACTOR, FLOOR_MS = 2.0, 1.0
INDEX = []


def save(fig, name, shows, data_file, source_file, source_script):
    os.makedirs(OUT, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, "%s.%s" % (name, ext)), dpi=200,
                    bbox_inches="tight")
    plt.close(fig)
    INDEX.append({"figure": name, "shows": shows, "data_file": data_file,
                  "source_file": source_file, "source_script": source_script,
                  "formats": "png, pdf"})
    print("  %-22s -> %s.png / .pdf" % (name, name))


# ---------------------------------------------------------------- figure 1 ---
def fig_primary(svc):
    d = svc[(svc.app == "socialnetwork") & (svc.in_analysis_set)].copy()
    data = d[["service", "fault_type", "ancestor_count", "ancestor_affected_count"]]
    data.to_csv(os.path.join(OUT, "fig_primary_sn_data.csv"), index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for ax, ft in zip(axes, ("kill", "latency")):
        g = d[d.fault_type == ft]
        lim = [0, max(g.ancestor_count.max(), g.ancestor_affected_count.max()) + 0.6]
        ax.plot(lim, lim, ls="--", lw=1.2, color="0.55", zorder=1,
                label="y = x (perfect saturation)")
        jitter = np.linspace(-0.06, 0.06, len(g))
        for (_, r), j in zip(g.iterrows(), jitter):
            dep = r.ancestor_affected_count != r.ancestor_count
            ax.scatter(r.ancestor_count + j, r.ancestor_affected_count,
                       s=95 if dep else 55,
                       color="#c0392b" if dep else "#2c6fbb",
                       edgecolor="black" if dep else "none",
                       linewidth=1.1 if dep else 0, zorder=3)
            if dep:
                ax.annotate(r.service, (r.ancestor_count + j, r.ancestor_affected_count),
                            textcoords="offset points", xytext=(9, -3),
                            fontsize=9, fontweight="bold", color="#c0392b")
        ax.set_xlim(lim); ax.set_ylim(lim)
        ax.set_xlabel("graph ancestor_count")
        ax.set_title("%s faults" % ft)
        ax.grid(alpha=0.25, lw=0.6)
    axes[0].set_ylabel("measured ancestor_affected_count\n(median of 5 repetitions)")
    axes[0].legend(loc="upper left", fontsize=9, frameon=False)
    fig.suptitle("Social Network: predicted vs measured blast radius. Points on the "
                 "dashed line are\nsaturated, where the outcome restates the predictor; "
                 "only the labelled services depart.",
                 fontsize=10.5, y=1.04)
    save(fig, "fig_primary_sn",
         "ancestor_count vs measured ancestor_affected_count per SN service, with y=x "
         "and the departing services labelled",
         "paper/figures/fig_primary_sn_data.csv",
         "analysis/final/service_level_data.csv", RCA)


# ---------------------------------------------------------------- figure 2 ---
def fig_rank_inversion(ranks):
    d = ranks[ranks.in_analysis_set].copy().sort_values("rank_hybrid_criticality")
    data = d[["service", "ancestor_count", "hybrid_criticality",
              "rank_ancestor_count", "rank_hybrid_criticality"]]
    data.to_csv(os.path.join(OUT, "fig_rank_inversion_data.csv"), index=False)

    # Both rankings contain ties, so points and labels are spread vertically within each
    # tie group. The spread is cosmetic; the plotted rank is the value in the data file.
    def spread(col):
        pos = {}
        for rank, grp in d.groupby(col):
            names = list(grp.service)
            offs = np.linspace(-0.16 * (len(names) - 1), 0.16 * (len(names) - 1),
                               len(names))
            for nm, o in zip(names, offs):
                pos[nm] = float(rank) + float(o)
        return pos

    yl, yr = spread("rank_hybrid_criticality"), spread("rank_ancestor_count")

    fig, ax = plt.subplots(figsize=(9.6, 6.6))
    n = len(d)
    for _, r in d.iterrows():
        cp = r.service == "compose-post-service"
        ax.plot([0, 1], [yl[r.service], yr[r.service]],
                marker="o", ms=7 if cp else 5,
                color="#c0392b" if cp else "0.65",
                lw=2.4 if cp else 1.1, zorder=3 if cp else 2)
        ax.annotate("%s (%d)" % (r.service, r.rank_hybrid_criticality),
                    (0, yl[r.service]), textcoords="offset points", xytext=(-9, 0),
                    ha="right", va="center", fontsize=8.5,
                    fontweight="bold" if cp else "normal",
                    color="#c0392b" if cp else "0.3")
        ax.annotate("(%d) %s" % (r.rank_ancestor_count, r.service),
                    (1, yr[r.service]), textcoords="offset points", xytext=(9, 0),
                    ha="left", va="center", fontsize=8.5,
                    fontweight="bold" if cp else "normal",
                    color="#c0392b" if cp else "0.3")
    ax.set_xlim(-1.05, 2.05); ax.set_ylim(n + 0.8, 0.2)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["rank by\nhybrid_criticality\n(the proposed metric)",
                        "rank by\nancestor_count\n(the corrected predictor)"])
    ax.set_ylabel("rank (1 = most critical)")
    ax.set_yticks(range(1, n + 1))
    ax.grid(axis="y", alpha=0.25, lw=0.6)
    ax.set_title("compose-post-service is ranked first by the proposed metric and last by\n"
                 "the corrected predictor; its measured blast radius is 1 ancestor in "
                 "10 of 10 runs.", fontsize=10.5)
    save(fig, "fig_rank_inversion",
         "Rank of all 11 SN services by hybrid_criticality vs by ancestor_count, "
         "compose-post-service highlighted",
         "paper/figures/fig_rank_inversion_data.csv",
         "analysis/final/sn_predictor_ranks.csv", RCA)


# ---------------------------------------------------------------- figure 3 ---
def fig_leave_one_out(loo):
    d = loo[(loo.fault_type == "kill") &
            (~loo.service_excluded.str.startswith("NONE"))].copy()
    full = float(loo[(loo.fault_type == "kill") &
                     (loo.service_excluded.str.startswith("NONE"))].rho.iloc[0])
    d = d.sort_values("rho")
    d[["service_excluded", "n_services", "rho",
       "p_permutation_nominal_uncorrected"]].to_csv(
        os.path.join(OUT, "fig_leave_one_out_data.csv"), index=False)

    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    colors = ["#c0392b" if s == "user-service" else "#7f8c8d" for s in d.service_excluded]
    ax.barh(range(len(d)), d.rho, color=colors, height=0.66)
    ax.axvline(full, color="#2c6fbb", ls="--", lw=1.6,
               label="full 11-service set (rho = %.3f)" % full)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d.service_excluded, fontsize=9)
    ax.set_xlabel("Spearman rho after excluding that service")
    ax.set_ylabel("service excluded")
    ax.set_xlim(0, 1.06)
    for i, v in enumerate(d.rho):
        ax.text(v + 0.012, i, "%.3f" % v, va="center", fontsize=8.5)
    ax.legend(loc="lower right", fontsize=9, frameon=False)
    ax.grid(axis="x", alpha=0.25, lw=0.6)
    ax.set_title("POST-HOC robustness check (not part of the preregistered family).\n"
                 "Excluding user-service drives rho to 1.000: it is the only service whose "
                 "removal\ncompletes the tautology.", fontsize=10.5)
    save(fig, "fig_leave_one_out",
         "Post-hoc: primary rho recomputed with each SN service excluded, kill faults",
         "paper/figures/fig_leave_one_out_data.csv",
         "analysis/final/leave_one_out.csv", "analysis/final/leave_one_out.py")


# ---------------------------------------------------------------- figure 4 ---
def q3_scopes(path):
    """Per-service p95 under both scopes, from one persisted span window.

    OLD scope -- 'end_to_end_root': every service present in a trace is charged the trace's
    ROOT span duration, so all services on a slow trace report the same tail.
    NEW scope -- own server spans only.
    """
    d = json.load(gzip.open(os.path.join(REPO, path), "rt", encoding="utf-8"))
    old, new = defaultdict(list), defaultdict(list)
    for tr in d["traces"]:
        pmap = {k: v["serviceName"] for k, v in tr["processes"].items()}
        roots = [s for s in tr["spans"] if not s.get("references")]
        if not roots:
            continue
        root_ms = max(s["duration"] for s in roots) / 1000.0
        present = set()
        for s in tr["spans"]:
            svc = pmap.get(s["processID"])
            if svc is None:
                continue
            present.add(svc)
            tags = {t["key"]: t["value"] for t in s["tags"]}
            if tags.get("span.kind") == "server":
                new[svc].append(s["duration"] / 1000.0)
        for svc in present:
            old[svc].append(root_ms)
    out = {}
    for svc in set(old) | set(new):
        out[svc] = {
            "old_p95": float(np.percentile(old[svc], 95)) if old.get(svc) else np.nan,
            "new_p95": float(np.percentile(new[svc], 95)) if new.get(svc) else np.nan,
        }
    return out


def flagged(base, fault):
    if base is None or fault is None:
        return False
    if not np.isfinite(base) or not np.isfinite(fault) or base <= 0:
        return False
    return fault > FACTOR * base and fault - base >= FLOOR_MS


def fig_q3():
    runs = sorted(glob.glob(os.path.join(
        REPO, "data", "pilot",
        "pilot_hotelreservation_search_latency_rep*_2026-09-26T*.json")))
    if not runs:
        print("  SKIP fig_q3_artifact: SOURCE NOT FOUND (no 2026-09-26 HR pilot runs)")
        return

    rows = []
    for rf in runs:
        r = json.load(open(rf, encoding="utf-8"))
        rep = r.get("repetition") or r.get("rep")
        b = q3_scopes(r["raw_spans"]["baseline_window"]["path"])
        a = q3_scopes(r["raw_spans"]["fault_window"]["path"])
        for svc in sorted(set(b) | set(a)):
            ob, of = b.get(svc, {}).get("old_p95"), a.get(svc, {}).get("old_p95")
            nb, nf = b.get(svc, {}).get("new_p95"), a.get(svc, {}).get("new_p95")
            rows.append({
                "run": os.path.basename(rf), "repetition": rep, "service": svc,
                "faulted": svc == r["service"],
                "old_baseline_p95_ms": ob, "old_fault_p95_ms": of,
                "old_flagged": flagged(ob, of),
                "new_baseline_p95_ms": nb, "new_fault_p95_ms": nf,
                "new_flagged": flagged(nb, nf),
            })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "fig_q3_artifact_data.csv"), index=False)

    rep1 = df[df.repetition == df.repetition.min()].sort_values("service")
    svcs = list(rep1.service)
    x = np.arange(len(svcs))
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.0), sharey=True)
    for ax, (bcol, fcol, flag, title) in zip(axes, [
            ("old_baseline_p95_ms", "old_fault_p95_ms", "old_flagged",
             "OLD scope: end-to-end root span\n(every service charged the trace tail)"),
            ("new_baseline_p95_ms", "new_fault_p95_ms", "new_flagged",
             "CORRECTED scope: the service's own server spans")]):
        ax.bar(x - 0.2, rep1[bcol], width=0.4, label="baseline p95", color="#8fb8de")
        ax.bar(x + 0.2, rep1[fcol], width=0.4, label="fault p95", color="#c0392b")
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels([("%s *" % s) if f else s
                            for s, f in zip(svcs, rep1[flag])],
                           rotation=45, ha="right", fontsize=9)
        ax.set_title("%s\nflagged: %s" % (title, ", ".join(rep1[rep1[flag]].service) or "none"),
                     fontsize=10)
        ax.grid(axis="y", alpha=0.25, lw=0.6, which="both")
    axes[0].set_ylabel("p95 latency (ms, log scale)")
    axes[0].legend(fontsize=9, frameon=False)
    # Counts are read off the data, never asserted: exclude the faulted service itself,
    # which is expected to be flagged under either scope.
    nf = rep1[~rep1.faulted]
    n_old, n_new = int(nf.old_flagged.sum()), int(nf.new_flagged.sum())
    fig.suptitle("Hotel Reservation, latency fault injected into 'search'. Excluding the "
                 "faulted service, the old\nscope flags %d services that clear the 2x "
                 "threshold together because they share a trace;\nthe corrected scope "
                 "flags %d. Asterisk marks a flagged service."
                 % (n_old, n_new), fontsize=10.5, y=1.10)
    save(fig, "fig_q3_artifact",
         "Per-service p95 under the old end-to-end root-span scope vs the corrected "
         "own-span scope, HR search latency fault",
         "paper/figures/fig_q3_artifact_data.csv",
         "data/pilot/pilot_hotelreservation_search_latency_rep*_2026-09-26T*.json "
         "+ data/spans/", "paper/make_figures.py")


def main():
    os.makedirs(OUT, exist_ok=True)
    svc = pd.read_csv(os.path.join(FINAL, "service_level_data.csv"))
    ranks = pd.read_csv(os.path.join(FINAL, "sn_predictor_ranks.csv"))
    loo = pd.read_csv(os.path.join(FINAL, "leave_one_out.csv"))

    fig_primary(svc)
    fig_rank_inversion(ranks)
    fig_leave_one_out(loo)
    fig_q3()

    pd.DataFrame(INDEX).to_csv(os.path.join(OUT, "figures_index.csv"), index=False)
    print("wrote %d figures and figures_index.csv" % len(INDEX))


if __name__ == "__main__":
    main()
