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

The campaign completed all 180 %[id:campaign_runs_total] planned runs across 36
%[id:campaign_cells] fully balanced cells, with no run lost to telemetry failure
%[id:campaign_runs_failed], no gateway service faulted %[id:campaign_gateway_runs], and
every recovery time observed rather than censored %[id:campaign_runs_censored]. Tables 1
and 2 give the per-service graph predictors alongside the measured outcomes for Social
Network and Hotel Reservation.

## 4.1 The confirmatory test

Our primary hypothesis was that a service's transitive caller count predicts the number of
services degraded by its failure. On Social Network under kill faults, the correlation
between `ancestor_count` and measured `ancestor_affected_count` is ρ = 0.785
%[id:primary_rho] across 11 %[id:primary_n_services] services, with a bias-corrected and
accelerated bootstrap interval of [0.000, 1.000] %[id:primary_ci_lo] %[id:primary_ci_hi]
%[id:primary_ci_method]. The uncorrected permutation p-value is 0.0080
%[id:primary_p_locked]. After Benjamini–Hochberg correction across the 44
%[id:conf_family_size] tests in the confirmatory family, the adjusted p-value is 0.3451
%[id:primary_p_bh_locked].

**None of the 44 confirmatory tests is significant at q = 0.05**
%[id:conf_family_significant] %[id:fdr_q]. The primary test carries the smallest
uncorrected p-value in the family %[id:conf_best_raw_p] %[id:conf_best_predictor], and its
adjusted value sits roughly an order of magnitude above the threshold. Table 3 gives the
primary predictor–outcome test in each family and architecture; Table 4 summarises both
families. We state the result plainly: the preregistered hypothesis is not confirmed. The
point estimate is large and positive, and we report it as such, but the correction we
committed to in advance rejects it, and the confidence interval spans the entire admissible
range.

Two features of the data qualify that number further, and both matter more than the p-value
does.

The first is saturation. If every service's measured blast radius simply equalled its graph
ancestor count, a correlation of 1.0 would follow by construction and would test nothing. On
Hotel Reservation this is exactly the case: the measured outcome equals the graph predictor
for every service in every run, under both fault types and at both the run and service level
%[id:saturation_hr_kill_run] %[id:saturation_hr_kill_service]
%[id:saturation_hr_latency_run]. Hotel Reservation is therefore tautological at the analysis
unit %[id:saturation_hr_kill_tautological], and we report every Hotel Reservation result in
this paper as directional only. It cannot confirm the hypothesis and it cannot disconfirm
it.

Social Network is not fully saturated, at 0.909 %[id:saturation_sn_kill_run] under kill
faults, which is what makes ρ = 0.785 rather than 1.0. Figure 1 shows why. Ten of the eleven
services lie exactly on the line *y = x*, and a single service departs from it:
`user-service`, which has 4 %[id:userservice_ancestor_count] graph ancestors but registers 2
%[id:userservice_measured] degraded ancestors, in all five of its kill repetitions
%[id:userservice_runs_departing]. The entire empirical content of the Social Network
correlation, as opposed to its definitional content, rests on the behaviour of that one
service.

We examined this directly with a leave-one-out recomputation, repeating the correlation
eleven times with one service withheld each time (Table 7, Figure 3). We report this as a
**post-hoc robustness check specified after the confirmatory results were known**; it
carries no inferential weight and is not part of the preregistered family. Across the eleven
recomputations ρ ranges from 0.696 %[id:loo_rho_min] to 1.000 %[id:loo_rho_max]. Withholding
`user-service` produces ρ = 1.000 %[id:loo_userservice_rho], a change of +0.215
%[id:loo_userservice_delta] and 2.4 times %[id:loo_swing_ratio] larger than the next largest
swing, which comes from `compose-post-service` at −0.089 %[id:loo_second_largest_delta]
%[id:loo_second_largest_service]. The correlation is thus stable under every exclusion
except the one that removes the only service preventing the outcome from restating the
predictor.

## 4.2 The hybrid criticality metric

The metric this work set out to evaluate combines inbound centrality with a fan-out-scaled
outbound term, on the premise that a service with many callees is critical because its
failure severs many downstream relationships. Our preregistered secondary hypothesis, H1b,
was that this fan-out premise is not merely unhelpful but directionally wrong, and that the
metric would correlate negatively with measured blast radius.

Table 5 gives all four architecture-by-fault cells %[id:h1b_cells]. The correlation between
`hybrid_criticality` and `ancestor_affected_count` is negative in every one
%[id:h1b_all_negative]: ρ = −0.144 on Social Network under both kill
%[id:h1b_sn_kill_rho] and latency %[id:h1b_sn_latency_rho] faults, and ρ = −0.258 on Hotel
Reservation %[id:h1b_hr_kill_rho] %[id:h1b_hr_latency_rho]. In none of the four cells is the
correlation distinguishable from zero after correction
%[id:h1b_any_distinguishable]; the adjusted p-values are 0.9925
%[id:h1b_sn_kill_bh_p] and 0.9152 %[id:h1b_sn_latency_bh_p] on Social Network and 1.0000
%[id:h1b_hr_kill_bh_p] %[id:h1b_hr_latency_bh_p] on Hotel Reservation, and the Social
Network interval runs from −0.810 %[id:h1b_sn_kill_ci_lo] to 0.698
%[id:h1b_sn_kill_ci_hi].

The careful statement is therefore this. The hybrid metric shows **no detectable association
with measured blast radius**, with a negative point estimate in every cell we examined. We
do not claim that it is anti-predictive: that would assert a negative relationship the data
cannot distinguish from no relationship at all. The direction preregistered under H1b is
observed consistently, and the magnitude is not separable from zero.

## 4.3 The motivating case

The metric was originally motivated by `compose-post-service`, Social Network's composition
service, which calls 7 %[id:composepost_out_degree] services directly and has 10
%[id:composepost_descendants] transitive descendants. On its fan-out, the hybrid metric
ranks it the most critical of the 11 %[id:composepost_set_size] services in the analysis set
%[id:composepost_rank_hybrid], with a score of 0.302 %[id:composepost_hybrid]. On transitive
callers it ranks last %[id:composepost_rank_ancestor_count], having a single graph ancestor
%[id:composepost_ancestor_count]. Figure 2 shows the full rank inversion across all eleven
services.

Measurement resolves the disagreement in favour of the caller-based ranking. Killing
`compose-post-service` degrades exactly 1 service in every one of its 5
%[id:composepost_kill_reps] kill repetitions, with a minimum and maximum of 1
%[id:composepost_kill_min] %[id:composepost_kill_max] and hence zero variance, and the
latency condition reproduces this exactly %[id:composepost_latency_mean]
%[id:composepost_latency_min] %[id:composepost_latency_max]. The service the original metric
identifies as the most critical in the application is, by measurement, among the least
consequential to fail.

We present this as a worked case and not as a general finding. It concerns one service in
one application, and the eleven-service correlation that would generalise it is the null
result of §4.1.

## 4.4 Replication under a second fault type

The replication family repeats all 44 %[id:repl_family_size] tests on latency faults. As in
the confirmatory family, no test is significant after correction
%[id:repl_family_significant], the smallest uncorrected p-value being 0.0076
%[id:repl_best_raw_p] and its adjusted value 0.1848 %[id:repl_best_bh_p].

The agreement between the two families needs a caveat rather than a celebration, and it is
the more interesting result of the two. The median `ancestor_affected_count` vector is
**identical** between kill and latency faults in both architectures
%[id:replication_primary_identical]. At run level the correspondence is nearly as tight: for
17 of 18 services %[id:fault_invariant_services_all] %[id:fault_invariant_services_all_total]
the full set of five per-run counts is the same under both fault types. The latency family
is therefore correlating the same outcome values against the same predictors as the kill
family, and the two cannot disagree about the primary outcome. The replication supplies no
independent evidence about the primary hypothesis.

Read as a finding rather than as a limitation, this says something worth stating: which
services degrade when a given service fails is essentially invariant to *how* that service
fails. A process that vanishes and a process that becomes slow propagate to the same
neighbours. The invariance does not extend to recovery, where the two fault types diverge
substantially; the correlation between kill and latency median recovery times is 0.384
%[id:trec_rho_between_faults_sn] on Social Network and 0.857
%[id:trec_rho_between_faults_hr] on Hotel Reservation. The replication remains informative
for recovery time, where the fault types genuinely differ.

## 4.5 Direction of propagation

Across the campaign, degradation travels to callers and not to callees. No descendant of a
faulted service was degraded in 179 of 180 runs %[id:descendant_affected_runs_zero]
%[id:descendant_affected_runs_zero_pct], and the service-level median, which is the unit of
analysis, is zero for every service in every condition
%[id:descendant_affected_count_distinct_values] %[id:descendant_affected_count_constant_at].
The single exception recorded two degraded descendants
%[id:descendant_affected_runs_nonzero] %[id:descendant_affected_max_in_any_run], in a
Social Network `compose-post-service` kill repetition
%[id:descendant_affected_exception_run]. Services unrelated to the faulted node behave the
same way, with 179 of 180 runs at zero %[id:unrelated_affected_runs_zero] and one exception
%[id:unrelated_affected_exception_run].

This is the most robust structural result in the study, and it is worth noting that it
cannot be expressed as a correlation. Because both outcomes have no variance at the service
level, 88 %[id:expl_undefined] of the 154 %[id:expl_attempted] attempted exploratory tests
are undefined rather than null. A constant outcome does not yield a weak correlation; it
yields no correlation at all. We report these as undefined, with the reason, in the same way
we report the two degenerate predictors %[id:degenerate_pairs], rather than entering them as
zeros.

## 4.6 Exploratory findings

Of the 66 %[id:expl_testable] testable exploratory tests, 2 %[id:expl_significant] survive
correction within that family. Both concern the *magnitude* of latency inflation under
latency faults on Social Network: Δp95 correlates with `hybrid_criticality` at ρ = 0.949
%[id:expl_sig_hybrid_criticality_rho] and with raw `degree` at ρ = 0.953
%[id:expl_sig_degree_rho], both at an adjusted p of 0.0033
%[id:expl_sig_hybrid_criticality_bh_p] %[id:expl_sig_degree_bh_p].

We label these exploratory and attach no confirmatory weight to them. Two caveats are
necessary. The outcome here is not the outcome H1b concerns: how much latency inflates is a
different quantity from how many ancestors degrade, and a metric performing well on the
former says nothing about the latter. This result does not rescue the hybrid metric. The
second caveat is that plain degree centrality performs at least as well as the hybrid metric
on this outcome %[id:expl_sig_degree_rho] %[id:expl_sig_hybrid_criticality_rho], so the
finding gives no reason to prefer the fan-out correction over a considerably simpler
measure.

## 4.7 What the design could have detected

Table 6 reproduces the preregistered power analysis against the realised analysis sets. Both
match what was registered in size %[id:power_sn_n_matches] %[id:power_hr_n_matches] and in
the number of distinct predictor levels %[id:power_sn_levels_match]
%[id:power_hr_levels_match], and the preregistered ceiling correlations reproduce exactly
%[id:power_sn_ceiling_matches] %[id:power_hr_ceiling_matches].

Those ceilings bound what the study could ever have shown. Because `ancestor_count` takes
only 4 %[id:power_sn_levels] distinct values across 11 %[id:power_sn_n] Social Network
services and 2 %[id:power_hr_levels] across 7 %[id:power_hr_n] Hotel Reservation services,
ties cap the attainable correlation at 0.941 %[id:power_sn_ceiling] and 0.791
%[id:power_hr_ceiling] respectively. For Hotel Reservation the consequence is severe: under
the exact permutation test our plan mandates, the best attainable p-value is 0.0952
%[id:power_hr_ceiling_p], which is above the conventional threshold before any correction is
applied. Hotel Reservation could not have reached nominal significance for this predictor at
any observed outcome whatsoever. This is a property of its tie structure and sample size,
not of anything we measured.
