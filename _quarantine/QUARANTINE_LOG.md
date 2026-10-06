# Quarantine Log

Files moved here are **not deleted** (per `CLAUDE.md` rule 5). They are preserved at their
original relative paths under `_quarantine/` so the provenance chain stays auditable.

**Nothing in this directory may be cited, re-run, or used to produce a number in the paper.**

Authority: `_audit/AUDIT_REPORT.md` (2026-09-23).
Quarantined: 2026-09-23.

---

## 1. `scripts/populate_results.py` → `_quarantine/scripts/populate_results.py`

**Defect: fabricates experimental measurements.**

Calls `random.seed(42)` and generates every impact value with `random.uniform()` /
`random.randint()` from hand-written ranges **selected by reading the service's own
centrality scores** (`out_degree`, `in_degree`, `composite_rank` from
`centrality/output/centrality_table.csv`). Its docstring claims it "Generates the
empirical failure measurements across all 12 microservices"; it measures nothing.

Audit refs: §D.2 (fabrication), §E.3/E.4/E.5 (circularity — impact derived from the same
centrality the study claims to validate).

Violates `CLAUDE.md` rules 1 and 3.

---

## 2. `scripts/generate_fig5.py` → `_quarantine/scripts/generate_fig5.py`

**Defect: Figure 5 is fabricated end to end.**

The 12 plotted points are hardcoded literal arrays under the author's own comment
`# Define the 12 data points to roughly match the rho values`. The correlation
coefficients are drawn as matplotlib `text()` labels (`rho = 0.897`, line 37;
`rho = 0.234`, line 53), not computed from anything. The script reads no data file.
The plotted ranges match no real variable: real `hybrid_criticality` spans 0.036–0.301
and real `recovery_time_s` is ~0.1 / ~1 / ~61 s.

It also writes its output **outside the repository**
(`<LOCAL_IDE_WORKSPACE>\554b5cc2-.../`), so the figure in the
paper is not reproducible from this repo at all.

Audit refs: §D.1, §F (Figure 5 row).

Violates `CLAUDE.md` rules 1 and 2.

---

## 3. `q1_p1.py` → `_quarantine/q1_p1.py`

**Defect: every number is hand-typed; contains a previously undetected fabricated value.**

A `.docx` manuscript generator with **zero data reads** — no `read_csv`, no `open()`,
no `json`, no `Path()`. Verified by grep. Every figure in its prose was typed by hand.

Beyond the known `rho = 0.897` string (line 133), it asserts:

| Line | Claim | Reality |
|---|---|---|
| 134 | `rho = 0.841, p = 0.009 in Hotel Reservation` | **Newly detected fabrication.** Real HR hybrid-vs-recovery is **rho = 0.0891, p = 0.8494** (`_audit/repro/recomputed_correlations.csv`). Not a rounding error — opposite conclusion. |
| 130 | "96 controlled experiment runs" | A **fourth** mutually incompatible run count (paper says 72+42=114; disk holds 107 / 122 / 81 / 42 / 59). |
| 131 | Hotel Reservation "with 8 loosely coupled services" | Observed graph is **7 nodes**; `user` absent from every trace. |
| 140 | compose-post "empirical blast-radius rank 2" | The manuscript elsewhere claims rank 1. |

Quarantined wholesale rather than repaired: there is no computed content to preserve.
The docx **layout helpers** (`_fr`, `_fp`, `h1`, `tbl_row`, `set_page`,
`add_footer_pagenum`, etc., lines 1–110) are reusable and defect-free — extract them into
a clean `tools/docx_style.py` if a generator is rebuilt. Do not reuse lines 111–150
(`build_abstract`, `build_title`).

Audit refs: §D.3.

Violates `CLAUDE.md` rules 1 and 2.

---

## 4. `measurement/results/experiment_log.csv` → `_quarantine/measurement/results/experiment_log.csv`

**Defect: 48 of 107 rows are fabricated. This is the file the paper's statistics consumed.**

Rows 1–48 are the output of `populate_results.py` (item 1). Their signature:

- timestamps `2026-08-24T18:00:00Z` … `18:00:47Z`, **incrementing by exactly 1 s per row**
  (generated as `f"...18:00:{len(rows):02d}Z"`, not wall clock);
- `downstream_affected_services` is the literal placeholder `['downstream_<svc>_nodes']`;
- `baseline_error_rate` is exactly `0.001` on all 48 rows;
- `fault_type` is `latency_100ms`, a label appearing in no real run.

Rows 49–107 are **genuine** (Sep 5–9 legacy SN runs) but carry `fault_p95_ms = 0.0` and
`downstream_affected_count = 0` throughout — so **every non-zero blast-radius value in
this file is fabricated**.

The genuine rows are preserved separately and uncontaminated as
`data/raw/sn_legacy.csv`. Nothing is lost by quarantining this file.

Audit refs: §C (forensics), §D.2, §E.3.

---

## 5. `analysis/output/correlation_results.csv` → `_quarantine/analysis/output/correlation_results.csv`

**Defect: computed from the contaminated log (item 4).**

Produced by `analysis/correlation_analysis.py` reading
`measurement/results/experiment_log.csv`. Its current contents give
`hybrid_criticality, recovery_time_s = 0.8471` and `degree = 0.7874` — which already
**disagree with the published 0.897 / 0.867**, because the log grew by 9 real runs after
the paper's numbers were taken.

The analysis script itself is **not** quarantined; it is correct code fed bad input.

Audit refs: §F.

---

## 6. `analysis/output/cross_arch_correlation_comparison.csv` → `_quarantine/analysis/output/cross_arch_correlation_comparison.csv`

**Defect: this is the direct source of the paper's headline numbers, and it is contaminated
*and* stale.**

Contains `hybrid_criticality, recovery_time_s, rho_sn = 0.8969` → paper's **0.897**;
`degree, ..., rho_sn = 0.8669` → paper's **0.867**; `in_degree, ..., 0.2337, p = 0.4647`
→ paper's "rho = 0.234, p = 0.465".

Two independent defects:

1. **Contaminated** — traceable to a version of the log that was 49 % synthetic (48 of
   98 rows). Reproduced exactly by truncating the log at `2026-09-09T11:34:37+0530`.
2. **Stale** — generated from a since-overwritten `correlation_results.csv`. The current
   pipeline no longer produces these values.

On the clean 122-run SN dataset the same quantity is **rho = 0.0605, p = 0.85** (null).

Audit refs: §F (origin of the headline numbers).

---

## 7. `analysis/output/outlier_analysis.{csv,md}` → `_quarantine/analysis/output/`

**Defect: computed from the contaminated log (item 4).**

Not named in the original quarantine instruction, but `analysis/identify_outliers.py`
defaults to `measurement/results/experiment_log.csv` (line 227), so these inherit the
contamination.

**This resolves an item the audit left open.** `_audit/AUDIT_REPORT.md` §F marked the
paper's Table 5 values `3.38` and `7.15%` as SOURCE NOT FOUND. They are here:

```
compose-post-service,7,0.5,3.375,9.3525,0.071525,3.19125,2,5,True,"False Negative (low centrality, high impact)"
```

`downstream_affected_count = 3.375` → paper's **3.38**; `error_rate_delta = 0.071525` →
paper's **7.15 %**. Both are averages over the fabricated rows.

Note this row also assigns compose-post `blast_rank = 2`, matching `q1_p1.py` (item 3)
and contradicting the manuscript's "Rank 1" claim.

---

## 8. `analysis/plots/*.png` (11 files) → `_quarantine/analysis/plots/`

**Defect: rendered from the contaminated log and/or the contaminated correlation CSVs.**

`analysis/generate_plots.py` reads `analysis/output/correlation_results.csv` (line 283)
and `measurement/results/experiment_log.csv` (line 285). Every top-level plot therefore
inherits the contamination.

Moved: `composite_vs_blast_radius.png`, `correlation_heatmap.png`,
`cross_arch_correlation_bar.png`, `scatter_composite_score_vs_error_rate_delta.png`,
`scatter_composite_score_vs_latency_p95_delta_ms.png`,
`scatter_composite_score_vs_recovery_time_s.png`,
`scatter_degree_vs_error_rate_delta.png`,
`scatter_degree_vs_latency_p95_delta_ms.png`,
`scatter_degree_vs_latency_p99_delta_ms.png`,
`scatter_degree_vs_recovery_time_s.png`,
`scatter_hybrid_criticality_vs_recovery_time_s.png`.

`analysis/generate_plots.py` is **not** quarantined — correct code, bad input.

---

## Explicitly NOT quarantined

| Path | Why kept |
|---|---|
| `centrality/hybrid_weight_optimizer.py` | Leaky protocol, but to be **fixed** (step 5), not discarded. Until then it must not be run. |
| `analysis/plots/hotel/*.png` (6 files) | Rendered by `scripts/generate_hotel_plots.py` from `measurement/results/hotel/experiment_log.csv`, which is **real**. Caveat: any panel plotting `recovery_time_s` is plotting container-restart time (see `_audit/AUDIT_REPORT.md` §C). |
| `analysis/output/hotel/*` | Derived from the real HR batch. |
| `analysis/correlation_analysis.py`, `identify_outliers.py`, `generate_plots.py`, `cross_architecture_analysis.py` | Correct code fed contaminated input. Re-runnable against `data/raw/`. |
| `measurement/results/*.json`, `measurement/results/hotel/*`, `measurement/results_controlled/**` | Genuine run records. |
| `centrality/output/*` | Computed from the dependency graph only. Never touched outcome data. Table 1 and Table 5 of the paper reproduce exactly from these. |
| `EVIDENCE_FREEZE/derived/*` | Contains copies of contaminated derived tables, but the directory is an immutable historical snapshot. Flagged, not moved; it must be regenerated after re-collection. |

---

## 9. `data/pilot/pilot_socialnetwork_*.json` (3 files) → `_quarantine/data/pilot_contaminated_concurrent/`

**Quarantined 2026-09-24. Defect: two pilot processes injected faults into the same
stack concurrently.**

A first Social Network pilot was launched with `nohup ... &`. It appeared not to have
survived (its log was empty and no output arrived), so a second pilot was launched. Both
were in fact running. The duplicate is unmistakable in the artefacts:

```
pilot_socialnetwork_compose-post-service_kill_rep1_2026-09-23T19-17-44.732151+00-00.json
pilot_socialnetwork_compose-post-service_kill_rep1_2026-09-23T19-17-57.595215+00-00.json
```

Two runs labelled `rep1`, **13 seconds apart**, each killing `compose-post-service` while
the other's load generator and recovery probe were active. Their baseline p95 values
differ (56.07 ms vs 57.98 ms) and one recorded recovery at 45.45 s while the other was
already recovered at its first probe sample (35.32 s) — consistent with the second run
measuring a system the first had already perturbed.

Neither run can be attributed to a clean single-fault condition, so **both** are
quarantined along with the third file from the same interleaved period. No attempt is
made to salvage the "good" one: there is no way to establish which samples were taken
while the other pilot's fault was active.

The Hotel Reservation pilot (4 runs) is **unaffected** — it ran to completion as a single
process before this happened, and is retained in `data/pilot/`.

**Lesson, applicable to the campaign:** the runner must refuse to start if another
instance is live. A PID lockfile in `data/pilot/` (or `data/campaign/`) is the minimal
fix, and is required before the 300-run campaign, where an accidental double-launch would
silently corrupt a large fraction of the runs in exactly this way.

---

## 10. `data/pilot/pilot_hotelreservation_search_latency_rep1_*.json` → `_quarantine/data/pilot_invalid_blocking_pumba/`

**Quarantined 2026-09-25. Defect: the fault expired ~40 s before the run recorded its
removal, so `T_rec` is measured from the wrong instant.**

`tools/run_pilot.py` injected every fault with `subprocess.run(...)`. That is correct for
`kill` (SIGKILL is instantaneous) but wrong for `latency` and `cpu`: `pumba netem` and
`pumba stress` **block for their entire `--duration`**. The sequence actually executed was:

```
t=0      pumba netem --duration 30s   (blocks)
t=30     pumba returns -- THE FAULT IS ALREADY OVER
t=30     runner begins its own 30 s "fault window"   <- no fault active
t=60     fault window closes; metrics collected
t=70.27  "fault removal" recorded; recovery probe starts
```

The recorded `fault_removal_offset_s = 70.27` against a 30 s configured window is the
signature. The run's `T_rec = 23.98 s` is therefore measured from ~40 s after the real
removal, and its fault-window metrics cover a period with no fault active.

`faultinjection/fault_runner.py::inject_fault` had this right all along, using `Popen`
for LATENCY/CPU and `subprocess.run` only for KILL. The pilot runner did not.

Fixed in `tools/run_pilot.py`: non-kill faults now launch via `Popen` and the runner
waits for that process to exit before recording the removal instant. Rep 2 was stopped
before it ran rather than collecting a second invalid observation.

**Not salvageable by reprocessing:** the baseline and fault-window metrics were collected
over the wrong intervals, so no re-derivation from the stored samples can recover a valid
measurement. Re-run required.

---

## Item 11 — 3 rehearsal campaign runs, superseded by preregistration amendment 1

**Date:** 2026-09-26
**Moved from:** `data/campaign/runs/`, `data/spans/`
**Moved to:** `_quarantine/data/campaign/runs_pre_amendment1/` (3 run records),
`_quarantine/data/spans_pre_amendment1/` (6 span files — baseline + fault window each)

| Run |
|---|
| `run_socialnetwork_compose-post-service_kill_1_2026-09-26T04-22-41.json` |
| `run_socialnetwork_home-timeline-service_kill_1_2026-09-26T04-25-10.json` |
| `run_socialnetwork_media-service_kill_1_2026-09-26T04-28-24.json` |

**Why.** These are the 3 runs produced by the pre-launch rehearsal (Preregistration v3 §9
verification sequence). They ran **before** amendment 1 added the 1.0 ms absolute floor to
the latency-degradation rule, so the pre-floor rule was in force for both of their primary
outcomes.

Blast radius **was** recoverable: recomputation from their persisted spans gives
`compose-post-service` 1/1/0 → **1/0/0** (the spurious `url-shorten-service` descendant
drops out) and leaves the other two unchanged at 2/0/0
(`_audit/REHEARSAL_RECOMPUTED.txt`).

$T_{rec}$ **was not.** The recovery probe re-applies the same degradation rule once per
poll over its own short windows, and those windows are not persisted — only the baseline
and fault windows are. The recorded `recovery_samples` show `downstream_affected` at 1–3 in
the majority of samples (27/40, 11/20, 9/15), in every case in samples preceding the first
all-clear, so the contaminated count was actively gating the recovery decision. In
`compose-post-service|kill|1` the first all-clear is at t = 13.85 s while $T_{rec}$ was
recorded as 54.39 s.

Since $T_{rec}$ is one of the two primary outcomes and its inflation is not measurable from
what is on disk, these 3 runs are **not valid corrected observations**. Their manifest
entries were reset from `done` to `pending` and the campaign will collect them again under
the amended rule (~8 minutes of an 8–11 hour campaign). Every row in the final dataset is
then produced by one code path at one commit.

**Retained deliberately.** These records are the primary evidence for amendment 1 and are
cited by `PREREGISTRATION.md` §12. They are not analysed as campaign data and must never be
pooled with it.

---

## Item 12 — 3 Hotel Reservation campaign runs invalidated by mis-targeted fault injection

**Date:** 2026-09-26
**Moved from:** `data/campaign/runs/`, `data/spans/`
**Moved to:** `_quarantine/data/campaign/runs_mistargeted/`,
`_quarantine/data/spans_mistargeted/`

| Run | Why invalid |
|---|---|
| `hotelreservation\|reservation\|kill\|1` | **Faulted the wrong container.** SIGKILLed `geo`, recorded as a `reservation` fault. |
| `hotelreservation\|search\|kill\|1` | Ran with `geo` dead; baseline topology incomplete (`geo`, `rate` absent from traces). |
| `hotelreservation\|user\|kill\|1` | Ran with `geo` dead; baseline topology incomplete (`geo`, `rate` absent from traces). |

### Root cause

`tools/run_pilot.container_for()` resolved a compose service name to a container by
**substring match on the container name**:

```python
exact = [n for n in out if service in n and "mongodb" not in n and "memcached" not in n]
return min(exact, key=len)          # "prefer the shortest name"
```

The compose project is `hotelReservation`, so every container carries the prefix
`hotelreservation-`, which **contains the substring `reservation`**. For
`service="reservation"` every container in the project matched, and `min(key=len)` then
selected the shortest — `hotelreservation-geo-1`.

Verified on the live stack:

```
container_for('reservation') -> hotelreservation-geo-1        (before the fix)
container_for('reservation') -> hotelreservation-reservation-1 (after)
```

### Consequences, in order

1. `reservation|kill|1` (06:12:43) SIGKILLed **geo** and recorded it as a reservation
   fault. The run was censored — unsurprisingly, since `reservation` was never faulted and
   the recovery probe was waiting for a service that had not been touched to recover.
2. Restoration ran `docker compose up -d reservation`, which restarted `reservation`
   (never down) and left **geo dead**.
3. `search|kill|1` (06:14:47) and `user|kill|1` (06:19:12) then ran against a stack with
   no `geo`. `rate` also vanished from their traces, because the HR `search` path is
   `frontend → search → {geo, rate}` and it fails at `geo` before reaching `rate`.
   `search|kill|1` recorded `A/D/U = 0/0/0` and `T_rec = 0.0 s`; `user|kill|1` recorded
   `T_rec = 140.08 s`. Both were marked **`done`**.
4. `geo|latency|1` (06:19:32) failed with `no running container matches 'geo'`. **This
   failure is what surfaced the problem** — it was the symptom, three runs after the cause.

### The second defect this exposed

`stack_healthy()` checked only that Jaeger answered `/api/services` and that the gateway
answered HTTP. Both were true throughout: the gateway serves happily with `geo` dead. A
partial stack therefore passed the health check and runs were marked `done` on a topology
that was not the topology being reported.

### Fixes

1. `container_for()` now resolves by the **`com.docker.compose.service` label**, which is
   an exact value, verifies the returned label anyway, and **raises on zero or on ambiguous
   matches rather than guessing**. Silently faulting a different service than the one being
   recorded is never preferable to stopping.
2. `stack_healthy()` now additionally requires that **every service in the canonical graph
   has a running container**, and names the missing ones in the progress log.
3. `tools/audit_run_topology.py` added: it re-derives, from each run's persisted fault-free
   baseline spans, whether every expected service was present. This is the check that
   bounded the damage to 3 runs, and it should be run over the campaign output before any
   analysis.
4. 21 regression tests in `tests/test_container_resolution.py`, including the exact
   `reservation` → `geo` case and the partial-stack health case.

### Scope of the damage — bounded and verified

`tools/audit_run_topology.py` over all 30 runs completed before the stop: **2 runs had an
incomplete baseline topology**, both listed above; the third invalid run is the
mis-targeted one, identified from its recorded `container` field. **All 22 Social Network
runs were clean** — the collision cannot occur there, because no Social Network service name
is a substring of the project name `socialnetwork`. The 5 surviving HR runs (`geo`,
`profile` ×2, `rate`, `recommendation`) all targeted their own containers and had complete
baselines.

**Retained deliberately.** These records are the evidence for the root cause and are cited
by `PREREGISTRATION.md` §12 amendment 2. They are not campaign data and must never be
pooled with it.

---

## Item 13 — 11 Social Network latency runs invalidated by a leaked `pumba netem` rule

**Date:** 2026-09-26
**Moved from:** `data/campaign/runs/`, `data/spans/`
**Moved to:** `_quarantine/data/campaign/runs_leaked_netem/`,
`_quarantine/data/spans_leaked_netem/`

| Run | Role |
|---|---|
| `socialnetwork\|compose-post-service\|latency\|1` | **Origin.** Its netem delay was never removed. |
| `socialnetwork\|{home-timeline, media, post-storage, social-graph, text, unique-id, url-shorten, user-mention, user, user-timeline}-service\|latency\|1` | 10 runs whose **baseline** was collected while that delay was still active. |

### What happened

`pumba netem delay --time 500 --jitter 100 --duration 30s` was applied to
`compose-post-service` at 05:31:41. The runner launched it with `Popen` and waited for the
process to exit, which it did (`container_restart_time_s = 32.85`). **The tc rule did not go
away with it.**

Evidence, from the persisted baseline spans of the runs that followed:

| Run start | `compose-post-service` own-span p95 in a **fault-free baseline** |
|---|---:|
| 05:31:41 (the origin run itself) | 8.87 ms |
| 05:34:02 → 05:56:51 (10 runs) | **2153 – 2486 ms** |
| 07:29:54 onward (rep 2, after a stack teardown) | **9.0 – 9.8 ms** |

The delay persisted for the whole remainder of the Social Network latency rep-1 block and
was cleared only by the stack teardown at 05:59. Gateway baseline p95 over those 10 runs was
**3132 – 4046 ms against a campaign median of 54.87 ms** (57–74× the median, 8600–11100 MAD).

### Why this was dangerous rather than merely noisy

The distortion is **systematic and directional**. An inflated baseline makes the fault look
smaller, because the rule asks whether fault p95 exceeds 2× baseline. The faulted service's
ancestors — `nginx-web-server` and `compose-post-service` — were **already degraded in the
baseline**, so they could not clear 2× their own inflated values and went uncounted.
`ancestor_affected_count`, the primary outcome, came out **lower by exactly 2 in most runs**:

| Service | rep 1 (contaminated) | rep 2 (clean) |
|---|---:|---:|
| home-timeline, media, text, unique-id, user, user-timeline | **0** | 2 |
| social-graph, url-shorten, user-mention | **1** | 3 |
| post-storage | **2** | 4 |

Every one of the ten is understated. Had this been analysed, it would have flattened the
Social Network H1 correlation and been indistinguishable from genuine measurement noise. No
individual run record looked anomalous; only the cross-run comparison exposed it.

The origin run is also invalid, for a different reason: it is recorded as censored with
`recovery_blocking_indicator = "p95"`, but the fault was **still active** throughout its
recovery probe. That censoring says nothing about how fast the application recovers.

### Fixes

1. **`one_run` now force-recreates the target container after every non-kill fault run**
   (`docker compose up -d --force-recreate <svc>`). A fresh container cannot carry a
   residual qdisc. It runs *after* the fault window and *after* the recovery probe, so it
   cannot influence the run that just completed — its only job is to guarantee the next run
   starts clean. Kill runs already received a fresh container by necessity. Recorded per run
   as `fault_cleanup`.
2. **`tools/audit_baseline_sanity.py`** added as a standing pre-analysis gate: it flags any
   run whose baseline p95 is an outlier for its application, by median and MAD. This is the
   check that caught the incident, and it must report zero flagged runs before any
   statistics are computed. It is now run alongside `tools/audit_run_topology.py`.

### Scope — verified, not assumed

`tools/audit_baseline_sanity.py` over all 180 runs flags **exactly these 10**; Hotel
Reservation has **no** run above 3× its median. The 11th (the origin) was identified from its
fault-removal timing and the demonstrated persistence of its rule. All other 169 runs have
steady-state baselines and complete topologies
(`tools/audit_run_topology.py`: 0 of 180 incomplete).

**Retained deliberately.** These records are the evidence for amendment 3 and are cited by
`PREREGISTRATION.md` §12. They are not campaign data and must never be pooled with it.
