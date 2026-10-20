# VII. Threats to Validity

## A. Sample Size and the Ceiling on Attainable Correlation

The unit of analysis is the service, so the sample size is 11 %[id:power_sn_n] for Social Network
and 7 %[id:power_hr_n] for Hotel Reservation. Those are the sizes the applications have. They
were registered in advance, and the realised sets match them exactly %[id:power_sn_n_matches]
%[id:power_hr_n_matches]. Repetition makes each service's measured outcome more precise, which is
why 5 %[id:campaign_reps_per_cell] repetitions per cell were used, but it adds no points to a
correlation. A study designed this way is bounded by how many services the system has.

Ties tighten the bound. The caller count *X* takes 4 %[id:power_sn_levels] distinct values on Social
Network and 2 %[id:power_hr_levels] on Hotel Reservation, and ties cap Spearman's ρ whatever is
measured. The best attainable correlations are 0.941 %[id:power_sn_ceiling] and 0.791
%[id:power_hr_ceiling]. The confirmatory null should be read with that in mind. These ceilings
were registered before data collection, so they are a stated property of the design and not an
explanation found afterwards.

## B. Hotel Reservation Could Not Have Reached Significance

For Hotel Reservation the problem goes beyond low power. Under the exact permutation test the
plan mandates, a perfect result with the observed ties, ρ = 1.0, yields p = 0.0952
%[id:power_hr_ceiling_p]. That is above the conventional 0.05 threshold before any correction
for multiplicity. No outcome that could have been measured on this application would have
reached nominal significance for this predictor.

The application is also saturated. Each service's measured count matched its graph count in every
run %[id:saturation_hr_kill_run] %[id:saturation_hr_kill_service], so a correlation computed here
only restates how the outcome was built %[id:saturation_hr_kill_tautological]. Every Hotel
Reservation result is reported as directional only, and it should be read neither as replicating
the Social Network result nor as failing to. Its value here is as a second, very differently
shaped topology on which the propagation-direction result of Section V-F also holds.

## C. Two Applications from One Benchmark Suite

Both applications come from one benchmark suite, built from one pinned upstream commit
%[id:dsb_commit]. They are research benchmarks. They were chosen because they are instrumented
and reproducible, which makes the experiment repeatable, but they do not sample the space of
microservice architectures in any principled way. Containment mechanisms such as retries with
back-off or circuit breakers were not configured or studied, and they could change how far a
failure travels. Nothing here describes production behaviour.

The workload is synthetic as well, fixed at 25 %[id:protocol_load_users] concurrent users with a
fixed request mix. Because the dependency graph is rebuilt from observed traffic, a different mix
would give a different graph on the same deployment, and both the predictors and the outcomes
would move with it (Section VII-F).

## D. The Primary Predictor Is Close to Definitional

The most serious threat to the primary result is conceptual. The outcome counts degraded
transitive callers and the predictor counts transitive callers, so the two coincide whenever
every ancestor degrades. On Hotel Reservation they always coincide
%[id:saturation_hr_kill_service]. On Social Network they coincide for ten of the eleven services
%[id:saturation_sn_kill_service], the exception being user-service, which registers 2
%[id:userservice_measured] of its 4 %[id:userservice_ancestor_count] ancestors in every kill
repetition %[id:userservice_runs_departing].

The whole gap between ρ = 0.785 %[id:primary_rho] and a correlation of exactly 1.0 therefore rests
on one service. The post hoc leave-one-out check confirms the arithmetic: dropping user-service
raises ρ to 1.000 %[id:loo_userservice_rho], a change 2.4 times %[id:loo_swing_ratio] the size of
the next largest. That check was specified after the confirmatory result was known, and it is
reported as a description of the data.

Before collection, the open question was whether a predictor this close to its outcome was worth
testing at all, and the saturation measure was registered to detect exactly this problem. The
test remained meaningful, because saturation was not guaranteed in advance and does not fully
hold. A reader may nonetheless treat the Social Network correlation as carrying roughly one
service's worth of independent information.

This study cannot say why user-service departs. In all five of its kill repetitions the two
ancestors that degraded both sit on request paths the workload drives, and its other two graph
ancestors showed no degradation in any run. That suggests the caller count is a ceiling, and that
how close the outcome comes to it depends on the request mix. This explanation was formed after
seeing the data and has not been tested. Testing it would need a workload-weighted predictor and
a new preregistration.

## E. Fault Removal Is Inferred, Not Verified

For latency faults, the runner infers that the `tc netem` rule has been removed from the fact that
the injecting process has exited. That inference failed at least once, and Section IV-J describes
the incident and the safeguards added afterwards. The safeguards limit the damage without ruling
it out. The cross-run baseline gate catches a rule that outlives the run that created it, because
the contamination then shows up in later runs' fault-free baselines. A rule that leaked and then
cleared within a single run would go unnoticed, since that run's own baseline comes before its
fault.

Latency-fault recovery times therefore carry an assumption that the current instrumentation
cannot check. If a rule persisted into a run's recovery probe, that run's *T*<sub>rec</sub> would
be inflated and nothing in the pipeline would flag it. Blast-radius counts are less exposed, since
they come from the fault window itself. Closing the gap would need a direct query of the
container's queueing discipline, which was not implemented.

## F. The Dependency Graph Depends on the Workload

Rebuilding the graph from traces gives the calls the system actually makes, which suits this
question. It also makes the graph a property of the deployment and the workload together.
Production call graphs have been found to change from request to request [@luo2021], and even the
fixed benchmark workload here shows the effect. Of the 8 %[id:hr_manifest_expected_edges] edges
implied by Hotel Reservation's published architecture, the traces recover 6
%[id:hr_manifest_edges_recovered]. Two %[id:hr_manifest_edges_missed] are never exercised
%[id:hr_manifest_edges_missed_names], and one appears that the documentation does not list
%[id:hr_manifest_edges_extra].

Since the caller count is computed on the rebuilt graph, a service's predictor value depends on
which of its callers the workload happens to drive. Here the user service has one observed
caller %[id:hr_user_observed_caller_count], where the documentation implies two. A different
request mix would give it a different predictor value with nothing about the deployed system
changed. This limits how far any relationship reported here carries over to other traffic, and it
is the same mechanism the post hoc reading of user-service in Section VII-D relies on, which is
one more reason to treat that reading as untested.

## G. Scope of the Measurement

The study measures whether a service degrades, by a preregistered threshold on its own latency or
error rate. It does not establish why any individual service degrades. Two fault types were
studied, a process kill and a 500 ms %[id:fault_latency_delay_ms] network delay. CPU contention was
evaluated in the pilot and dropped before the campaign, because its effect was too small to
classify reliably, and the preregistration records that as a scope decision. Other failure
modes, from resource exhaustion to slow or corrupted responses, are outside what was measured.

## H. Social Network Recovery Times Were Not Replayed

For Social Network, per-service latency included every span a service emitted, client spans among
them (Section IV-G, Deviation 11). The blast-radius outcomes could be replayed on server-only spans
from the stored baseline and fault windows. Recovery times could not, because the recovery probe's
windows were not stored, so Social Network recovery times stand as measured.

## I. The Baseline Window Includes the Load Ramp-Up

The fault-free baseline is computed over the 60-second %[id:protocol_baseline_window_s] window in
which the load generator starts, spawns its users and runs (Section IV-E), not over a
separate window after a warm-up (Deviation 13). A baseline percentile can therefore include start-up effects that a
steady-state baseline would not. The same procedure ran in every run, and the baseline-sanity gate,
which compares each run's baseline with the rest of the campaign, reported no exceptions
%[id:integrity_checks_passed]. The size of any start-up effect was not measured.

## J. Testbed Records

Some testbed values in Table 1 were queried after the campaign, on 2026-10-20
%[id:testbed_measured_on], and are labelled as measured. The Docker client binary predates the
campaign, but the host operating system build and the Docker Desktop version could have changed
between the campaign and the query, and no record from the campaign days confirms them.
