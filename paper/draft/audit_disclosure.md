# 6. Audit and deviations from the preregistration

> **Drafting note (strip before submission).** Trailing `%[id:...]` comments name the
> `paper/numbers.csv` claim_id each number comes from. Table 8 is
> `paper/tables/tbl_deviations.csv`.

## 6.1 Why this study was rebuilt

An earlier version of this work was submitted for project review. A subsequent self-audit of
its analysis pipeline found that parts of its reported results did not come from measurement.
Impact values and recovery times that the manuscript presented as experimental findings were
produced by code that drew from hard-coded numeric ranges, and the metric weights carrying
the headline correlation had been selected by a grid search maximising that same correlation
against the same outcome the paper then reported, with no held-out data. Results obtained
that way are a maximum over a search presented as a single test.

We withdrew those results in full. The affected scripts and outputs were not deleted but
moved to a quarantine directory, which now holds 13 %[id:quarantine_items] numbered items,
each with a record of what was removed and why, so that the withdrawn material remains
inspectable rather than disappearing from the history. The measurement pipeline, the metric
implementation and the analysis were then rebuilt from the ground up, and the study
reported here is an entirely new campaign.

Three commitments follow from that history and shape everything in this paper. Every number
we report is produced by a script reading logged data, and where a value cannot be traced to
a script and an input file we record the gap rather than fill it. The metric weights are
fixed a priori in a constants module with written reasoning for each, and were never fitted
to outcome data %[id:hybrid_weights_tuned]. And the analysis was specified and locked before
the campaign began, with every subsequent change to that specification logged, dated, and
marked according to whether campaign data had been analysed at the time.

We state this history because a reader assessing the present results is entitled to know it,
and because the safeguards described throughout §3 are only meaningful in light of what they
were built to prevent.

## 6.2 Deviations from the locked specification

Nine deviations from the locked plan are recorded (Table 8) %[id:deviations_total]. Across
all of them, 17 runs %[id:deviations_runs_invalidated] were invalidated; every one was
quarantined and re-collected rather than analysed or dropped, which is why the final dataset
is complete and balanced at 180 runs %[id:campaign_runs_total]. Four deviations invalidated
no data at all. We group them below by when they occurred, since that is what determines how
much they could have influenced a result.

**Before any campaign data existed.** One deviation %[id:deviations_precampaign] was found
during the pre-launch rehearsal. The blast-radius rule as locked flagged a service purely on
a multiplicative condition, with no absolute floor. That was defensible while per-service
percentiles were still end-to-end values in the tens of milliseconds, but the corrected
per-service definition of §3.5 moved 8 of 20 services into the range below 0.6 ms
%[tbl:tbl_deviations — deviation 1], where a multiplicative threshold responds to scheduler
noise rather than to anything physical. The
evidence was direct: a service moved from 0.02 ms to 0.06 ms between two consecutive
*fault-free* baseline windows, a factor of three, and the rehearsal duly flagged it as
degraded. We added the 1.0 ms %[id:threshold_degradation_floor_ms] absolute floor described
in §3.6 and discarded the three rehearsal runs. No campaign data existed at the time and
none had been analysed.

**During collection.** Two defects surfaced while the campaign was running. The first, found
79 minutes in %[tbl:tbl_deviations — deviation 2, stage], was in how the runner resolved a
service name to a container. It matched by substring and took the shortest match, and
because the Hotel Reservation compose project
prefixes every container with `hotelreservation-`, which contains the substring
`reservation`, a request to fault `reservation` resolved to the `geo` container instead. The
run killed `geo` while recording a `reservation` fault, and restoration then started
`reservation`, which had never been down, leaving `geo` dead for subsequent runs. A second
weakness compounded it: the health check verified only that the tracing backend and the
gateway responded, and both did with `geo` absent. We replaced substring matching with exact
resolution by container label, which refuses to guess when a name is ambiguous, and
strengthened the health gate to require every service in the graph to be running. Three runs
were invalidated and re-collected. The fix itself then introduced the second defect: the new
gate compared graph service names against compose service names, and these differ for the
Social Network gateway, which reports itself to the tracing backend under one name and is
declared in compose under another. Social Network could not pass the gate and the campaign
aborted on a healthy stack. No data was affected, and we record it because a correction that
introduces a fault of its own is part of the same audit trail.

**Found by the pre-analysis gates.** The most consequential deviation was detected
immediately after the final run, before any statistic had been computed. An injected network
delay rule outlived the process that created it and stayed active for the remainder of a
block of Social Network latency runs, clearing only when the stack was torn down. The
distortion this produced is worth describing because of its direction. The contaminated runs'
*fault-free baselines* were inflated by two to three orders of magnitude, and since the
degradation rule asks whether fault-window latency exceeds twice the baseline, an inflated
baseline makes the fault look smaller. The services that should have been counted were
already degraded when the baseline was taken, so they could not clear their own inflated
threshold and went uncounted. The primary outcome was understated by exactly two in most of
the affected runs. Analysed as collected, this would have flattened the Social Network
correlation while being indistinguishable from ordinary measurement noise; no individual run
record looked anomalous, and only the cross-run comparison exposed it. Eleven runs were
invalidated and re-collected. We now force-recreate the target container after every non-kill
run, which cannot affect the run just completed but guarantees the next starts clean, and we
added the baseline-sanity gate that caught the incident as a standing pre-analysis check.
§5.5 states the residual limitation this leaves.

**Specification gaps and analysis decisions.** Two points required a decision the locked text
did not make: the level at which the survival models should run, and which fault types each
exploratory outcome covers. Both were escalated and resolved before the analysis was written,
and both are recorded with the resolution taken. Separately, the locked plan fixed in advance
that if fewer than 10% of recovery observations were censored, the rank test would be promoted
to the primary result for recovery time. No observation was censored
%[id:campaign_censoring_rate_pct], so that rule fired as written; survival models are reported
alongside but are not separately corrected, since they test the same hypotheses as the primary
tests they accompany.

**Implementation and documentation.** The reference implementation of the rank statistic
costs roughly 1.4 ms per call, and the analysis requires on the order of 2.5 million
evaluations, so we reimplemented the statistic, the permutation test and the bootstrap in
vectorised form, reducing a run from about an hour to 25 seconds. The replacement is
algebraic rather than approximate, and an equivalence test suite pins it against the
reference implementation, including on the tie-heavy inputs this dataset actually contains.
We also record an internal inconsistency in the locked document itself: the p-value its power
section quotes for the Hotel Reservation ceiling is the asymptotic value, which the same
document forbids for inference. Under the exact test it mandates, that ceiling p-value is
0.0952 %[id:power_hr_ceiling_p] rather than the 0.034 %[id:power_hr_prereg_stated_p] stated.
This sharpens the preregistration's own conclusion rather than contradicting it, and §5.2
gives the consequence. No analysis in this paper used the asymptotic value.

**After the analysis was complete.** The final deviation was made after the results were
known, and we mark it as such. The Social Network permutation tests had fallen back to Monte
Carlo sampling because exhaustive enumeration of 11 factorial orderings was judged infeasible.
That judgement was wrong: the permutation null depends only on the two rank vectors, so
permuting the vector carrying more ties enumerates the identical null distribution from far
fewer distinct arrangements, in this case 9,240 %[id:primary_p_exact_arrangements]. The exact
uncorrected p-value for the primary test is 0.006926 %[id:primary_p_exact] against the locked
Monte Carlo estimate of 0.0080 %[id:primary_p_locked], and the adjusted value moves from
0.3451 %[id:primary_p_bh_locked] to 0.3048 %[id:primary_p_bh_exact].

A p-value refinement made after a null result is known has the shape of a rescue attempt, so
we record the safeguards explicitly. The refinement was applied to all 43
%[id:exact_tests_refined] testable tests in the family rather than to the primary test alone,
so it could not be aimed. It changes the computation and not the hypothesis, the statistic,
the analysis unit or the family membership. The direction of the change was not knowable in
advance, an independent resampling with a different seed having landed on the other side of
the locked value. The verdict is unchanged either way
%[id:primary_significant_exact], the exact values appear only in a supplementary table
(Table 9), and the locked Monte Carlo value remains the preregistered one.

## 6.3 Verification

Two checks beyond the preregistered analysis are reported as supplementary. The first is the
leave-one-out recomputation of §4.1, which we mark post-hoc throughout. The second is an
independent reimplementation of the primary statistic, written without reference to the
analysis code, reading only the raw persisted spans and the dependency graph, and computing
the statistic through a different code path. It reproduces the reported correlation
%[id:primary_rho_full] and agrees with the stored per-run outcome fields on the identity of
the affected services, not merely their count, in all 110 %[id:sn_runs] Social Network runs.
This establishes that the analysis implementation is faithful to the data it was given. It
does not establish that the definitions in §3.5 and §3.6 are the right ones, which is a
question no recomputation can settle.
