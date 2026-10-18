# 1. Background

A microservice application is built from many small services that call one another over
the network [@dragoni2017]. Each service can be changed and deployed on its own, which is
much of the appeal. The price is that a fault in one service can show up far from where it
started, and industrial experience suggests such faults are slow to diagnose
[@zhou2021]. Teams that run these systems therefore want to know, before anything breaks,
which services to harden first. Injecting faults into every service to find out is expensive.
A cheaper option is to read the answer off the dependency graph.

Graph measures have a long record as indicators of importance and risk. The standard notions
of centrality were set out for social networks [@freeman1978], and network measures computed
on software dependency graphs have been used to predict which components will have defects
[@zimmermann2008]. Applied to a service graph, the intuition most people bring is that a
service which calls many others is a hub, and that hubs are dangerous. This project began
from that intuition. Its original metric gave extra weight to fan-out, the number of services
a service calls directly, on the reasoning that a service with many callees cuts many
connections when it fails.

A simple argument points the other way. When a service fails, the services that wait on its
answers are the ones that call it. Its callees lose a client and see less traffic. If that
argument holds, the number of services that degrade should follow a service's transitive
callers, its ancestors in the graph, and a fan-out ranking should go wrong precisely for the
services it rates highest. Social Network's composition service shows the conflict in one
example. It calls 7 %[id:composepost_out_degree] services directly, and the fan-out metric
ranks it first %[id:composepost_rank_hybrid] of the 11 %[id:composepost_set_size] services we
analysed. It has a single caller %[id:composepost_ancestor_count], and by caller count it
ranks last %[id:composepost_rank_ancestor_count].

We tested the caller-based prediction, and the fan-out metric alongside it, in a
preregistered fault-injection campaign [@nosek2018] on two applications from the
DeathStarBench suite [@gan2019]. We formulated the caller-based hypothesis after a pilot study (preregistration, §1.3) %[prereg:§1.3] and locked it, together with every analysis choice, before any campaign data existed, keeping the fan-out metric as a comparator. The
campaign completed all 180 %[id:campaign_runs_total] planned runs. Every analysable service
received both fault types, a process kill and an injected network delay, with 5
%[id:campaign_reps_per_cell] repetitions per cell. We rebuilt each dependency graph from
traces, attributed latency to the spans each service emits itself, and classified every
degraded service by its position relative to the faulted one, so that degradation of callers
and of callees could be counted apart.

The preregistered hypothesis was not confirmed. On Social Network under kill faults, caller
count and the number of degraded callers correlated at ρ = 0.785 %[id:primary_rho], yet none
of the 44 %[id:conf_family_size] tests in the confirmatory family survived correction
%[id:conf_family_significant], and the replication under latency faults gave the same answer
%[id:repl_family_significant]. Much of that correlation is definitional, because the outcome
counts a subset of the predictor and most services degraded every caller they had. The
fan-out metric did no better. Its correlation with degraded callers was negative in every
architecture and fault type %[id:h1b_all_negative] and was never distinguishable from zero
%[id:h1b_any_distinguishable]. The plainest result needs no test at all: degradation reached
callers and almost never callees, with no descendant of the faulted service degraded in 179
of 180 runs %[id:descendant_affected_runs_zero].

This paper makes four contributions.

- A preregistered test of whether caller count, or a fan-out-weighted centrality metric,
  tracks measured failure impact in two benchmark applications, reported with its null result
  and with the power ceiling the design imposed.
- Documentation of a measurement pitfall, in which a request's end-to-end latency is charged
  to every service on its path, and of its effect in the pilot, where it flagged services
  unrelated to the faulted one in the graph.
- An observation on the direction of propagation that held in both applications and under
  both fault types.
- An artifact in which every number in the paper is produced by a script from logged
  campaign data.

An earlier analysis from this project was withdrawn after a self-audit found results that
had not come from measurement; §7 describes what happened and the safeguards that followed.

The paper is organised as follows. §2 reviews related work, and §3 describes how
the faults were injected and how degradation was measured. §4 reports the results,
which §5 discusses. §6 sets out the threats to validity, §7 records the audit together with
every deviation from the preregistration, and §8 concludes.
