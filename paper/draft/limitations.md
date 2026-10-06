# 5. Limitations

> **Drafting note (strip before submission).** Trailing `%[id:...]` comments name the
> `paper/numbers.csv` claim_id each number comes from.

## 5.1 Sample size and the ceiling on any attainable correlation

The unit of analysis is the service, which puts the sample size at 11 %[id:power_sn_n] for
Social Network and 7 %[id:power_hr_n] for Hotel Reservation. These are the sizes the
applications have; they were registered in advance and the realised sets match them exactly
%[id:power_sn_n_matches] %[id:power_hr_n_matches]. Repetition improves the precision of each
service's measured outcome, and we used 5 %[id:campaign_reps_per_cell] repetitions per cell
for that reason, but it does not increase the number of points entering a correlation. A
study of this design is bounded by how many services the system has.

The tie structure compounds this. `ancestor_count` takes 4 %[id:power_sn_levels] distinct
values on Social Network and 2 %[id:power_hr_levels] on Hotel Reservation, and ties place a
ceiling on Spearman's ρ irrespective of what is measured. The best attainable correlation is
0.941 %[id:power_sn_ceiling] and 0.791 %[id:power_hr_ceiling] respectively. A reader should
take the confirmatory null in that light: the design had limited room to produce a
significant result, and we registered these ceilings before collecting data rather than
offering them afterwards as an explanation.

## 5.2 Hotel Reservation could not have reached significance

The Hotel Reservation limitation is stronger than low power, and we want to be exact about
it. Under the exact permutation test our analysis plan mandates, a *perfect* result on Hotel
Reservation, ρ = 1.0 with the observed tie structure, yields a p-value of 0.0952
%[id:power_hr_ceiling_p]. That is above the conventional 0.05 threshold before any
multiplicity correction is applied. No outcome we could have measured on this application
would have reached nominal significance for this predictor.

Hotel Reservation is additionally saturated: its measured outcome equals its graph predictor
for every service in every run %[id:saturation_hr_kill_run] %[id:saturation_hr_kill_service],
which makes any correlation computed on it a restatement of how the outcome was constructed
rather than an independent prediction %[id:saturation_hr_kill_tautological]. We report every
Hotel Reservation result as directional only, and it should not be read as either replicating
or failing to replicate the Social Network result. Its value in this study is as a
structurally different topology on which the propagation-direction result of §4.5 also holds,
not as a second test of the correlation.

## 5.3 Two applications from one benchmark suite

We studied two applications from a single benchmark suite, built from one pinned upstream
commit %[id:dsb_commit]. Both are research benchmarks rather than production systems. They
were chosen because they are instrumented, reproducible and widely used, which makes the
experiment repeatable, but they do not sample the space of microservice architectures in any
principled way. Neither application has the retry policies, circuit breakers, bulkheads or
autoscaling that production deployments typically use to arrest propagation, and all of
these would be expected to change how far a failure travels. Nothing here should be read as
characterising production behaviour.

The workload is likewise synthetic and fixed at 25 concurrent users
%[id:protocol_load_users] with a fixed request mix. Since the dependency graph is
reconstructed from observed traffic, a different mix would produce a different graph on the
same deployment, and both the predictors and the measured outcomes would shift with it. We
return to this below.

## 5.4 The primary predictor is close to definitional

The most serious threat to the primary result is not statistical but conceptual. We define
the outcome as the number of degraded transitive callers and the predictor as the number of
transitive callers, so the two coincide whenever every ancestor degrades. On Hotel
Reservation they coincide always %[id:saturation_hr_kill_service]. On Social Network they
coincide for 10 of 11 services %[id:saturation_sn_kill_service], the exception being
`user-service`, which registers 2 %[id:userservice_measured] of its 4
%[id:userservice_ancestor_count] ancestors in every kill repetition
%[id:userservice_runs_departing].

The whole difference between ρ = 0.785 %[id:primary_rho] and a correlation of exactly 1.0
therefore rests on a single service. Our post-hoc leave-one-out check confirms this
arithmetic directly: withholding `user-service` yields ρ = 1.000
%[id:loo_userservice_rho], a swing 2.4 times %[id:loo_swing_ratio] larger than any other
service's. We flag that check as post-hoc, specified after the confirmatory result was
known, and we report it as a description of the data rather than as a test.

We considered before collection whether a predictor this close to its own outcome is worth
testing at all, and registered the saturation measure specifically to detect the problem.
Our position is that the test remains meaningful because saturation was not guaranteed in
advance and does not in fact hold. But a reader is entitled to treat the Social Network
correlation as carrying roughly one service's worth of independent information, and we would
not argue.

Why `user-service` departs is not something this study can answer. In all five of its kill
repetitions the ancestors that degraded were the two on paths the workload exercises, while
its other two graph ancestors never degraded, which suggests that `ancestor_count` functions
as an upper bound whose tightness depends on the workload mix rather than on graph structure
alone. **This explanation was generated after seeing the data and has not been tested. We
offer it as a hypothesis for future work, not as a finding.** Testing it would require a
workload-weighted predictor and a fresh preregistration.

## 5.5 Fault removal is inferred, not verified

For latency faults, the runner infers that the injected `tc netem` rule has been removed
from the fact that the injecting process has exited. That inference proved unreliable at
least once, and §6 describes the incident and the safeguards now in place. Those safeguards
bound the damage rather than eliminating the possibility. The cross-run baseline gate
detects a rule that outlives the run that created it, because the contamination then shows
up in later runs' fault-free baselines. A rule that leaked and then cleared within a single
run would not be detected, since that run's own baseline precedes its fault.

The practical consequence is that latency-fault recovery times carry a residual assumption
we cannot discharge with the current instrumentation: if a rule persisted into a run's
recovery probe, that run's *T*<sub>rec</sub> would be inflated and nothing in our pipeline
would flag it. Blast-radius counts are less exposed, since they are computed over the fault
window itself. Closing this gap properly requires querying the container's queueing
discipline directly rather than inferring its state, which we did not implement.

## 5.6 The dependency graph is workload-dependent

Reconstructing the graph from traces gives us the calls the system actually makes, which we
consider the right choice for this question, but it makes the graph a property of the
deployment and the workload together rather than of the software alone. Hotel Reservation
illustrates the point concretely. Of the 8 %[id:hr_manifest_expected_edges] edges implied by
the published architecture, our traces recover 6 %[id:hr_manifest_edges_recovered], while 2
%[id:hr_manifest_edges_missed] are never exercised %[id:hr_manifest_edges_missed_names], and
one edge appears that the documented architecture does not list
%[id:hr_manifest_edges_extra].

Since `ancestor_count` is computed on the reconstructed graph, a service's predictor value
depends on which of its callers the workload happens to drive. The `user` service has one
observed caller %[id:hr_user_observed_caller_count] here rather than the two the
documentation implies. A different request mix would assign it a different predictor value
without anything about the deployed system having changed. This limits how far any
predictor–outcome relationship we report can be transported to a deployment under different
traffic, and it is the same mechanism our post-hoc reading of `user-service` in §5.4
invokes, which is a further reason to treat that reading as untested.

## 5.7 Scope of the measurement

Two further boundaries are worth stating. We measure whether a service degrades, by a
preregistered threshold on its own latency or error rate, and not why it degrades; no causal
mechanism for any individual service's degradation is established here. And we studied two
fault types, process kill and a 500 ms %[id:fault_latency_delay_ms] network delay. CPU
contention was evaluated during piloting and dropped before the campaign because its effect
size was too small to classify reliably, which we record as a scope decision in §6. Resource
exhaustion, partial failures, and corrupted or slow responses are all outside what we
measured.
