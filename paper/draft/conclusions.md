# 8. Conclusions

We ran a preregistered fault-injection campaign of 180 %[id:campaign_runs_total] balanced runs
on two benchmark applications to ask whether a service's position in its dependency graph
indicates how much damage its failure does. The design crossed every analysable service with
two fault types and five repetitions %[id:campaign_reps_per_cell], and the analysis was locked before the first run.

The correlational hypothesis did not survive. The number of transitive callers correlated
strongly with the number of degraded callers on Social Network, but after correction not one test survived in either family, the 44 %[id:conf_family_size] confirmatory and the 44 %[id:repl_family_size] replication tests alike %[id:conf_family_significant] %[id:repl_family_significant] %[id:conf_family_significant]
%[id:repl_family_significant]. The fan-out-weighted metric this project began with showed a
negative correlation in every cell %[id:h1b_all_negative] and could not be separated from zero
in any %[id:h1b_any_distinguishable].

What did hold is structural. Failures reached callers and almost never callees: no descendant
degraded in 179 of 180 runs %[id:descendant_affected_runs_zero], and the service-level median
was zero in every condition %[id:descendant_affected_count_constant_at]. This result needs no
inference, and it held in both applications and under both fault types.

For practitioners, this points towards ranking services by their callers and away from
ranking them by fan-out, with the caveat that our own test of the caller ranking did not reach
significance. For researchers, the study shows two steps that are easy to skip: attributing
latency to each service's own spans, and measuring how far the outcome merely restates a
structural predictor before reporting a correlation between them. Every number in this paper
can be regenerated from the logged campaign data.
