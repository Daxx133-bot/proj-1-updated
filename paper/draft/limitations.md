# 6. Threats to Validity

> **Drafting note (strip before submission).** Trailing `%[id:...]` comments name the
> `paper/numbers.csv` claim_id each number comes from.

## 6.1 Sample size and the ceiling on attainable correlation

The unit of analysis is the service, so the sample size is 11 %[id:power_sn_n] for Social
Network and 7 %[id:power_hr_n] for Hotel Reservation. Those are the sizes the applications
have. They were registered in advance, and the realised sets match them exactly
%[id:power_sn_n_matches] %[id:power_hr_n_matches]. Repetition makes each service's measured
outcome more precise, which is why we used 5 %[id:campaign_reps_per_cell] repetitions per
cell, but it adds no points to a correlation. A study designed this way is bounded by how many
services the system has.

Ties tighten the bound. `ancestor_count` takes 4 %[id:power_sn_levels] distinct values on
Social Network and 2 %[id:power_hr_levels] on Hotel Reservation, and ties cap Spearman's ρ
whatever is measured. The best attainable correlations are 0.941 %[id:power_sn_ceiling] and
0.791 %[id:power_hr_ceiling]. The confirmatory null should be read with that in mind. We
registered these ceilings before collecting data, so they are a stated property of the design
and not an explanation found afterwards.

## 6.2 Hotel Reservation could not have reached significance

For Hotel Reservation the problem goes beyond low power. Under the exact permutation test the
plan mandates, a perfect result with the observed ties, ρ = 1.0, yields p = 0.0952
%[id:power_hr_ceiling_p]. That is above the conventional 0.05 threshold before any
correction for multiplicity. No outcome we could have measured on this application would have reached
nominal significance for this predictor.

The application is also saturated. Each service's measured count matched its graph count in every run %[id:saturation_hr_kill_run] %[id:saturation_hr_kill_service], so a correlation computed here only restates how the outcome was built %[id:saturation_hr_kill_tautological] %[id:saturation_hr_kill_tautological].
We report every Hotel Reservation result as directional only, and it should be read neither as
replicating the Social Network result nor as failing to. Its value here is as a second, very
differently shaped topology on which the propagation-direction result of §4.5 also holds.

## 6.3 Two applications from one benchmark suite

Both applications come from one benchmark suite, built from one pinned upstream commit
%[id:dsb_commit]. They are research benchmarks. We chose them because they are instrumented
and reproducible, which makes the experiment repeatable, but they do not sample the space of
microservice architectures in any principled way. We did not configure or study containment mechanisms such as retries with back-off or circuit breakers, which could change how far a failure travels. Nothing here describes
production behaviour.

The workload is synthetic as well, fixed at 25 %[id:protocol_load_users] concurrent users with
a fixed request mix. Because the dependency graph is rebuilt from observed traffic, a
different mix would give a different graph on the same deployment, and both the predictors
and the outcomes would move with it (§6.6).

## 6.4 The primary predictor is close to definitional

The most serious threat to the primary result is conceptual. The outcome counts degraded
transitive callers and the predictor counts transitive callers, so the two coincide whenever
every ancestor degrades. On Hotel Reservation they always coincide
%[id:saturation_hr_kill_service]. On Social Network they coincide for ten of the eleven
services %[id:saturation_sn_kill_service], the exception being `user-service`, which registers
2 %[id:userservice_measured] of its 4 %[id:userservice_ancestor_count] ancestors in every kill
repetition %[id:userservice_runs_departing].

The whole gap between ρ = 0.785 %[id:primary_rho] and a correlation of exactly 1.0 therefore
rests on one service. The post-hoc leave-one-out check confirms the arithmetic: dropping `user-service` raises ρ to 1.000 %[id:loo_userservice_rho], a change 2.4 times %[id:loo_swing_ratio] the size of the next largest. That check was specified after the
confirmatory result was known, and we report it as a description of the data.

Before collection we asked whether a predictor this close to its outcome was worth testing at
all, and we registered the saturation measure to detect exactly this problem. We still think
the test was meaningful, because saturation was not guaranteed in advance and does not fully
hold. A reader may nonetheless treat the Social Network correlation as carrying roughly one
service's worth of independent information.

This study cannot say why `user-service` departs. In all five of its kill repetitions the two ancestors that degraded both sit on request paths the workload drives, and its other two graph ancestors showed no degradation in any run. That suggests `ancestor_count` is a ceiling, and that how close the outcome comes to it depends on the request mix. We formed this explanation after seeing the data and
have not tested it. Testing it would need a workload-weighted predictor and a new
preregistration.

## 6.5 Fault removal is inferred, not verified

For latency faults, the runner infers that the `tc netem` rule has been removed from the fact
that the injecting process has exited. That inference failed at least once, and §7 describes
the incident and the safeguards added afterwards. The safeguards limit the damage without
ruling it out. The cross-run baseline gate catches a rule that outlives the run that created
it, because the contamination then shows up in later runs' fault-free baselines. A rule that
leaked and then cleared within a single run would go unnoticed, since that run's own baseline
comes before its fault.

Latency-fault recovery times therefore carry an assumption we cannot check with the current
instrumentation. If a rule persisted into a run's recovery probe, that run's
*T*<sub>rec</sub> would be inflated and nothing in our pipeline would flag it. Blast-radius
counts are less exposed, since they come from the fault window itself. Closing the gap would
need a direct query of the container's queueing discipline, which we did not implement.

## 6.6 The dependency graph depends on the workload

Rebuilding the graph from traces gives the calls the system actually makes, which we consider
the right basis for this question. It also makes the graph a property of the deployment and
the workload together. Production call graphs have been found to change from request to
request [@luo2021], and even our fixed benchmark workload shows the effect. Of the 8
%[id:hr_manifest_expected_edges] edges implied by Hotel Reservation's published architecture,
our traces recover 6 %[id:hr_manifest_edges_recovered]. Two %[id:hr_manifest_edges_missed] are
never exercised %[id:hr_manifest_edges_missed_names], and one appears that the documentation
does not list %[id:hr_manifest_edges_extra].

Since `ancestor_count` is computed on the rebuilt graph, a service's predictor value depends on
which of its callers the workload happens to drive. Here the `user` service has one observed
caller %[id:hr_user_observed_caller_count], where the documentation implies two. A different
request mix would give it a different predictor value with nothing about the deployed system
changed. This limits how far any relationship we report carries over to other traffic, and it
is the same mechanism the post-hoc reading of `user-service` in §6.4 relies on, which is one
more reason to treat that reading as untested.

## 6.7 Scope of the measurement

We measure whether a service degrades, by a preregistered threshold on its own latency or
error rate. We do not establish why any individual service degrades. We studied two fault
types, a process kill and a 500 ms %[id:fault_latency_delay_ms] network delay. CPU contention
was evaluated in the pilot and dropped before the campaign, because its effect was too small
to classify reliably; §7 records that as a scope decision. Other failure modes, from resource
exhaustion to slow or corrupted responses, are outside what we measured.

## 6.8 Social Network recovery times were not replayed

For Social Network, per-service latency included every span a service emitted, client spans among them (§3.5, Deviation 11). The blast-radius outcomes could be replayed on server-only spans from
the stored baseline and fault windows. Recovery times could not, because the recovery probe's
windows were not stored, so Social Network recovery times stand as measured.
