# Abstract

> **Drafting note (not rendered).** One paragraph, at most 250 words, no headings (IEEE
> Access). Trailing `%[id:...]` markers name the paper/numbers.csv claim_id of each number.

One way to decide which services of a microservice system to harden first is to rank them
by their position in the dependency graph, and an intuitive version of that ranking treats a
service that calls many others as the riskiest. When a service fails, however, the services
left waiting are its callers. This study tested whether the number of transitive callers of
a service tracks how many services degrade when it fails, and whether a fan-out-weighted
centrality metric does. A preregistered campaign ran 180 %[id:campaign_runs_total]
fault-injection runs on two %[id:campaign_architectures] DeathStarBench applications, giving
each analysable service a process kill and an injected network delay in 5
%[id:campaign_reps_per_cell] repetitions. Dependency graphs were rebuilt from traces, latency
was attributed to each service's own spans, and each degraded service was classified by its
graph relation to the faulted one. On Social Network under kill faults, caller count and the
number of degraded callers correlated at ρ = 0.785 %[id:primary_rho], but none of the 44
%[id:conf_family_size] confirmatory tests survived Benjamini-Hochberg correction
%[id:conf_family_significant] (adjusted p = 0.3451 %[id:primary_p_bh_locked]), and a
latency-fault replication agreed %[id:repl_family_significant]. Much of the correlation is
definitional, since ten of the eleven services degraded every caller they had
%[id:saturation_sn_kill_service]. The fan-out metric correlated negatively in all four
architecture-by-fault cells %[id:h1b_all_negative] and was distinguishable from zero in none
%[id:h1b_any_distinguishable]; a post hoc sweep of 231 %[id:ws_triplets] weightings found no
significant association with degraded callers %[id:ws_sn_kill_anc_triplets_significant_bh] %[id:ws_hr_kill_anc_triplets_significant_bh].
Degradation reached callers and almost never callees: no descendant of the faulted service
degraded in 179 of 180 runs %[id:descendant_affected_runs_zero].
