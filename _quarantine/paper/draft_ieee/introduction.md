# I. Introduction

A microservice application is built from many small services that call one another over the
network [@dragoni2017]. Each service can be changed and deployed on its own, which is much of
the appeal. The price is that a fault in one service can show up far from where it started,
and industrial experience suggests such faults are slow to diagnose [@zhou2021]. Teams that
run these systems therefore want to know, before anything breaks, which services to harden
first. Injecting faults into every service to find out is expensive. A cheaper option is to
read the answer off the dependency graph.

Graph measures have a long record as indicators of importance and risk. The standard notions
of centrality were set out for social networks [@freeman1978], and network measures computed
on software dependency graphs have been used to predict which components will have defects
[@zimmermann2008]. Applied to a service graph, the usual intuition is that a service which
calls many others is a hub, and that hubs are dangerous. This project began from that
intuition. Its original metric gave extra weight to fan-out, the number of services a service
calls directly, on the reasoning that a service with many callees cuts many connections when
it fails.

A simple argument points the other way. When a service fails, the services that wait on its
answers are the ones that call it. Its callees lose a client and see less traffic. If that
argument holds, the number of services that degrade should follow a service's transitive
callers, its ancestors in the graph, and a fan-out ranking should go wrong precisely for the
services it rates highest. Social Network's composition service shows the conflict in one
example. It calls 7 %[id:composepost_out_degree] services directly, and the fan-out metric
ranks it first %[id:composepost_rank_hybrid] of the 11 %[id:composepost_set_size] services
analysed. It has a single caller %[id:composepost_ancestor_count], and by caller count it ranks
last %[id:composepost_rank_ancestor_count].

This study tested the caller-based prediction, with the fan-out metric alongside it, in a
preregistered fault-injection campaign [@nosek2018] on two applications from the
DeathStarBench suite [@gan2019]. The caller-based hypothesis was formulated after a pilot
study and locked, together with every analysis choice, before any campaign data existed; the
fan-out metric was kept as a comparator. The campaign completed all 180
%[id:campaign_runs_total] planned runs. Every analysable service received both fault types, a
process kill and an injected network delay, with 5 %[id:campaign_reps_per_cell] repetitions per
cell. Each dependency graph was rebuilt from traces, latency was attributed to the spans each
service emits itself, and every degraded service was classified by its position relative to
the faulted one, so that degradation of callers and of callees could be counted apart.

The preregistered hypothesis was not confirmed. On Social Network under kill faults, caller
count and the number of degraded callers correlated at ρ = 0.785 %[id:primary_rho], yet none of
the 44 %[id:conf_family_size] tests in the confirmatory family survived correction
%[id:conf_family_significant], and the replication under latency faults gave the same answer
%[id:repl_family_significant]. Much of that correlation is definitional, because the outcome
counts a subset of the predictor and most services degraded every caller they had. The
fan-out metric did no better. Its correlation with degraded callers was negative in every
architecture and fault type %[id:h1b_all_negative] and was never distinguishable from zero
%[id:h1b_any_distinguishable]. The plainest result needs no test at all: degradation reached
callers and almost never callees, with no descendant of the faulted service degraded in 179 of
180 runs %[id:descendant_affected_runs_zero].

The work cited above leaves a specific question open. Network measures on software dependency
graphs have been shown to predict where defects accumulate [@zimmermann2008], but a defect
count describes the code, not how far a run-time failure spreads under load. Fault-injection
practice and tools [@basiri2016; @heorhiadi2016; @alvaro2015] are built to check that a system
tolerates failure or to find bugs; they are not used to test whether a structural ranking
anticipates the damage a failure does. Root-cause localisation [@wu2020; @zhou2021] uses the
service graph together with live metrics after an anomaly has begun, which is a different task
from ranking services before any fault occurs. Trace-derived call graphs also change with the
traffic that produces them [@luo2021], so a graph-based ranking inherits that dependence. None
of the cited works reports a test, fixed in advance, of a graph-derived ranking against failure
propagation measured in a controlled campaign.

This paper makes four contributions. First, it reports a preregistered test of whether caller
count, or a fan-out-weighted centrality metric, tracks measured failure impact in two benchmark
applications, with its null result and with the power ceiling the design imposed. Second, it
documents a measurement pitfall, in which a request's end-to-end latency is charged to every
service on its path, and its effect in the pilot, where it flagged services unrelated to the
faulted one in the graph. Third, it reports an observation on the direction of propagation that
held in both applications and under both fault types. Finally, it provides an artifact in which
every number in the paper is produced by a script from logged campaign data.

Section II reviews related work. Section III states the problem and the hypotheses, and
Section IV describes the testbed and the methodology. Section V reports the results and
Section VI discusses them. Section VII sets out the threats to validity, and Section VIII
concludes.
