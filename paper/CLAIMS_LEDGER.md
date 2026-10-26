# Claims ledger

Every claim that could reasonably appear in the Abstract or Conclusions, one sentence each,
with its status and the `paper/numbers.csv` ids that carry its numbers. This is an audit
artifact, not manuscript text — nothing here is written to be quoted.

**Status key**

| mark | meaning |
|---|---|
| **SUPPORTED** | The data support the claim as worded. Cite the listed ids. |
| **POST-HOC** | True of the data, but the analysis was specified after the results were known. Usable only if labelled post-hoc or exploratory in the manuscript, and never as confirmation. |
| **UNSUPPORTED** | The data do not support this claim. Do not make it. Each entry says what may be said instead. |

Anything not listed here has not been checked. Do not assume silence means support.

---

## 1. The headline result

**1.1 SUPPORTED** — The preregistered confirmatory hypothesis is not confirmed: none of the
44 confirmatory tests is significant after Benjamini–Hochberg correction at q = 0.05.
`conf_family_size`, `conf_family_significant`, `fdr_q`

**1.2 SUPPORTED** — The primary test — Social Network, `ancestor_count` versus measured
`ancestor_affected_count` under kill faults — gives a strong positive rank correlation that
does not survive correction.
`primary_rho`, `primary_ci_lo`, `primary_ci_hi`, `primary_ci_method`, `primary_p_locked`,
`primary_p_bh_locked`, `primary_significant`, `primary_n_services`

**1.3 SUPPORTED** — The replication family behaves the same way: none of its 44 tests is
significant after its own correction.
`repl_family_size`, `repl_family_significant`, `repl_best_raw_p`, `repl_best_bh_p`

**1.4 UNSUPPORTED** — "`ancestor_count` predicts blast radius." The point estimate is large
and positive but the preregistered correction rejects it, and on the confirmatory
architecture most of the relationship is definitional (§3.1 below). **Say instead:** the
correlation is positive and does not survive the preregistered correction.

**1.5 UNSUPPORTED** — "The result is marginal / approaches significance / would be
significant in a larger sample." The adjusted p is about seven times the threshold
(`primary_p_bh_over_q`), and no sample-size claim was tested. **Say instead:** the test is
null after correction, and §4 gives the preregistered power ceiling.

---

## 2. The hybrid metric (H1b)

**2.1 SUPPORTED** — The hybrid criticality metric's correlation with measured blast radius
is negative in all four architecture-by-fault cells, the direction preregistered under H1b.
`h1b_all_negative`, `h1b_cells`, `h1b_sn_kill_rho`, `h1b_hr_kill_rho`,
`h1b_sn_latency_rho`, `h1b_hr_latency_rho`

**2.2 SUPPORTED** — In none of those four cells is the correlation distinguishable from zero
after correction.
`h1b_any_distinguishable`, `h1b_sn_kill_bh_p`, `h1b_hr_kill_bh_p`, `h1b_sn_latency_bh_p`,
`h1b_hr_latency_bh_p`

**2.3 UNSUPPORTED** — "The hybrid metric is anti-predictive." That asserts a negative
association the data cannot distinguish from no association; the Social Network confidence
interval spans zero in both directions. **Say instead:** the metric shows no detectable
association with measured blast radius, with a negative point estimate in every cell.
`h1b_sn_kill_ci_lo`, `h1b_sn_kill_ci_hi`

**2.4 UNSUPPORTED** — "The hybrid metric is worse than `ancestor_count`." The two were never
compared in a test that controls for anything; only their separate correlations are
reported. **Say instead:** report both correlations and let them stand side by side.

---

## 3. What actually drives the Social Network result

**3.1 SUPPORTED** — On Hotel Reservation the measured outcome equals the graph predictor for
every service in every run, so any correlation there is a restatement of how the outcome was
constructed rather than an independent prediction.
`saturation_hr_kill_run`, `saturation_hr_kill_service`, `saturation_hr_kill_tautological`,
`saturation_hr_latency_run`, `saturation_hr_latency_tautological`

**3.2 SUPPORTED** — Social Network is not fully saturated, and the whole of its departure
from tautology is one service, `user-service`, which registers 2 of its 4 graph ancestors in
every one of its five kill repetitions.
`saturation_sn_kill_run`, `saturation_sn_kill_service`, `userservice_ancestor_count`,
`userservice_measured`, `userservice_runs_departing`

**3.3 POST-HOC** — Removing `user-service` from the analysis set drives the correlation to
exactly 1.000, a swing 2.4 times larger than that of any other service, so the correlation is
stable under every exclusion except the one that completes the tautology.
`loo_rho_min`, `loo_rho_max`, `loo_userservice_rho`, `loo_userservice_delta`,
`loo_second_largest_service`, `loo_second_largest_delta`, `loo_swing_ratio`,
`loo_n_exclusions`
*Specified after the confirmatory results were known. Label as a post-hoc robustness check.*

**3.4 POST-HOC** — In all five `user-service` kill runs the ancestors that degraded were the
two on paths the workload exercises, suggesting `ancestor_count` is an upper bound whose
tightness depends on workload mix rather than on graph structure alone.
*No supporting id: this is an explanation generated after seeing the data, not a tested
claim. Testing it needs a workload-weighted predictor and a new preregistration. It may be
offered as a hypothesis for future work and must never be stated as a finding.*

**3.5 UNSUPPORTED** — "The replication independently confirms the confirmatory result." The
median outcome vector is identical between the two fault types in both architectures, so the
latency family correlates the same values against the same predictors and cannot disagree.
**Say instead:** the two families agree because for this outcome they are not independent;
the replication remains informative for recovery time, where the fault types do differ.
`replication_primary_identical`, `trec_rho_between_faults_sn`, `trec_rho_between_faults_hr`

---

## 4. Power and the preregistration's own arithmetic

**4.1 SUPPORTED** — The realised analysis sets match the preregistration exactly in size and
in the number of distinct predictor levels, and the preregistered ceiling correlations
reproduce.
`power_sn_n`, `power_sn_n_prereg`, `power_sn_n_matches`, `power_sn_levels`,
`power_sn_levels_match`, `power_sn_ceiling`, `power_sn_ceiling_matches`, `power_hr_n`,
`power_hr_n_matches`, `power_hr_levels`, `power_hr_levels_match`, `power_hr_ceiling`,
`power_hr_ceiling_matches`

**4.2 SUPPORTED (corrected 2026-10-26)** — Under the exact permutation test the
preregistration itself mandates, an outcome without ties cannot bring Hotel Reservation below
p = 0.05 for this predictor: the best it can reach is the untied ceiling, whose exact p is
above 0.05. Only an outcome that repeats the predictor's ties can do better, reaching a
correlation of one with p just under 0.05, and that is the saturated outcome observed; after
correction the test is far from significant. *Correction:* the earlier wording said Hotel
Reservation could not reach nominal significance at any observed outcome, which overlooked the
tie-matching ceiling in `analysis/final/power_table.csv`; the confirmatory row for Hotel
Reservation shows that uncorrected p.
`power_hr_ceiling_p`, `power_hr_tied_rho`, `power_hr_tied_p`, `power_hr_levels`, `power_hr_n`

**4.3 SUPPORTED** — The p-value quoted in the preregistration's power section for that
ceiling is the asymptotic value, which the same document forbids for inference; the exact
value is roughly three times larger.
`power_hr_prereg_stated_p`, `power_hr_ceiling_p_asymptotic`, `power_hr_ceiling_p`

**4.4 UNSUPPORTED** — "Hotel Reservation replicates / fails to replicate the Social Network
result." It is saturated (3.1) and underpowered to the point of being unable to reach
significance (4.2), so it can neither confirm nor disconfirm. **Say instead:** Hotel
Reservation is reported as directional only.

---

## 5. Propagation topology

**5.1 SUPPORTED** — Degradation propagates to callers, not to callees: no descendant of a
faulted service degraded in 179 of the 180 runs, and the service-level median is zero for
every service in every condition.
`descendant_affected_runs_zero`, `descendant_affected_runs_zero_pct`,
`descendant_affected_count_distinct_values`, `descendant_affected_count_constant_at`

**5.2 SUPPORTED** — Services unrelated to the faulted service are likewise almost never
affected, on the same 179-of-180 count.
`unrelated_affected_runs_zero`, `unrelated_affected_runs_zero_pct`,
`unrelated_affected_count_distinct_values`

**5.3 UNSUPPORTED** — "Descendants never degrade" / "`descendant_affected_count` is
identically zero across all 180 runs." One run recorded two degraded descendants, and one
other run recorded two degraded unrelated services. **Say instead:** zero in 179 of 180 runs,
naming the exceptions, and note that the service-level median — the unit of analysis — is
zero everywhere.
`descendant_affected_runs_nonzero`, `descendant_affected_exception_run`,
`descendant_affected_max_in_any_run`, `unrelated_affected_runs_nonzero`,
`unrelated_affected_exception_run`

**5.4 SUPPORTED** — Because both of these outcomes have no variance at the service level,
88 of the 154 attempted exploratory tests are undefined rather than null, which is a
structural result and not a failure to detect one.
`expl_attempted`, `expl_testable`, `expl_undefined`

**5.5 SUPPORTED** — The set of services that degrade is essentially invariant to fault type:
for 17 of the 18 services the full set of five per-run counts is identical under kill and
under latency injection, and the service-level medians are identical in both architectures.
`fault_invariant_services_all`, `fault_invariant_services_all_total`,
`fault_invariant_services_sn`, `fault_invariant_services_hr`,
`replication_primary_identical`
*Caveat to state alongside it: this invariance is also exactly why the replication family is
not independent evidence (3.5). Recovery time is not fault-invariant —
`trec_rho_between_faults_sn` is 0.384.*

---

## 6. The motivating example

**6.1 SUPPORTED** — `compose-post-service`, the example the original metric was built around,
is ranked most critical by that metric and least critical by the corrected predictor, out of
all 11 Social Network services.
`composepost_rank_hybrid`, `composepost_rank_ancestor_count`, `composepost_set_size`,
`composepost_hybrid`, `composepost_ancestor_count`

**6.2 SUPPORTED** — Its measured blast radius is one affected ancestor in every one of ten
runs, with zero variance across both fault types, despite having seven direct callees and ten
descendants.
`composepost_kill_mean`, `composepost_kill_min`, `composepost_kill_max`,
`composepost_latency_mean`, `composepost_latency_min`, `composepost_latency_max`,
`composepost_kill_reps`, `composepost_out_degree`, `composepost_descendants`

**6.3 UNSUPPORTED** — "The inversion generalises to other services or systems." It is
demonstrated for one service in one architecture; the 11-service correlation that would
generalise it is the null result of §1. **Say instead:** present it as a worked case, and
say plainly that the general claim was tested and did not survive correction.

---

## 7. Measurement

**7.1 SUPPORTED** — Attributing each trace's end-to-end root-span latency to every service on
that trace makes services on a shared path cross any multiplicative threshold together; under
this scope five non-faulted services are flagged where the corrected per-service scope flags
one.
*Source: `paper/figures/fig_q3_artifact_data.csv`, produced by `paper/make_figures.py` from
the persisted pilot spans. Counts are in that file; no numbers.csv id, because this is pilot
validation data rather than campaign data.*

**7.2 SUPPORTED** — Two of the services the old scope flagged are neither ancestors nor
descendants of the faulted service, so the old measure was tracking the trace cohort rather
than the dependency neighbourhood.
*Source as 7.1: `paper/figures/fig_q3_artifact_data.csv`. There is no numbers.csv id, this
being pilot validation data rather than campaign data.*

**7.3 UNSUPPORTED** — "The corrected measurement changes the conclusion." The corrected
measurement is what the entire campaign used; there is no uncorrected campaign to compare
against. **Say instead:** the correction was made before data collection, and the pilot
comparison shows what it would otherwise have produced.

---

## 8. Conduct of the study

**8.1 SUPPORTED** — The campaign is complete and balanced: 180 runs over 36 cells at 5
repetitions each, with no failed runs and no gateway runs.
`campaign_runs_total`, `campaign_cells`, `campaign_reps_per_cell`, `campaign_runs_failed`,
`campaign_gateway_runs`, `campaign_architectures`, `campaign_fault_types`, `sn_runs`,
`hr_runs`, `sn_services`, `hr_services`

**8.2 SUPPORTED** — Every recovery time was observed, so nothing is censored, and the
preregistered rule promoting the rank test to primary fired on a threshold fixed in advance.
`campaign_runs_censored`, `campaign_censoring_rate_pct`

**8.3 SUPPORTED** — All ten pre-analysis integrity checks passed before any statistic was
computed.
`integrity_checks_total`, `integrity_checks_passed`

**8.4 SUPPORTED** — Thirteen deviations from the preregistration are logged, invalidating 17 runs
in total, all of which were quarantined and re-collected rather than analysed or discarded.
`deviations_total`, `deviations_runs_invalidated`, `quarantine_items`

**8.5 SUPPORTED** — Two predictor-architecture pairs are degenerate because the predictor is
constant, and are reported as undefined rather than as null results.
`degenerate_pairs`, `testable_pairs`, `total_predictor_pairs`, `degenerate_sn_predictor`,
`degenerate_hr_predictor`

**8.6 POST-HOC** — The primary test's raw p was later recomputed by exact enumeration
instead of Monte-Carlo sampling, moving the adjusted p slightly without changing the verdict.
`primary_p_exact`, `primary_p_exact_arrangements`, `primary_p_bh_exact`,
`primary_significant_exact`, `exact_tests_refined`
*Deviation 9. Applied to all 43 testable tests, not to the primary alone, so it could not be
targeted. The locked Monte-Carlo value remains the preregistered one; cite the exact value
only where it is labelled supplementary.*

**8.7 POST-HOC** — An independent from-scratch recomputation of the primary statistic from
raw spans reproduces it, and agrees with the stored per-run outcome fields on the identity of
the affected services in all 110 Social Network runs.
*Source: `analysis/final/blind_recompute.md`. Supplementary verification; it establishes that
the implementation is faithful to the data, not that the definitions are correct.*

**8.8 SUPPORTED** — The weights 0.4, 0.4 and 0.2 were inherited from the original proposal.
In the earlier, withdrawn analysis they had been chosen by an empirical search, so they are
not a priori. We did not re-tune them on the campaign data. The preregistered protocol, which
tuned weights on Social Network and froze them for Hotel Reservation, was not carried out
(Deviation 10). Because the original search favoured the metric, this is unlikely to explain
a failure to find an association.
`hybrid_w_in`, `hybrid_w_out`, `hybrid_w_btw`, `hybrid_weights_lockfile_exists`,
`hybrid_weights_reoptimised_on_campaign`
*Provenance: `centrality/metric_constants.py` CHANGELOG; `PREREGISTRATION.md` §12 deviation
10.*

**8.9 UNSUPPORTED** — "The weights were set a priori" / "never fitted to outcome data" / "the
equal in/out split is a neutral prior". They were chosen by an empirical search in the
withdrawn analysis and carried over. **Say instead:** the wording of 8.8.

---

## 9. Exploratory findings — usable only as exploratory

**9.1 SUPPORTED, EXPLORATORY** — Two of the 66 testable exploratory tests survive their own
correction: the magnitude of latency inflation under latency faults correlates strongly with
both the hybrid metric and raw degree on Social Network.
`expl_significant`, `expl_testable`, `expl_sig_hybrid_criticality_rho`,
`expl_sig_hybrid_criticality_bh_p`, `expl_sig_degree_rho`, `expl_sig_degree_bh_p`

**9.2 UNSUPPORTED** — "The hybrid metric does predict impact after all, just a different
kind." 9.1 concerns a different outcome from the one H1b is about, in one architecture, under
one fault type, in a family carrying no confirmatory weight. **Say instead:** report 9.1 as
exploratory and state explicitly that it does not rescue H1b.

---

## 10. Claims with no evidence either way

These were not tested. Do not assert or deny them.

- Any claim about architectures other than the two studied.
- Any claim about fault types other than process kill and 500 ms network delay.
- Any claim that one centrality metric is generally preferable to another.
- Any claim about production systems, real user traffic, or workloads other than the
  DeathStarBench generators used here.
- Any causal claim about *why* a service degrades; the study measures whether it degrades.
- Any claim about recovery time as a function of criticality: every such test is inside the
  null families of §1.

---

## 11. Post-hoc descriptive analyses — usable only with that label

Added 2026-10-18. Each was specified after the confirmatory results were known and runs no
test that enters any family.

**11.1 POST-HOC** — The gateway was among the degraded ancestors in every one of the 180
runs, and it is a graph ancestor of every analysis-set service in both architectures, so
every measured ancestor count includes the gateway. For `compose-post-service` the gateway
was the only degraded ancestor in all ten runs.
`gw_runs_gateway_degraded_all`, `gw_runs_all`, `gw_sn_services_gateway_ancestor`,
`gw_hr_services_gateway_ancestor`, `composepost_runs_only_gateway_ancestor`,
`composepost_runs_total`
*Source: `analysis/final/gateway_decomposition.md`. Descriptive; no test.*

**11.2 POST-HOC, EXPLORATORY** — Under kill faults, the gateway's end-to-end error rate
follows the share of the request mix whose path passes through the faulted service
(descriptive rank correlation 0.788 on Social Network, 0.964 on Hotel Reservation). On
Social Network, the exploratory association between `hybrid_criticality` and gateway error,
which is not significant after correction, tracks the metric's in-degree term (0.715) more
closely than its fan-out term (0.310).
`uf_sn_rho_err_weight_share`, `uf_hr_rho_err_weight_share`, `uf_test_sn_hybrid_rho`,
`uf_test_sn_hybrid_bh_p`, `uf_sn_rho_err_term_in`, `uf_sn_rho_err_term_fanout`,
`uf_sn_rho_err_term_btw`, `uf_kill_runs_baseline_error_zero`
*Source: `analysis/final/user_facing_impact.md`. The rank correlations with weight share
carry no p-value. The baseline uses the gateway's own spans and the fault window is
end-to-end; the baseline is 0.0 in all 90 kill runs, so this has no numerical effect.*

**11.3 POST-HOC** — Restricting Social Network per-service latency to server spans changes
2 of 110 run-level outcomes and no service-level median, and leaves the primary correlation
and its exact p unchanged.
`replay_runs`, `replay_runs_changed`, `replay_service_medians_changed`,
`replay_primary_identical`, `replay_primary_rho_kill`, `replay_primary_p_kill`,
`sn_span_samples_fallback`, `sn_span_samples`, `sn_spans_selected_client_pct`
*Deviation 11. Social Network recovery times could not be replayed.*

**11.4 UNSUPPORTED** — "The request mix explains which services degrade" or "explains why
`user-service` departs." 11.2 concerns the gateway's error rate, not ancestor counts, and the
`user-service` reading in 3.4 remains untested. **Say instead:** describe the gateway-error
association as exploratory and descriptive, and keep 3.4 labelled as an untested hypothesis.

---

## 12. Post-hoc weight sensitivity — usable only with that label

Added 2026-10-20. `analysis/final/weight_sensitivity.py` was written and run after the
confirmatory results were known. It recomputes `hybrid_criticality` for all 231 weight
triplets on the 0.05 grid with the producing code and correlates each with the outcomes,
exact permutation p where enumeration is feasible, BH within each family of 231. No triplet
is selected, recommended or adopted; the reported metric keeps 0.4/0.4/0.2.

**12.1 POST-HOC** — Against `ancestor_affected_count` on Social Network, rho ranges from
-0.544 to 0.337 (median -0.167) over the 231 triplets; 28 are positive; none has an
uncorrected p below 0.05 and none survives BH within the 231. Kill and latency faults give
identical results. On Hotel Reservation every defined triplet gives -0.258 (230 defined, the
in-degree-only triplet is constant) and none is significant. At the reported weights rho is
-0.144 (exact p 0.669); 47 triplets give a larger rho.
`ws_triplets`, `ws_grid_step`, `ws_sn_kill_anc_rho_min`, `ws_sn_kill_anc_rho_median`,
`ws_sn_kill_anc_rho_max`, `ws_sn_kill_anc_triplets_rho_positive`,
`ws_sn_kill_anc_triplets_p_raw_below_05`, `ws_sn_kill_anc_triplets_significant_bh`,
`ws_sn_kill_anc_p_raw_min`, `ws_sn_kill_anc_reported_rho`, `ws_sn_kill_anc_reported_p`,
`ws_sn_kill_anc_triplets_rho_above_reported`, `ws_anc_identical_across_faults`,
`ws_hr_kill_anc_triplets_defined`, `ws_hr_kill_anc_triplets_undefined`,
`ws_hr_kill_anc_rho_min`, `ws_hr_kill_anc_rho_max`, `ws_hr_kill_anc_triplets_significant_bh`,
`hybrid_weights_grid_evaluated_post_hoc`
*Source: `analysis/final/weight_sensitivity_summary.csv`. The reported triplet reproduces the
stored rho and exact p.*

**12.2 POST-HOC, EXPLORATORY** — Against the gateway error rate under kill faults on Social
Network, rho is positive for all 231 triplets (0.229 to 0.832, median 0.753); 145 have an
uncorrected p below 0.05 and 128 pass BH within the 231; at the reported weights rho is
0.786. On Hotel Reservation every defined triplet gives -0.204 and none is significant. The
preregistered exploratory test at the reported weights was not significant after correction
within its own family (adjusted p 0.0913).
`ws_sn_kill_err_rho_min`, `ws_sn_kill_err_rho_median`, `ws_sn_kill_err_rho_max`,
`ws_sn_kill_err_triplets_rho_positive`, `ws_sn_kill_err_triplets_p_raw_below_05`,
`ws_sn_kill_err_triplets_significant_bh`, `ws_sn_kill_err_reported_rho`,
`ws_hr_kill_err_rho_min`, `ws_hr_kill_err_triplets_significant_bh`,
`uf_test_sn_hybrid_bh_p`, `ws_mc_permutations`
*Social Network p-values for this outcome use 10,000 random permutations (11! orderings
cannot be enumerated).*

**12.3 UNSUPPORTED** — "Some weighting of the metric predicts failure impact", "the metric
works with weights X", any recommended or adopted triplet, or reading 12.2's BH counts as a
finding. The 231 triplets are correlated tries on one dataset, chosen after the results were
known. **Say instead:** report the distribution, state that the analysis is post hoc and that
the reported metric keeps 0.4/0.4/0.2, and call any extreme triplet the best (or worst) of
231 tries.

---

## 13. Testbed, run protocol and fault injection

Added 2026-10-20.

**13.1 SUPPORTED** — Testbed. Host OS and CPU were queried on 2026-10-20, after the campaign;
host RAM, the Docker Desktop WSL2 backend, the 7.598 GiB VM ceiling and the container counts
(27 Social Network, 24 Hotel Reservation, one stack at a time) were recorded on 2026-09-24,
before it. Jaeger 1.62.0 all-in-one ran with in-memory storage. Locust ran 25 users with a
spawn rate of 10 users per second.
`testbed_measured_on`, `testbed_host_os`, `testbed_host_os_version`, `testbed_cpu_model`,
`testbed_cpu_cores`, `testbed_cpu_logical`, `testbed_vm_record_date`, `testbed_host_ram_gb`,
`testbed_docker_backend`, `testbed_docker_vm_gib`, `testbed_containers_sn`,
`testbed_containers_hr`, `version_docker_desktop`, `version_docker_compose`,
`version_docker_client`, `version_jaeger`, `testbed_jaeger_storage`, `version_locust`,
`protocol_load_users`, `protocol_spawn_rate`
The Docker client binary was last written on 2026-09-20, before the campaign; no record from
the campaign days confirms the host OS build or the Docker Desktop version.
*Sources: `data/environment/testbed.txt` (queried by `tools/record_testbed.py`),
`data/environment/tool_versions.txt` (Docker client),
`data/environment/docker_vm.txt` (lines from the 2026-09-24 record).*

**13.2 SUPPORTED** — Fault injection. Pumba runs as a container from the untagged image
`ghcr.io/alexei-led/pumba`. A kill sends SIGKILL; a latency fault is `pumba netem` with a 30 s
duration, 500 ms delay and 100 ms jitter. The target container is resolved by an exact match
on the `com.docker.compose.service` label, and the runner stops if no container or more than
one matches. The netem process is launched in the background and the fault-removal instant
is taken when it exits; a killed service is restored with `docker compose up -d`, and after
every non-kill run the target container is recreated (`--force-recreate`) after the recovery
probe.
`fault_kill_signal`, `fault_latency_delay_ms`, `fault_latency_jitter_ms`,
`protocol_fault_duration_s`
*Sources: `faultinjection/fault_config.py` (pumba_command), `tools/run_pilot.py` (one_run,
container_for); the command lines in `paper/tables/tbl_commands.csv` are generated from that
code.*

**13.3 SUPPORTED (correction of earlier manuscript text)** — The baseline percentiles are
computed over the 60 s window that ends when the pre-fault load period ends. That window is
the load period itself, starting when the load generator starts; it is not a separate window
after a warm-up. Manuscript text before 2026-10-20 described a 60 s warm-up followed by a
60 s baseline, which the code does not do.
`protocol_warmup_s`, `protocol_baseline_window_s`, `protocol_baseline_window_distinct`
*Source: `tools/run_pilot.py` one_run (`baseline_start_us = baseline_end_us - warmup`), and
the baseline-window timestamps stored in every run record. The preregistration lists "60 s warm-up →
baseline"; the difference is recorded as Deviation 13 (2026-10-20), with no run
invalidated.*

---

## 14. Problem statement and hypothesis labels

Added 2026-10-20.

**14.1 SUPPORTED** — The formal definitions in the manuscript's problem statement (directed
call graph, fault types, the three disjoint outcome counts, `ancestor_count`, the hybrid
formula with linear fan-out weight) and the hypotheses restate the locked preregistration.
The manuscript's H2 is the preregistration's H1b; the preregistration's own H2 is a
structural observation and is not tested.
*There is no numbers.csv id: these are definitions, from PREREGISTRATION_v3_LOCKED.md §1.4, §2 and §6.2.*
