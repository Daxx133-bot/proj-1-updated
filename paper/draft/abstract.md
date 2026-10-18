# Abstract

**Background.** Operators of microservice systems often rank services for hardening by
their position in the dependency graph, and a common intuition treats a service that calls
many others as the riskiest. When a service fails, however, the services left waiting are its
callers. We tested whether the number of transitive callers of a service tracks how many
services degrade when it fails, and whether a fan-out-weighted centrality metric does.

**Methods.** We preregistered the hypotheses and the full analysis, then ran 180
%[id:campaign_runs_total] fault-injection runs on Social Network and Hotel Reservation, two %[id:campaign_architectures] applications from the DeathStarBench suite. Each analysable service
received a process kill and an injected network delay, with 5 %[id:campaign_reps_per_cell]
repetitions in each of 36 %[id:campaign_cells] cells. Dependency graphs were rebuilt from
distributed traces, latency was attributed to each service's own spans, and every degraded
service was classified by its graph relation to the faulted one. Rank correlations were
tested by permutation, with Benjamini-Hochberg correction inside each test family.

**Results.** On Social Network under kill faults, caller count and the number of degraded
callers correlated at ρ = 0.785 %[id:primary_rho]. After correction, none of the 44
%[id:conf_family_size] confirmatory tests was significant %[id:conf_family_significant]
(adjusted p = 0.3451 %[id:primary_p_bh_locked]), and the latency replication reached the same
verdict %[id:repl_family_significant]. Much of the correlation is definitional, since ten of
the eleven services degraded every caller they had %[id:saturation_sn_kill_service]. The
fan-out metric's correlation was negative in all four architecture-by-fault cells
%[id:h1b_all_negative] and distinguishable from zero in none %[id:h1b_any_distinguishable].
Degradation reached callers and almost never callees: no descendant of the faulted service
degraded in 179 of 180 runs %[id:descendant_affected_runs_zero]. The service the fan-out metric ranked most critical had exactly one degraded caller in each of its ten %[id:composepost_runs_total] runs %[id:composepost_kill_min] %[id:composepost_kill_max] %[id:composepost_latency_min] %[id:composepost_latency_max]
%[id:composepost_runs_only_gateway_ancestor]. Hotel Reservation was saturated, and its ties
kept the best attainable p-value at 0.0952 %[id:power_hr_ceiling_p], above the usual
threshold.

**Conclusions.** In these two benchmark applications a failure's reach followed callers,
and the fan-out premise found no support. Our test of the caller count did not survive the
correction we committed to, so we present the caller ranking as the better-motivated choice,
not as a demonstrated predictor. We also recommend two measurement steps that this study needed: attributing latency to each service's own spans, and checking whether the outcome simply restates the predictor. Every number reported here regenerates from logged data.
