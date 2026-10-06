# 8. Conclusion — paragraph outline

Not prose. Four paragraphs, kept short. Ledger references are section numbers in
`paper/CLAIMS_LEDGER.md`; ids are `paper/numbers.csv` claim_ids.

| ¶ | Purpose | Draws on |
|---|---|---|
| 1 | Restate what was done in two sentences: a preregistered fault-injection campaign of 180 balanced runs across two applications and two fault types, testing whether dependency-graph centrality predicts measured failure impact. | `campaign_runs_total`, `campaign_cells`, `campaign_reps_per_cell`, `campaign_architectures`, `campaign_fault_types`. Ledger §8.1. |
| 2 | State the null as the primary finding, without softening and without apology. No test in either the confirmatory or the replication family survives correction, and the fan-out metric's correlation is negative everywhere but separable from zero nowhere. | `conf_family_significant`, `conf_family_size`, `repl_family_significant`, `repl_family_size`, `primary_rho`, `primary_p_bh_locked`, `h1b_all_negative`, `h1b_any_distinguishable`. Ledger §1.1–1.3, §2.1, §2.2. **§1.4, §1.5, §2.3 constrain the wording.** |
| 3 | State the structural finding as the result that survives: degradation reaches callers and not callees in 179 of 180 runs, with a service-level median of zero in every condition, consistently across both architectures and both fault types. Note that this is the claim the paper can defend without inference. | `descendant_affected_runs_zero`, `descendant_affected_runs_zero_pct`, `descendant_affected_count_constant_at`, `unrelated_affected_runs_zero`, `fault_invariant_services_all`. Ledger §5.1, §5.2, §5.5. **§5.3 forbids "never".** |
| 4 | Close on what the study offers a practitioner and a methodologist. For the practitioner: rank by transitive callers rather than fan-out, with the caveat that our test of the caller ranking did not reach significance. For the methodologist: measure saturation before reporting a structural predictor against a structurally defined outcome, and attribute latency to a service's own spans. End on the artifact being fully regenerable from raw data. | `composepost_rank_hybrid`, `composepost_rank_ancestor_count`, `saturation_hr_kill_tautological`, `saturation_sn_kill_service`, `integrity_checks_passed`. Ledger §6.1, §3.1, §7.1, §8.3. **§6.3 forbids generalising the case; §1.4 forbids claiming the caller ranking was demonstrated.** |

## Constraints carried into this section

- The conclusion must not introduce a claim that appears nowhere in §4. Every id above is
  already cited in `results.md`.
- ¶4's practitioner recommendation rests on mechanism and on the null for the alternative,
  not on a demonstrated predictive result. It must say so in the same sentence.
- No forward-looking claim about production systems (ledger §10).
