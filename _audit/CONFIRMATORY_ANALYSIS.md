# Confirmatory analysis

**Specification:** `_audit/preregistration_versions/PREREGISTRATION_v3_LOCKED.md` (amendments 1–3), which is the sole authority for everything below.
**Data:** 180 campaign runs in `data/campaign/runs/`, dataset commit `5976178`.
**Produced by:** `analysis/final/run_confirmatory_analysis.py` — every number in this document is written by that script from the campaign records or the canonical graphs. Tables and figures are in `analysis/final/`.
**Run date:** 2026-09-27

---

## 0. Integrity gates

| check | passed | detail |
|---|:--:|---|
| run count is 180 | yes | 180 |
| no gateway runs | yes | 0 gateway runs |
| telemetry_ok on every run | yes | 0 failures |
| 36 cells | yes | 36 |
| every cell has exactly 5 repetitions | yes | cells not at 5: {} |
| censoring recorded | yes | 0 of 180 censored (0.0%) |
| socialnetwork: campaign services == analysis set | yes | campaign 11, analysis set 11 |
| socialnetwork: service sets identical | yes | only in campaign [], only in analysis set [] |
| hotelreservation: campaign services == analysis set | yes | campaign 7, analysis set 7 |
| hotelreservation: service sets identical | yes | only in campaign [], only in analysis set [] |

Source: `integrity_checks.csv`.

## 1. Unit of analysis, families and the promotion rule

- Unit of analysis: the **service**, repetitions aggregated by the **median** (§7).
- Testable (predictor × architecture) pairs: **22** of 24, after excluding the declared-degenerate pairs (§5.1, verified in §7 below).
- Confirmatory family (kill): **44 tests**, BH-FDR at q = 0.05 within the family.
- Replication family (latency): **44 tests**, corrected separately.
- Exploratory family: **66 testable tests** of 154 attempted, corrected separately, labelled exploratory throughout. The 88 remaining are **undefined, not null** — see §6.1.

**The censoring promotion rule fired.** §7 states: *"if under 10% of observations are censored, Spearman is promoted to primary — that threshold is fixed here, in advance."* This dataset has **0 censored observations of 180 (0.0%)**, so the Spearman permutation p-value is the primary test for `T_rec` as well as for `ancestor_affected_count`, and it is the value entering each BH-FDR family. Cox and log-rank are computed and reported alongside and are **not** separately FDR-corrected, because they test the same hypotheses as the primary tests they accompany.

## 2. The saturation question — does H1 test anything?

§1.5 was written before the campaign to forestall exactly this: if `ancestor_affected_count` always equals `|ancestors|`, then ρ = 1.0 **by construction** and H1 is confirmed tautologically. Both the run-level rate §1.5 defines and the rate at the actual unit of analysis (the service median) are reported, because they can differ and only the second governs the test.

| architecture | fault | run-level saturation | service-median saturation | tautological at the analysis unit? |
|---|---|---:|---:|:--:|
| Social Network | kill | 50/55 = 0.909 | 10/11 = 0.909 | no |
| Social Network | latency | 49/55 = 0.891 | 10/11 = 0.909 | no |
| Hotel Reservation | kill | 35/35 = 1.000 | 7/7 = 1.000 | **YES** |
| Hotel Reservation | latency | 35/35 = 1.000 | 7/7 = 1.000 | **YES** |

Source: `ancestor_saturation.csv`.

## 3. Confirmatory family — kill faults

#### Primary outcome: `ancestor_affected_count`

| architecture | predictor | n | levels | ρ | 95% CI | CI method | p (perm) | p (BH) | sig? |
|---|---|---:|---:|---:|---|---|---:|---:|:--:|
| **HR\*** | `ancestor_count` | 7 | 2 | 1.000 | [1.000, 1.000] | percentile | 0.0476 | 0.3451 | no |
| **HR\*** | `closeness` | 7 | 2 | 1.000 | [1.000, 1.000] | percentile | 0.0476 | 0.3451 | no |
| **HR\*** | `eigenvector` | 7 | 2 | 1.000 | [1.000, 1.000] | percentile | 0.0476 | 0.3451 | no |
| **HR\*** | `pagerank` | 7 | 5 | 0.805 | [0.624, 0.935] | BCa | 0.0476 | 0.3451 | no |
| **HR\*** | `composite_score` | 7 | 6 | 0.798 | [0.618, 0.917] | BCa | 0.0952 | 0.4190 | no |
| **HR\*** | `hybrid_criticality` | 7 | 2 | -0.258 | [-0.730, -0.167] | BCa | 1.0000 | 1.0000 | no |
| **HR\*** | `degree` | 7 | 2 | -0.258 | [-0.750, -0.167] | BCa | 1.0000 | 1.0000 | no |
| **HR\*** | `out_degree` | 7 | 2 | -0.258 | [-0.750, -0.167] | BCa | 1.0000 | 1.0000 | no |
| **HR\*** | `betweenness` | 7 | 2 | -0.258 | [-0.750, -0.167] | BCa | 1.0000 | 1.0000 | no |
| **HR\*** | `descendant_count` | 7 | 2 | -0.258 | [-0.750, -0.167] | BCa | 1.0000 | 1.0000 | no |
| **HR\*** | `dominator_subtree_size` | 7 | 2 | -0.258 | [-0.750, -0.167] | BCa | 1.0000 | 1.0000 | no |
| SN | `ancestor_count` | 11 | 4 | 0.785 | [0.000, 1.000] | BCa | 0.0080 | 0.3451 | no |
| SN | `pagerank` | 11 | 8 | 0.674 | [0.125, 0.941] | BCa | 0.0256 | 0.3451 | no |
| SN | `closeness` | 11 | 7 | 0.600 | [-0.133, 0.945] | BCa | 0.0549 | 0.3451 | no |
| SN | `descendant_count` | 11 | 5 | -0.542 | [-0.877, 0.106] | BCa | 0.0907 | 0.4190 | no |
| SN | `out_degree` | 11 | 4 | -0.544 | [-0.881, 0.082] | BCa | 0.0942 | 0.4190 | no |
| SN | `dominator_subtree_size` | 11 | 3 | -0.557 | [-0.900, -0.194] | BCa | 0.1095 | 0.4380 | no |
| SN | `betweenness` | 11 | 6 | -0.467 | [-0.839, 0.271] | BCa | 0.1485 | 0.5444 | no |
| SN | `degree` | 11 | 5 | -0.342 | [-0.837, 0.406] | BCa | 0.2948 | 0.9264 | no |
| SN | `in_degree` | 11 | 3 | 0.337 | [-0.418, 0.840] | BCa | 0.3383 | 0.9922 | no |
| SN | `composite_score` | 11 | 7 | 0.273 | [-0.437, 0.820] | BCa | 0.4014 | 0.9925 | no |
| SN | `hybrid_criticality` | 11 | 8 | -0.144 | [-0.810, 0.698] | BCa | 0.6688 | 0.9925 | no |

#### Primary outcome: `T_rec` (Spearman, promoted to primary)

| architecture | predictor | n | levels | ρ | 95% CI | CI method | p (perm) | p (BH) | sig? |
|---|---|---:|---:|---:|---|---|---:|---:|:--:|
| **HR\*** | `pagerank` | 7 | 5 | -0.364 | [-0.882, 0.750] | BCa | 0.4222 | 0.9925 | no |
| **HR\*** | `composite_score` | 7 | 6 | -0.234 | [-0.939, 0.750] | BCa | 0.6135 | 0.9925 | no |
| **HR\*** | `ancestor_count` | 7 | 2 | -0.158 | [-0.813, 0.907] | BCa | 0.8571 | 0.9925 | no |
| **HR\*** | `hybrid_criticality` | 7 | 2 | 0.204 | [-0.837, 0.624] | BCa | 0.8571 | 0.9925 | no |
| **HR\*** | `degree` | 7 | 2 | 0.204 | [-0.837, 0.624] | BCa | 0.8571 | 0.9925 | no |
| **HR\*** | `out_degree` | 7 | 2 | 0.204 | [-0.926, 0.624] | BCa | 0.8571 | 0.9925 | no |
| **HR\*** | `betweenness` | 7 | 2 | 0.204 | [-0.683, 0.629] | BCa | 0.8571 | 0.9925 | no |
| **HR\*** | `closeness` | 7 | 2 | -0.158 | [-0.820, 0.907] | BCa | 0.8571 | 0.9925 | no |
| **HR\*** | `eigenvector` | 7 | 2 | -0.158 | [-0.813, 0.917] | BCa | 0.8571 | 0.9925 | no |
| **HR\*** | `descendant_count` | 7 | 2 | 0.204 | [-0.661, 0.624] | BCa | 0.8571 | 0.9925 | no |
| **HR\*** | `dominator_subtree_size` | 7 | 2 | 0.204 | [-0.607, 0.624] | BCa | 0.8571 | 0.9925 | no |
| SN | `ancestor_count` | 11 | 4 | -0.356 | [-0.738, 0.339] | BCa | 0.2807 | 0.9264 | no |
| SN | `pagerank` | 11 | 8 | -0.235 | [-0.745, 0.565] | BCa | 0.4804 | 0.9925 | no |
| SN | `descendant_count` | 11 | 5 | 0.227 | [-0.482, 0.778] | BCa | 0.4908 | 0.9925 | no |
| SN | `out_degree` | 11 | 4 | 0.220 | [-0.476, 0.775] | BCa | 0.5168 | 0.9925 | no |
| SN | `closeness` | 11 | 7 | -0.212 | [-0.692, 0.515] | BCa | 0.5234 | 0.9925 | no |
| SN | `degree` | 11 | 5 | 0.162 | [-0.647, 0.919] | BCa | 0.6214 | 0.9925 | no |
| SN | `betweenness` | 11 | 6 | 0.156 | [-0.551, 0.717] | BCa | 0.6401 | 0.9925 | no |
| SN | `dominator_subtree_size` | 11 | 3 | 0.128 | [-0.326, 0.590] | BCa | 0.6985 | 0.9925 | no |
| SN | `hybrid_criticality` | 11 | 8 | 0.098 | [-0.662, 0.792] | BCa | 0.7699 | 0.9925 | no |
| SN | `in_degree` | 11 | 3 | -0.089 | [-0.658, 0.553] | BCa | 0.7978 | 0.9925 | no |
| SN | `composite_score` | 11 | 7 | -0.071 | [-0.799, 0.728] | BCa | 0.8317 | 0.9925 | no |

#### `T_rec` — survival models reported alongside (not separately FDR-corrected)

| architecture | predictor | Cox HR (run level, clustered) | 95% CI | Cox p | Cox HR (service level) | log-rank χ² | log-rank p | groups |
|---|---|---:|---|---:|---:|---:|---:|---:|
| **HR\*** | `ancestor_count` | 1.522 | [1.067, 2.171] | 0.0204 | 2.179 | n/a | undefined | 1 |
| **HR\*** | `betweenness` | 0.108 | [0.000, 40.166] | 0.4609 | 0.089 | n/a | undefined | 1 |
| **HR\*** | `closeness` | 6783.770 | [3.927, 11720242.119] | 0.0204 | 12652406.058 | n/a | undefined | 1 |
| **HR\*** | `composite_score` | 0.106 | [0.006, 1.910] | 0.1282 | 0.002 | 1.00 | 0.6051 | 3 |
| **HR\*** | `degree` | 0.690 | [0.257, 1.851] | 0.4609 | 0.668 | n/a | undefined | 1 |
| **HR\*** | `descendant_count` | 0.948 | [0.824, 1.092] | 0.4609 | 0.944 | n/a | undefined | 1 |
| **HR\*** | `dominator_subtree_size` | 0.948 | [0.824, 1.092] | 0.4609 | 0.944 | n/a | undefined | 1 |
| **HR\*** | `eigenvector` | 1.814 | [1.097, 3.000] | 0.0204 | 3.015 | n/a | undefined | 1 |
| **HR\*** | `hybrid_criticality` | 0.147 | [0.001, 24.134] | 0.4609 | 0.124 | n/a | undefined | 1 |
| **HR\*** | `out_degree` | 0.690 | [0.257, 1.851] | 0.4609 | 0.668 | n/a | undefined | 1 |
| **HR\*** | `pagerank` | 3800.772 | [0.160, 90512017.121] | 0.1089 | 8566514953.272 | 1.52 | 0.4681 | 3 |
| SN | `ancestor_count` | 1.173 | [0.876, 1.570] | 0.2836 | 1.479 | 1.33 | 0.5154 | 3 |
| SN | `betweenness` | 0.000 | [0.000, 0.146] | 0.0241 | 19.979 | 1.17 | 0.2790 | 2 |
| SN | `closeness` | 6.099 | [0.095, 392.993] | 0.3949 | 320.558 | 1.06 | 0.5899 | 3 |
| SN | `composite_score` | 1.835 | [0.183, 18.384] | 0.6056 | 0.017 | 0.80 | 0.6687 | 3 |
| SN | `degree` | 0.202 | [0.079, 0.516] | 8.26e-04 | 1.338 | 2.85 | 0.0914 | 2 |
| SN | `descendant_count` | 0.895 | [0.863, 0.929] | 3.56e-09 | 0.992 | 1.88 | 0.1698 | 2 |
| SN | `dominator_subtree_size` | 0.810 | [0.751, 0.873] | 4.26e-08 | 0.990 | n/a | undefined | 1 |
| SN | `hybrid_criticality` | 0.010 | [0.002, 0.043] | 6.36e-10 | 1.408 | 1.57 | 0.2099 | 2 |
| SN | `in_degree` | 3.665 | [0.122, 110.060] | 0.4542 | 64.619 | 0.27 | 0.6027 | 2 |
| SN | `out_degree` | 0.188 | [0.095, 0.371] | 1.56e-06 | 0.923 | 1.88 | 0.1698 | 2 |
| SN | `pagerank` | 3.284 | [0.004, 2793.226] | 0.7298 | 200265.912 | 1.06 | 0.5899 | 3 |

HR\* = Hotel Reservation, **directional only — not confirmatory** (§7.2). Source: `confirmatory_family_kill.csv`.

> **Two caveats on the hazard ratios, applying wherever they appear.**
>
> **1. A hazard ratio is per ONE UNIT of the raw predictor, and several predictors never span one unit.** `hybrid_criticality` runs from 0.036 to 0.302 across the Social Network analysis set, so a one-unit increase is about four times the entire observed range and the fitted HR extrapolates far outside the data. The same holds for every normalised centrality (`degree`, `closeness`, `pagerank`, `betweenness`, `eigenvector`, `composite_score`). Hazard ratios are therefore **not comparable across predictors on different scales**, and an HR of 0.01 or 28 means "steep on an unstandardised scale", not a 100-fold or 28-fold effect. Only the count-valued predictors (`ancestor_count`, `descendant_count`, `dominator_subtree_size`) have HRs where one unit is a meaningful step.
>
> **2. Cluster-robust standard errors with 7-11 clusters are likely anti-conservative.** The Cox models are fitted at run level (n = 55 SN, n = 35 HR) with errors clustered on 11 and 7 services. Sandwich estimators need many clusters to be calibrated; with this few they under-state uncertainty. Several Cox p-values below are 1e-8 to 1e-10 while the primary Spearman test of the same hypothesis is not significant at all. **The primary test governs**: §7's promotion rule makes Spearman primary at 0% censoring. These survival models are reported alongside so the contrast is visible rather than hidden; the small Cox p-values are not treated as evidence for H1 and are not FDR-corrected.

## 4. Replication family — latency faults

#### Primary outcome: `ancestor_affected_count`

| architecture | predictor | n | levels | ρ | 95% CI | CI method | p (perm) | p (BH) | sig? |
|---|---|---:|---:|---:|---|---|---:|---:|:--:|
| **HR\*** | `ancestor_count` | 7 | 2 | 1.000 | [1.000, 1.000] | percentile | 0.0476 | 0.2328 | no |
| **HR\*** | `closeness` | 7 | 2 | 1.000 | [1.000, 1.000] | percentile | 0.0476 | 0.2328 | no |
| **HR\*** | `eigenvector` | 7 | 2 | 1.000 | [1.000, 1.000] | percentile | 0.0476 | 0.2328 | no |
| **HR\*** | `pagerank` | 7 | 5 | 0.805 | [0.624, 0.935] | BCa | 0.0476 | 0.2328 | no |
| **HR\*** | `composite_score` | 7 | 6 | 0.798 | [0.618, 0.917] | BCa | 0.0952 | 0.3330 | no |
| **HR\*** | `hybrid_criticality` | 7 | 2 | -0.258 | [-0.750, -0.167] | BCa | 1.0000 | 1.0000 | no |
| **HR\*** | `degree` | 7 | 2 | -0.258 | [-0.730, -0.167] | BCa | 1.0000 | 1.0000 | no |
| **HR\*** | `out_degree` | 7 | 2 | -0.258 | [-0.730, -0.167] | BCa | 1.0000 | 1.0000 | no |
| **HR\*** | `betweenness` | 7 | 2 | -0.258 | [-0.750, -0.167] | BCa | 1.0000 | 1.0000 | no |
| **HR\*** | `descendant_count` | 7 | 2 | -0.258 | [-0.748, -0.167] | BCa | 1.0000 | 1.0000 | no |
| **HR\*** | `dominator_subtree_size` | 7 | 2 | -0.258 | [-0.750, -0.167] | BCa | 1.0000 | 1.0000 | no |
| SN | `ancestor_count` | 11 | 4 | 0.785 | [0.000, 1.000] | BCa | 0.0076 | 0.1848 | no |
| SN | `pagerank` | 11 | 8 | 0.674 | [0.171, 0.949] | BCa | 0.0280 | 0.2328 | no |
| SN | `closeness` | 11 | 7 | 0.600 | [-0.127, 0.958] | BCa | 0.0554 | 0.2437 | no |
| SN | `descendant_count` | 11 | 5 | -0.542 | [-0.874, 0.107] | BCa | 0.0918 | 0.3330 | no |
| SN | `out_degree` | 11 | 4 | -0.544 | [-0.878, 0.087] | BCa | 0.0984 | 0.3330 | no |
| SN | `dominator_subtree_size` | 11 | 3 | -0.557 | [-0.900, -0.194] | BCa | 0.1060 | 0.3331 | no |
| SN | `betweenness` | 11 | 6 | -0.467 | [-0.853, 0.316] | BCa | 0.1511 | 0.4155 | no |
| SN | `degree` | 11 | 5 | -0.342 | [-0.837, 0.385] | BCa | 0.2977 | 0.6549 | no |
| SN | `in_degree` | 11 | 3 | 0.337 | [-0.402, 0.835] | BCa | 0.3368 | 0.6667 | no |
| SN | `composite_score` | 11 | 7 | 0.273 | [-0.446, 0.813] | BCa | 0.4106 | 0.7226 | no |
| SN | `hybrid_criticality` | 11 | 8 | -0.144 | [-0.805, 0.713] | BCa | 0.6656 | 0.9152 | no |

#### Primary outcome: `T_rec` (Spearman, promoted to primary)

| architecture | predictor | n | levels | ρ | 95% CI | CI method | p (perm) | p (BH) | sig? |
|---|---|---:|---:|---:|---|---|---:|---:|:--:|
| **HR\*** | `pagerank` | 7 | 5 | -0.436 | [-1.000, 0.840] | BCa | 0.3238 | 0.6667 | no |
| **HR\*** | `hybrid_criticality` | 7 | 2 | 0.408 | [-1.000, 0.618] | BCa | 0.5714 | 0.8111 | no |
| **HR\*** | `degree` | 7 | 2 | 0.408 | [-1.000, 0.618] | BCa | 0.5714 | 0.8111 | no |
| **HR\*** | `out_degree` | 7 | 2 | 0.408 | [-1.000, 0.618] | BCa | 0.5714 | 0.8111 | no |
| **HR\*** | `betweenness` | 7 | 2 | 0.408 | [-0.529, 0.618] | BCa | 0.5714 | 0.8111 | no |
| **HR\*** | `descendant_count` | 7 | 2 | 0.408 | [-1.000, 0.618] | BCa | 0.5714 | 0.8111 | no |
| **HR\*** | `dominator_subtree_size` | 7 | 2 | 0.408 | [-0.529, 0.618] | BCa | 0.5714 | 0.8111 | no |
| **HR\*** | `composite_score` | 7 | 6 | -0.162 | [-0.971, 0.882] | BCa | 0.7286 | 0.9714 | no |
| **HR\*** | `ancestor_count` | 7 | 2 | -0.158 | [-0.820, 0.913] | BCa | 0.8571 | 1.0000 | no |
| **HR\*** | `closeness` | 7 | 2 | -0.158 | [-0.813, 0.907] | BCa | 0.8571 | 1.0000 | no |
| **HR\*** | `eigenvector` | 7 | 2 | -0.158 | [-0.813, 0.907] | BCa | 0.8571 | 1.0000 | no |
| SN | `hybrid_criticality` | 11 | 8 | 0.767 | [0.190, 0.964] | BCa | 0.0084 | 0.1848 | no |
| SN | `degree` | 11 | 5 | 0.647 | [-0.199, 0.930] | BCa | 0.0338 | 0.2328 | no |
| SN | `composite_score` | 11 | 7 | 0.625 | [0.248, 0.876] | BCa | 0.0418 | 0.2328 | no |
| SN | `in_degree` | 11 | 3 | 0.511 | [-0.213, 0.845] | BCa | 0.1196 | 0.3508 | no |
| SN | `descendant_count` | 11 | 5 | 0.428 | [-0.592, 0.841] | BCa | 0.1800 | 0.4658 | no |
| SN | `out_degree` | 11 | 4 | 0.380 | [-0.636, 0.844] | BCa | 0.2475 | 0.6011 | no |
| SN | `pagerank` | 11 | 8 | 0.373 | [-0.307, 0.833] | BCa | 0.2596 | 0.6011 | no |
| SN | `betweenness` | 11 | 6 | 0.308 | [-0.676, 0.808] | BCa | 0.3491 | 0.6667 | no |
| SN | `closeness` | 11 | 7 | 0.300 | [-0.612, 0.795] | BCa | 0.3637 | 0.6667 | no |
| SN | `ancestor_count` | 11 | 4 | -0.060 | [-0.627, 0.641] | BCa | 0.8647 | 1.0000 | no |
| SN | `dominator_subtree_size` | 11 | 3 | -0.014 | [-0.713, 0.700] | BCa | 1.0000 | 1.0000 | no |

#### `T_rec` — survival models reported alongside (not separately FDR-corrected)

| architecture | predictor | Cox HR (run level, clustered) | 95% CI | Cox p | Cox HR (service level) | log-rank χ² | log-rank p | groups |
|---|---|---:|---|---:|---:|---:|---:|---:|
| **HR\*** | `ancestor_count` | 0.882 | [0.578, 1.346] | 0.5609 | 2.179 | n/a | undefined | 1 |
| **HR\*** | `betweenness` | 0.000 | [0.000, 0.314] | 0.0234 | 0.000 | n/a | undefined | 1 |
| **HR\*** | `closeness` | 0.072 | [0.000, 512.060] | 0.5609 | 12652406.058 | n/a | undefined | 1 |
| **HR\*** | `composite_score` | 6.784 | [0.177, 259.686] | 0.3032 | 0.001 | 2.15 | 0.3405 | 3 |
| **HR\*** | `degree` | 0.240 | [0.070, 0.824] | 0.0234 | 0.108 | n/a | undefined | 1 |
| **HR\*** | `descendant_count` | 0.816 | [0.684, 0.973] | 0.0234 | 0.728 | n/a | undefined | 1 |
| **HR\*** | `dominator_subtree_size` | 0.816 | [0.684, 0.973] | 0.0234 | 0.728 | n/a | undefined | 1 |
| **HR\*** | `eigenvector` | 0.837 | [0.460, 1.524] | 0.5609 | 3.015 | n/a | undefined | 1 |
| **HR\*** | `hybrid_criticality` | 0.001 | [0.000, 0.368] | 0.0234 | 0.000 | n/a | undefined | 1 |
| **HR\*** | `out_degree` | 0.240 | [0.070, 0.824] | 0.0234 | 0.108 | n/a | undefined | 1 |
| **HR\*** | `pagerank` | 0.034 | [0.000, 2352.154] | 0.5516 | 106348180908279424.000 | 0.22 | 0.8967 | 3 |
| SN | `ancestor_count` | 0.998 | [0.816, 1.221] | 0.9859 | 1.184 | 1.17 | 0.5561 | 3 |
| SN | `betweenness` | 0.011 | [0.000, 847.796] | 0.4328 | 0.000 | 0.00 | 0.9710 | 2 |
| SN | `closeness` | 0.054 | [0.002, 1.864] | 0.1064 | 0.067 | 1.80 | 0.4068 | 3 |
| SN | `composite_score` | 28.083 | [8.697, 90.677] | 2.45e-08 | 1767.526 | 6.12 | 0.0468 | 3 |
| SN | `degree` | 0.220 | [0.053, 0.916] | 0.0375 | 0.010 | 1.67 | 0.1967 | 2 |
| SN | `descendant_count` | 0.948 | [0.903, 0.996] | 0.0343 | 0.835 | 0.57 | 0.4510 | 2 |
| SN | `dominator_subtree_size` | 0.960 | [0.869, 1.061] | 0.4232 | 0.905 | n/a | undefined | 1 |
| SN | `hybrid_criticality` | 0.045 | [0.002, 1.163] | 0.0616 | 0.000 | 2.56 | 0.1099 | 2 |
| SN | `in_degree` | 0.014 | [0.000, 0.446] | 0.0157 | 0.002 | 0.41 | 0.5209 | 2 |
| SN | `out_degree` | 0.442 | [0.204, 0.958] | 0.0386 | 0.083 | 0.57 | 0.4510 | 2 |
| SN | `pagerank` | 0.036 | [0.000, 3.018] | 0.1411 | 0.091 | 1.80 | 0.4068 | 3 |

Source: `replication_family_latency.csv`.

### 4.1 Agreement between the confirmatory and replication families

| architecture | predictor | kill ρ | kill sig? | latency ρ | latency sig? | same sign? | same verdict? |
|---|---|---:|:--:|---:|:--:|:--:|:--:|
| SN | `ancestor_count` | 0.785 | no | 0.785 | no | yes | yes |
| SN | `hybrid_criticality` | -0.144 | no | -0.144 | no | yes | yes |
| SN | `degree` | -0.342 | no | -0.342 | no | yes | yes |
| SN | `in_degree` | 0.337 | no | 0.337 | no | yes | yes |
| SN | `out_degree` | -0.544 | no | -0.544 | no | yes | yes |
| SN | `betweenness` | -0.467 | no | -0.467 | no | yes | yes |
| SN | `closeness` | 0.600 | no | 0.600 | no | yes | yes |
| SN | `pagerank` | 0.674 | no | 0.674 | no | yes | yes |
| SN | `composite_score` | 0.273 | no | 0.273 | no | yes | yes |
| SN | `descendant_count` | -0.542 | no | -0.542 | no | yes | yes |
| SN | `dominator_subtree_size` | -0.557 | no | -0.557 | no | yes | yes |
| **HR\*** | `ancestor_count` | 1.000 | no | 1.000 | no | yes | yes |
| **HR\*** | `hybrid_criticality` | -0.258 | no | -0.258 | no | yes | yes |
| **HR\*** | `degree` | -0.258 | no | -0.258 | no | yes | yes |
| **HR\*** | `out_degree` | -0.258 | no | -0.258 | no | yes | yes |
| **HR\*** | `betweenness` | -0.258 | no | -0.258 | no | yes | yes |
| **HR\*** | `closeness` | 1.000 | no | 1.000 | no | yes | yes |
| **HR\*** | `eigenvector` | 1.000 | no | 1.000 | no | yes | yes |
| **HR\*** | `pagerank` | 0.805 | no | 0.805 | no | yes | yes |
| **HR\*** | `composite_score` | 0.798 | no | 0.798 | no | yes | yes |
| **HR\*** | `descendant_count` | -0.258 | no | -0.258 | no | yes | yes |
| **HR\*** | `dominator_subtree_size` | -0.258 | no | -0.258 | no | yes | yes |

### 4.2 Is the replication independent?

| architecture | median `ancestor_affected_count` identical across fault types? | median `T_rec` identical? | ρ between kill and latency `T_rec` |
|---|:--:|:--:|---:|
| Social Network | **YES** | no | 0.384 |
| Hotel Reservation | **YES** | no | 0.857 |

**The replication is not independent for the primary outcome.** The median `ancestor_affected_count` vector is *identical* between kill and latency faults in both architectures, so the latency family correlates the same 18 outcome values against the same predictors as the kill family. The ρ values agree exactly and the only difference in p-values is Monte-Carlo permutation noise. Section 7.1 anticipated that the two families might disagree and said the disagreement would be the finding; instead they cannot disagree here, and **the replication therefore provides no additional evidence about H1 or H1b.** It remains informative for `T_rec`, where the two fault types do give different values.

### 4.3 Where saturation breaks, and what carries the Social Network signal

Social Network is not fully saturated (§2), and ρ = 0.785 rather than 1.0 depends entirely on which services depart. Every departing run is listed:

| architecture | service | `ancestor_count` | runs departing / 10 | measured `ancestor_affected_count` |
|---|---|---:|---:|---|
| Social Network | `post-storage-service` | 4 | 1 / 10 | 3 |
| Social Network | `user-service` | 4 | 10 / 10 | 2 |

**The Social Network result rests on one service.** `user-service` registers 2 of its 4 graph ancestors in **10 of 10 runs** — perfectly reproducible, not noise — and `post-storage-service` falls short in 1 of 10. Remove `user-service` and the outcome is identical to the predictor for every remaining service, i.e. ρ = 1.0 by construction. So the single thing that makes H1 an empirical claim rather than a restatement, on the confirmatory architecture, is the behaviour of one service.

**Post-hoc observation, not a preregistered finding.** In all 10 `user-service` runs the services that degraded were exactly `compose-post-service` and `nginx-web-server`; its other two graph ancestors, `home-timeline-service` and `social-graph-service`, never did. The plausible mechanism is that `ancestor_count` counts ancestors in the dependency graph, whereas only the ancestors whose paths the workload actually exercises can degrade. That would make `ancestor_count` an upper bound whose tightness depends on the workload mix. This is offered as an explanation generated after seeing the data and is **not** evidence for it; testing it needs a workload-weighted predictor and a new preregistration.

## 5. H1b — is the hybrid metric anti-predictive?

§1.4 preregistered H1b as a directional hypothesis: the fan-out-corrected hybrid metric's ρ against `ancestor_affected_count` is **≤ 0**. Stating it in advance is what makes a negative ρ a finding rather than a salvage.

| family | architecture | ρ | 95% CI | p (perm) | p (BH) | ρ ≤ 0? | distinguishable from 0 after FDR? | verdict |
|---|---|---:|---|---:|---:|:--:|:--:|---|
| confirmatory (kill) | SN | -0.144 | [-0.810, 0.698] | 0.6688 | 0.9925 | yes | no | directionally anti-predictive but NOT distinguishable from zero after FDR |
| confirmatory (kill) | **HR\*** | -0.258 | [-0.730, -0.167] | 1.0000 | 1.0000 | yes | no | directionally anti-predictive but NOT distinguishable from zero after FDR |
| replication (latency) | SN | -0.144 | [-0.805, 0.713] | 0.6656 | 0.9152 | yes | no | directionally anti-predictive but NOT distinguishable from zero after FDR |
| replication (latency) | **HR\*** | -0.258 | [-0.750, -0.167] | 1.0000 | 1.0000 | yes | no | directionally anti-predictive but NOT distinguishable from zero after FDR |

Source: `h1b_hybrid_metric.csv`.

## 6. Exploratory family

**Labelled exploratory throughout. These results are not confirmatory and carry no inferential weight in support of H1, H1b or H2.** Scope, decided 2026-09-27 before the analysis was written (deviation 5): Δp95 latency only, Δp99 latency only, Δerror kill only, both affected counts under both fault types. Δp95 is never pooled across architectures (§6.5).

### 6.1 Outcomes with no variance at the unit of analysis

**88 of 154 attempted exploratory tests are undefined.** In every case the OUTCOME is constant across the services of that architecture, so Spearman ρ does not exist. This is the same situation as a degenerate predictor (§5.1): it is not a null result and it is not reported as ρ = 0.

| outcome | fault | architecture | services | distinct outcome values | constant value | tests undefined |
|---|---|---|---:|---:|---:|---:|
| `descendant_affected_count` | kill | HR* | 7 | 1 | **0** | 11 |
| `descendant_affected_count` | kill | SN | 11 | 1 | **0** | 11 |
| `descendant_affected_count` | latency | HR* | 7 | 1 | **0** | 11 |
| `descendant_affected_count` | latency | SN | 11 | 1 | **0** | 11 |
| `unrelated_affected_count` | kill | HR* | 7 | 1 | **0** | 11 |
| `unrelated_affected_count` | kill | SN | 11 | 1 | **0** | 11 |
| `unrelated_affected_count` | latency | HR* | 7 | 1 | **0** | 11 |
| `unrelated_affected_count` | latency | SN | 11 | 1 | **0** | 11 |

That `descendant_affected_count` has a median of **0 for every service, in every condition, in both architectures** is itself the strongest single piece of evidence for the reversed causal direction of §1.2 — descendants do not degrade. It cannot be expressed as a correlation because it has no variance to correlate, and stating it as a constant is the honest form.

### 6.2 Testable exploratory tests

| outcome | fault | architecture | predictor | ρ | p (perm) | p (BH) | sig? |
|---|---|---|---|---:|---:|---:|:--:|
| `delta_error_rate` | kill | HR\* | `pagerank` | 0.691 | 0.0952 | 0.3697 | no |
| `delta_error_rate` | kill | HR\* | `composite_score` | 0.450 | 0.3111 | 0.7333 | no |
| `delta_error_rate` | kill | HR\* | `ancestor_count` | 0.158 | 0.8571 | 0.9588 | no |
| `delta_error_rate` | kill | HR\* | `hybrid_criticality` | -0.204 | 0.8571 | 0.9588 | no |
| `delta_error_rate` | kill | HR\* | `degree` | -0.204 | 0.8571 | 0.9588 | no |
| `delta_error_rate` | kill | HR\* | `out_degree` | -0.204 | 0.8571 | 0.9588 | no |
| `delta_error_rate` | kill | HR\* | `betweenness` | -0.204 | 0.8571 | 0.9588 | no |
| `delta_error_rate` | kill | HR\* | `closeness` | 0.158 | 0.8571 | 0.9588 | no |
| `delta_error_rate` | kill | HR\* | `eigenvector` | 0.158 | 0.8571 | 0.9588 | no |
| `delta_error_rate` | kill | HR\* | `descendant_count` | -0.204 | 0.8571 | 0.9588 | no |
| `delta_error_rate` | kill | HR\* | `dominator_subtree_size` | -0.204 | 0.8571 | 0.9588 | no |
| `delta_error_rate` | kill | SN | `hybrid_criticality` | 0.786 | 0.0066 | 0.0913 | no |
| `delta_error_rate` | kill | SN | `composite_score` | 0.726 | 0.0144 | 0.0913 | no |
| `delta_error_rate` | kill | SN | `in_degree` | 0.715 | 0.0216 | 0.1042 | no |
| `delta_error_rate` | kill | SN | `degree` | 0.652 | 0.0340 | 0.1402 | no |
| `delta_error_rate` | kill | SN | `closeness` | 0.478 | 0.1400 | 0.4620 | no |
| `delta_error_rate` | kill | SN | `pagerank` | 0.408 | 0.2191 | 0.5784 | no |
| `delta_error_rate` | kill | SN | `descendant_count` | 0.349 | 0.2978 | 0.7279 | no |
| `delta_error_rate` | kill | SN | `out_degree` | 0.310 | 0.3456 | 0.7865 | no |
| `delta_error_rate` | kill | SN | `betweenness` | 0.229 | 0.4886 | 0.9199 | no |
| `delta_error_rate` | kill | SN | `dominator_subtree_size` | -0.108 | 0.7530 | 0.9588 | no |
| `delta_error_rate` | kill | SN | `ancestor_count` | 0.027 | 0.9411 | 1.0000 | no |
| `delta_p95_ms` | latency | HR\* | `composite_score` | 0.613 | 0.1548 | 0.4643 | no |
| `delta_p95_ms` | latency | HR\* | `pagerank` | 0.564 | 0.1984 | 0.5456 | no |
| `delta_p95_ms` | latency | HR\* | `ancestor_count` | 0.316 | 0.5714 | 0.9199 | no |
| `delta_p95_ms` | latency | HR\* | `closeness` | 0.316 | 0.5714 | 0.9199 | no |
| `delta_p95_ms` | latency | HR\* | `eigenvector` | 0.316 | 0.5714 | 0.9199 | no |
| `delta_p95_ms` | latency | HR\* | `hybrid_criticality` | 0.204 | 0.8571 | 0.9588 | no |
| `delta_p95_ms` | latency | HR\* | `degree` | 0.204 | 0.8571 | 0.9588 | no |
| `delta_p95_ms` | latency | HR\* | `out_degree` | 0.204 | 0.8571 | 0.9588 | no |
| `delta_p95_ms` | latency | HR\* | `betweenness` | 0.204 | 0.8571 | 0.9588 | no |
| `delta_p95_ms` | latency | HR\* | `descendant_count` | 0.204 | 0.8571 | 0.9588 | no |
| `delta_p95_ms` | latency | HR\* | `dominator_subtree_size` | 0.204 | 0.8571 | 0.9588 | no |
| `delta_p95_ms` | latency | SN | `hybrid_criticality` | 0.949 | 1.00e-04 | 0.0033 | yes |
| `delta_p95_ms` | latency | SN | `degree` | 0.953 | 1.00e-04 | 0.0033 | yes |
| `delta_p95_ms` | latency | SN | `composite_score` | 0.775 | 0.0072 | 0.0913 | no |
| `delta_p95_ms` | latency | SN | `out_degree` | 0.733 | 0.0126 | 0.0913 | no |
| `delta_p95_ms` | latency | SN | `descendant_count` | 0.751 | 0.0133 | 0.0913 | no |
| `delta_p95_ms` | latency | SN | `betweenness` | 0.674 | 0.0265 | 0.1166 | no |
| `delta_p95_ms` | latency | SN | `in_degree` | 0.535 | 0.1061 | 0.3890 | no |
| `delta_p95_ms` | latency | SN | `dominator_subtree_size` | 0.405 | 0.2411 | 0.6120 | no |
| `delta_p95_ms` | latency | SN | `pagerank` | 0.280 | 0.4067 | 0.8947 | no |
| `delta_p95_ms` | latency | SN | `closeness` | 0.253 | 0.4469 | 0.9199 | no |
| `delta_p95_ms` | latency | SN | `ancestor_count` | -0.174 | 0.6103 | 0.9429 | no |
| `delta_p99_ms` | latency | HR\* | `pagerank` | 0.655 | 0.1286 | 0.4466 | no |
| `delta_p99_ms` | latency | HR\* | `composite_score` | 0.577 | 0.1865 | 0.5352 | no |
| `delta_p99_ms` | latency | HR\* | `ancestor_count` | 0.316 | 0.5714 | 0.9199 | no |
| `delta_p99_ms` | latency | HR\* | `closeness` | 0.316 | 0.5714 | 0.9199 | no |
| `delta_p99_ms` | latency | HR\* | `eigenvector` | 0.316 | 0.5714 | 0.9199 | no |
| `delta_p99_ms` | latency | HR\* | `hybrid_criticality` | 0.000 | 1.0000 | 1.0000 | no |
| `delta_p99_ms` | latency | HR\* | `degree` | 0.000 | 1.0000 | 1.0000 | no |
| `delta_p99_ms` | latency | HR\* | `out_degree` | 0.000 | 1.0000 | 1.0000 | no |
| `delta_p99_ms` | latency | HR\* | `betweenness` | 0.000 | 1.0000 | 1.0000 | no |
| `delta_p99_ms` | latency | HR\* | `descendant_count` | 0.000 | 1.0000 | 1.0000 | no |
| `delta_p99_ms` | latency | HR\* | `dominator_subtree_size` | 0.000 | 1.0000 | 1.0000 | no |
| `delta_p99_ms` | latency | SN | `degree` | 0.791 | 0.0043 | 0.0913 | no |
| `delta_p99_ms` | latency | SN | `hybrid_criticality` | 0.754 | 0.0095 | 0.0913 | no |
| `delta_p99_ms` | latency | SN | `betweenness` | 0.724 | 0.0154 | 0.0913 | no |
| `delta_p99_ms` | latency | SN | `composite_score` | 0.720 | 0.0158 | 0.0913 | no |
| `delta_p99_ms` | latency | SN | `descendant_count` | 0.711 | 0.0166 | 0.0913 | no |
| `delta_p99_ms` | latency | SN | `out_degree` | 0.703 | 0.0221 | 0.1042 | no |
| `delta_p99_ms` | latency | SN | `in_degree` | 0.484 | 0.1470 | 0.4620 | no |
| `delta_p99_ms` | latency | SN | `closeness` | 0.235 | 0.4833 | 0.9199 | no |
| `delta_p99_ms` | latency | SN | `dominator_subtree_size` | 0.243 | 0.4908 | 0.9199 | no |
| `delta_p99_ms` | latency | SN | `ancestor_count` | -0.212 | 0.5255 | 0.9199 | no |
| `delta_p99_ms` | latency | SN | `pagerank` | 0.170 | 0.6143 | 0.9429 | no |

Source: `exploratory_family.csv`.

## 7. Degenerate predictors (§5.1), verified against the campaign's service set

| architecture | predictor | services | distinct levels | status |
|---|---|---:|---:|---|
| Hotel Reservation | `ancestor_count` | 7 | 2 | testable |
| Hotel Reservation | `betweenness` | 7 | 2 | testable |
| Hotel Reservation | `closeness` | 7 | 2 | testable |
| Hotel Reservation | `composite_score` | 7 | 6 | testable |
| Hotel Reservation | `degree` | 7 | 2 | testable |
| Hotel Reservation | `descendant_count` | 7 | 2 | testable |
| Hotel Reservation | `dominator_subtree_size` | 7 | 2 | testable |
| Hotel Reservation | `eigenvector` | 7 | 2 | testable |
| Hotel Reservation | `hybrid_criticality` | 7 | 2 | testable |
| Hotel Reservation | `in_degree` | 7 | 1 | **UNDEFINED** — constant at 0.142857 across all 7 Hotel Reservation analysis-set services; Spearman rho is undefined. This is a degeneracy of the dependency graph, not a null result. |
| Hotel Reservation | `out_degree` | 7 | 2 | testable |
| Hotel Reservation | `pagerank` | 7 | 5 | testable |
| Social Network | `ancestor_count` | 11 | 4 | testable |
| Social Network | `betweenness` | 11 | 6 | testable |
| Social Network | `closeness` | 11 | 7 | testable |
| Social Network | `composite_score` | 11 | 7 | testable |
| Social Network | `degree` | 11 | 5 | testable |
| Social Network | `descendant_count` | 11 | 5 | testable |
| Social Network | `dominator_subtree_size` | 11 | 3 | testable |
| Social Network | `eigenvector` | 11 | 1 | **UNDEFINED** — constant at 0 across all 11 Social Network analysis-set services; Spearman rho is undefined. This is a degeneracy of the dependency graph, not a null result. |
| Social Network | `hybrid_criticality` | 11 | 8 | testable |
| Social Network | `in_degree` | 11 | 3 | testable |
| Social Network | `out_degree` | 11 | 4 | testable |
| Social Network | `pagerank` | 11 | 8 | testable |

Source: `degenerate_predictors.csv`.

## 8. Power (§7.2), reproduced from the campaign's own service set

| architecture | n actual / prereg | match | `ancestor_count` levels actual / prereg | match | ceiling ρ, untied outcome (actual / prereg) | match | p | ceiling ρ, tie-matching outcome | p | role |
|---|---|:--:|---|:--:|---|:--:|---:|---:|---:|---|
| Social Network | 11 / 11 | yes | 4 / 4 | yes | 0.941 / 0.941 | yes | 2.00e-04 | 1.000 | 1.00e-04 | confirmatory |
| Hotel Reservation | 7 / 7 | yes | 2 / 2 | yes | 0.791 / 0.791 | yes | 0.0952 | 1.000 | 0.0476 | held-out, DIRECTIONAL ONLY |

Two ceilings are reported because §7.2 does not say what the outcome is assumed to look like, and the answer differs. With a strictly ordered, untied outcome the predictor's own ties cap ρ below 1. With an outcome that mirrors the predictor's ties, ρ reaches 1.0 — and that is the ceiling that applies wherever saturation holds (§2), because there the outcome *is* the predictor.

The untied-outcome column **reproduces §7.2's preregistered 0.941 and 0.791 to within 5e-4**, so the preregistered power table is confirmed, not revised, and the preregistered numbers correspond to that reading.

### 8.1 A p-value discrepancy inside the locked document

| architecture | ceiling ρ (untied) | exact permutation p (mandated) | asymptotic p (forbidden) | §7.2 states | which test §7.2 used |
|---|---:|---:|---:|---:|---|
| Social Network | 0.941 | **2.00e-04** | 1.53e-05 | p < 0.0001 (no exact value given) | consistent with either |
| Hotel Reservation | 0.791 | **0.0952** | 0.0343 | 0.034 | **the asymptotic one** |

**§7.2's stated Hotel Reservation ceiling of p = 0.034 is the asymptotic Spearman p-value** — the test §3 and §7.2 themselves forbid, on the grounds that its measured false-positive rate is 0.097 against a nominal 0.05. Under the exact permutation test the same document mandates, the ceiling p is **0.0952**.

The consequence sharpens §7.2 rather than contradicting it. §7.2 says a perfect Hotel Reservation result would be *"barely significant"*. Under the mandated test it would **not be significant at all**: even a flawless HR result cannot reach p < 0.05, let alone survive FDR correction. Hotel Reservation is therefore not merely underpowered — for this predictor and this tie structure it is **incapable of nominal significance**, which is a stronger statement than the one preregistered, and it is independent of anything the campaign measured. This is a flagged internal inconsistency in the locked document, not a deviation in execution: no analysis used the asymptotic p.

Source: `power_table.csv`.

## 9. `compose-post-service` — the service the paper was built around

| fault | reps | mean | median | range | `ancestor_count` | rank on `ancestor_count` | `hybrid_criticality` | rank on hybrid | out-degree | descendants |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| kill | 5 | 1.00 | 1.0 | 1–1 | 1 | **11 of 11** | 0.3015 | **1 of 11** | 7 | 10 |
| latency | 5 | 1.00 | 1.0 | 1–1 | 1 | **11 of 11** | 0.3015 | **1 of 11** | 7 | 10 |

Source: `compose_post_service.csv`, `sn_predictor_ranks.csv`.

## 10. Deviations from preregistration (§10.5)

Ready to drop into the paper. Every row is traceable to the amendment log in `PREREGISTRATION.md` §12, the `_quarantine/QUARANTINE_LOG.md` item, or the commit named.

### Deviation 1 — Absolute floor added to the latency-degradation threshold

- **Date:** 2026-09-26
- **Stage:** pre-launch rehearsal (before any campaign data existed)
- **Detected by:** the pre-launch rehearsal's own data
- **Outcome affected:** ancestor_affected_count, descendant_affected_count
- **Runs invalidated:** 3

**What happened.** The blast-radius rule flagged a service on a purely multiplicative condition, p95_fault > 2.0 x p95_baseline, with no absolute floor. That was safe only while per-service p95 was in fact the end-to-end p95 of the trace cohort (tens of ms). Once the Q3 fix made percentiles genuinely per-service, 8 of 20 services fell into the 0.02-0.58 ms range, where a multiplicative threshold has no physical meaning. Measured evidence: url-shorten-service moved 0.02 -> 0.06 ms (3.00x) between two FAULT-FREE baseline windows. It was the service the rehearsal flagged as a degraded descendant of compose-post-service.

**What changed.** A second, absolute condition is now required: p95_fault - p95_baseline >= 1.0 ms. Percentiles are no longer rounded to 2 decimals before comparison. Implemented once in measurement.metrics_collector.latency_degraded and shared by the runner, the recovery probe and the offline replay tool. 8 regression tests.

**Disposition of affected runs.** 3 rehearsal runs reset and re-collected. Blast radius was recomputable from persisted spans (compose-post-service 1/1/0 -> 1/0/0) but T_rec was not, because recovery-probe windows are not persisted and downstream_affected was 1-3 in the majority of samples preceding the first all-clear.

**Record:** PREREGISTRATION.md section 12 amendment 1; _quarantine item 11

### Deviation 2 — Fault targeting resolved by compose label; stack completeness enforced

- **Date:** 2026-09-26
- **Stage:** 79 minutes into the campaign
- **Detected by:** a run failure three runs downstream of the cause (geo|latency|1: 'no running container matches geo')
- **Outcome affected:** all outcomes for the affected runs
- **Runs invalidated:** 3

**What happened.** container_for() resolved a compose service to a container by substring match on the container name, taking the shortest match. The compose project is hotelReservation, so every container carries the prefix 'hotelreservation-', which CONTAINS the substring 'reservation'. Every container matched for service='reservation' and the shortest was chosen: container_for('reservation') -> hotelreservation-geo-1. The run SIGKILLed geo and recorded it as a reservation fault; restoration then brought up reservation, which had never been down, leaving geo dead. A second defect compounded it: stack_healthy() checked only that Jaeger and the gateway answered, and both did with geo dead, so the next two runs executed against a stack missing geo and were marked done.

**What changed.** container_for() resolves by the com.docker.compose.service label, re-verifies it, and raises on zero or ambiguous matches instead of guessing. stack_healthy() additionally requires every canonical-graph service to have a running container. tools/audit_run_topology.py added as a standing pre-analysis gate. 21 regression tests.

**Disposition of affected runs.** reservation|kill|1 (wrong container faulted), search|kill|1 and user|kill|1 (incomplete topology). All 3 reset and re-collected. All 22 Social Network runs to that point were verified clean; the collision cannot occur there because no SN service name is a substring of 'socialnetwork'.

**Record:** PREREGISTRATION.md section 12 amendment 2; _quarantine item 12

### Deviation 3 — Graph/Jaeger service names are not docker compose service names

- **Date:** 2026-09-26
- **Stage:** 28 minutes after resuming; caused a false abort, no data affected
- **Detected by:** the exit-2 unrecoverable-stack condition, as designed
- **Outcome affected:** none
- **Runs invalidated:** 0

**What happened.** The stack-completeness gate added by deviation 2 compared canonical-graph node names against docker compose service names. Those differ for the Social Network gateway: it reports itself to Jaeger as 'nginx-web-server' but is the compose service 'nginx-thrift'. Social Network could therefore never pass the gate, and the campaign aborted (exit 2) on a healthy stack. This defect was introduced by the previous fix, roughly an hour before it fired.

**What changed.** APPS gained an explicit compose_aliases map (one entry: nginx-web-server -> nginx-thrift; Hotel Reservation is all identity). compose_service() translates at every Docker boundary, which also fixed the same latent bug in 'docker compose up -d <service>' on the restore path. A new preflight_service_names() check refuses to launch if any graph service has no declared compose counterpart, so a mismatch fails at launch rather than mid-campaign. 6 regression tests.

**Disposition of affected runs.** No data affected. The abort occurred before any Social Network run started; the gate refused to run rather than producing garbage, which is the designed behaviour acting on a wrong premise.

**Record:** PREREGISTRATION.md section 12 amendment 3 preamble; commit 4a8937b

### Deviation 4 — Leaked pumba netem rule contaminated 10 later runs

- **Date:** 2026-09-26
- **Stage:** detected by the pre-analysis gates immediately after run 180
- **Detected by:** tools/audit_baseline_sanity.py, before any statistic was computed
- **Outcome affected:** ancestor_affected_count (systematically under-counted), T_rec for the origin run
- **Runs invalidated:** 11

**What happened.** A netem delay applied to compose-post-service at 05:31:41 did not expire with its --duration. The pumba process exited normally and the runner recorded the removal instant from that exit, but the tc rule remained active for the whole remainder of the Social Network latency rep-1 block and was cleared only by the stack teardown 28 minutes later. In the FAULT-FREE baselines of the 10 runs that followed, compose-post-service's own-span p95 was 2153-2486 ms against 8.9 ms before and 9.0-9.8 ms after; gateway baseline p95 was 3132-4046 ms against a campaign median of 54.87 ms. The distortion was directional, not noisy: an inflated baseline makes the fault look smaller, and because the faulted services' ancestors were already degraded in the baseline they could not clear 2x and went uncounted. ancestor_affected_count came out low by exactly 2 in most of the ten (0 vs 2, 1 vs 3, 2 vs 4 against clean rep 2). Analysed as collected it would have flattened the Social Network H1 correlation and been indistinguishable from measurement noise.

**What changed.** one_run force-recreates the target container after every non-kill fault run, after the fault window and after the recovery probe, so it cannot affect the run just completed but guarantees the next starts clean; recorded per run as fault_cleanup. tools/audit_baseline_sanity.py added as a standing pre-analysis gate (median/MAD outlier detection on baseline p95) -- it is what caught this.

**Disposition of affected runs.** 10 contaminated runs plus the origin run reset and re-collected. The origin run was also invalid on its own terms: recorded as censored on p95, but its fault was still active throughout its recovery probe. It was the campaign's only censored observation; the corrected dataset has none.

**Record:** PREREGISTRATION.md section 12 amendment 3; _quarantine item 13

### Deviation 5 — Two specification gaps resolved by the principal investigator

- **Date:** 2026-09-27
- **Stage:** before the analysis was written
- **Detected by:** reading the locked specification against the actual dataset
- **Outcome affected:** none (analysis specification only)
- **Runs invalidated:** 0

**What happened.** Executing section 7 required two choices the locked text does not make. (a) Section 7 fixes the Spearman unit (service level, median-aggregated) but never states the level at which Kaplan-Meier, log-rank and Cox run. (b) Section 7.1 lists the exploratory outcomes but not which fault types each covers.

**What changed.** Both were put to the principal investigator and answered before any analysis code was written. (a) Survival models run at RUN level with standard errors clustered by service, with the service-level version reported alongside as a consistency check. (b) delta-p95 latency only, delta-p99 latency only, delta-error-rate kill only, and both affected counts under both fault types. Neither choice was made after seeing a result.

**Disposition of affected runs.** not applicable

**Record:** this file; analysis/final/run_confirmatory_analysis.py docstring

### Deviation 7 — Documentation inconsistency: section 7.2's stated Hotel Reservation p-value is the asymptotic one

- **Date:** 2026-09-27
- **Stage:** analysis (no execution deviation)
- **Detected by:** recomputing the preregistered power table with the mandated exact test
- **Outcome affected:** none (HR was already directional-only)
- **Runs invalidated:** 0

**What happened.** Section 7.2 gives Hotel Reservation's best attainable rho as 0.791 with p = 0.034. The rho reproduces exactly, but 0.034 is the ASYMPTOTIC Spearman p-value -- the test sections 3 and 7.2 themselves forbid, on the stated grounds that its measured false-positive rate is 0.097 against a nominal 0.05. Under the exact permutation test the same document mandates, the ceiling p is 0.0952.

**What changed.** Nothing in the analysis: no inference anywhere used an asymptotic p-value. The discrepancy is reported because it strengthens the preregistered conclusion rather than weakening it. Section 7.2 says a perfect HR result would be 'barely significant'; under the mandated test it would not be significant at all, so HR is incapable of nominal significance for this predictor and tie structure, independently of anything measured. The paper should quote 0.0952, not 0.034.

**Disposition of affected runs.** not applicable

**Record:** _audit/CONFIRMATORY_ANALYSIS.md section 8.1; power_table.csv

### Deviation 8 — Vectorised Spearman/permutation/bootstrap implementation

- **Date:** 2026-09-27
- **Stage:** analysis (implementation only)
- **Detected by:** not a defect; a performance change, disclosed for completeness
- **Outcome affected:** none (equivalence tested)
- **Runs invalidated:** 0

**What happened.** scipy.stats.spearmanr costs ~1.4 ms per call and the preregistered analysis needs roughly 2.5 million evaluations (10 000 permutations plus 10 000 bootstrap resamples for each of ~240 tests), which is about an hour of interpreter overhead. The statistics were reimplemented in vectorised form in analysis/final/fast_stats.py, reducing the run to 25 seconds.

**What changed.** No statistic changed. Spearman's rho IS Pearson's r on average ranks, and in a permutation test the normalising denominator is invariant under permutation, so the test reduces algebraically to one matrix multiply. Equivalence to scipy is asserted by 15 tests in tests/test_fast_stats.py, including a brute-force reference implementation for n = 7 and the tie-heavy vectors this dataset actually contains. Reported here because it changed the code path that produced every p-value, even though it did not change any value.

**Disposition of affected runs.** not applicable

**Record:** analysis/final/fast_stats.py; tests/test_fast_stats.py

### Deviation 6 — Zero censoring promoted Spearman to primary for T_rec

- **Date:** 2026-09-27
- **Stage:** analysis
- **Detected by:** the dataset (0 of 180 censored)
- **Outcome affected:** T_rec inference
- **Runs invalidated:** 0

**What happened.** Section 7 anticipates censored recovery times and specifies survival analysis as the primary inferential result for T_rec, adding: 'if under 10% of observations are censored, Spearman is promoted to primary -- that threshold is fixed here, in advance.' The final dataset has ZERO censored observations out of 180.

**What changed.** Nothing was decided: the preregistered rule fired. The Spearman permutation p-value is the primary test for T_rec and is the value entering each BH-FDR family. Cox and log-rank are computed and reported alongside but are NOT separately FDR-corrected, because they test the same hypotheses as the primary tests they accompany and correcting both would double-count. The 'biased toward fast recoveries' label section 7 attaches to Spearman-on-uncensored does not apply, there being nothing censored to exclude.

**Disposition of affected runs.** not applicable

**Record:** section 7 as written; this file

Source: `deviations.csv`.

## 11. Output index

| file | contents |
|---|---|
| `analysis/final/ancestor_saturation.csv` | 4 rows |
| `analysis/final/compose_post_service.csv` | 2 rows |
| `analysis/final/confirmatory_family_kill.csv` | 44 rows |
| `analysis/final/degenerate_predictors.csv` | 24 rows |
| `analysis/final/deviations.csv` | 8 rows |
| `analysis/final/exploratory_family.csv` | 154 rows |
| `analysis/final/h1b_hybrid_metric.csv` | 4 rows |
| `analysis/final/integrity_checks.csv` | 10 rows |
| `analysis/final/power_table.csv` | 2 rows |
| `analysis/final/predictors.csv` | 20 rows |
| `analysis/final/replication_family_latency.csv` | 44 rows |
| `analysis/final/run_level_data.csv` | 180 rows |
| `analysis/final/service_level_data.csv` | 36 rows |
| `analysis/final/sn_predictor_ranks.csv` | 11 rows |
| `analysis/final/figures/fig_primary_kill.png` | ancestor_count vs median ancestor_affected_count, kill faults, both architectures |
| `analysis/final/figures/fig_primary_latency.png` | ancestor_count vs median ancestor_affected_count, latency faults, both architectures |
| `analysis/final/figures/fig_km_ancestor_count_kill.png` | KM curves by ancestor_count tercile, kill faults |
| `analysis/final/figures/fig_km_ancestor_count_latency.png` | KM curves by ancestor_count tercile, latency faults |
| `analysis/final/figures/fig_forest_confirmatory.png` | rho with CI for every confirmatory test on ancestor_affected_count |
| `analysis/final/figures/fig_forest_replication.png` | rho with CI for every replication test on ancestor_affected_count |

