# Cover letter

> **Drafting note (strip before submission).** Rendered by `paper/build_docx.py` to
> `paper/submission/cover_letter.docx`. `{title}` and `{affiliation}` are replaced from `COVER` and
> `AFFILIATION` in `build_docx.py`.
> Trailing `%[id:...]` comments name the `paper/numbers.csv` claim_id each number comes from.

[TO FILL: date]

Dear Editors of PeerJ Computer Science,

We submit the manuscript "{title}" for consideration as a research article.

The study tests whether a service's position in the dependency graph tracks how many other
services degrade when it fails. We compared the number of transitive callers of each service
with a fan-out-weighted centrality metric in 180 %[id:campaign_runs_total] fault-injection
runs on two %[id:campaign_architectures] DeathStarBench applications. The hypotheses and the
full analysis were preregistered and locked before any campaign data existed.

The preregistered hypothesis was not confirmed. On one application under kill faults, caller
count and the number of degraded callers correlated at ρ = 0.785 %[id:primary_rho], but none
of the 44 %[id:conf_family_size] confirmatory tests survived the Benjamini-Hochberg correction
we committed to %[id:conf_family_significant], and the fan-out metric showed no detectable
association %[id:h1b_any_distinguishable]. The clearest finding concerns direction:
degradation reached the callers of the faulted service, and no callee degraded in 179 of 180
runs %[id:descendant_affected_runs_zero] %[id:campaign_runs_total].

We believe the paper suits PeerJ Computer Science because the journal evaluates submissions
on methodological soundness, not on perceived impact. The design was preregistered and every
deviation from it is reported. The code and raw trace data are openly available, together
with the scripts that produce every number in the manuscript.

We also disclose that an earlier analysis from this project was withdrawn after a self-audit
found results that had not come from measurement. Section 7 of the manuscript describes what
was withdrawn and the safeguards that followed.

The manuscript has not been published and is not under consideration elsewhere. An AI
assistant, Claude (Anthropic), was used for code development and review and for drafting and
language editing, as set out in the AI-Use Statement.

Sincerely,

Dakshrajsinh Tank, B.Tech student

Dr. Badrinath N, Assistant Professor

{affiliation}

Corresponding author: [TO FILL: corresponding author name and email]
