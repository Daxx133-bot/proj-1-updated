# 3. Method

> **Drafting note (strip before submission).** Trailing `%[id:...]` comments name the
> `paper/numbers.csv` claim_id each number comes from. Two other marker forms appear:
> `%[fig:...]` points at a figure's backing data file for values that have no numbers.csv
> id, which `CLAIMS_LEDGER.md` §7.1 records as a deliberate exemption for pilot-derived
> validation data; `%[prereg:§n]` points at a section of
> `_audit/preregistration_versions/PREREGISTRATION_v3_LOCKED.md` for design decisions that
> carry no number. No value in this section was typed by hand.

## 3.1 Benchmark applications and dependency graph reconstruction

We ran all experiments on two applications from the DeathStarBench suite, Social Network and
Hotel Reservation, built from a single pinned upstream commit `6ecb097` %[id:dsb_commit] so
that topology, instrumentation and service versions are identical across every run reported
here. The two differ in ways that matter for the question we are asking. Social Network is
deep and fans out widely from a single composition service, while Hotel Reservation is
shallow and almost star-shaped around its gateway. Running both lets us ask whether any
relationship we observe survives a change of shape, and, as it turns out, the difference
between them determines what each application is capable of showing at all.

We did not take the service dependency graph from documentation. Published architecture
diagrams describe the calls a system can make, whereas the quantity our hypothesis concerns
is the set of calls a system does make under the workload being perturbed. We therefore
reconstructed each graph from distributed traces, following parent–child span relationships
through Jaeger and emitting a directed edge from caller to callee wherever one service's
span is the parent of another's. Social Network's graph was built from 2,449 traces
%[id:graph_sn_traces_examined] containing 32,847 spans %[id:graph_sn_spans_examined], and
Hotel Reservation's from 3,446 traces %[id:graph_hr_traces_examined] containing 31,155 spans
%[id:graph_hr_spans_examined]. The resulting graphs have 12 %[id:graph_sn_nodes] and 8
%[id:graph_hr_nodes] service nodes, with 17 %[id:graph_sn_edges] and 7
%[id:graph_hr_edges] observed call edges respectively. Both graphs are frozen as
`data/graphs/{sn,hr}_CANONICAL.json` and every downstream predictor is computed from those
files, so a change in workload cannot silently alter a structural quantity after the fact.

Reconstruction from traces makes the graph an empirical object, and it is worth being
precise about how the reconstructed Hotel Reservation graph compares to the architecture the
benchmark documents. Of the 8 call edges %[id:hr_manifest_expected_edges] implied by the
published service tree, our traces recover 6 %[id:hr_manifest_edges_recovered]. Two are
never observed under this workload %[id:hr_manifest_edges_missed]: `reservation→user` and
`search→profile` %[id:hr_manifest_edges_missed_names]. One edge appears in the traces that
the documented tree does not list, `frontend→profile` %[id:hr_manifest_edges_extra], and it
accounts for the missing `search→profile`: in the deployed workload, profile lookups are
issued by the gateway directly rather than routed through search. The consequence for our
analysis is concrete rather than cosmetic. The `user` service has exactly one observed
caller %[id:hr_user_observed_caller_count], `frontend` %[id:hr_user_observed_callers], not
the two the documented architecture implies, and so its ancestor count is 1 rather than 2.
Had we used the documented graph, the primary predictor would have carried a value for
`user` that no traffic in our experiments could ever have produced. We treat the divergence
as a property of the workload and report it, rather than patching the observed graph toward
the diagram.

## 3.2 Analysis set and gateway exclusion

We exclude from all correlation analysis any service with in-degree zero in the
reconstructed graph, which in practice means each application's single entry point:
`nginx-web-server` in Social Network and `frontend` in Hotel Reservation %[prereg:§4]. The
exclusion is forced by the design of the study rather than chosen for convenience. Such a
service receives traffic only from the external load generator, which is not a node in the
graph, so its ancestor count is zero by construction and it cannot vary on the primary
predictor. Killing it also removes the application's only ingress, which leaves the outcome
we are trying to measure undefined rather than merely small. Both gateways remain in the
paper as labelled qualitative examples. The exclusion leaves 11 services
%[id:sn_services] in Social Network and 7 %[id:hr_services] in Hotel Reservation, and it
costs Hotel Reservation its highest-fan-out service, which we note as a scope limitation in
§5 rather than as a finding.

## 3.3 Predictors

The primary predictor is `ancestor_count`, the number of services that can reach a given
service transitively in the dependency graph, that is, its transitive callers. Eleven
further graph measures are retained as comparators: the hybrid criticality metric described
below, degree, in-degree, out-degree, betweenness, closeness, eigenvector, PageRank, a
composite rank, descendant count, and dominator subtree size %[prereg:§5]. None may be
dropped after results are seen, and none was.

The hybrid criticality metric is the measure this work set out to evaluate. It combines
in-degree centrality, out-degree centrality scaled by a linear fan-out weight, and directed
betweenness. Its weights are 0.4 %[id:hybrid_w_in] on the inbound channel, 0.4
%[id:hybrid_w_out] on the fan-out-scaled outbound channel and 0.2 %[id:hybrid_w_btw] on
betweenness. These weights were inherited from the original proposal. In the earlier,
withdrawn analysis they had been chosen by an empirical search, so they are not a priori. We
did not re-tune them on the campaign data %[id:hybrid_weights_reoptimised_on_campaign]. The
preregistered protocol, which tuned weights on Social Network and froze them for Hotel
Reservation, was not carried out (Deviation 10) %[id:hybrid_weights_lockfile_exists].
Because the original search favoured the metric, this is unlikely to explain a failure to
find an association.

Two predictor–architecture pairs are declared degenerate in advance because the predictor is
constant across an architecture's analysis set, which leaves Spearman's ρ undefined
%[prereg:§5.1]. Eigenvector centrality is 0 for every Social Network service in the analysis
set, the reconstructed graph being acyclic, and in-degree is identical for every Hotel
Reservation service, each having exactly one caller. We exclude both pairs from the test
family rather than entering them as zeros, since a degeneracy of the graph is not a null
result and should not dilute a false-discovery-rate correction. That leaves 22
%[id:testable_pairs] testable pairs of the 24 %[id:total_predictor_pairs] considered.

## 3.4 Fault injection protocol

Each run follows a fixed sequence. We start the application, apply a synthetic workload of
25 concurrent users %[id:protocol_load_users], and allow 60 seconds %[id:protocol_warmup_s]
of warm-up so that caches, connection pools and JIT behaviour reach steady state. We then
record a 60-second %[id:protocol_baseline_window_s] fault-free baseline, whose length is
identical in all 180 %[id:campaign_runs_total] runs %[id:protocol_baseline_window_distinct].
The fault is injected and held for 30 seconds %[id:protocol_fault_duration_s], after which
we probe for recovery, and each run ends with a 20-second %[id:protocol_cooldown_s]
cooldown before the next begins.

We use two fault types, injected with Pumba against the target service's container. A kill
fault sends SIGKILL %[id:fault_kill_signal], which removes the process without allowing it
to drain connections or respond to in-flight requests. A latency fault applies a `tc netem`
rule adding 500 ms %[id:fault_latency_delay_ms] of delay with 100 ms
%[id:fault_latency_jitter_ms] of jitter to the container's network interface. The two probe
different failure modes deliberately: a kill tests what happens when a dependency vanishes,
and a delay tests what happens when it remains available but stops being timely. Because
`pumba netem` blocks for the whole of its declared duration, it is launched as a separate
process and the runner waits for that process to exit before recording the instant of fault
removal; running it synchronously would let the rule expire before the measurement window
even opened.

The design is fully crossed and balanced. Every service in each analysis set receives every
fault type, with 5 repetitions %[id:campaign_reps_per_cell] of each combination, giving 36
%[id:campaign_cells] cells and 180 runs in total %[id:campaign_runs_total], of which 110
%[id:sn_runs] are Social Network and 70 %[id:hr_runs] Hotel Reservation. Balance is enforced
rather than hoped for: a run whose telemetry is incomplete is discarded and re-run in the
same cell, never topped up elsewhere and never analysed as zeros. The campaign ran from
2026-09-26 05:02 %[id:campaign_start_utc] to 13:35 UTC %[id:campaign_end_utc], a span of 8.5
hours %[id:campaign_duration_hours], with 0 %[id:campaign_runs_failed] runs lost to
telemetry failure.

We persist the raw spans for both the baseline and the fault window of every run. This costs
little and buys a great deal: any subsequent change to a metric definition can be replayed
against the original bytes instead of requiring the experiment to be repeated, and a
definitional claim can be checked rather than trusted. Several of the analyses in this paper
depend on that capability.

## 3.5 Per-service latency and error attribution

The definition of a service's latency is the part of this method that required the most
care, and we state it precisely because the natural implementation is wrong in a way that is
easy to miss.

A distributed trace records a whole request path. Querying a tracing backend for traces
involving service *X* returns every trace that touches *X*, and each such trace carries a
root span whose duration is the end-to-end latency of the entire request. If one computes
percentiles over those root-span durations and labels the result "the p95 of *X*", what has
actually been computed is the end-to-end p95 of *X*'s trace cohort. Every service on a given
request path is then assigned the same number. Error rate admits the identical defect: if a
trace counts as failed whenever any span within it carries an error, a failure anywhere on a
path marks every service on that path as failing.

The consequence is not a matter of precision but of identifiability. Services that share a
request path become indistinguishable, and any threshold applied to such a measure will
flag them as a block. Figure 4 shows what this does in practice on Hotel Reservation under a
latency fault injected into `search`. Under the end-to-end scope, four services report an
identical baseline p95 to two decimal places, and applying a multiplicative degradation
threshold flags five services that were not faulted
%[fig:fig_q3_artifact — paper/figures/fig_q3_artifact_data.csv]. Two of them, `profile` and
`reservation`, are neither ancestors nor descendants of `search`. They share a trace with it
and nothing more.

We therefore define a service's latency distribution over the server spans that service
itself emits. Client spans are excluded: a client span emitted by *X* measures a callee's
latency as observed by *X*, so counting it would re-attribute a downstream service's
slowness to *X* and reintroduce the same confusion through a narrower channel. Error rate is
attributed to the service whose own spans carry the error tag, with the denominator being
the traces in which that service actually appears. Where a service's instrumentation emits
no span-kind tag at all, which is the case for Social Network's Thrift services, the
implementation falls back to all of that service's spans and discloses the sample count
rather than silently returning an empty distribution. End-to-end root-span percentiles are
retained for the gateway alone, where they are the correct quantity, and are labelled with
an explicit scope tag in the returned record so that the two definitions cannot be conflated
downstream.

Under the corrected scope, the same Hotel Reservation runs flag one non-faulted service
rather than five %[fig:fig_q3_artifact — paper/figures/fig_q3_artifact_data.csv], and that
service is the faulted service's ancestor. The services that drop out do not merely fall
below the threshold; their own service time is flat, and in one case slightly negative,
while the end-to-end number they had been inheriting moves by more than two orders of
magnitude. This distinguishes a measurement artifact from genuine shared-resource
contention, which could not leave a service's own service time unchanged, and certainly
could not make it negative.

## 3.6 Blast radius classification

For each run we identify the set of services degraded during the fault window, then classify
each degraded service by its graph relation to the faulted node. A service is counted as
degraded when either of two conditions holds on its own spans. The latency condition
requires both that its fault-window p95 exceed 2.0× %[id:threshold_degradation_factor] its
baseline p95 and that the absolute increase be at least 1.0 ms
%[id:threshold_degradation_floor_ms]. The error condition requires its error rate to rise by
at least 0.05 %[id:threshold_error_rate_abs] in absolute terms.

The absolute floor alongside the multiplicative threshold is necessary once percentiles are
genuinely per-service. Several services in these applications have baseline p95 values in
the hundredths of a millisecond, and at that scale a purely multiplicative rule responds to
scheduler noise: a service moving from 0.02 ms to 0.06 ms between two consecutive fault-free
windows satisfies a 2× test three times over while representing no physically meaningful
change %[tbl:tbl_deviations — deviation 1, recorded evidence]. Both conditions are evaluated
at full floating-point precision, with rounding applied only for display. Rounding
percentiles to two decimals before the comparison would put the quantisation step at 0.01 ms
%[tbl:tbl_deviations — deviation 1], which is comparable to the entire signal for the
fastest services. The rule exists once in the codebase and is called by the run executor,
the recovery probe and the offline replay tool alike, so that the three cannot drift apart.

Degraded services are then separated into three counts that are recorded and analysed
separately and never summed. `ancestor_affected_count`, the primary outcome, counts degraded
transitive callers of the faulted service. `descendant_affected_count` counts degraded
transitive callees. `unrelated_affected_count` counts degraded services that are neither,
which would indicate shared-resource contention or synchronous fan-out rather than
dependency propagation. Collapsing these into a single "blast radius" would discard exactly
the distinction the hypothesis turns on, since the direction of propagation is what is being
tested.

Which indicator carries signal depends on the fault type, and we fix the pairing in advance
rather than choosing per result %[prereg:§6.5]. Under kill faults, error rate is the primary
indicator and Δp95 is not valid: when a service dies, its requests fail fast, so the
surviving latency distribution is dominated by quick failures and p95 can fall even as a
majority of requests error. The sign of that effect is determined by the runtime rather than
by chance, and it differs between our two applications, so kill-fault Δp95 is never pooled
across architectures. Under latency faults the position reverses. Δp95 is the primary
indicator and error rate carries no signal at all, nothing having failed. No single indicator
is valid across both fault types, and the analysis is run per fault type with its own
preregistered primary indicator.

## 3.7 Recovery time

We define recovery time, *T*<sub>rec</sub>, as the elapsed seconds from fault *removal*
until Δp95, Δp99, Δerror-rate and the downstream-affected count simultaneously return within
10% of their pre-fault baseline and hold there for a 5-second %[id:protocol_confirm_s]
confirmation period. Measuring from removal rather than from injection matters: timing from
injection makes *T*<sub>rec</sub> the sum of the fault duration, the restart and the
convergence, which floors it at the protocol's own fault duration and measures the
experiment rather than the system.

The recovery probe polls at a nominal 1-second interval, and each sample is drawn from a
lagged window offset 5 seconds %[id:protocol_probe_lag_s] into the past. The lag is not
cosmetic. Tracing backends flush spans in batches, so a window ending at the present instant
samples a partially written interval and systematically under-counts. A sample must contain
at least 20 traces %[id:protocol_min_traces] before its percentiles may vote for recovery,
which prevents a thin window from declaring recovery on the strength of a handful of fast
requests. The tolerance is one-sided, an empty or thin window counts as no signal rather
than as recovery, and no probe window may reach back past the fault instant.

A run that has not recovered within 180 seconds %[id:protocol_recovery_cap_s] is recorded as
right-censored, with the observation horizon stored alongside it. A censored recovery time
is never filled with a number, and censored runs are retained in the analysis as censored
observations rather than dropped or imputed. In the final dataset, 0 %[id:campaign_runs_censored]
of 180 runs were censored %[id:campaign_censoring_rate_pct], with observed recovery times
ranging from 9.72 s %[id:trec_min_s] to 156.27 s %[id:trec_max_s] around a median of 15.74 s
%[id:trec_median_s]. The preregistration fixed in advance that if under 10% of observations
were censored, the rank test would be promoted to the primary inferential result for
*T*<sub>rec</sub>, with survival models reported alongside it. That threshold was set before
collection and the rule fired on the data as collected.

## 3.8 Statistical plan and preregistration

The full analysis was specified in advance and locked before the campaign was launched,
including the hypotheses, the primary predictor and outcome, the analysis unit, the test
statistic, the correction procedure and the reporting commitments. The locked document is
reproduced as supplementary material, and every change made to it after the lock timestamp
is logged in its own amendment log with a date and a statement of whether campaign data had
been analysed at the time. §6 discusses those changes.

Associations between a graph predictor and a measured outcome are tested with Spearman's ρ
at the service level, aggregating each service's repetitions by their median. Significance
is assessed by permutation rather than by the asymptotic approximation, which is unreliable
at these sample sizes and in the presence of the tie structures these graphs produce.
Confidence intervals are obtained by bias-corrected and accelerated bootstrap, falling back
to a percentile interval, and disclosing the fallback, where the tie structure leaves the
bias-correction undefined.

Tests are organised into three families, each corrected separately by the Benjamini–Hochberg
procedure at q = 0.05 %[id:fdr_q]. The confirmatory family comprises 44
%[id:conf_family_size] tests on kill faults. The replication family comprises 44
%[id:repl_family_size] tests on latency faults and is reported as a replication rather than
as confirmatory evidence. A third, exploratory family covers secondary outcomes and is
labelled exploratory throughout, carrying no confirmatory weight. Pooling all families into
a single correction was considered and explicitly rejected in the locked plan, on the grounds
that the confirmatory and replication families answer the same question on different data
and should not be allowed to dilute one another.

Finally, two gates run before any statistic is computed. One verifies that every expected
service was present in every run, and the other that each run's fault-free baseline is a
plausible steady state for its application, flagging any baseline that is an outlier by
median and median-absolute-deviation against the rest of the campaign. Both must report zero
exceptions before analysis proceeds. All 10 %[id:integrity_checks_total] pre-analysis
integrity checks passed %[id:integrity_checks_passed] on the final dataset.
