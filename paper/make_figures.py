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
    # PNG at 400 dpi so every figure is at least 3000 px wide (PeerJ); the PDF is vector.
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, "%s.%s" % (name, ext)), dpi=400,
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
    # The highlighted bar is also hatched, so it does not depend on colour alone.
    hatches = ["///" if s == "user-service" else "" for s in d.service_excluded]
    bars = ax.barh(range(len(d)), d.rho, color=colors, height=0.66, edgecolor="black",
                   linewidth=0.6)
    for b, h in zip(bars, hatches):
        b.set_hatch(h)
    ax.axvline(full, color="#2c6fbb", ls="--", lw=1.6,
               label="full 11-service set (rho = %.3f)" % full)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d.service_excluded, fontsize=9)
    ax.set_xlabel("Spearman rho after excluding that service")
    ax.set_ylabel("service excluded")
    ax.set_xlim(0, 1.06)
    for i, v in enumerate(d.rho):
        ax.text(v + 0.012, i, "%.3f" % v, va="center", fontsize=8.5)
    # Outside the plot area, so it cannot cover bars, value labels or the reference line.
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=9, frameon=False)
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
        ax.bar(x - 0.2, rep1[bcol], width=0.4, label="baseline p95", color="#8fb8de",
               edgecolor="black", linewidth=0.6)
        # Fault bars are hatched so the two series do not depend on colour alone.
        ax.bar(x + 0.2, rep1[fcol], width=0.4, label="fault p95", color="#c0392b",
               hatch="///", edgecolor="black", linewidth=0.6)
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels([("%s *" % s) if f else s
                            for s, f in zip(svcs, rep1[flag])],
                           rotation=45, ha="right", fontsize=9)
        ax.set_title("%s\nflagged: %s" % (title, ", ".join(rep1[rep1[flag]].service) or "none"),
                     fontsize=10)
        ax.grid(axis="y", alpha=0.25, lw=0.6, which="both")
    axes[0].set_ylabel("p95 latency (ms, log scale)")
    # One legend for both panels, outside the plot area so it covers no bar.
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=9,
               frameon=False)
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


# ------------------------------------------- figures added 2026-10-20 (IEEE) ---

def numbers():
    df = pd.read_csv(os.path.join(HERE, "numbers.csv"), dtype=str, keep_default_na=False)
    return dict(zip(df.claim_id, df.value))


def box(ax, x, y, w, h, title, sub="", fc="#ffffff", ec="#333333", fs=8.5, sfs=6.5):
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                fc=fc, ec=ec, lw=0.9))
    ax.text(x + w / 2, y + h * (0.64 if sub else 0.5), title, ha="center", va="center",
            fontsize=fs, fontweight="bold")
    if sub:
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", fontsize=sfs,
                family="monospace", color="#333333")


def arrow(ax, x0, y0, x1, y1, text="", fs=6.5, color="#333333"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", lw=0.9, color=color,
                                shrinkA=0, shrinkB=0))
    if text:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, text, fontsize=fs, ha="center", va="bottom",
                color=color, backgroundcolor="white")


# Each step of the campaign pipeline and the repository files that carry it out. The figure
# is drawn from this list, and every file must exist.
PIPELINE = [
    ("Deploy stack", "tools/run_campaign.py (stack_up, stack_healthy)",
     ["tools/run_campaign.py", "infra/docker-compose.override.yml",
      "infra/hotel-compose.override.yml"]),
    ("Locust workload", "infra/_locustfile_*.py; run_pilot.start_load",
     ["infra/_locustfile_baseline.py", "infra/_locustfile_hotel.py", "tools/run_pilot.py"]),
    ("Trace collection (Jaeger)", "measurement/metrics_collector.py",
     ["measurement/metrics_collector.py"]),
    ("Graph reconstruction", "tools/extract_graph.py -> data/graphs/",
     ["tools/extract_graph.py", "data/graphs/sn_CANONICAL.json",
      "data/graphs/hr_CANONICAL.json"]),
    ("Predictor computation", "tools/build_predictor_table.py; centrality/",
     ["tools/build_predictor_table.py", "centrality/compute_centrality.py",
      "centrality/hybrid_weight_optimizer.py"]),
    ("Preregistration lock", "PREREGISTRATION_v3_LOCKED.md",
     ["_audit/preregistration_versions/PREREGISTRATION_v3_LOCKED.md"]),
    ("Fault injection (Pumba kill / netem)", "faultinjection/fault_config.py; run_pilot.one_run",
     ["faultinjection/fault_config.py", "tools/run_pilot.py"]),
    ("Per-service metric extraction", "measurement/metrics_collector.py",
     ["measurement/metrics_collector.py"]),
    ("Blast-radius classification", "measurement/blast_radius.py",
     ["measurement/blast_radius.py"]),
    ("Recovery probe", "measurement/recovery_probe.py", ["measurement/recovery_probe.py"]),
    ("Integrity gates", "tools/audit_run_topology.py; tools/audit_baseline_sanity.py",
     ["tools/audit_run_topology.py", "tools/audit_baseline_sanity.py"]),
    ("Statistical analysis", "analysis/final/run_confirmatory_analysis.py",
     ["analysis/final/run_confirmatory_analysis.py", "analysis/final/fast_stats.py"]),
]


def fig_pipeline():
    nums = numbers()
    rows = []
    for i, (step, sub, files) in enumerate(PIPELINE, 1):
        for f in files:
            if not os.path.isfile(os.path.join(REPO, f)):
                raise SystemExit("pipeline figure names a missing file: %s" % f)
        rows.append({"step": i, "name": step, "files": "; ".join(files)})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "fig_pipeline_data.csv"), index=False)

    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    w, h, gap = 0.42, 0.115, 0.034
    cols = [(0.02, PIPELINE[:6], range(1, 7)), (0.56, PIPELINE[6:], range(7, 13))]
    tops = 0.92
    geo = []
    for x, steps, nos in cols:
        for k, ((step, sub, _), n) in enumerate(zip(steps, nos)):
            y = tops - k * (h + gap) - h
            fc = "#eef3fb" if n <= 6 else ("#fdf2e9" if n <= 10 else "#edf7ee")
            box(ax, x, y, w, h, "%d. %s" % (n, step), sub.replace("; ", "\n"), fc=fc,
                fs=7.8, sfs=5.6)
            geo.append((x, y))
    for (xa, ya), (xb, yb) in list(zip(geo[:5], geo[1:6])) + list(zip(geo[6:11], geo[7:12])):
        arrow(ax, xa + w / 2, ya, xb + w / 2, yb + h)
    # 6 -> 7 through the gap between the columns
    (x6, y6), (x7, y7) = geo[5], geo[6]
    xm = (x6 + w + x7) / 2
    ax.plot([x6 + w, xm, xm], [y6 + h / 2, y6 + h / 2, y7 + h / 2], color="#333333", lw=0.9)
    arrow(ax, xm, y7 + h / 2, x7, y7 + h / 2)
    ax.text(0.23, 0.955, "Before the campaign", ha="center", fontsize=7.5, style="italic")
    ax.text(0.77, 0.955, "Steps 7-10 in each of the %s runs; 11-12 after the campaign"
            % nums["campaign_runs_total"], ha="center", fontsize=7.5, style="italic")
    save(fig, "fig_pipeline",
         "Methodology pipeline in execution order; each box names the repository files "
         "that carry out the step, and the steps from fault injection to the recovery probe "
         "repeat for every run",
         "paper/figures/fig_pipeline_data.csv", "repository files listed in the figure",
         "paper/make_figures.py")

def fig_deployment():
    import importlib.util
    import sys as _sys
    nums = numbers()
    _sys.path.insert(0, REPO)
    spec = importlib.util.spec_from_file_location("run_pilot",
                                                  os.path.join(REPO, "tools", "run_pilot.py"))
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)
    port = lambda url: url.rsplit(":", 1)[1]  # noqa: E731
    sn, hr = rp.APPS["socialnetwork"], rp.APPS["hotelreservation"]

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((0.01, 0.02), 0.98, 0.94, boxstyle="round,pad=0.005",
                                fc="#fafafa", ec="#555555", lw=1))
    ax.text(0.03, 0.925, "Host: %s, %s cores / %s threads, %s GB RAM"
            % (nums["testbed_host_os"], nums["testbed_cpu_cores"],
               nums["testbed_cpu_logical"], nums["testbed_host_ram_gb"]),
            fontsize=7, fontweight="bold", va="center")
    ax.add_patch(FancyBboxPatch((0.34, 0.05), 0.63, 0.82, boxstyle="round,pad=0.005",
                                fc="#eef3fb", ec="#4a6fa5", lw=1))
    ax.text(0.36, 0.835, "Docker Desktop %s, %s VM, %s GiB memory"
            % (nums["version_docker_desktop"], nums["testbed_docker_backend"],
               nums["testbed_docker_vm_gib"]), fontsize=7, fontweight="bold", va="center")
    box(ax, 0.37, 0.48, 0.30, 0.30, "Application stack",
        "one stack at a time\nSocial Network: %s containers\nHotel Reservation: %s containers"
        % (nums["testbed_containers_sn"], nums["testbed_containers_hr"]),
        fc="#ffffff", fs=7.5, sfs=5.6)
    box(ax, 0.75, 0.52, 0.20, 0.22, "Jaeger %s" % nums["version_jaeger"],
        "all-in-one\n%s storage" % nums["testbed_jaeger_storage"], fc="#ffffff", fs=7.5,
        sfs=5.6)
    box(ax, 0.37, 0.09, 0.30, 0.19, "Pumba container",
        "docker run --rm\nmounts /var/run/docker.sock", fc="#ffffff", fs=7.5, sfs=5.6)
    box(ax, 0.04, 0.60, 0.24, 0.20, "Locust %s" % nums["version_locust"],
        "%s users, host process" % nums["protocol_load_users"], fc="#ffffff", fs=7.5,
        sfs=5.6)
    box(ax, 0.04, 0.12, 0.24, 0.30, "Campaign runner",
        "tools/run_campaign.py\nPython %s" % nums["version_python"], fc="#ffffff", fs=7.5,
        sfs=5.6)

    def lab(x, y, t):
        ax.text(x, y, t, fontsize=5.6, ha="center", va="center", color="#333333")
    arrow(ax, 0.28, 0.70, 0.37, 0.70)
    lab(0.325, 0.75, "HTTP\n:%s / :%s" % (port(sn["url"]), port(hr["url"])))
    arrow(ax, 0.67, 0.63, 0.75, 0.63)
    lab(0.71, 0.665, "spans")
    ax.plot([0.28, 0.85], [0.38, 0.38], color="#333333", lw=0.9)
    arrow(ax, 0.85, 0.38, 0.85, 0.52)
    lab(0.76, 0.405, "trace queries :%s / :%s" % (port(sn["jaeger"]), port(hr["jaeger"])))
    arrow(ax, 0.28, 0.185, 0.37, 0.185)
    lab(0.325, 0.215, "docker CLI")
    arrow(ax, 0.52, 0.28, 0.52, 0.48)
    lab(0.585, 0.33, "kill / netem")
    arrow(ax, 0.16, 0.42, 0.16, 0.60)
    lab(0.215, 0.51, "start / stop")
    pd.DataFrame([{"element": k, "value": v} for k, v in (
        ("host", nums["testbed_host_os"]), ("cpu_cores", nums["testbed_cpu_cores"]),
        ("vm_gib", nums["testbed_docker_vm_gib"]),
        ("containers_sn", nums["testbed_containers_sn"]),
        ("containers_hr", nums["testbed_containers_hr"]),
        ("gateway_port_sn", port(sn["url"])), ("gateway_port_hr", port(hr["url"])),
        ("jaeger_port_sn", port(sn["jaeger"])), ("jaeger_port_hr", port(hr["jaeger"])))]) \
        .to_csv(os.path.join(OUT, "fig_deployment_data.csv"), index=False)
    save(fig, "fig_deployment",
         "Testbed deployment: the host, the Docker Desktop VM, the application stack, Jaeger "
         "and Pumba containers, and the host-side Locust and campaign runner",
         "paper/figures/fig_deployment_data.csv",
         "paper/numbers.csv + tools/run_pilot.py (APPS)", "paper/make_figures.py")

def fig_service_graph(app, short, label):
    import networkx as nx
    g = json.load(open(os.path.join(REPO, "data", "graphs", "%s_CANONICAL.json" % short),
                       encoding="utf-8"))
    G = nx.node_link_graph(g, edges="edges")
    gateway = [n for n in G.nodes if G.in_degree(n) == 0]
    level = {n: 0 for n in G.nodes}
    for n in nx.topological_sort(G):            # layered by longest path from the gateway
        for m in G.successors(n):
            level[m] = max(level[m], level[n] + 1)
    layers = defaultdict(list)
    for n, lv in level.items():
        layers[lv].append(n)
    order = {lv: sorted(ns) for lv, ns in layers.items()}
    for _ in range(4):                          # barycentre ordering to reduce crossings
        for lv in sorted(order)[1:]:
            idx = {n: i - (len(order[l2]) - 1) / 2
                   for l2 in order if l2 < lv for i, n in enumerate(order[l2])}

            def bary(n):
                ps = [idx[q] for q in G.predecessors(n) if q in idx]
                return (sum(ps) / len(ps)) if ps else 0
            order[lv] = sorted(order[lv], key=lambda n: (bary(n), n))
    pos = {}
    for lv, ns in order.items():
        for k, n in enumerate(ns):
            pos[n] = (lv * 3.0, -(k - (len(ns) - 1) / 2) * 0.9)
    tall = max(len(v) for v in order.values())
    fig, ax = plt.subplots(figsize=(7.2, 0.42 * tall + 0.9))
    texts = {}
    for n, (x, y) in pos.items():
        gw = n in gateway
        texts[n] = ax.text(x, y, n + ("\n(gateway)" if gw else ""), ha="center",
                           va="center", fontsize=6.5, zorder=3,
                           bbox=dict(boxstyle="round,pad=0.3",
                                     fc="#f6d7b0" if gw else "#eef3fb",
                                     ec="#b5651d" if gw else "#4a6fa5", lw=0.9))
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    ax.set_xlim(min(xs) - 1.4, max(xs) + 1.4)
    ax.set_ylim(min(ys) - 0.6, max(ys) + 0.6)
    ax.axis("off")
    # Arrows run from the edge of the caller's label box to the edge of the callee's.
    fig.canvas.draw()
    inv = ax.transData.inverted()
    boxes = {n: inv.transform(t.get_bbox_patch().get_window_extent())
             for n, t in texts.items()}

    def exit_point(n, other):
        (x0, y0), (x1, y1) = boxes[n]
        cx, cy = pos[n]
        dx, dy = other[0] - cx, other[1] - cy
        ts = [t for t in ((x1 - cx) / dx if dx > 0 else (x0 - cx) / dx if dx < 0 else 9,
                          (y1 - cy) / dy if dy > 0 else (y0 - cy) / dy if dy < 0 else 9)
              if t > 0]
        t = min(ts)
        return cx + t * dx, cy + t * dy
    for u, v in G.edges:
        a = exit_point(u, pos[v])
        b = exit_point(v, pos[u])
        ax.annotate("", xy=b, xytext=a, zorder=2,
                    arrowprops=dict(arrowstyle="-|>", lw=0.7, color="#555555",
                                    shrinkA=0, shrinkB=0, mutation_scale=8))
    pd.DataFrame([{"caller": u, "callee": v, "call_count": d.get("call_count")}
                  for u, v, d in G.edges(data=True)]) \
        .to_csv(os.path.join(OUT, "fig_graph_%s_data.csv" % short), index=False)
    save(fig, "fig_graph_%s" % short,
         "%s dependency graph as observed in traces: %d services and %d caller-to-callee "
         "edges, gateway marked" % (label, G.number_of_nodes(), G.number_of_edges()),
         "paper/figures/fig_graph_%s_data.csv" % short,
         "data/graphs/%s_CANONICAL.json" % short, "paper/make_figures.py")

def fig_weight_sensitivity():
    ws = pd.read_csv(os.path.join(FINAL, "weight_sensitivity.csv"))
    panels = [("socialnetwork", "kill", "ancestor_affected_count",
               "(a) Social Network,\nancestor_affected_count"),
              ("hotelreservation", "kill", "ancestor_affected_count",
               "(b) Hotel Reservation,\nancestor_affected_count"),
              ("socialnetwork", "kill", "delta_error_rate",
               "(c) Social Network,\ngateway error rate (exploratory)"),
              ("hotelreservation", "kill", "delta_error_rate",
               "(d) Hotel Reservation,\ngateway error rate (exploratory)")]
    fig, axes = plt.subplots(2, 2, figsize=(5.2, 4.9))
    s3 = np.sqrt(3) / 2
    for ax, (app, fault, outcome, title) in zip(axes.flat, panels):
        d = ws[(ws.architecture == app) & (ws.fault_type == fault) & (ws.outcome == outcome)]
        x = d.w_out + d.w_btw / 2
        y = d.w_btw * s3
        ok = d.spearman_rho.notna()
        sc = ax.scatter(x[ok], y[ok], c=d.spearman_rho[ok], cmap="RdBu_r", vmin=-1, vmax=1,
                        s=11, linewidths=0)
        ax.scatter(x[~ok], y[~ok], marker="x", c="#555555", s=16, linewidths=0.9)
        r = d[d.is_reported_triplet]
        ax.scatter(r.w_out + r.w_btw / 2, r.w_btw * s3, marker="o", s=55,
                   facecolors="none", edgecolors="black", linewidths=1.2)
        ax.plot([0, 1, 0.5, 0], [0, 0, s3, 0], color="#444444", lw=0.6)
        ax.text(0.0, -0.05, "$w_{in}$=1", fontsize=6.5, ha="center", va="top")
        ax.text(1.0, -0.05, "$w_{out}$=1", fontsize=6.5, ha="center", va="top")
        ax.text(0.5, s3 + 0.03, "$w_{btw}$=1", fontsize=6.5, ha="center", va="bottom")
        ax.set_title(title, fontsize=7)
        ax.set_xlim(-0.12, 1.12)
        ax.set_ylim(-0.16, 1.0)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.subplots_adjust(right=0.86, hspace=0.30, wspace=0.05)
    cax = fig.add_axes([0.89, 0.25, 0.025, 0.5])
    cb = fig.colorbar(sc, cax=cax)
    cb.set_label("Spearman rho", fontsize=7)
    cb.ax.tick_params(labelsize=6.5)
    save(fig, "fig_weight_sensitivity",
         "Post hoc weight sensitivity: Spearman rho of the hybrid metric against each outcome "
         "for all 231 weight triplets (kill faults; latency faults give identical "
         "ancestor_affected_count results); circled point: the reported weights 0.4/0.4/0.2; "
         "x: metric constant",
         "analysis/final/weight_sensitivity.csv", "analysis/final/weight_sensitivity.csv",
         "paper/make_figures.py")

def main():
    os.makedirs(OUT, exist_ok=True)
    svc = pd.read_csv(os.path.join(FINAL, "service_level_data.csv"))
    ranks = pd.read_csv(os.path.join(FINAL, "sn_predictor_ranks.csv"))
    loo = pd.read_csv(os.path.join(FINAL, "leave_one_out.csv"))

    fig_primary(svc)
    fig_rank_inversion(ranks)
    fig_leave_one_out(loo)
    fig_q3()
    fig_pipeline()
    fig_deployment()
    fig_service_graph("socialnetwork", "sn", "Social Network")
    fig_service_graph("hotelreservation", "hr", "Hotel Reservation")
    fig_weight_sensitivity()

    pd.DataFrame(INDEX).to_csv(os.path.join(OUT, "figures_index.csv"), index=False)
    print("wrote %d figures and figures_index.csv" % len(INDEX))


if __name__ == "__main__":
    main()
