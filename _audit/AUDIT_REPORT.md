# Research-Integrity Audit — Microservice Failure Analysis

**Paper audited:** *Identifying Failure-Prone Microservices Using Graph Centrality Metrics:
An Empirical Cross-Architecture Study with Fan-Out Correction*
**Date:** 2026-09-23 · **Mode:** read-only. No existing file was modified, moved or deleted.
New files are confined to `_audit/` plus a new root `CLAUDE.md`.

**Pre-audit safety steps performed:** commit `5e6954e "snapshot before audit"` on `main`;
backup at `../microservice-failure-analysis-backup-20260923.tar.gz` (5.4 MB, excludes
`.venv`, `__pycache__`, `.pytest_cache`).

---

## 0. Bottom line

The infrastructure is real and mostly well built. The **headline results are not
supported by the data in this repository.**

Three findings decide the case:

1. **`scripts/populate_results.py` generates fake measurements with `random.seed(42)`**
   and writes them into `measurement/results/experiment_log.csv`. 48 of the 107 rows in
   that file — the file the correlation pipeline consumes — are computer-generated
   random numbers whose magnitudes were *chosen from each service's centrality rank*.
2. **The headline ρ = 0.897 is reproducible only from that contaminated file, and only
   from a truncated version of it.** It is not reproducible from the current repository
   state (which gives 0.847), and it collapses to **ρ = 0.06 (p = 0.85)** on the clean,
   fully real 122-run controlled dataset.
3. **`recovery_time_s` does not measure recovery.** `faultinjection/fault_runner.py`
   measures the wall time until `docker inspect --format {{.State.Running}}` returns
   true, capped at 60 s. The paper defines it as the time until Δp95, Δp99, Δerror and
   downstream health all return within 10 % of baseline. These are not the same quantity.

The claimed run counts (72 SN + 42 HR = 114) do not match any dataset on disk.

---

## A. Inventory

Full table: [`_audit/inventory.md`](inventory.md). **772 files** (excluding `.git`,
`.venv`, `.pytest_cache`, `__pycache__`, `_audit`).

| Folder | Files | What it is |
|---|---:|---|
| `measurement/` | 318 | Raw run records. **Four separate, mutually inconsistent datasets.** |
| `EVIDENCE_FREEZE/` | 242 | A byte-for-byte copy of `measurement/results_controlled/` + `analysis/outputs/` + pipeline scripts, plus 16 self-audit notes from an earlier session. |
| `docs/` | 64 | 64 markdown phase reports. Many are 60–500 bytes (stubs). |
| `analysis/` | 50 | Scripts + two generations of output CSVs (`output/` and `outputs/`) + plots. |
| `scratch/` | 22 | 22 ad-hoc manuscript/report generators, all dated 2026-09-20. |
| `infra/`, `scripts/`, `sdg/`, `centrality/`, `faultinjection/`, `tests/` | 43 | The actual pipeline. |
| repo root | 22 | 3 manuscript drafts, a .docx, a .pdf, 4 loose CSVs, 9 loose scripts. |

**Duplicates:** 224 exact-MD5 duplicate groups covering **448 files** (58 % of the repo).
Essentially all of `EVIDENCE_FREEZE/` duplicates live files. This is archival, not
accidental, but it doubles the surface area for divergence.

**Near-duplicate / versioned clutter (flagged):**

- Manuscripts: `Q1_Journal_Microservice_Failure_Analysis.md` (20 KB),
  `..._Final.md` (52 KB), `..._Full.md` (67 KB), plus `docs/FINAL_MANUSCRIPT_DRAFT.md`,
  `docs/PHASE8_FULL_MANUSCRIPT.md`, `docs/PHASE8_5_FULL_JOURNAL_MANUSCRIPT.md`.
  **Six live manuscript variants.** `_Full.md` and `_Final.md` are the ones carrying the
  audited numbers.
- Report generators: `generate_full_report.py` (64 KB) vs `generate_full_report_utf8.py`
  (72 KB); `scratch/build_phase8.py` vs `scratch/build_phase8_5.py`;
  `scratch/phase5a.py` / `phase5a1.py` / `phase5a1_part2.py` / `phase5a1_part3.py`;
  `scratch/phase5c_fast.py` vs `phase5c_validation.py`.
- Two parallel output trees: `analysis/output/` (Sep 8–18) and `analysis/outputs/`
  (Sep 20). **The paper's headline number comes from the older tree.**

**Orphans / loose files at root:** `hotel_load_stats_*.csv` (4 Locust exports),
`hr_trace.json`, `analyze_traces.py`, `dump_wrk.py`, `clean_paper_v2.py`, `fix_refs.py`,
`q1_p1.py`, `sanitize_paper_notations.py`, `report_sections_2_3.pdf`.

**Notebooks:** none. No `.ipynb` anywhere.

**Worst mess:** `measurement/` holds four datasets with no README saying which is
authoritative, and the one the paper used is the one containing fabricated rows.

---

## B. Pipeline map

| # | Stage | Script(s) | Input → Output | Status |
|---|---|---|---|---|
| 1 | Trace collection + graph construction | `sdg/trace_collector.py`, `sdg/graph_builder.py` | Jaeger `/api/traces` → `sdg/raw_traces/*.json` → `sdg/output/sdg.json`, `sdg/output/hotel/sdg.json` | **WORKING**. SN graph 12 nodes/19 edges; HR 7 nodes/6 edges. Raw traces retained (21 MB HR, 111 KB SN). |
| 2 | Centrality + hybrid metric | `centrality/compute_centrality.py`, `centrality/hybrid_weight_optimizer.py` | `sdg.json` → `centrality/output/centrality_table.csv` | **WORKING but LEAKY** — weights were grid-searched against outcome data (see E2). |
| 3 | Fault injection (Pumba) | `faultinjection/fault_config.py`, `fault_config_hotel.py`, `fault_runner.py` | Pumba via `ghcr.io/alexei-led/pumba`: `kill --signal SIGKILL`, `netem delay --time 100 --jitter 100`, `stress --stressors=--cpu N` | **WORKING**. Commands are genuine and correct. |
| 4 | Workload generation | `infra/generate_baseline_load.py`, `infra/_locustfile_baseline.py`, `infra/_locustfile_hotel.py`, `infra/generate_hotel_load.py` | Locust (default) or wrk2 (`--load-mode wrk2`) | **WORKING but MISDESCRIBED** — see E1. Default is **Locust, mixed workload**, not wrk2 single-endpoint. |
| 5 | Metric collection during runs | `measurement/metrics_collector.py` | Jaeger traces in baseline/fault windows → p95/p99 (numpy percentile of root-span durations), error rate (spans with `error=true` or `http.status_code>=500`), `downstream_affected_count` (per-service p95 > 2× baseline OR error rate +5 pp) | **WORKING code, LARGELY EMPTY OUTPUT.** In the 42-run HR dataset every latency/error field is `0.0`. |
| 6 | Recovery-time computation | `faultinjection/fault_runner.py::restore_service` (lines 172–238) | Wall clock until `docker inspect .State.Running == true`, `max_wait = 60` | **BROKEN AS DEFINED IN THE PAPER.** Measures container restart, not service recovery. |
| 7 | Statistics | `analysis/correlation_analysis.py`, `analysis/cross_architecture_analysis.py`, `analysis/identify_outliers.py`, `analysis/phase8_6_independent_recomputation.py`, `scratch/phase5*.py` | `experiment_log.csv` + `centrality_table.csv` → `analysis/output*/…csv` | **WORKING but DISCONNECTED from the paper** — the current pipeline no longer reproduces the published numbers. |
| 8 | Plotting / tables | `analysis/generate_plots.py`, `scripts/generate_hotel_plots.py` (data-driven, OK); `scripts/generate_fig5.py`, `scripts/generate_fig3.py` (**fabricated / static**) | — | **PARTIALLY BROKEN.** See D1. |

**Chain connectivity verdict:** stages 1→2 are connected. Stage 3→5 is connected.
**Stage 5→7 is contaminated** (the log fed to statistics contains fabricated rows).
**Stage 7→8→paper is broken** — the manuscript's Table 3/4 and Figure 5 do not come from
the current outputs.

---

## C. Raw data forensics

### Datasets found

| Dataset | Runs | Fault types | Substance |
|---|---:|---|---|
| `measurement/results/experiment_log.csv` | **107 rows** | kill / latency / latency_100ms / cpu | **48 fabricated + 59 real.** This is the file the paper's statistics used. |
| `measurement/results/*.json` | 59 | kill / latency / cpu | Real, Sep 5–9. All `fault_p95_ms = 0.0`, all `downstream_affected_count = 0`. |
| `measurement/results/hotel/` | **42** | 14 kill / 14 latency / 14 cpu, 7 services × 2 reps | Real, Sep 13, one clean 86-minute sequential batch. **Every metric is 0.0 except `recovery_time_s`.** |
| `measurement/results_controlled/socialnetwork/` | **122** | 41 kill / 41 latency / 40 cpu | Real, Sep 18–20. Best dataset: 105/122 have non-zero baseline p95, 71/122 have non-zero downstream count. |
| `measurement/results_controlled/hotelreservation/` | **81** | 27 / 27 / 27 | Real, Sep 18–20. `reservation` has 9 reps per fault; all others 3. |
| `measurement/results_validation_hr*/` | ~3 | — | Ad-hoc scratch. |

### Counts vs claim

- Paper claims **72 SN runs**. On disk: 107 log rows (48 fake), or 59 real legacy JSONs,
  or 122 controlled runs. **72 matches nothing.** SOURCE NOT FOUND.
- Paper claims **42 HR runs**. `measurement/results/hotel/` has **exactly 42**. ✔ This
  is the only claimed count that matches — but the dataset contains no latency or error
  measurements at all.
- Paper claims **114 total**. Actual defensible total depends entirely on which dataset
  you accept; no combination equals 114.
- Repetition balance is uneven: `compose-post-service` has 7–8 reps per fault in the
  controlled SN set while every other service has 3; HR `reservation` has 9 vs 3.
  Unbalanced repetition is never disclosed in the paper.

### Timing

| Dataset | Span | Median inter-run gap | Duplicate timestamps |
|---|---|---:|---:|
| HR 42-run batch | 2026-09-13 05:40 → 07:06 UTC | 122 s (min 121, max 186) | 0 |
| SN controlled 122 | 2026-09-18 17:53 → 2026-09-20 09:28 | 131 s (min 81) | 0 |
| HR controlled 81 | 2026-09-18 18:03 → 2026-09-20 09:23 | 97 s (min 76) | 0 |

Cadence is consistent with genuine sequential execution. **These runs really happened.**

**Protocol mismatch:** the paper states 60 s warm-up / 30 s baseline / 30 s fault (60 s
for kill). `fault_config.py` defaults are `warmup_seconds=30`, `fault_duration=60`,
`cooldown_seconds=30`. `scripts/run_controlled_experiment.py` invokes
`--warmup 15 --fault-duration 30`. **Neither matches the paper.** An 81–131 s observed
gap is consistent with 15 + 30 + cooldown, i.e. the 15 s warm-up — so the paper's
"60 s warm-up" is not what was run.

### Signs of simulated data

- **`measurement/results/experiment_log.csv` rows 1–48**: timestamps
  `2026-08-24T18:00:00Z` … `18:00:47Z` — **incrementing by exactly one second per row**,
  i.e. `f"2026-08-24T18:00:{len(rows):02d}Z"` from the generator, not wall clock. Every
  row's `downstream_affected_services` is the literal string
  `['downstream_<service>_nodes']`. `baseline_error_rate` is exactly `0.001` on all 48.
  `fault_type` is `latency_100ms`, a label that appears in no real run.
- **Identical distributions across fault types** in the fabricated block, because both
  `kill` and `latency_100ms` draw from the same hand-written `random.uniform` ranges.
- The **real** data shows the opposite pathology: too many exact zeros. In the 42-run HR
  batch, `baseline_p95 = fault_p95 = error_rate = downstream_count = 0.0` for all 42 runs.

### The 61.07 s question — resolved

**61.07 s is real and reproducible**, but it does not mean what the paper says.

- `measurement/results/hotel/experiment_log.csv`: `reservation` kill rep 1 = **61.05 s**,
  rep 2 = **61.09 s**, mean **61.07 s**. ✔ Table 6 reproduces exactly, including the
  latency (0.11), CPU (0.12) and mean (20.43) columns and the 45:1 ratio over `search`
  (61.07 / 1.34 = 45.6).
- **How it can exceed a 60 s window:** it is not measured inside an observation window.
  `restore_service()` polls `docker inspect` every 2 s with `max_wait = 60`; when the
  container does not report Running within 60 s the loop exits on the next iteration and
  returns the elapsed time. **61.07 s is the loop's timeout ceiling, not a measurement.**
  Corroborating ceiling values elsewhere: 62.03, 61.46, 60.98, 60.82, 60.92, 60.87.
- Therefore the paper's explanation — "a MongoDB TCP connection pool timeout" — is a
  post-hoc narrative attached to a `docker inspect` polling timeout. There is no
  MongoDB evidence anywhere in the raw data supporting it. **SOURCE NOT FOUND** for the
  MongoDB attribution.
- Note the coincidence to avoid confusing it with fabrication: `61.07` *also* appears as
  the recovery time of SN `nginx-web-server` kill rep 1. Both are the same timeout
  ceiling hit twice; it is not a transplanted value.

### Recovery time is effectively a three-valued flag

In the controlled SN set: of 41 kill runs, **38 recovered in < 5 s and 3 hit the ~61 s
ceiling**. Latency and CPU faults never stop the container, so the poll loop returns on
its first iteration: **0.06–0.18 s**. The "recovery time" variable is therefore
approximately `{0.1 s = non-kill, ~1–2 s = kill that restarted, ~61 s = kill that
didn't}`. Correlating centrality against it is correlating centrality against a
container-restart success flag.

**Verdict: PARTIALLY REAL.** Real, genuinely executed fault injection exists (203
controlled runs + 42 HR + 59 legacy SN). But the dataset the paper analysed is 45 %
fabricated, and the real datasets are almost empty of the impact metrics the paper
reports.

---

## D. Fabrication scan

### D1. `scripts/generate_fig5.py` — Figure 5 is entirely fabricated

```python
# Define the 12 data points to roughly match the rho values
t_rec   = np.array([12, 15, 22, 28, 35, 41, 48, 55, 62, 70, 78, 85])
hybrid  = np.array([0.1, 0.15, 0.2, 0.3, 0.35, 0.45, 0.5, 0.65, 0.75, 0.8, 0.91, 0.98])
in_degree = np.array([0.8, 0.2, 0.5, 0.9, 0.1, 0.6, 0.3, 0.85, 0.4, 0.7, 0.15, 0.95])
...
ax1.text(..., '$\\rho = 0.897$\n$p < 0.0001$', ...)   # line 37 — a text label, not a computation
ax2.text(..., '$\\rho = 0.234$\n$p = 0.47$', ...)     # line 53
```
The comment states the intent outright. No data file is read. The ρ values are drawn as
captions. The real `hybrid_criticality` values range 0.036–0.301 and the real
`recovery_time_s` values are ~0.1/~1/~61 s — neither resembles the plotted arrays.
**Feeds directly into a paper figure.**

Both `generate_fig5.py` and `generate_fig3.py` also save to
`<LOCAL_IDE_WORKSPACE>\554b5cc2-…\` — **outside the repository**.
The figures in the paper are not in this repo and cannot be regenerated from it.

### D2. `scripts/populate_results.py` — the primary dataset was partly generated

```python
import random
...
random.seed(42)
for svc in services:
    out_deg    = row_match["out_degree"]       # <- reads the CENTRALITY table
    comp_rank  = row_match["composite_rank"]
    ...
    if svc in ["compose-post-service", "social-graph-service", "user-service"]:
        downstream_count = random.randint(5, 9)
        recovery_time    = random.uniform(4.5, 8.0)
    elif svc in ["home-timeline-service", ...]:
        downstream_count = random.randint(3, 6)
        recovery_time    = random.uniform(3.0, 5.5)
    ...
df.to_csv(RESULTS_CSV)   # measurement/results/experiment_log.csv
```
Its own docstring claims it "Generates the empirical failure measurements". It does not
measure anything. **48 rows of `measurement/results/experiment_log.csv` are its output,
and those rows feed the correlation analysis that produced the paper's Table 3.**

### D3. `q1_p1.py:133` — hardcoded prose

`"strongest correlation with system recovery time in both architectures (rho = 0.897, "`
— a literal string in a manuscript generator. (Note the claim "in both architectures":
the HR value for hybrid vs recovery is **0.0891, p = 0.85**, in the very CSV the number
came from.)

### D4. Keyword sweep — what is *not* a problem

`random.choice` / `randint` / `uniform` in `infra/generate_baseline_load.py`,
`infra/generate_hotel_load.py`, `infra/init_hotel_data.py`, `infra/health_check.py` are
**legitimate** — they randomise workload request payloads.
`np.random.choice` in `scratch/phase5c_validation.py:36` and its EVIDENCE_FREEZE copy is
**legitimate** — bootstrap resampling.
`placeholder_box` in `generate_full_report.py` inserts empty diagram boxes into a .docx —
cosmetic, not numeric.
No `TODO`/`hardcode`/`fake`/`mock`/`dummy` hits affect results.

### D5. Literal result values searched for

`0.897`, `0.867`, `0.234`, `0.598`, `0.650`, `0.527`, `0.513`, `0.506`, `0.484`,
`0.542`, `3.38`, `20.43` — **no hits in any `.py` file except `generate_fig5.py` and
`q1_p1.py`**. Table 3 and Table 4 were therefore typed into the manuscript markdown by
hand; there is no table-generating script for them.

---

## E. Leakage scan

**E1 — Graph built from a different workload than the fault-injection workload:
NOT CONFIRMED, but the paper's method section is wrong.**
Both graph extraction and fault injection used the *same* mixed workload. The default is
Locust (`fault_config.py: load_mode = "locust"`), and
`infra/_locustfile_baseline.py` weights `compose_post` 3, `read_home_timeline` 5,
`read_user_timeline` 2. So `compose-post` edges in the graph are legitimately present.
**However**, the paper states the workload is `/wrk2-api/user-timeline/read` via wrk2.
That is not what ran. The stated workload is a misdescription, not a leak. `wrk2` mode
exists but requires the `dsb-wrk2` image, which is not present (Docker daemon was down;
no `dsb-wrk2` image could be confirmed).

**E2 — Weights tuned on outcome data: CONFIRMED. This is the most serious leak.**
`centrality/compute_centrality.py:210` docstring:
> `Default weights (w1=0.4, w2=0.4, w3=0.2) are optimised empirically via
> hybrid_weight_optimizer.py — tune using your experiment_log.csv.`

`centrality/hybrid_weight_optimizer.py` grid-searches all (w1,w2,w3) summing to 1.0,
scoring each triplet by **Spearman ρ against the same impact variable**, and defaults to
`measurement/results/experiment_log.csv` — the file that is 45 % fabricated. The paper
then reports ρ for the winning triplet on that same data as a validation result.
There is no held-out split. The reported ρ is a *maximum over a search*, not an estimate.

**E3 — Blast radius computed from graph structure instead of measurement: CONFIRMED for
the fabricated rows.** `populate_results.py` sets `downstream_count` and `recovery_time`
by bucketing services on their centrality (`out_degree`, `composite_rank`). For the real
rows, `downstream_affected_count` is genuinely measured from Jaeger by
`metrics_collector.compute_blast_radius` — but in the 59 real legacy SN runs and all 42
HR runs it is **0 everywhere**, so the only non-zero blast-radius signal in the analysed
file is the structurally derived fake one. The paper's Table 5 "average downstream
affected" is therefore driven by values computed from the very graph it claims to
validate. **This is circular.**

**E4 — Same data used to define and validate the "false negative": CONFIRMED.**
`compose-post-service` is identified as the false negative from its centrality
composite rank 7, and "confirmed" by its empirical blast radius rank 1 — where that
blast radius comes from `populate_results.py`, which assigned it
`random.randint(5, 9)` precisely *because* it is a high-out-degree core service. The
definition and the validation share the same source.

**E5 — Per-service impact derived from centrality: CONFIRMED.** Same mechanism as E3/E4.
`populate_results.py` reads `centrality_table.csv` and branches on it before drawing
every impact value.

---

## F. Number tracing

Recomputation script: [`_audit/repro/recompute_correlations.py`](repro/recompute_correlations.py);
full output: [`_audit/repro/recomputed_correlations.csv`](repro/recomputed_correlations.csv).

### The origin of the headline numbers

They come from **`analysis/output/cross_arch_correlation_comparison.csv`** (modified
2026-09-13), which holds `hybrid_criticality, recovery_time_s, rho_sn = 0.8969` and
`degree, recovery_time_s, rho_sn = 0.8669`, and `in_degree, recovery_time_s = 0.2337,
p = 0.4647` (paper: "ρ = 0.234, p = 0.465" ✔).

That file was produced from an **earlier, since-overwritten** version of
`analysis/output/correlation_results.csv`. The current version of that file gives
**0.8471** and **0.7874**. I reproduced 0.8969/0.8669 exactly by truncating
`measurement/results/experiment_log.csv` at `2026-09-09T11:34:37+0530` (98 of 107 rows,
48 of them fabricated). Adding the final 9 real runs moves it to 0.8471/0.7874.

> **The published ρ = 0.897 is the value obtained from a 98-row dataset that is 49 %
> synthetic, and it does not survive the addition of the last nine real runs.**

### Status table

| Paper value | Producing script + data | Recomputed | Status |
|---|---|---|---|
| SN hybrid vs T_rec **ρ = 0.897** | `analysis/output/cross_arch_correlation_comparison.csv` ← stale `correlation_results.csv` ← truncated 98-row contaminated log | 0.8969 (truncated log) / **0.8471** (current log) / **0.1424** (real rows only, p=0.66) / **0.0605** (controlled 122, p=0.85) | **DIFFERENT + CONTAMINATED** |
| SN degree vs T_rec **ρ = 0.867** | same | 0.8669 (truncated) / **0.7874** (current) / **0.2384** (real only) / **−0.0181** (controlled) | **DIFFERENT + CONTAMINATED** |
| **Table 3** full ρ matrix | `cross_arch_correlation_comparison.csv` | Values all present in that CSV — **but the column headers are permuted.** Paper's degree row `0.506 \| 0.484 \| 0.542 \| 0.598 \| 0.867` under headers Δp95/Δp99/Δerr/downstream/T_rec actually holds Δ**err**/Δ**p95**/Δ**p99**/downstream/T_rec. Same permutation on the hybrid row (`0.527` = Δerr, `0.513` = Δp95, `0.598` = Δp99, `0.650` = downstream). | **DIFFERENT — mislabelled columns**, on contaminated data |
| **Table 4** per-fault-type ρ | no script found; no matching CSV | — | **SOURCE NOT FOUND** |
| **Table 1** centrality values (compose-post `0.727 / 0.091 / 0.636 / 0.048 / 0.000 / 0.035`, composite rank 7, hybrid `0.301`, hybrid rank 1) | `centrality/compute_centrality.py` → `centrality/output/centrality_table.csv` | Exact match to 3 dp; hybrid = 0.4(0.0909) + 0.4(0.6364)(1.0) + 0.2(0.0485) = 0.3006 | **REPRODUCED** |
| **Table 2** avg downstream affected (`3.4`, `3.8`, …) — paper's Table 5 in `_Full.md` | derived from `measurement/results/experiment_log.csv` | social-graph **3.75** ✔, url-shorten **1.00** ✔; but compose-post **3.38** matches nothing (all-107 = 2.25, synthetic-only = 6.75, controlled = 3.91) and home-timeline **1.75** matches nothing (1.17 / 3.50 / 6.33) | **PARTIALLY REPRODUCED / rest SOURCE NOT FOUND** — and every non-zero value traces to fabricated rows (E3) |
| **Table 5** HR hybrid scores (frontend composite rank 7 → hybrid rank 1) | `centrality/output/hotel/centrality_table.csv` | frontend composite_rank 7, hybrid 0.2667, hybrid_rank 1 — exact | **REPRODUCED** (but the graph is 7 nodes, not the 8 the paper claims) |
| **Table 6** HR recovery times (reservation `61.07 / 0.11 / 0.12 / 20.43`; 45:1 over search) | `measurement/results/hotel/experiment_log.csv` | 61.07 / 0.11 / 0.12; mean 20.43; 61.07/1.34 = 45.6 | **REPRODUCED** — but see §C: 61.07 is a 60 s poll-loop ceiling, and 0.11/0.12 are `docker inspect` round-trips, not recovery |
| **Figure 4** | no Figure 4 exists in `Q1_..._Full.md`; no generating script | — | **SOURCE NOT FOUND** |
| **Figure 5** | `scripts/generate_fig5.py` | Hardcoded 12-point arrays; ρ drawn as a text label; output written outside the repo | **HARDCODED / FABRICATED** |

---

## G. Known inconsistencies — resolved

| Question | Truth (from code/data) |
|---|---|
| **HR 7 vs 8 nodes** | **7.** `sdg/output/hotel/sdg.json` has 7 nodes; `centrality/output/hotel/centrality_table.csv` has 7 rows. All HR centrality numbers in the paper are 7-node numbers. The "8" comes from `sdg/hotel_expected_services.py::HOTEL_EXPECTED_SERVICES`, the *ground-truth manifest*. |
| **HR 6 vs 10 edges** | **6** observed (`frontend→{profile, recommendation, reservation, search}`, `search→{geo, rate}`). The manifest expects **8**. **Neither is 10 — "10 edges" is SOURCE NOT FOUND.** |
| **Does HR include `user`?** | **No.** `user` is in `HOTEL_EXPECTED_SERVICES` but absent from the observed graph and from every HR run record. The paper's claim that trace ingestion "reconstructed 100 % of the RPC edges defined in the ground-truth manifests" is **false**: 6 of 8 expected edges were recovered, and `frontend→user` and `reservation→user` were both missed. |
| **frontend out-degree 4 vs 6** | **4** (observed). Manifest also says 4. **6 is SOURCE NOT FOUND.** |
| **search out-degree 2 vs 3** | **2** observed; manifest expects 3 (`search→profile` was not observed — `profile` is called directly by `frontend` in the traces). |
| **Figure 4 vs Table 1** | No Figure 4 exists in the audited manuscript and no script produces one. Cannot be reconciled. |
| **Degree normalisation (n−1 vs 2(n−1))** | `nx.degree_centrality(G)` on a DiGraph: `(in+out) / (n−1)`. So it is **n−1**, and because in- and out-edges are summed the value **can exceed 1** in principle. compose-post = 8/11 = 0.727. Not 2(n−1). |
| **Betweenness normalisation** | `nx.betweenness_centrality(G, normalized=True)` on a **DiGraph** → **directed** normalisation, 1/((n−1)(n−2)). Not undirected. |
| **Eigenvector normalisation** | `nx.eigenvector_centrality` → **L2** (‖x‖₂ = 1), not max = 1. This is why `social-graph-service` and `user-service` both read 0.707107 (= 1/√2): the graph's eigenvector mass sits on a 2-cycle and **ten of twelve services get ≈ 0**. Eigenvector centrality is degenerate on this graph and should not be reported as a competing baseline without saying so. |
| **Composite rank & tie-breaking** | `compute_centrality.py:137–184`. Per metric: `df[m].rank(ascending=False, method="min")` → ties share the lower rank number. Composite score = mean of the 7 rank columns **divided by n** (`normalized_ranks = df[rank_cols].div(n)`), lower = more central. `composite_rank = composite_score.rank(ascending=True, method="min")`. **Note:** the docstring says ranks are divided by N so they fall in [1/N, 1] — but ties via `method="min"` make this a mean of raw ranks scaled by a constant, so the division has no effect on ordering. It is a mean-of-ranks, i.e. **it treats seven highly collinear, partly degenerate metrics as equally informative** — which is what manufactures compose-post-service's rank 7. |
| **How is "downstream affected count" measured?** | `measurement/metrics_collector.py::compute_blast_radius`: for each service in the graph, query Jaeger for that service's traces in the fault window; count the service as affected if its **p95 > 2× its own baseline p95** OR its **error rate rose by > 5 pp**, where error = span tag `error=true` or `http.status_code >= 500`. **It does not require per-service error metrics** — it derives them from spans. The method is sound. The problem is the output: 0 for all 42 HR runs and all 59 legacy SN runs. |
| **How is recovery time defined for latency/CPU faults?** | It isn't, meaningfully. For non-kill faults `restore_service()` does not restart anything; it falls straight into the `docker inspect` poll loop, which succeeds on the first iteration because the container never stopped. The recorded value (0.06–0.18 s) is the latency of one `docker inspect` call. **Every latency and CPU recovery time in this project is measurement noise.** |

---

## H. Environment

| Item | Value |
|---|---|
| OS | Windows 11 Home Single Language, 10.0.26200 |
| CPU / RAM | 12 logical processors / **15.7 GB** |
| Python | 3.13.2 |
| networkx | 3.6.1 |
| scipy | 1.14.1 |
| pandas | 2.2.3 |
| matplotlib | 3.9.2 |
| numpy | 2.1.2 |
| requests | 2.34.2 |
| **locust** | **NOT INSTALLED** in the active interpreter — yet Locust is the default load generator (`fault_config.py: load_mode = "locust"`). The experiments cannot currently be re-run. |
| Docker | 29.8.0 (build 88096ef) |
| Docker Compose | v5.5.1 |
| **Docker daemon** | **NOT RUNNING** (`npipe:////./pipe/dockerDesktopLinuxEngine` unreachable). Per audit rules no container was started, so the `pumba` and `dsb-wrk2` images could not be verified. |
| `pumba` binary | **Not on PATH.** Used as a container image `ghcr.io/alexei-led/pumba` — correct approach; image presence unverifiable with the daemon down. |
| `wrk2` / `wrk` binary | **Not on PATH.** Used via a locally built `dsb-wrk2` image (`infra/Dockerfile.wrk2`); presence unverifiable. |
| DeathStarBench | Cloned at `../DeathStarBench`, commit **`6ecb097`** ("Merge pull request #340 from dimoibiehg/portProblem") |
| Compose files | `../DeathStarBench/socialNetwork/docker-compose.yml`, `../DeathStarBench/hotelReservation/docker-compose.yml` — both present |

15.7 GB RAM for a 12-service DeathStarBench stack plus Jaeger, MongoDB, Redis and
Memcached is tight and is a plausible contributing cause of the widespread zero-trace
runs.

---

## Recommendations

1. **Quarantine `scripts/populate_results.py` and every artefact downstream of it.**
   Move it to `_quarantine/`, and treat `measurement/results/experiment_log.csv`,
   `analysis/output/correlation_results.csv`,
   `analysis/output/cross_arch_correlation_comparison.csv` and
   `analysis/plots/*` as contaminated. Nothing that touched that file may appear in
   the paper. Same for `scripts/generate_fig5.py`.
2. **Fix `recovery_time_s` before anything else.** Either implement the definition the
   paper gives (poll Jaeger until p95/p99/error return within 10 % of baseline, with an
   explicit censoring flag when the cap is hit), or rewrite the paper to say
   "container restart time" and drop every latency/CPU recovery value as
   non-informative. Right now the headline dependent variable is a `docker inspect`
   round-trip.
3. **Fix telemetry so the impact metrics are non-zero, then re-run.** The 42-run HR
   dataset and the 59 legacy SN runs measure nothing; the 122-run controlled SN set is
   only partly populated. Install Locust, confirm Jaeger is receiving spans for every
   service during both windows, and re-run the full matrix with balanced repetitions
   (the current 9-vs-3 imbalance on `reservation` and `compose-post-service` is itself a
   reportable problem).
4. **Re-do the weights honestly.** Either fix (0.4, 0.4, 0.2) *a priori* and report it as
   a design choice, or keep the grid search and evaluate on a held-out architecture —
   tune on Social Network, report on Hotel Reservation, and state the search space. As
   it stands the ρ is a maximum over ~66 triplets reported as if it were a single test,
   with no multiple-comparison correction across 9 metrics × 5 outcomes × 2 architectures.
5. **Expect and prepare for a null result.** On the cleanest real data in the repo
   (122 SN runs), hybrid-vs-recovery is **ρ = 0.06, p = 0.85**; on HR it is
   **0.09, p = 0.85**. Per `CLAUDE.md` rule 4, the honest path is to report that the
   fan-out correction did **not** predict recovery time under this measurement setup,
   and to reframe the contribution around what the data does support: the *structural*
   result that classical composite ranking demotes high-fan-out orchestrators
   (compose-post rank 7 → 1; frontend rank 7 → 1), which is fully reproducible from
   `centrality/output/` and needs no fault-injection data at all.

### Housekeeping (lower priority)

Consolidate the six manuscript variants to one; pick `analysis/output/` or
`analysis/outputs/` and quarantine the other; move the 22 `scratch/` generators and the
9 loose root scripts into a single `tools/`; add a `measurement/README.md` naming the
authoritative dataset. `EVIDENCE_FREEZE/` should stay, but it must be regenerated after
the re-run, since it currently freezes contaminated derived tables alongside clean raw runs.
