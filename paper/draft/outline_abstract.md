# Abstract — sentence outline

Not prose. Target 180–220 words, structured abstract in continuous text (no headings).
Ledger references are section numbers in `paper/CLAIMS_LEDGER.md`; ids are
`paper/numbers.csv` claim_ids.

| # | Sentence | Draws on |
|---|---|---|
| 1 | Context: teams rank services for hardening by dependency-graph centrality, and the prevailing intuition treats high fan-out as high criticality. | No numbers. |
| 2 | Gap and reversal: when a service fails, the services that degrade are those waiting on it, so transitive callers rather than callees should predict impact; the two rankings disagree most sharply for exactly the services fan-out favours. | Ledger §6.1 as setup. No numbers. |
| 3 | Method: a preregistered fault-injection campaign of 180 balanced runs, two applications, two fault types, five repetitions per cell, with the analysis plan locked before collection. | `campaign_runs_total`, `campaign_cells`, `campaign_reps_per_cell`, `campaign_architectures`, `campaign_fault_types`. Ledger §8.1. |
| 4 | Primary result: the transitive-caller correlation is positive but does not survive the preregistered correction; no test in the 44-test confirmatory family is significant, and the replication family agrees. | `primary_rho`, `primary_p_bh_locked`, `conf_family_size`, `conf_family_significant`, `repl_family_significant`, `fdr_q`. Ledger §1.1–1.3. **§1.4, §1.5 constrain wording.** |
| 5 | H1b: the fan-out metric's correlation with measured blast radius is negative in all four architecture-by-fault cells and distinguishable from zero in none. | `h1b_all_negative`, `h1b_any_distinguishable`, `h1b_cells`. Ledger §2.1, §2.2. **§2.3 forbids "anti-predictive".** |
| 6 | Structural result: degradation reached callers and not callees in 179 of 180 runs, with a service-level median of zero in every condition, consistent across both architectures and both fault types. | `descendant_affected_runs_zero`, `descendant_affected_count_constant_at`, `fault_invariant_services_all`. Ledger §5.1, §5.5. **§5.3 forbids "never".** |
| 7 | Worked case: the service the fan-out metric ranks most critical of eleven ranks last on transitive callers, and degrades exactly one service in all ten of its runs. | `composepost_rank_hybrid`, `composepost_rank_ancestor_count`, `composepost_set_size`, `composepost_kill_mean`. Ledger §6.1, §6.2. **§6.3 forbids generalising.** |
| 8 | Honest scope: one application is saturated and reported directional-only, and its tie structure puts the best attainable p-value above the conventional threshold, so it could not have reached significance at any outcome. | `saturation_hr_kill_tautological`, `power_hr_ceiling_p`, `power_hr_n`. Ledger §3.1, §4.2. |
| 9 | Methodological contribution: attributing latency to each service's own spans rather than to the enclosing trace, which otherwise makes services on a shared request path indistinguishable and flags them together. | Figure 4 / `paper/figures/fig_q3_artifact_data.csv`. Ledger §7.1, §7.2. |
| 10 | Closing: report the artifact, in which every number regenerates from raw logged data, and note in one clause that this study replaces an earlier withdrawn analysis. | `integrity_checks_passed`, `deviations_total`. Ledger §8.3, §8.4. |

## Constraints carried into this section

- The abstract must lead with the null rather than burying it behind the structural result.
  Sentence 4 comes before sentence 6.
- No sentence may claim the caller ranking was demonstrated (§1.4) or that the fan-out metric
  is anti-predictive (§2.3).
- Sentence 10's clause about the withdrawn analysis is a factual disclosure, not an apology,
  and should occupy no more than one clause.
- Every id above already appears in `results.md`; the abstract introduces no new number.
