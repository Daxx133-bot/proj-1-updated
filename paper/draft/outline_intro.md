# 1. Introduction — paragraph outline

Not prose. One line per paragraph: its job, and the evidence it draws on. Ledger references
are section numbers in `paper/CLAIMS_LEDGER.md`; ids are `paper/numbers.csv` claim_ids.

| ¶ | Purpose | Draws on |
|---|---|---|
| 1 | Open on the operational problem: teams must decide which services to harden first, and dependency-graph centrality is the obvious way to rank them without running experiments. Establish that this is a prediction problem, not a description problem. | No numbers. [CITATION NEEDED: microservice reliability / operational criticality ranking] |
| 2 | State the intuition the field has inherited: a service that calls many others is a hub, and hubs matter. Name the fan-out premise explicitly, since it is what the paper tests. | No numbers. [CITATION NEEDED: graph centrality for software dependency risk] |
| 3 | Turn the premise around. When a service fails, the services that *notice* are the ones waiting on it, that is, its callers. Callees are idle, not broken. State this as the causal argument that motivates the reversal, and note that it predicts the opposite ranking from fan-out for exactly the services fan-out considers most critical. | Ledger §6.1. Setup only, no numbers here. |
| 4 | Introduce the concrete case that makes the disagreement sharp: Social Network's composition service, ranked first by the fan-out metric and last by transitive callers. Preview that measurement sides with callers. | `composepost_rank_hybrid`, `composepost_rank_ancestor_count`, `composepost_set_size`, `composepost_out_degree`, `composepost_descendants`, `composepost_kill_mean`. Ledger §6.1, §6.2 (SUPPORTED). Must not imply generality here; §6.3 forbids it. |
| 5 | State what we did: preregistered the hypotheses and the full analysis before collecting, then ran a balanced fault-injection campaign across two applications, two fault types and five repetitions per cell. Emphasise that the analysis plan was locked before any data existed. | `campaign_runs_total`, `campaign_cells`, `campaign_reps_per_cell`, `campaign_architectures`, `campaign_fault_types`, `sn_runs`, `hr_runs`. Ledger §8.1. |
| 6 | Give the headline result without softening: the preregistered hypothesis is not confirmed. Zero of 44 confirmatory tests survive correction, and the same holds in the replication family. Report the point estimate alongside, so the reader sees both. | `conf_family_significant`, `conf_family_size`, `repl_family_significant`, `repl_family_size`, `primary_rho`, `primary_p_bh_locked`, `fdr_q`. Ledger §1.1–1.3. **Wording constrained by §1.4 and §1.5: no "marginal", no "would be significant with more data".** |
| 7 | Give the second headline, which is positive and robust: degradation travels to callers, not callees, in 179 of 180 runs, with a service-level median of zero everywhere. Note that this cannot be expressed as a correlation because the outcome has no variance, which is why it appears as a structural result rather than a test. | `descendant_affected_runs_zero`, `descendant_affected_runs_zero_pct`, `descendant_affected_count_constant_at`, `expl_undefined`, `expl_attempted`. Ledger §5.1, §5.4. **§5.3 forbids "never".** |
| 8 | State the H1b result in the exact form the ledger permits: the fan-out metric's correlation with blast radius is negative in all four architecture-by-fault cells and distinguishable from zero in none of them. | `h1b_all_negative`, `h1b_any_distinguishable`, `h1b_cells`, `h1b_sn_kill_rho`, `h1b_hr_kill_rho`. Ledger §2.1, §2.2. **§2.3 forbids the word "anti-predictive".** |
| 9 | Be explicit about what limits the study before the reader discovers it themselves: the analysis unit is the service, so n is 11 and 7; one application is saturated and reported directional-only; and the primary predictor is close to definitional. Frame these as registered in advance, not offered afterwards. | `power_sn_n`, `power_hr_n`, `saturation_hr_kill_tautological`, `saturation_sn_kill_service`, `power_hr_ceiling_p`. Ledger §3.1, §4.2, §4.4. |
| 10 | Disclose the provenance in one short paragraph: an earlier version of this work was withdrawn after a self-audit found fabricated results, and the pipeline was rebuilt under a locked preregistration. Point to §6. Keep it factual and brief; the full account belongs in §6. | `deviations_total`, `quarantine_items`, `hybrid_weights_lockfile_exists`, `hybrid_weights_reoptimised_on_campaign`. Ledger §8.4, §8.5. |
| 11 | List contributions and close with a roadmap. Contributions: a preregistered test of the fan-out premise that reports a null; a per-service latency attribution that avoids the trace-cohort artifact; a structural result on propagation direction; and a fully traceable artifact in which every reported number is regenerable from raw data. | `campaign_runs_total`, `integrity_checks_passed`. Ledger §7.1, §8.1, §8.3. |

## Constraints carried into this section

- Paragraph 6 must not hedge the null. Ledger §1.4 and §1.5 mark "predicts blast radius" and
  "approaches significance" UNSUPPORTED.
- Paragraph 4 may present `compose-post-service` only as a case, never as generalising
  (§6.3).
- Paragraph 8 must avoid asserting a negative relationship (§2.3).
- Any claim not in the ledger has not been checked and must not appear here.
