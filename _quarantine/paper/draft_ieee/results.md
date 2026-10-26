# V. Results

> **Drafting note (not rendered).** Trailing `%[id:...]` markers name the paper/numbers.csv
> claim_id of each number; float numbers resolve through paper/draft_ieee/floats.md.

## A. Campaign Completion

All 180 %[id:campaign_runs_total] planned runs completed, across 36 %[id:campaign_cells]
balanced cells. No run was lost to telemetry failure %[id:campaign_runs_failed], no gateway was
faulted %[id:campaign_gateway_runs], and every recovery time was observed
%[id:campaign_runs_censored]. Table 3 and Table 4 list the graph predictors and measured outcomes
for each service in Social Network and Hotel Reservation.

## B. The Confirmatory Test of H1

H1 replaced the original fan-out hypothesis after the pilot %[prereg:§1]. On Social Network under
kill faults, the caller count *X* and the measured number of degraded callers *Y* correlate at
ρ = 0.785
%[id:primary_rho] across 11 %[id:primary_n_services] services, with a bias-corrected and
accelerated bootstrap interval of [0.000, 1.000] %[id:primary_ci_lo] %[id:primary_ci_hi]
%[id:primary_ci_method]. The uncorrected permutation p-value, from 10,000
%[id:primary_n_permutations] Monte-Carlo permutations, is 0.0080 %[id:primary_p_locked]. After Benjamini-Hochberg correction across the 44
%[id:conf_family_size] tests of the confirmatory family, the adjusted p-value is 0.3451
%[id:primary_p_bh_locked]. Exact enumeration, run after the results were known (Deviation 9),
gives 0.006926 %[id:primary_p_exact] uncorrected and 0.3048 %[id:primary_p_bh_exact] adjusted,
and the verdict is unchanged %[id:primary_significant_exact].^[The locked Monte Carlo values
above remain the preregistered result.]

At q = 0.05 %[id:fdr_q], not one of the 44 confirmatory tests is significant
%[id:conf_family_significant]. The primary test has the smallest uncorrected p-value in the family
%[id:conf_best_raw_p] %[id:conf_best_predictor], and its adjusted value is about 6.9
%[id:primary_p_bh_over_q] times the threshold. Table 6 gives the primary test in each family and
architecture, and Table 7 summarises both families. H1 is not confirmed. The point estimate is
large and positive, the correction fixed in advance rejects it, and the confidence interval runs
from no association to a perfect one.

Two features of the data qualify that estimate further, and they matter more than the p-value.

The first is saturation. If every service's measured blast radius equalled its graph ancestor
count, a correlation of 1.0 would follow by construction and would test nothing. On Hotel
Reservation that is exactly what happened: each service's measured outcome matched its graph
predictor in every run, under both fault types and at both run and service level
%[id:saturation_hr_kill_run] %[id:saturation_hr_kill_service] %[id:saturation_hr_latency_run].
Hotel Reservation is therefore tautological at the unit of analysis
%[id:saturation_hr_kill_tautological], and every Hotel Reservation result is reported as
directional only. It can neither confirm the hypothesis nor disconfirm it.

Social Network is not fully saturated. Its run-level saturation is 0.909
%[id:saturation_sn_kill_run] under kill faults, which is why ρ is 0.785 %[id:primary_rho] and not
1.0. Figure 6 shows the pattern. Ten of the eleven services lie exactly on the line *y = x*. One
departs from it: user-service, which has 4 %[id:userservice_ancestor_count] graph ancestors and
registers 2 %[id:userservice_measured] degraded ancestors in all five of its kill repetitions
%[id:userservice_runs_departing]. The empirical content of the Social Network correlation, as
distinct from its definitional content, rests on that one service.

A leave-one-out recomputation, designed after the confirmatory results were known and so
carrying no inferential weight, withholds one service at a time (Figure 7): ρ ranges from
0.696 %[id:loo_rho_min] to 1.000 %[id:loo_rho_max], and the value of 1.000
%[id:loo_userservice_rho] comes from withholding user-service, the one service that stops the
outcome from restating the predictor.

## C. The Hybrid Metric and H2

The metric this work set out to evaluate combines inbound centrality with a fan-out-scaled
outbound term, on the assumption that a service calling many others matters because its failure
breaks many downstream links. H2 (H1b in the preregistration) expected this premise to point the
wrong way.

Table 9 gives all four architecture-by-fault cells %[id:h1b_cells]. They are not independent. The
outcome vectors coincide across fault types %[id:replication_primary_identical], so the cells
contain 2 %[id:h1b_distinct_comparisons] distinct comparisons, one per architecture. The
correlation between the hybrid metric and *Y* is negative in every cell
%[id:h1b_all_negative]: ρ = −0.144 on Social Network under both kill %[id:h1b_sn_kill_rho] and
latency %[id:h1b_sn_latency_rho] faults, and ρ = −0.258 on Hotel Reservation %[id:h1b_hr_kill_rho]
%[id:h1b_hr_latency_rho]. After correction, no cell's correlation can be told apart from zero
%[id:h1b_any_distinguishable]. The adjusted p-values are 0.9925 %[id:h1b_sn_kill_bh_p] and 0.9152
%[id:h1b_sn_latency_bh_p] on Social Network and 1.0000 %[id:h1b_hr_kill_bh_p]
%[id:h1b_hr_latency_bh_p] on Hotel Reservation, and the Social Network interval runs from −0.810
%[id:h1b_sn_kill_ci_lo] to 0.698 %[id:h1b_sn_kill_ci_hi].

So the hybrid metric has no detectable association with measured blast radius, even though every
point estimate is negative. The direction stated by H2 appears consistently, but its size cannot
be separated from zero, and no negative relationship is claimed.

## D. The Motivating Case

The metric was first motivated by compose-post-service, the composition service of Social
Network, which calls 7 %[id:composepost_out_degree] services directly and has 10
%[id:composepost_descendants] transitive descendants. Because of that fan-out, the hybrid metric
ranks it first of the 11 %[id:composepost_set_size] analysed services
%[id:composepost_rank_hybrid], with a score of 0.302 %[id:composepost_hybrid]. By transitive
callers it ranks last %[id:composepost_rank_ancestor_count], having a single graph ancestor
%[id:composepost_ancestor_count]. Figure 8 shows the full rank inversion across the eleven
services.

Measurement sides with the caller-based ranking. Faulting compose-post-service left exactly one
degraded ancestor in every run. In each of its 5 %[id:composepost_kill_reps] kill repetitions the
minimum and maximum were both 1 %[id:composepost_kill_min] %[id:composepost_kill_max], and the
latency runs gave the same result %[id:composepost_latency_mean] %[id:composepost_latency_min]
%[id:composepost_latency_max]. A post hoc breakdown shows that in all 10
%[id:composepost_runs_only_gateway_ancestor] %[id:composepost_runs_total] runs that ancestor was
nginx-web-server, the gateway. The third kill repetition also recorded two degraded descendants
%[id:descendant_affected_max_in_any_run] %[id:descendant_affected_exception_run], the only such
run in the campaign (Section V-F). On the preregistered outcome, the service the original metric
rates most critical is the lowest in its application. That outcome counts degraded services; it
does not measure requests or functionality lost.

This is a worked case and not a general finding. It concerns one service in one application, and
the test across all eleven services, which could have generalised it, is the null result of
Section V-B.

## E. Replication under a Second Fault Type

The replication family repeats all 44 %[id:repl_family_size] tests on latency faults. As in the
confirmatory family, no test is significant after correction %[id:repl_family_significant]. The
smallest uncorrected p-value is 0.0076 %[id:repl_best_raw_p], with an adjusted value of 0.1848
%[id:repl_best_bh_p].

The agreement between the families comes with a caveat. Under kill and latency faults, the
service medians of *Y* are the same in both architectures
%[id:replication_primary_identical], and at run level the match is nearly as close: for 17 of the
18 services %[id:fault_invariant_services_all] %[id:fault_invariant_services_all_total], the five
per-run counts are the same under both fault types. On the primary outcome, then, the latency
family repeats the kill family's correlations on identical data, so the two cannot disagree. The
replication adds no independent evidence about the primary hypothesis.

Taken as a finding in its own right, this says that which services degrade when a given service
fails hardly depends on how it fails. A process that disappears and a process that slows down
reach the same neighbours. Recovery is a different matter. The correlation between median
recovery times under kill and under latency faults shows moderate agreement on Social Network
(0.384 %[id:trec_rho_between_faults_sn]) and strong agreement on Hotel Reservation (0.857
%[id:trec_rho_between_faults_hr], n = 7 %[id:hr_services]). For recovery time the replication
remains informative, since there the two fault types give different values (Section V-I).

## F. Direction of Propagation

Across the campaign, degradation travelled to callers and not to callees. No descendant of the
faulted service degraded in 179 of 180 runs %[id:descendant_affected_runs_zero]
%[id:descendant_affected_runs_zero_pct], and the service-level median, which is the unit of
analysis, is zero for each service under both fault types
%[id:descendant_affected_count_distinct_values] %[id:descendant_affected_count_constant_at]. The
single exception recorded two degraded descendants %[id:descendant_affected_runs_nonzero]
%[id:descendant_affected_max_in_any_run], in a Social Network compose-post-service kill
repetition %[id:descendant_affected_exception_run]. Services unrelated to the faulted node behave
the same way, with 179 of 180 runs at zero %[id:unrelated_affected_runs_zero] and one exception
%[id:unrelated_affected_exception_run].

This is the firmest structural result in the study, and it cannot be expressed as a correlation.
Neither outcome varies between services, so 88 %[id:expl_undefined] of the 154
%[id:expl_attempted] exploratory tests attempted have no defined value. A constant outcome does
not give a weak correlation. It gives none. These tests are reported as undefined, with the
reason, in the same way as the two degenerate predictors %[id:degenerate_pairs], and are not
entered as zeros.

## G. Exploratory Findings

Of the 66 %[id:expl_testable] testable exploratory tests, 2 %[id:expl_significant] survive
correction within that family. Both concern the size of latency inflation under latency faults on
Social Network. Δp95 correlates with the hybrid metric at ρ = 0.949 %[id:expl_sig_hybrid_criticality_rho] and
with plain degree at ρ = 0.953
%[id:expl_sig_degree_rho], both with an adjusted p of 0.0033
%[id:expl_sig_hybrid_criticality_bh_p] %[id:expl_sig_degree_bh_p].

These results are exploratory and carry no confirmatory weight. Their outcome is not the one H2
concerns. How much latency inflates is a different quantity from how many ancestors degrade, and
doing well on the first says nothing about the second, so this does not rescue the hybrid
metric. Plain degree centrality also does at least as well as the hybrid metric on this outcome
%[id:expl_sig_degree_rho] %[id:expl_sig_hybrid_criticality_rho], which gives no reason to prefer
the fan-out correction over the simpler measure.

## H. What the Design Could Have Detected

Table 10 reproduces the preregistered power analysis against the realised analysis sets. Both
sets have the registered size %[id:power_sn_n_matches] %[id:power_hr_n_matches] and the
registered number of distinct predictor levels %[id:power_sn_levels_match]
%[id:power_hr_levels_match], and the ceiling correlations come out exactly as preregistered
%[id:power_sn_ceiling_matches] %[id:power_hr_ceiling_matches].

Those ceilings limit what the study could ever show. The caller count *X* takes only 4
%[id:power_sn_levels] distinct values across the 11 %[id:power_sn_n] Social Network services and
2 %[id:power_hr_levels] across the 7 %[id:power_hr_n] Hotel Reservation services, and the ties cap
the attainable correlation at 0.941 %[id:power_sn_ceiling] and 0.791 %[id:power_hr_ceiling]
respectively. For Hotel Reservation the effect is severe. Under the exact permutation test the
plan mandates, the best attainable p-value is 0.0952 %[id:power_hr_ceiling_p], above the
conventional threshold before any correction. The preregistration quoted p = 0.034
%[id:power_hr_prereg_stated_p] for this ceiling, which is the asymptotic value (Deviation 7); the
exact value the plan requires is 0.0952 %[id:power_hr_ceiling_p]. Hotel Reservation could not
have reached nominal significance for this predictor whatever outcome was observed. That follows
from its tie structure and sample size, not from anything measured.

## I. Recovery Time

No run was censored %[id:campaign_runs_censored], so under the preregistered rule the Spearman
rank test is the primary test for recovery time, and the Cox and log-rank models are secondary
and uncorrected (Deviation 6). Table 11 gives all three for both predictors. No recovery-time
test is significant after correction in either family %[id:trec_conf_significant]
%[id:trec_repl_significant]. The log-rank test is undefined for 10 of the 22 recovery-time tests
in each family %[id:trec_conf_logrank_undefined] %[id:trec_repl_logrank_undefined]
%[id:trec_conf_tests] %[id:trec_repl_tests], including *X* on Hotel Reservation,
where the predictor has fewer than two distinct terciles. Supplementary file S2 gives the
unrounded estimates.

## J. Post Hoc Weight Sensitivity

The confirmatory results were already known when this analysis was specified and run, and it
belongs to no preregistered family. It asks how much the hybrid metric's association with the outcome
depends on its weights. The metric was recomputed for all 231 %[id:ws_triplets] weight triplets
on the preregistered grid, with step 0.05 %[id:ws_grid_step] and weights summing to one, using
the same code, the same service medians and the same permutation tests. Each set of 231 tests was
corrected with the Benjamini-Hochberg procedure within that set. No triplet was selected or
adopted, and every other result in this paper uses the reported weights. Table 12 and Figure 9
give the full distribution.

Against the number of degraded callers *Y* on Social Network, ρ ranged from −0.544
%[id:ws_sn_kill_anc_rho_min] to 0.337 %[id:ws_sn_kill_anc_rho_max], with a median of −0.167
%[id:ws_sn_kill_anc_rho_median]. It was positive for 28 %[id:ws_sn_kill_anc_triplets_rho_positive]
of the 231 triplets. No triplet reached an uncorrected p below 0.05 %[id:fdr_q]
%[id:ws_sn_kill_anc_triplets_p_raw_below_05], the smallest being 0.0952
%[id:ws_sn_kill_anc_p_raw_min], and none survived correction
%[id:ws_sn_kill_anc_triplets_significant_bh]. Kill and latency faults gave identical results
%[id:ws_anc_identical_across_faults], because the service medians coincide. On Hotel Reservation
every triplet with a defined correlation gave ρ = −0.258 %[id:ws_hr_kill_anc_rho_min]
%[id:ws_hr_kill_anc_rho_max], 230 %[id:ws_hr_kill_anc_triplets_defined] in all, because the
in-degree-only weighting leaves the metric constant there %[id:ws_hr_kill_anc_triplets_undefined].
The reported weights gave ρ = −0.144 %[id:ws_sn_kill_anc_reported_rho] on Social Network, and 47
%[id:ws_sn_kill_anc_triplets_rho_above_reported] triplets gave a larger value. The null result for
H2 therefore does not depend on the inherited weights: no weighting on the grid produced a
significant association with degraded callers in either direction.

Against the gateway's error rate under kill faults, an exploratory outcome, the picture on Social
Network differs. ρ was positive for all 231 %[id:ws_sn_kill_err_triplets_rho_positive] triplets,
from 0.229 %[id:ws_sn_kill_err_rho_min] to 0.832 %[id:ws_sn_kill_err_rho_max] with a median of
0.753 %[id:ws_sn_kill_err_rho_median]. Of these, 145 %[id:ws_sn_kill_err_triplets_p_raw_below_05] had uncorrected p-values under 0.05
%[id:fdr_q], and 128 %[id:ws_sn_kill_err_triplets_significant_bh] remained significant after
correction within the 231; the p-values come from 10,000 %[id:ws_mc_permutations] random
permutations, because this outcome has too many distinct orderings to enumerate. At the
reported weights ρ was 0.786 %[id:ws_sn_kill_err_reported_rho]. The largest value, 0.832
%[id:ws_sn_kill_err_rho_max], is the best of 231 tries on one dataset and not a finding. On
Hotel Reservation every defined triplet gave ρ = −0.204 %[id:ws_hr_kill_err_rho_min] and none was
significant %[id:ws_hr_kill_err_triplets_significant_bh]. At the reported weights, the preregistered exploratory test of this association did not
survive the correction applied across its exploratory family (adjusted p = 0.0913
%[id:uf_test_sn_hybrid_bh_p]), and Section VI-C shows that this association follows
the metric's in-degree term.

## K. Verification

Two checks beyond the preregistered analysis are reported as supplementary. One is the post hoc
leave-one-out recomputation of Section V-B. The other is an independent reimplementation of the
primary statistic, written without reference to the analysis code and reading only the persisted
spans and the dependency graph. It reproduces the reported correlation %[id:primary_rho_full] and
agrees with the stored per-run outcomes on which services were affected, not only how many, in
all 110 %[id:sn_runs] Social Network runs. That shows the analysis code is faithful to its data.
Whether the definitions of Sections IV-G and IV-H are the right ones is a question no
recomputation can settle.
