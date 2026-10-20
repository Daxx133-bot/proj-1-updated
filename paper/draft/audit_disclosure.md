# 7. Audit and Deviations from Preregistration

> **Drafting note (strip before submission).** Trailing `%[id:...]` comments name the
> `paper/numbers.csv` claim_id each number comes from. Table 8 is
> `paper/tables/tbl_deviations.csv`.

## 7.1 Why this study was rebuilt

An earlier version of this work went to project review. A later self-audit of its pipeline
found that some reported results had not come from measurement. Impact values and recovery times presented as experimental findings were random values drawn from ranges selected according to each service's centrality rank, so the metric agreed with them by construction %[src:_audit/AUDIT_REPORT.md finding 1]. The metric weights behind the headline correlation had also been chosen by a grid search that maximised that same correlation on the same outcome, with no held-out data. A
result produced that way is the best of many tries reported as one test.

We withdrew those results in full. The affected scripts and outputs were moved, not deleted,
into a quarantine directory that now holds 13 %[id:quarantine_items] numbered items, each with
a note of what was removed and why. We then rebuilt the pipeline from measurement through to analysis, and everything reported
here comes from a new campaign. Two
rules follow from that history. Each reported number comes from a script that reads logged data, and any value we cannot trace to a script and an input file is marked as missing. The
analysis was also locked before the campaign, and every later change is logged with its date
and with whether campaign data had been analysed by then.

One element was carried over. The hybrid metric's weights of 0.4 %[id:hybrid_w_in], 0.4
%[id:hybrid_w_out] and 0.2 %[id:hybrid_w_btw] come from the original proposal, where an
empirical search had selected them. They were left as they were for the campaign %[id:hybrid_weights_reoptimised_on_campaign], and the preregistered tuning on Social Network never happened (Deviation 10) %[id:hybrid_weights_lockfile_exists] %[id:hybrid_weights_lockfile_exists]. That search was set up
to favour the metric, so the inherited weights are an unlikely cause of its null result.

## 7.2 Deviations from the locked specification

Table 8 lists thirteen deviations from the locked plan %[id:deviations_total]. Together they
invalidated 17 %[id:deviations_runs_invalidated] runs, each of which was quarantined and
collected again in its own cell, which is why the final dataset is complete and balanced at
180 %[id:campaign_runs_total] runs. Ten %[id:deviations_no_data] of the thirteen invalidated no
data. The three %[id:deviations_with_data] that did are deviation 1 (3 runs
%[id:deviation_1_runs_invalidated]), deviation 2 (3 runs %[id:deviation_2_runs_invalidated])
and deviation 4 (11 runs %[id:deviation_4_runs_invalidated]). We describe them in the order
they occurred, because timing determines how far each could have shaped a result.

One deviation %[id:deviations_precampaign] predates all campaign data. It came from the
pre-launch rehearsal. The locked rule flagged a service on a multiplicative condition alone,
which was safe while per-service percentiles were still end-to-end values of tens of
milliseconds. The per-service definition of §3.5 moved several services into the
sub-millisecond range %[tbl:tbl_deviations — deviation 1], where a ratio responds to scheduler
noise. In the rehearsal, one service's p95 rose threefold between two consecutive fault-free
baseline windows and the rule flagged it as degraded. We added the 1.0 ms
%[id:threshold_degradation_floor_ms] floor described in §3.6 and discarded the three rehearsal
runs.

Two defects appeared during collection. The first was found 79 minutes in
%[id:deviation_2_found_after_min] and lay in how the runner matched a service name to a
container. It matched by substring and took the shortest match. The Hotel Reservation compose
project prefixes every container with `hotelreservation-`, which contains `reservation`, so a
request to fault `reservation` hit the `geo` container. The run killed `geo` while recording a
`reservation` fault, and the restore step then restarted the healthy `reservation`, so `geo` stayed down for the runs that followed. The health check made it worse, since it asked only
whether the tracing backend and the gateway answered, and both did without `geo`. We switched
to exact matching on the container label, which refuses ambiguous names, required every graph
service to be running before a run could start, and collected the three affected runs again.
That fix caused the second defect (deviation 3). The new gate compared graph names with
compose names, and the two differ for the Social Network gateway, so the campaign aborted on a
healthy stack. No data were affected.

The most consequential deviation (deviation 4) was caught by the pre-analysis gates straight
after the final run, before any statistic was computed. A network delay rule outlived the
process that created it and stayed active through a block of Social Network latency runs until
the stack was torn down. The damage had a direction. The contaminated runs' fault-free
baselines were inflated by two to three orders of magnitude, and since the rule asks whether
fault-window latency exceeds twice the baseline, the faults looked smaller than they were.
Services that should have been counted were already slow when the baseline was taken and went
uncounted, so the primary outcome was understated by two in most affected runs. No single run
record looked wrong; only the comparison across runs exposed it. The eleven runs were
collected again. The runner now recreates the target container after every non-kill run, and
the baseline-sanity gate that caught the problem is a standing check. §6.5 states the risk
that remains.

Four deviations concern the analysis. Deviation 5 records two choices the locked text left
open, the level at which the survival models run and which fault types each exploratory outcome
covers; both were settled before the analysis was written. Deviation 6 is a rule firing as
written. The plan promoted the rank test to primary for recovery time if fewer than 10% of
observations were censored, and none was %[id:campaign_censoring_rate_pct]; the survival models
are reported beside it without a separate correction, since they test the same hypotheses.
Deviation 7 is an inconsistency in the locked document. Its power section quotes 0.034
%[id:power_hr_prereg_stated_p] as the Hotel Reservation ceiling p-value, which is the asymptotic
value the same document forbids for inference, and the exact value is 0.0952
%[id:power_hr_ceiling_p] (§6.2). No analysis here used the asymptotic value. Deviation 8
replaced the reference statistical routines with vectorised versions, because the originals
were too slow for the number of evaluations required. The change is algebraic, and an equivalence test suite pins it to the
reference implementation, including on the tie-heavy inputs this dataset contains.

Deviation 9 was made after the results were known, and we mark it so. The Social Network
permutation tests had used Monte Carlo sampling because enumerating all orderings of eleven
services looked infeasible. It was not. The null distribution depends only on the two rank
vectors, so permuting the vector with more ties enumerates the same distribution from 9,240
%[id:primary_p_exact_arrangements] distinct arrangements. The exact uncorrected p-value of the
primary test is 0.006926 %[id:primary_p_exact], against the locked Monte Carlo estimate of
0.0080 %[id:primary_p_locked], and the adjusted value moves from 0.3451 %[id:primary_p_bh_locked]
to 0.3048 %[id:primary_p_bh_exact]. A refinement made after a null result looks like an attempt to rescue it, so the safeguards need stating. We applied it to every one of the 43 %[id:exact_tests_refined] testable tests, which rules out aiming it at a single result. It changes how the p-value is computed and leaves the test itself
untouched. Its direction could not be known in advance,
since a resampling with a different seed had landed on the other side of the locked value. The
verdict is unchanged %[id:primary_significant_exact], the exact values appear only in a
supplementary table (Table 9), and the locked value remains the preregistered one.

The last three deviations were found after the analysis by a read-only check of the
repository against its own records. None changed a stored outcome or a locked output.
Deviation 10 is the weight protocol described in §7.1; the fixed weights were already in the
analysis code before the lock, but the departure was recorded only at this check. Deviation 11
concerns Social Network spans, which carry no span-kind tag, so per-service latency there used
all of a service's spans while the run records labelled them server spans (§3.5). Replaying on server spans alone, after the fact, changed the outcome of 2 %[id:replay_runs_changed] of 110 %[id:replay_runs] runs but no service-level median %[id:replay_service_medians_changed], and the primary result stayed the same %[id:replay_primary_identical] %[id:replay_primary_identical]; recovery times could not be
replayed (§6.8). Deviation 12 concerns one Hotel Reservation latency run that was attempted
twice. The first attempt was interrupted in its recovery probe when the campaign stopped for
deviation 2. It wrote no run record and was never analysed, and the completed second attempt is
the run reported.

## 7.3 Verification

Two checks beyond the preregistered analysis are reported as supplementary. One is the
post-hoc leave-one-out recomputation of §4.1. The other is an independent reimplementation of
the primary statistic, written without reference to the analysis code and reading only the
persisted spans and the dependency graph. It reproduces the reported correlation
%[id:primary_rho_full] and agrees with the stored per-run outcomes on which services were
affected, not only how many, in all 110 %[id:sn_runs] Social Network runs. That shows the
analysis code is faithful to its data. Whether the definitions in §3.5 and §3.6 are the right
ones is a question no recomputation can settle.
