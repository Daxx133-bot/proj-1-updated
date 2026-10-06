# Blind recomputation of the primary statistic

**SUPPLEMENTARY VERIFICATION - NOT PART OF THE PREREGISTERED ANALYSIS.** This document does not change the preregistered confirmatory or replication results in either direction. Produced by `analysis/final/blind_recompute.py`.

Written without reading `PREREGISTRATION.md`, anything in `_audit/`, or any other script in `analysis/`. Inputs: `data/campaign/runs/`, `data/spans/`, `data/graphs/sn_CANONICAL.json`. The statistic is implemented on `scipy.stats.rankdata` rather than the project's `fast_stats` module.

## 1. Runs per service

- Run records read: **180**; Social Network records: **110**.
- Distinct Social Network services faulted: **11**.
- Repetitions per (service, fault type) cell: **[5]** across 22 cells.

| service | ancestor_count (graph) | kill reps | latency reps |
|---|---:|---:|---:|
| `compose-post-service` | 1 | 5 | 5 |
| `home-timeline-service` | 2 | 5 | 5 |
| `media-service` | 2 | 5 | 5 |
| `post-storage-service` | 4 | 5 | 5 |
| `social-graph-service` | 3 | 5 | 5 |
| `text-service` | 2 | 5 | 5 |
| `unique-id-service` | 2 | 5 | 5 |
| `url-shorten-service` | 3 | 5 | 5 |
| `user-mention-service` | 3 | 5 | 5 |
| `user-service` | 4 | 5 | 5 |
| `user-timeline-service` | 2 | 5 | 5 |

## 2. Agreement with the run records' stored outcome fields

ancestor_affected_count was recomputed from the persisted spans and compared against the value the campaign runner stored at collection time.

| quantity | runs agreeing |
|---|---|
| ancestor_count vs stored n_ancestors | **110 / 110** |
| recomputed vs stored ancestor_affected_count | **110 / 110** |
| recomputed vs stored affected *service set* | **110 / 110** |

Every run agrees, on the identity of the affected services and not merely on their count. The stored outcome fields are faithful to the spans they were derived from.

## 3. The primary statistic

### kill faults (n = 11 services)

| service | ancestor_count | median recomputed ancestor_affected_count | per-repetition values |
|---|---:|---:|---|
| `compose-post-service` | 1 | 1.0 | 1, 1, 1, 1, 1 |
| `home-timeline-service` | 2 | 2.0 | 2, 2, 2, 2, 2 |
| `media-service` | 2 | 2.0 | 2, 2, 2, 2, 2 |
| `post-storage-service` | 4 | 4.0 | 4, 4, 4, 4, 4 |
| `social-graph-service` | 3 | 3.0 | 3, 3, 3, 3, 3 |
| `text-service` | 2 | 2.0 | 2, 2, 2, 2, 2 |
| `unique-id-service` | 2 | 2.0 | 2, 2, 2, 2, 2 |
| `url-shorten-service` | 3 | 3.0 | 3, 3, 3, 3, 3 |
| `user-mention-service` | 3 | 3.0 | 3, 3, 3, 3, 3 |
| `user-service` | 4 | 2.0 | 2, 2, 2, 2, 2 |
| `user-timeline-service` | 2 | 2.0 | 2, 2, 2, 2, 2 |

- **Spearman rho = 0.785119**
- permutation p = **0.006883** (2,000,000 random pairings, seed 20260928)
- asymptotic p = 0.004198 (for completeness only; the preregistered test is the permutation test)

### latency faults (n = 11 services)

| service | ancestor_count | median recomputed ancestor_affected_count | per-repetition values |
|---|---:|---:|---|
| `compose-post-service` | 1 | 1.0 | 1, 1, 1, 1, 1 |
| `home-timeline-service` | 2 | 2.0 | 2, 2, 2, 2, 2 |
| `media-service` | 2 | 2.0 | 2, 2, 2, 2, 2 |
| `post-storage-service` | 4 | 4.0 | 3, 4, 4, 4, 4 |
| `social-graph-service` | 3 | 3.0 | 3, 3, 3, 3, 3 |
| `text-service` | 2 | 2.0 | 2, 2, 2, 2, 2 |
| `unique-id-service` | 2 | 2.0 | 2, 2, 2, 2, 2 |
| `url-shorten-service` | 3 | 3.0 | 3, 3, 3, 3, 3 |
| `user-mention-service` | 3 | 3.0 | 3, 3, 3, 3, 3 |
| `user-service` | 4 | 2.0 | 2, 2, 2, 2, 2 |
| `user-timeline-service` | 2 | 2.0 | 2, 2, 2, 2, 2 |

- **Spearman rho = 0.785119**
- permutation p = **0.006883** (2,000,000 random pairings, seed 20260928)
- asymptotic p = 0.004198 (for completeness only; the preregistered test is the permutation test)

## 4. Verdict

Recomputed Social Network kill-fault **rho = 0.785119**, against the reported **0.785**.

**MATCH.** The primary statistic reproduces to the precision at which it was reported, from raw spans, through an independent implementation.

The user-service departure that the confirmatory analysis identified as the sole source of Social Network's non-tautology is reproduced independently here: ancestor_count = 4, measured ancestor_affected_count = [2] across all repetitions.

One difference worth recording. The reported raw permutation p for this test was **0.0080**, from 10,000 Monte-Carlo pairings; this script's 2,000,000 pairings give **0.006883**. The gap is Monte-Carlo noise in the original's 10,000-resample estimate (standard error about 0.0008 at this p, so the two lie within roughly 1.3 standard errors of each other), not a computational disagreement. It has no bearing on the verdict: both are far above the BH-FDR threshold for this family, and the test remains non-significant after correction.

Neither this recomputation nor its p-value refinement changes the preregistered result: **0 of 44 confirmatory and 0 of 44 replication tests survive BH-FDR at q = 0.05.**
