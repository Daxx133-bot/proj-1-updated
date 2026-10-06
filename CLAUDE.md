# Project Rules — Microservice Failure Analysis

These are standing rules for every session in this repository. They exist because a
research-integrity audit (`_audit/AUDIT_REPORT.md`, 2026-09-23) found fabricated and
hardcoded values in the manuscript pipeline. Do not relax them.

## Research integrity

1. **Never fabricate or hardcode experimental results.** No invented numbers, no
   "representative" values, no numbers typed directly into a manuscript, figure label,
   table or report generator.
2. **Every number in the paper must be produced by a script from raw logged data.**
   If a value cannot be traced to a script plus an input file, it does not go in the
   paper. Write `SOURCE NOT FOUND` rather than filling a gap.
3. **Never use random or synthetic data outside clearly labelled unit tests.**
   `random`/`np.random` is allowed only for (a) workload request randomisation inside
   load generators and (b) bootstrap/permutation resampling in statistics. It is never
   allowed to produce a measurement, an impact value or a recovery time.
4. **When a result is weaker than expected, report it honestly.** Do not adjust code,
   filter runs, retune weights, or swap datasets to produce a better number. A null
   result is a result.

## File handling

5. **Never delete files.** Move them to `_quarantine/` instead, preserving the relative
   path, and note the move in the commit message.
6. **Commit before and after each major change**, so every state is recoverable.

## Practical consequences

- Metric weights must be fixed before looking at outcome data, or the tuning must be
  reported and evaluated on held-out data. Grid-searching weights against the same
  outcome you then report is leakage.
- Impact values must come from measurement, never from graph structure or centrality.
- A metric's definition in the paper must match what the code computes. If the code
  measures container restart time, the paper says container restart time.
