# 4. Results

> **Drafting note (strip before submission).** Trailing `%[id:...]` comments name the
> `paper/numbers.csv` claim_id each number comes from; `%[fig:...]` points at a figure's
> backing data file where `CLAIMS_LEDGER.md` records that no numbers.csv id exists. Table
> and figure numbers are provisional and map to files as follows.
>
> | Ref | File |
> |---|---|
> | Table 1 | `paper/tables/tbl_predictors_sn.csv` |
> | Table 2 | `paper/tables/tbl_predictors_hr.csv` |
> | Table 3 | `paper/tables/tbl_primary_by_family.csv` |
> | Table 4 | `paper/tables/tbl_family_summary.csv` |
> | Table 5 | `paper/tables/tbl_h1b.csv` |
> | Table 6 | `paper/tables/tbl_power.csv` |
> | Table 7 | `paper/tables/tbl_leave_one_out.csv` |
> | Table 8 | `paper/tables/tbl_deviations.csv` |
> | Table 9 | `paper/tables/tbl_primary_exact_p_supplementary.csv` |
> | Figure 1 | `paper/figures/fig_primary_sn.pdf` |
> | Figure 2 | `paper/figures/fig_rank_inversion.pdf` |
> | Figure 3 | `paper/figures/fig_leave_one_out.pdf` |
> | Figure 4 | `paper/figures/fig_q3_artifact.pdf` |

All 180 %[id:campaign_runs_total] planned runs completed, across 36 %[id:campaign_cells]
balanced cells. No run was lost to telemetry failure %[id:campaign_runs_failed], no gateway was
faulted %[id:campaign_gateway_runs], and every recovery time was observed
%[id:campaign_runs_censored]. Tables 1 and 2 list the graph predictors and measured outcomes
for each service in Social Network and Hotel Reservation.

## 4.1 The confirmatory test

The primary hypothesis was that a service's transitive caller count predicts the number of
services its failure degrades. It replaced the original fan-out hypothesis after the pilot
%[prereg:§1]. On Social Network under kill faults, `ancestor_count` and the measured
`ancestor_affected_count` correlate at ρ = 0.785 %[id:primary_rho] across 11
%[id:primary_n_services] services, with a bias-corrected and accelerated bootstrap interval of
[0.000, 1.000] %[id:primary_ci_lo] %[id:primary_ci_hi] %[id:primary_ci_method]. The
uncorrected permutation p-value, from 10,000 %[id:primary_n_permutations] Monte-Carlo
permutations, is 0.0080 %[id:primary_p_locked]. The exact value, 0.006926
%[id:primary_p_exact], is in Table 9 (Deviation 9). After Benjamini-Hochberg correction across
the 44 %[id:conf_family_size] tests of the confirmatory family, the adjusted p-value is 0.3451
%[id:primary_p_bh_locked].

At q = 0.05 %[id:fdr_q], not one of the 44 confirmatory tests is significant %[id:conf_family_significant] %[id:conf_family_significant]
%[id:fdr_q]. The primary test has the smallest uncorrected p-value in the family
%[id:conf_best_raw_p] %[id:conf_best_predictor], and its adjusted value is about seven times
the threshold (6.9 %[id:primary_p_bh_over_q]). Table 3 gives the primary test in each family
and architecture, and Table 4 summarises both families. The preregistered hypothesis is not
confirmed. The point estimate is large and positive, the correction we committed to in advance
rejects it, and the confidence interval runs from no association to a perfect one.

Two features of the data qualify that estimate further, and they matter more than the
p-value.

The first is saturation. If every service's measured blast radius equalled its graph ancestor
count, a correlation of 1.0 would follow by construction and would test nothing. On Hotel Reservation that is exactly what happened: each service's measured outcome matched its graph predictor in every run, under both fault types and at both run and service level %[id:saturation_hr_kill_run] %[id:saturation_hr_kill_service] %[id:saturation_hr_latency_run]
%[id:saturation_hr_kill_run] %[id:saturation_hr_kill_service] %[id:saturation_hr_latency_run].
Hotel Reservation is therefore tautological at the unit of analysis
%[id:saturation_hr_kill_tautological], and we report every Hotel Reservation result as
directional only. It can neither confirm the hypothesis nor disconfirm it.

Social Network is not fully saturated. Its run-level saturation is 0.909
%[id:saturation_sn_kill_run] under kill faults, which is why ρ is 0.785 %[id:primary_rho] and
not 1.0. Figure 1 shows the pattern. Ten of the eleven services lie exactly
on the line *y = x*. One departs from it: `user-service`, which has 4
%[id:userservice_ancestor_count] graph ancestors and registers 2 %[id:userservice_measured]
degraded ancestors in all five of its kill repetitions %[id:userservice_runs_departing]. The
empirical content of the Social Network correlation, as distinct from its definitional
content, rests on that one service.

We examined this with a leave-one-out recomputation that repeats the correlation eleven times,
withholding one service each time (Table 7, Figure 3). We designed this check after seeing the confirmatory results, so it is post hoc and carries no inferential weight.
Across the eleven recomputations ρ ranges from 0.696 %[id:loo_rho_min] to 1.000
%[id:loo_rho_max]. Withholding `user-service` gives ρ = 1.000 %[id:loo_userservice_rho], a
change of +0.215 %[id:loo_userservice_delta] that is 2.4 times %[id:loo_swing_ratio] the next
largest swing, −0.089 %[id:loo_second_largest_delta] for `compose-post-service`
%[id:loo_second_largest_service]. Only one exclusion moves the correlation much, and it is the one that removes the single service that stops the outcome from restating the predictor.

## 4.2 The hybrid criticality metric

The metric this work set out to evaluate combines inbound centrality with a fan-out-scaled
outbound term, on the assumption that a service calling many others matters because its failure breaks many downstream links. Our preregistered secondary hypothesis, H1b, was that this
premise points the wrong way and that the metric would correlate negatively with measured blast
radius.

Table 5 gives all four architecture-by-fault cells %[id:h1b_cells]. They are not independent.
The outcome vectors coincide across fault types %[id:replication_primary_identical], so the
cells contain 2 %[id:h1b_distinct_comparisons] distinct comparisons, one per architecture. The
correlation between `hybrid_criticality` and `ancestor_affected_count` is negative in every
cell %[id:h1b_all_negative]: ρ = −0.144 on Social Network under both kill %[id:h1b_sn_kill_rho]
and latency %[id:h1b_sn_latency_rho] faults, and ρ = −0.258 on Hotel Reservation
%[id:h1b_hr_kill_rho] %[id:h1b_hr_latency_rho]. After correction, no cell's correlation can be told apart from zero %[id:h1b_any_distinguishable] %[id:h1b_any_distinguishable]. The adjusted p-values are 0.9925
%[id:h1b_sn_kill_bh_p] and 0.9152 %[id:h1b_sn_latency_bh_p] on Social Network and 1.0000
%[id:h1b_hr_kill_bh_p] %[id:h1b_hr_latency_bh_p] on Hotel Reservation, and the Social Network
interval runs from −0.810 %[id:h1b_sn_kill_ci_lo] to 0.698 %[id:h1b_sn_kill_ci_hi].

So the hybrid metric has no detectable association with measured blast radius, even though every point estimate is negative. The direction preregistered under H1b appears
consistently, but its size cannot be separated from zero, and we make no claim of a negative
relationship.

## 4.3 The motivating case

The metric was first motivated by `compose-post-service`, the composition service of Social
Network, which calls 7 %[id:composepost_out_degree] services directly and has 10
%[id:composepost_descendants] transitive descendants. Because of that fan-out, the hybrid
metric ranks it first of the 11 %[id:composepost_set_size] analysed services
%[id:composepost_rank_hybrid], with a score of 0.302 %[id:composepost_hybrid]. By transitive
callers it ranks last %[id:composepost_rank_ancestor_count], having a single graph ancestor
%[id:composepost_ancestor_count]. Figure 2 shows the full rank inversion across the eleven
services.

Measurement sides with the caller-based ranking. Faulting `compose-post-service` left exactly
one degraded ancestor in every run. In each of its 5 %[id:composepost_kill_reps] kill
repetitions the minimum and maximum were both 1 %[id:composepost_kill_min]
%[id:composepost_kill_max], and the latency runs gave the same result
%[id:composepost_latency_mean] %[id:composepost_latency_min] %[id:composepost_latency_max]. A post-hoc breakdown shows that in all 10 %[id:composepost_runs_only_gateway_ancestor] %[id:composepost_runs_total] runs that ancestor was `nginx-web-server`, the gateway. The third kill repetition also recorded two degraded descendants %[id:descendant_affected_max_in_any_run] %[id:descendant_affected_exception_run],
the only such run in the campaign (§4.5). On the preregistered outcome, the service the
original metric rates most critical is the lowest in its application. That outcome counts
degraded services; it does not measure requests or functionality lost.

This is a worked case and not a general finding. It concerns one service in one application,
and the test across all eleven services, which could have generalised it, is the null result reported in §4.1.

## 4.4 Replication under a second fault type

The replication family repeats all 44 %[id:repl_family_size] tests on latency faults. As in
the confirmatory family, no test is significant after correction %[id:repl_family_significant].
The smallest uncorrected p-value is 0.0076 %[id:repl_best_raw_p], with an adjusted value of
0.1848 %[id:repl_best_bh_p].

The agreement between the families comes with a caveat. Under kill and latency faults, the service medians of `ancestor_affected_count` are the same in both architectures %[id:replication_primary_identical]
%[id:replication_primary_identical], and at run level the match is nearly as close: for 17 of
the 18 services %[id:fault_invariant_services_all] %[id:fault_invariant_services_all_total],
the five per-run counts are the same under both fault types. On the primary outcome, then, the latency family repeats the kill family's correlations on identical data, so the two cannot disagree. The replication adds no independent evidence
about the primary hypothesis.

Taken as a finding in its own right, this says that which services degrade when a given
service fails hardly depends on how it fails. A process that disappears and a process that
slows down reach the same neighbours. Recovery is a different matter. The correlation between
median recovery times under kill and under latency faults shows moderate agreement on Social
Network (0.384 %[id:trec_rho_between_faults_sn]) and strong agreement on Hotel Reservation
(0.857 %[id:trec_rho_between_faults_hr], n = 7 %[id:hr_services]). For recovery time the
replication remains informative, since there the two fault types give different values (§4.8).

## 4.5 Direction of propagation

Across the campaign, degradation travelled to callers and not to callees. No descendant of the
faulted service degraded in 179 of 180 runs %[id:descendant_affected_runs_zero]
%[id:descendant_affected_runs_zero_pct], and the service-level median, which is the unit of
analysis, is zero for each service under both fault types %[id:descendant_affected_count_distinct_values] %[id:descendant_affected_count_constant_at]
%[id:descendant_affected_count_distinct_values] %[id:descendant_affected_count_constant_at].
The single exception recorded two degraded descendants %[id:descendant_affected_runs_nonzero]
%[id:descendant_affected_max_in_any_run], in a Social Network `compose-post-service` kill
repetition %[id:descendant_affected_exception_run]. Services unrelated to the faulted node
behave the same way, with 179 of 180 runs at zero %[id:unrelated_affected_runs_zero] and one
exception %[id:unrelated_affected_exception_run].

This is the firmest structural result in the study, and it cannot be expressed as a
correlation. Neither outcome varies between services, so 88 %[id:expl_undefined] of the 154 %[id:expl_attempted] exploratory tests we attempted have no defined value. A constant outcome
does not give a weak correlation. It gives none. We report these tests as undefined, with the
reason, in the same way as the two degenerate predictors %[id:degenerate_pairs], and do not
enter them as zeros.

## 4.6 Exploratory findings

Of the 66 %[id:expl_testable] testable exploratory tests, 2 %[id:expl_significant] survive
correction within that family. Both concern the size of latency inflation under latency faults
on Social Network. Δp95 correlates with `hybrid_criticality` at ρ = 0.949
%[id:expl_sig_hybrid_criticality_rho] and with plain `degree` at ρ = 0.953
%[id:expl_sig_degree_rho], both with an adjusted p of 0.0033
%[id:expl_sig_hybrid_criticality_bh_p] %[id:expl_sig_degree_bh_p].

These results are exploratory and carry no confirmatory weight. Their outcome is not the one
H1b concerns. How much latency inflates is a different quantity from how many ancestors
degrade, and doing well on the first says nothing about the second, so this does not rescue
the hybrid metric. Plain degree centrality also does at least as well as the hybrid metric on
this outcome %[id:expl_sig_degree_rho] %[id:expl_sig_hybrid_criticality_rho], which gives no
reason to prefer the fan-out correction over the simpler measure.

## 4.7 What the design could have detected

Table 6 reproduces the preregistered power analysis against the realised analysis sets. Both sets have the registered size %[id:power_sn_n_matches] %[id:power_hr_n_matches] and the registered number of distinct predictor levels %[id:power_sn_levels_match] %[id:power_hr_levels_match], and the ceiling correlations come out exactly as preregistered %[id:power_sn_ceiling_matches] %[id:power_hr_ceiling_matches]
%[id:power_sn_ceiling_matches] %[id:power_hr_ceiling_matches].

Those ceilings limit what the study could ever show. `ancestor_count` takes only 4
%[id:power_sn_levels] distinct values across the 11 %[id:power_sn_n] Social Network services
and 2 %[id:power_hr_levels] across the 7 %[id:power_hr_n] Hotel Reservation services, and the
ties cap the attainable correlation at 0.941 %[id:power_sn_ceiling] and 0.791
%[id:power_hr_ceiling] respectively. For Hotel Reservation the effect is severe. Under the
exact permutation test the plan mandates, the best attainable p-value is 0.0952
%[id:power_hr_ceiling_p], above the conventional threshold before any correction. The
preregistration quoted p = 0.034 %[id:power_hr_prereg_stated_p] for this ceiling, which is the
asymptotic value (Deviation 7); the exact value the plan requires is 0.0952
%[id:power_hr_ceiling_p]. Hotel Reservation could not have reached nominal significance for
this predictor whatever outcome we observed. That follows from its tie structure and sample
size, not from anything we measured.

## 4.8 Recovery time

No run was censored %[id:campaign_runs_censored], so under the preregistered rule the Spearman
rank test is the primary test for recovery time and the survival models are secondary
(Deviation 6). Each family contains 22 recovery-time tests %[id:trec_conf_tests]
%[id:trec_repl_tests], corrected within the family together with the primary-outcome tests.

For `ancestor_count` on Social Network, ρ = −0.356 %[id:trec_conf_sn_ancestor_rho] under kill
faults (uncorrected p = 0.2807 %[id:trec_conf_sn_ancestor_p], adjusted 0.9264
%[id:trec_conf_sn_ancestor_bh_p]) and −0.060 %[id:trec_repl_sn_ancestor_rho] under latency
faults (p = 0.8647 %[id:trec_repl_sn_ancestor_p], adjusted 1.0000
%[id:trec_repl_sn_ancestor_bh_p]). On Hotel Reservation, reported as directional only,
ρ = −0.158 under both fault types %[id:trec_conf_hr_ancestor_rho]
%[id:trec_repl_hr_ancestor_rho] (p = 0.8571 %[id:trec_conf_hr_ancestor_p]
%[id:trec_repl_hr_ancestor_p]; adjusted 0.9925 %[id:trec_conf_hr_ancestor_bh_p] and 1.0000
%[id:trec_repl_hr_ancestor_bh_p]). For `hybrid_criticality` on Social Network, ρ = 0.098
%[id:trec_conf_sn_hybrid_rho] under kill faults (p = 0.7699 %[id:trec_conf_sn_hybrid_p],
adjusted 0.9925 %[id:trec_conf_sn_hybrid_bh_p]) and 0.767 %[id:trec_repl_sn_hybrid_rho] under
latency faults (p = 0.0084 %[id:trec_repl_sn_hybrid_p], adjusted 0.1848
%[id:trec_repl_sn_hybrid_bh_p]). On Hotel Reservation it is 0.204 %[id:trec_conf_hr_hybrid_rho]
under kill faults (p = 0.8571 %[id:trec_conf_hr_hybrid_p], adjusted 0.9925
%[id:trec_conf_hr_hybrid_bh_p]) and 0.408 %[id:trec_repl_hr_hybrid_rho] under latency faults
(p = 0.5714 %[id:trec_repl_hr_hybrid_p], adjusted 0.8111 %[id:trec_repl_hr_hybrid_bh_p]). No
recovery-time test is significant after correction in either family %[id:trec_conf_significant]
%[id:trec_repl_significant].

The Cox and log-rank results below are secondary and not corrected for multiplicity. Hazard
ratios are per unit of `ancestor_count`. With standard errors clustered by service, the run-level hazard ratio for `ancestor_count` on Social Network is 1.173
%[id:trec_conf_sn_ancestor_cox_run_hr] (95% %[id:cox_ci_level_pct] CI 0.876
%[id:trec_conf_sn_ancestor_cox_run_ci_lo] to 1.570 %[id:trec_conf_sn_ancestor_cox_run_ci_hi],
p = 0.2836 %[id:trec_conf_sn_ancestor_cox_run_p]) under kill faults and 0.998
%[id:trec_repl_sn_ancestor_cox_run_hr] (0.816 %[id:trec_repl_sn_ancestor_cox_run_ci_lo] to
1.221 %[id:trec_repl_sn_ancestor_cox_run_ci_hi], p = 0.9859
%[id:trec_repl_sn_ancestor_cox_run_p]) under latency faults. On Hotel Reservation it is 1.522
%[id:trec_conf_hr_ancestor_cox_run_hr] (1.067 %[id:trec_conf_hr_ancestor_cox_run_ci_lo] to
2.171 %[id:trec_conf_hr_ancestor_cox_run_ci_hi], p = 0.0204
%[id:trec_conf_hr_ancestor_cox_run_p]) under kill faults and 0.882
%[id:trec_repl_hr_ancestor_cox_run_hr] (0.578 %[id:trec_repl_hr_ancestor_cox_run_ci_lo] to
1.346 %[id:trec_repl_hr_ancestor_cox_run_ci_hi], p = 0.5609
%[id:trec_repl_hr_ancestor_cox_run_p]) under latency faults. At service level the hazard ratios
are 1.479 %[id:trec_conf_sn_ancestor_cox_service_hr] (0.688
%[id:trec_conf_sn_ancestor_cox_service_ci_lo] to 3.181
%[id:trec_conf_sn_ancestor_cox_service_ci_hi], p = 0.3163
%[id:trec_conf_sn_ancestor_cox_service_p]) and 1.184 %[id:trec_repl_sn_ancestor_cox_service_hr]
(0.627 %[id:trec_repl_sn_ancestor_cox_service_ci_lo] to 2.236
%[id:trec_repl_sn_ancestor_cox_service_ci_hi], p = 0.6018
%[id:trec_repl_sn_ancestor_cox_service_p]) on Social Network under kill and latency faults, and
2.179 %[id:trec_conf_hr_ancestor_cox_service_hr] %[id:trec_repl_hr_ancestor_cox_service_hr]
(0.302 %[id:trec_conf_hr_ancestor_cox_service_ci_lo] to 15.722
%[id:trec_conf_hr_ancestor_cox_service_ci_hi], p = 0.4399
%[id:trec_conf_hr_ancestor_cox_service_p] %[id:trec_repl_hr_ancestor_cox_service_p]) on Hotel
Reservation under both. The log-rank test across predictor terciles gives p = 0.5154
%[id:trec_conf_sn_ancestor_logrank_p] and 0.5561 %[id:trec_repl_sn_ancestor_logrank_p] for
`ancestor_count` on Social Network under kill and latency faults, and 0.2099
%[id:trec_conf_sn_hybrid_logrank_p] and 0.1099 %[id:trec_repl_sn_hybrid_logrank_p] for
`hybrid_criticality`. It is undefined for 10 of the 22 recovery-time tests in each family
%[id:trec_conf_logrank_undefined] %[id:trec_repl_logrank_undefined], including `ancestor_count`
on Hotel Reservation, where the predictor has fewer than two distinct terciles.
