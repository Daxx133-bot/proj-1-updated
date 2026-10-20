# IV. Testbed and Methodology

> **Drafting note (not rendered).** Trailing `%[id:...]` markers name the paper/numbers.csv
> claim_id of each number; `%[fig:...]` points at a figure's data file for pilot values the
> ledger exempts (§7.1); `%[prereg:§n]` points at the locked preregistration. A fenced
> ```algorithm block renders as Algorithm 1.

Figure 1 shows the pipeline in the order the campaign executed it. The six steps in the first
column built the dependency graphs and the predictors and locked the analysis plan before any
campaign data existed. The next four repeated in every run, and the last two ran once the
campaign was complete. Each box names the repository files that carry out the step.

## A. Testbed

All experiments ran on a single host whose configuration is given in Table 1. The application
stacks, Jaeger and Pumba ran as containers inside the virtual machine of Docker Desktop's WSL2
backend, while the load generator and the campaign runner ran as host processes (Figure 2). The
runner stops every stack before the campaign and brings up one application at a time, stopping
it before the other starts, so the two never shared the 7.598 %[id:testbed_docker_vm_gib] GiB
memory ceiling of the virtual machine. The Social Network stack has 27
%[id:testbed_containers_sn] containers and the Hotel Reservation stack 24
%[id:testbed_containers_hr], as recorded before the campaign. Traces were
collected with Jaeger 1.62.0 %[id:version_jaeger] (https://www.jaegertracing.io), one all-in-one
instance per application with in-memory storage %[id:testbed_jaeger_storage].

The host operating system, CPU and Docker Desktop version in Table 1 were queried on
2026-10-20 %[id:testbed_measured_on], after the campaign, and are labelled as measured. The
memory ceiling, host memory and container counts were recorded on 2026-09-24
%[id:testbed_vm_record_date], before the campaign. Values with no record from the campaign
period are omitted.

## B. Applications and Dependency Graphs

Both applications come from DeathStarBench, Social Network and Hotel Reservation [@gan2019],
built from one pinned upstream commit, 6ecb097 %[id:dsb_commit]. The code under test was
therefore the same in every run. The two applications have different shapes. Social Network is
deep and fans out from a single composition service, while Hotel Reservation is shallow and
close to a star around its gateway. That difference ended up deciding what each application
could show at all (Section V-B).

The dependency graph was not taken from documentation. A diagram shows the calls a system can
make, while the hypotheses concern the calls it does make under the workload being perturbed.
Each graph was therefore rebuilt from distributed traces, with a directed edge from caller to
callee wherever a span from one service is the parent of a span from another [@sigelman2010].
The Social Network graph came from 2,449 %[id:graph_sn_traces_examined] traces holding 32,847
%[id:graph_sn_spans_examined] spans, and the Hotel Reservation graph from 3,446
%[id:graph_hr_traces_examined] traces holding 31,155 %[id:graph_hr_spans_examined] spans. The
graphs have 12 %[id:graph_sn_nodes] and 8 %[id:graph_hr_nodes] service nodes, with 17
%[id:graph_sn_edges] and 7 %[id:graph_hr_edges] observed call edges, and Figure 3 and Figure 4
show them as observed. Both are frozen as files, and every predictor is computed from those
files, so no later change of workload can shift a structural value.

The observed Hotel Reservation graph differs from the documented one. Of the 8
%[id:hr_manifest_expected_edges] call edges implied by the published service tree, the traces
recover 6 %[id:hr_manifest_edges_recovered]. Two never appear under this workload
%[id:hr_manifest_edges_missed]: reservation→user and search→profile
%[id:hr_manifest_edges_missed_names]. One edge appears that the tree does not list,
frontend→profile %[id:hr_manifest_edges_extra], which appears to stand in for the missing
search→profile, with the gateway fetching profiles directly. The difference matters for one
service. user has a single observed caller %[id:hr_user_observed_caller_count], frontend
%[id:hr_user_observed_callers], where the documentation implies two, so its ancestor count is 1
%[id:hr_user_observed_caller_count]. With the documented graph, user would carry a predictor
value that no traffic in the experiments could have produced. The observed graph is kept and
the divergence reported.

## C. Analysis Set and Gateway Exclusion

Every correlation excludes the one service in each application that has no caller in the
graph: nginx-web-server in Social Network and frontend in Hotel Reservation
%[prereg:§4]. A gateway receives traffic only from the load generator, which is not a node in
the graph, so its ancestor count is zero by construction and cannot vary. Killing it also
removes the only way into the application, which leaves the outcome undefined. Excluding the
gateways leaves 11 %[id:sn_services] services in Social Network and 7 %[id:hr_services] in Hotel
Reservation. In Hotel Reservation it also removes the service with the highest fan-out, a scope
limit taken up in Section VII.

## D. Predictors

The primary predictor and the hybrid metric are defined in Section III-B. The ten further
measures kept as comparators are degree, in-degree, out-degree, betweenness, closeness,
eigenvector centrality, PageRank, a composite rank, descendant count and dominator subtree size
%[prereg:§5]. The plan forbade dropping any of them once results were seen, and none was
dropped. Centralities follow the standard definitions [@freeman1978], and betweenness is
computed with the algorithm of Brandes as implemented in NetworkX [@brandes2001; @hagberg2008].

The hybrid weights of 0.4 %[id:hybrid_w_in], 0.4 %[id:hybrid_w_out] and 0.2 %[id:hybrid_w_btw]
come from the project's original proposal, in which an empirical search chose them; they were
therefore not fixed independently of all data. The locked plan called for tuning the
weights on Social Network and freezing them for Hotel Reservation, and that step was never run
(Deviation 10) %[id:hybrid_weights_lockfile_exists]. No re-tuning on campaign data took place %[id:hybrid_weights_reoptimised_on_campaign]. A sensitivity analysis over every weighting
on the preregistered grid, run after the confirmatory results were known, is reported in
Section V-J %[id:hybrid_weights_grid_evaluated_post_hoc].

Two predictor-architecture pairs were declared degenerate in advance, because the predictor is
constant across the analysis set and Spearman's ρ is then undefined %[prereg:§5.1].
Eigenvector centrality is 0 %[id:degenerate_sn_value] for every analysed Social Network
service, the reconstructed graph being acyclic, and every Hotel Reservation service has the
same in-degree, each having exactly one caller. Both pairs are left out of the test family. A
degenerate graph property is not a null result, and entering it as one would dilute the
false-discovery-rate correction. That leaves 22 %[id:testable_pairs] testable pairs of the 24
%[id:total_predictor_pairs] considered.

## E. Workload and Run Protocol

Each run starts the load generator, Locust 2.46.3 %[id:version_locust] (https://locust.io), with
25 %[id:protocol_load_users] users spawned at 10 %[id:protocol_spawn_rate] per second. Each
simulated user waits between 0.5 %[id:protocol_sn_wait_min_s] %[id:protocol_hr_wait_min_s] and
1.5 seconds %[id:protocol_sn_wait_max_s] %[id:protocol_hr_wait_max_s] between requests, and each
request is drawn from a fixed weighted mix of tasks. On Social Network the weights are 3
%[id:protocol_sn_task_weight_compose_post] for composing a post, 5
%[id:protocol_sn_task_weight_read_home_timeline] for reading a home timeline and 2
%[id:protocol_sn_task_weight_read_user_timeline] for reading a user timeline. On Hotel
Reservation they are 6 %[id:protocol_hr_task_weight_hotel_search] for a hotel search, 2
%[id:protocol_hr_task_weight_make_reservation] for a reservation, 2
%[id:protocol_hr_task_weight_get_user] for a user lookup and 1
%[id:protocol_hr_task_weight_get_recommendations] for recommendations.

The load runs for 60 seconds %[id:protocol_warmup_s] before the fault, and the fault-free
baseline percentiles are computed over that same 60-second %[id:protocol_baseline_window_s]
window. The window therefore begins when the load generator starts and includes its ramp-up
(Deviation 13); its length was identical in all 180 %[id:campaign_runs_total] runs
%[id:protocol_baseline_window_distinct]. The fault is then injected and held for 30 seconds
%[id:protocol_fault_duration_s], the recovery probe runs, and a 20-second %[id:protocol_cooldown_s]
cooldown separates one run from the next.

The design is fully crossed and balanced. Each analysable service receives each fault type in 5
%[id:campaign_reps_per_cell] repetitions, giving 36 %[id:campaign_cells] cells and 180
%[id:campaign_runs_total] runs, of which 110 %[id:sn_runs] are Social Network runs and 70
%[id:hr_runs] Hotel Reservation runs. A run whose telemetry is incomplete is discarded and
repeated in the same cell; it is never topped up elsewhere and never analysed as zeros. The same
rule covered the 17 %[id:deviations_runs_invalidated] runs invalidated by deviations 1, 2 and 4
(3 %[id:deviation_1_runs_invalidated], 3 %[id:deviation_2_runs_invalidated] and 11
%[id:deviation_4_runs_invalidated] runs; Section IV-J), which were collected again in their own
cells. Measured from the first to the last end-timestamp of the kept runs, the campaign ran from
2026-09-26 05:02 %[id:campaign_start_utc] to 13:35 UTC %[id:campaign_end_utc], 8.5 hours
%[id:campaign_duration_hours] in all, and lost 0 %[id:campaign_runs_failed] runs to telemetry
failure. Earlier records give 9.3 hours %[id:campaign_duration_incl_rehearsal_hours] because
they also count the 3 %[id:deviation_1_runs_invalidated] pre-launch rehearsal runs.

The raw spans of both the baseline and the fault window were kept for every run. Storing them
is cheap, and it means any later change to a metric definition can be replayed against the
original data instead of being re-run. Several analyses in this paper depend on that.

## F. Fault Injection with Pumba

Faults are injected with Pumba (https://github.com/alexei-led/pumba), which the runner starts as
a short-lived container (image `ghcr.io/alexei-led/pumba`, with no version tag) that acts on the
target container through the Docker socket. The runner issues every command through the Docker 29.8.0
%[id:version_docker_client] client (https://www.docker.com). Table 2 lists the command lines,
generated from the runner code. A kill fault sends SIGKILL %[id:fault_kill_signal], which ends
the process without letting it drain connections or answer requests in flight. A latency fault
applies a `tc netem` (https://wiki.linuxfoundation.org/networking/netem) rule that adds 500 ms
%[id:fault_latency_delay_ms] of delay with 100 ms %[id:fault_latency_jitter_ms] of jitter to
the container's network interface for 30 seconds %[id:protocol_fault_duration_s]. The kill asks
what happens when a dependency vanishes; the delay asks what happens when it stays up but stops
being timely.

To find the target container, the runner looks for the one whose `com.docker.compose.service`
label, which Docker Compose sets on every container, equals the service name exactly. The runner
stops if no running container or more than one matches, so a fault cannot land on a different
service from the one recorded (Deviation 2). The Social Network gateway reports itself to
Jaeger as nginx-web-server but runs as the compose service nginx-thrift, and the runner
translates between the two names.

Timing differs by fault type. A kill completes at once; the runner waits out the fault window
and then restores the service with `docker compose up -d`, and the fault-removal instant is
taken when that command returns. Because `pumba netem` blocks for its whole declared duration,
the runner launches it as a separate process, waits out the window, and takes the
fault-removal instant when that process exits. Running it synchronously would let the rule
expire before the measurement window had opened. After the recovery probe of every non-kill run,
the runner recreates the target container with `--force-recreate`, so that no residual netem
rule can reach the next run (Deviation 4). Algorithm 1 gives one run in full, with the warm-up
and baseline window *W* = 60 s %[id:protocol_warmup_s], the fault hold *H* = 30 s
%[id:protocol_fault_duration_s], probe interval *P* = 1 s %[id:trec_poll_interval_nominal_s],
confirmation period *K* = 5 s %[id:protocol_confirm_s], probe lag *L* = 5 s
%[id:protocol_probe_lag_s] and recovery cap *C* = 180 s %[id:protocol_recovery_cap_s].

```algorithm
Algorithm 1: One campaign run (tools/run_pilot.py, one_run), called in manifest order with a cooldown after each run
Input: application a, service s, fault type f, repetition r; graph G of a
c ← the running container whose label com.docker.compose.service equals the compose name of s; stop unless exactly one matches
start the Locust load against the gateway of a
wait W; B ← per-service baseline percentiles and error rates over the last W
t_inj ← now; issue the Pumba command for f on c   ▷ kill: synchronous; latency: background process
wait H; t_end ← now
Dg ← services degraded in [t_inj, t_end] relative to B (Section IV-H)
persist the raw spans of the baseline and fault windows
if f = kill then run docker compose up -d for s else wait for the Pumba process to exit
t_rm ← now   ▷ fault-removal instant
T_rec ← recovery probe from t_rm with interval P, confirmation K, lag L and cap C
if f ≠ kill then run docker compose up -d --force-recreate for s
classify Dg into ancestors, descendants and unrelated services of s in G
stop the load; return the run record
```

## G. Per-Service Latency and Error Attribution

The latency definition needed more care than any other part of the method, because the obvious
implementation is wrong in a way that is easy to miss.

A distributed trace records a whole request path. A tracing backend asked for the traces
involving *X* hands back every trace in which *X* appears, and each of those traces has a root
span whose duration is the end-to-end latency of the whole request. A percentile taken over
those root spans and called "the p95 of *X*" is really the end-to-end p95 of all requests that
passed through *X*, and every service on a request path receives the same value. Error rate has
the same flaw if a trace counts as failed whenever any span in it carries an error.

Services on a shared path then become indistinguishable, and any threshold applied to them flags
them as a group. Figure 5 shows the effect on Hotel Reservation under a latency fault injected
into search. The figure uses two %[id:q3_pilot_runs] pilot method-validation runs, which are
not among the 180 campaign runs, and its end-to-end values are reconstructed from their
persisted spans. Under that scope three services %[id:q3_identical_baseline_services], geo,
rate and search %[id:q3_identical_baseline_names], share an identical baseline p95 in both
runs, and a multiplicative threshold flags five services that were not faulted
%[fig:fig_q3_artifact — paper/figures/fig_q3_artifact_data.csv]. Two of these, profile and
reservation, are neither ancestors nor descendants of search. They share a trace with it and
nothing more.

Each service's latency is therefore measured on the server spans that service emits. On Hotel
Reservation, whose spans carry a span-kind tag, client spans are excluded, since a client span
recorded by *X* times the callee as *X* sees it and would pass a downstream delay back to *X*.
Social Network's spans carry no span-kind tag, so for Social Network all of a service's spans
were used. That applied to 2,598 %[id:sn_span_samples_fallback] of 2,598 %[id:sn_span_samples]
Social Network samples, and about half of the spans used, 49.7%
%[id:sn_spans_selected_client_pct], are client spans. The run records nonetheless label these
samples as server spans %[id:sn_record_samples_labelled_server] %[id:sn_record_samples]. A post
hoc replay limited to server spans altered the outcome of 2 %[id:replay_runs_changed] of the 110
%[id:replay_runs] runs and none of the service-level medians %[id:replay_service_medians_changed],
and the primary result came out identical %[id:replay_primary_identical]
%[id:replay_primary_rho_kill] (Deviation 11). An error counts against a service only when one of
that service's own spans is tagged as an error, and the rate is divided by the number of traces
in which the service appears. End-to-end root-span percentiles are kept only for the gateway,
where they are the right quantity, and every returned record carries a scope tag that says
which definition produced it.

With per-service attribution, the same Hotel Reservation runs flag one non-faulted service
instead of five %[fig:fig_q3_artifact — paper/figures/fig_q3_artifact_data.csv], and that
service is an ancestor of the faulted one. The services that drop out do more than fall below
the threshold. Their own service time stays flat, and in one case drops slightly, while the
end-to-end value previously assigned to them grows more than a hundredfold. Contention for
shared resources would be expected to raise a service's own service time, so this pattern
points to a measurement artifact.

## H. Outcomes: Blast Radius and Recovery Time

For each run, the services degraded during the fault window are found and each is classified
by its graph relation to the faulted node. A service counts as degraded when either of two
conditions holds on its own spans. The latency condition requires its fault-window p95 to exceed
2.0× %[id:threshold_degradation_factor] its baseline p95 and to rise by at least 1.0 ms
%[id:threshold_degradation_floor_ms]. The error condition requires its error rate to rise by at
least 0.05 %[id:threshold_error_rate_abs] in absolute terms.

The absolute floor became necessary once percentiles were truly per-service. Some services here
have baseline p95 values in the hundredths of a millisecond, and at that scale a purely
multiplicative rule reacts to scheduler noise. A service whose p95 rises threefold between two
consecutive fault-free windows passes a 2× %[id:threshold_degradation_factor] test without any
physically meaningful change %[tbl:tbl_deviations — deviation 1, recorded evidence]. Both
conditions are evaluated at full floating-point precision, and values are rounded only for
display, since rounding to two decimals first would leave a step about as large as the whole
signal of the fastest services %[tbl:tbl_deviations — deviation 1]. The run executor and the
recovery probe share a single implementation of the latency rule, which the offline replay tool
also calls. The error-rate rule is repeated in three modules with the same value
%[src:_audit/VERIFICATION_2026-10-06.md §3].

Degraded services are split into the three counts of Section III-A, which are recorded and
analysed separately. The primary outcome, *Y*, counts degraded transitive callers of the faulted service. A second
count covers degraded transitive callees, and a third covers degraded services that are
neither, which would indicate
shared-resource contention or synchronous fan-out.

Which indicator carries signal depends on the fault type, and the pairing was fixed in the plan
%[prereg:§6.5]. Under kill faults the primary indicator is error rate, and Δp95 is not used. In
the pilot, across 10 kill runs %[prereg:§6.5], the sign of kill-fault Δp95 split by application.
It was negative in every Hotel Reservation run, where p95 fell even as most requests errored,
and positive in every Social Network run. The likely explanation, that Hotel Reservation's
services fail requests quickly when a dependency dies while Social Network's clients wait for a
timeout, was not tested. Kill-fault Δp95 is never pooled across architectures. Under latency
faults the roles reverse: Δp95 is the primary indicator, and error rate carries no signal
because nothing has failed. Each fault type is therefore analysed with its own preregistered
indicator.

Recovery time, *T*<sub>rec</sub>, is the number of seconds from fault *removal* until Δp95, Δp99,
Δerror-rate and the downstream-affected count are all back within 10% of their pre-fault
baseline and stay there for a 5-second %[id:protocol_confirm_s] confirmation period. Timing from
removal matters. Timed from injection, *T*<sub>rec</sub> would include the whole fault duration
and could never fall below it. The recovery probe polls at a nominal 1-second
%[id:trec_poll_interval_nominal_s] interval. Measured as the median gap between successive
samples within each run, its effective resolution was 1.4 %[id:trec_poll_interval_eff_min_s] to
2.4 seconds %[id:trec_poll_interval_eff_max_s]. Each sample is drawn from a window lagged 5
seconds %[id:protocol_probe_lag_s] into the past, because tracing backends flush spans in batches
and a window ending at the present instant under-counts. A sample needs at least 20 traces
%[id:protocol_min_traces] before its percentiles can vote for recovery, so a handful of fast
requests cannot end a run early. The tolerance is one-sided, and an empty or thin window counts
as no signal. No probe window may reach back past the fault instant.

A run that has not recovered within 180 seconds %[id:protocol_recovery_cap_s] is recorded as
right-censored, with the observation horizon stored beside it, and is never filled in with a
number. In the final dataset 0 %[id:campaign_runs_censored] of the 180 runs were censored
%[id:campaign_censoring_rate_pct]. Observed recovery times ranged from 9.72 s %[id:trec_min_s] to
156.27 s %[id:trec_max_s], with a median of 15.74 s %[id:trec_median_s]. The plan stated in
advance that if fewer than 10% of observations were censored, the rank test would become the
primary inferential result for *T*<sub>rec</sub> and survival models would be reported beside it.
That rule fired on the data as collected.

## I. Statistical Analysis

Associations between a graph predictor and a measured outcome are tested with Spearman's ρ at
the service level, after taking the median over each service's repetitions. Significance comes
from permutation tests, exact where the permutations can be enumerated and otherwise from 10,000
%[id:primary_n_permutations] random permutations. The asymptotic approximation is unreliable at
these sample sizes and with the ties these graphs produce. Confidence intervals are
bias-corrected and accelerated bootstrap intervals, with a percentile interval used, and
disclosed, where the ties leave the bias correction undefined. The analysis was developed and
verified on Python 3.13.2 %[id:version_python] (https://www.python.org), with SciPy 1.14.1
%[id:version_scipy] (https://scipy.org) supplying ranks and the reference Spearman
implementation, and statsmodels 0.14.6 %[id:version_statsmodels] (https://www.statsmodels.org)
the Cox and log-rank models.

Tests fall into three families, each corrected separately with the Benjamini-Hochberg procedure
at q = 0.05 %[id:fdr_q] [@benjamini1995]. The confirmatory family holds 44 %[id:conf_family_size]
tests on kill faults. The replication family holds 44 %[id:repl_family_size] tests on latency
faults and is reported as a replication. A third, exploratory family covers secondary outcomes
and carries no confirmatory weight. The locked plan considered pooling all families into one
correction and rejected it, on the grounds that the confirmatory and replication families ask
the same question under different fault types and should not dilute each other. For the primary
outcome, the replication in fact reuses the same outcome values as the confirmatory family
%[id:replication_primary_identical] (Section V-E).

Two gates run before any statistic is computed. One confirms that every expected service was
present in every run. The other compares each run's fault-free baseline with those of all other runs, using the
median and the median absolute deviation, and flags any baseline that does not look like a
steady state. Both must report zero exceptions before analysis can proceed. All 10
%[id:integrity_checks_total] pre-analysis integrity checks passed %[id:integrity_checks_passed]
on the final dataset.

## J. Preregistration and Deviations

The plan was specified and locked before the campaign started [@nosek2018], and every later
change was logged with its date and with whether campaign data had been analysed by then.
Thirteen deviations were recorded %[id:deviations_total], and the Appendix lists them. Ten
%[id:deviations_no_data] invalidated no data. The other three %[id:deviations_with_data]
invalidated 17 runs %[id:deviations_runs_invalidated], each collected again in its own cell, so
the final dataset is complete and balanced. Deviation 1 arose in the pre-launch rehearsal
%[id:deviations_precampaign]: at per-service percentiles of a few hundredths of a millisecond, a
purely multiplicative rule reacted to scheduler noise, so the absolute floor of Section IV-H was
added and the 3 %[id:deviation_1_runs_invalidated] rehearsal runs were discarded. Deviation 2
was a substring match that faulted the wrong Hotel Reservation container; exact label matching
replaced it, and 3 %[id:deviation_2_runs_invalidated] runs were collected again. Deviation 4 was
a netem rule that outlived its run and inflated later baselines; the 11
%[id:deviation_4_runs_invalidated] affected runs were collected again, and per-run container
recreation and a baseline-sanity gate were added. Deviation 3 was a name mismatch that stopped
the campaign on a healthy stack. Deviations 5, 6, 7, 8 and 9 concern the analysis: two choices
the plan left open, the rank test becoming primary for recovery time, an asymptotic p-value
quoted in the plan, vectorised statistical routines, and exact p-values reported only as
supplementary. Deviation 10 is the weight tuning that was not run (Section IV-D), Deviation 11
concerns Social Network span selection (Section IV-G), and Deviation 12 a latency run attempted
twice, of which only the completed attempt is analysed. Deviation 13, found during manuscript
preparation, records that baselines were computed over the opening 60 s
%[id:protocol_baseline_window_s] of load, ramp-up included; it invalidated no run, and the
baseline-sanity gate found no anomalies.

## K. Data and Code Availability

The code, the raw campaign data (persisted trace spans, run records and the reconstructed
dependency graphs) and the analysis outputs are available at
https://github.com/Daxx133-bot/proj-1-updated and will be archived at Zenodo (DOI: [TO FILL]).
The repository's build script regenerates every number in this paper from the logged data.
Three supplementary files accompany the paper in the repository: S1, the leave-one-out
recomputation of Section V-B (`paper/tables/tbl_leave_one_out.csv`); S2, the unrounded
recovery-time estimates of Section V-I, including the Cox fits shown there as not estimable
(`paper/tables/tbl_trec_supplementary.csv`); and S3, the exact-enumeration p-values for the
confirmatory family (`analysis/final/exact_p_supplement.csv`). The
experiments used DeathStarBench at upstream commit 6ecb097 %[id:dsb_commit]. Code is released
under the MIT licence; data and figures are released under CC BY 4.0.
