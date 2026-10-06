# Preregistration v3

**Study:** Identifying Failure-Prone Microservices Using Graph Centrality Metrics
**Version:** 3 (2026-09-25). Supersedes v2 (same day, archived at
`_audit/preregistration_versions/PREREGISTRATION_v2.md`) and v1 (2026-09-23).
**Status:** READY TO LOCK. All three v2 open questions are resolved and recorded in §11.
**Supersedes:** every analysis in `_quarantine/` and every number in the current
manuscript drafts.

Changes from v2 are marked **[v3]**. All of them stem from measured pilot behaviour
(`_audit/PILOT_FINDINGS.md`, `_audit/CAUSAL_DIRECTION.md`, `_audit/Q3_VALIDATION.txt`) or
from decisions recorded in §11 — none from preference, and none from seeing a result the
campaign has not produced yet.

---

## 0. Why this exists

An audit (`_audit/AUDIT_REPORT.md`) found the prior results were produced by a dataset in
which 48 of 107 rows came from `random.uniform()` keyed to each service's own centrality,
by weights grid-searched against the outcome they were then validated on, and by an
outcome variable that measured container restart rather than application recovery. The
headline ρ = 0.897 was a maximum over a search on 49%-synthetic data; on the cleanest real
dataset the same quantity is ρ = 0.0605, p = 0.85.

---

## 1. The hypothesis reversal, stated plainly **[v3 — expanded]**

This section exists because the confirmatory campaign no longer tests the mechanism the
project was designed around. That has to be on the record before any data is collected.

### 1.1 What v1 predicted

The fan-out-corrected hybrid metric weights **out-degree** (callees) and adds a fan-out
multiplier φ. Its premise: **a service with many callees is critical, because its failure
severs many downstream dependencies at once.** H1 predicted that hybrid criticality would
correlate with measured blast radius, and H2 held up `compose-post-service` (out-degree 7,
10 descendants) as the paper's central case — a service classical centrality allegedly
"missed".

### 1.2 The causal chain, re-derived

Let `X → Y` mean "X calls Y". Kill Y:

* **X (a caller, i.e. an ANCESTOR of Y)** issues an RPC to Y, receives connection-refused
  or blocks until timeout, and therefore errors or slows. **X degrades.** X's own callers
  then see X slow, so the effect climbs transitively through the whole ancestor set.
* **Z (a callee, i.e. a DESCENDANT of Y)** is never called, because Y — the thing that
  called Z — is dead. Z receives *less* traffic and goes **idle**. An idle service shows
  no latency or error anomaly.

Failure propagates **up** the call graph, toward callers. The size of the degraded set is
governed by **|ancestors(Y)|**, a transitive *in-degree* property. Out-degree predicts how
many services go **idle**, which is not an impact.

### 1.3 What the pilot showed

Across all 8 kill-fault pilot runs
(`data/pilot/recomputed_pilot_outcomes.csv`, via `tools/recompute_pilot.py`):

| | |
|---|---|
| `ancestor_affected_count == |ancestors|` | **8 / 8 runs** |
| Descendants degraded, summed over all runs | **0** |
| `compose-post-service` (out-degree 7, 10 descendants) | blast radius **1** |
| `media-service` (out-degree 0, 2 ancestors) | blast radius **2** ancestors + 5 unrelated |

Out-degree was **anti-predictive**: the out-degree-7 service degraded one other service;
an out-degree-0 service degraded two.

### 1.4 What the confirmatory campaign now tests

**H1 [v3].** `ancestor_affected_count` is predicted by **`ancestor_count`** — the number
of transitive callers — and **not** by out-degree, descendant count, or the
fan-out-corrected hybrid metric.

**H1b [v3, directional and preregistered].** The hybrid metric is **anti-predictive**:
its Spearman ρ against `ancestor_affected_count` is **≤ 0**. This is stated as a
hypothesis, not discovered afterwards, so that a negative ρ is a preregistered finding
rather than a salvaged one. On the canonical graphs the hybrid metric's rank correlation
with `ancestor_count` is already **−0.089 (SN)** and **−0.258 (HR)**
(`_audit/PREDICTOR_TABLE.txt`), so a negative outcome correlation is the expected result
if H1 holds.

**H2 [v3 — status changed].** v1's H2 was "classical composite centrality demotes
high-fan-out orchestrators relative to their measured impact." Under the corrected
direction this is no longer a claim of a *false negative*:

> `compose-post-service` ranks **11 of 11 — last — on `ancestor_count`**, while ranking
> **1 of 11 — first — on the hybrid metric.** A complete inversion. The corrected
> predictor says it is the *least* impactful service in the Social Network analysis set,
> and the pilot measured exactly that (blast radius 1, the smallest observed).

H2 is therefore retained only as a **structural, non-inferential observation**: classical
composite ranking and the hybrid metric disagree about this service. Whether that
disagreement is a *failure* of classical centrality is precisely what H1 tests, and the
pilot evidence currently points the other way. **The paper must be prepared to report that
its central example was ranked correctly by the metrics it set out to criticise.**

**H0 for all of the above:** no monotone association beyond chance. **H0 is a publishable
outcome.**

---

## 2. The hybrid metric — exact formula (unchanged)

$$
\mathrm{Criticality}(v) = w_{in}C_{in}(v) + w_{out}C_{out}(v)\phi(v) + w_{btw}C_{btw}(v),
\qquad \phi(v) = \frac{d^{+}(v)}{\max_u d^{+}(u)}
$$

| Term | Definition | NetworkX |
|---|---|---|
| $C_{in}$ | in-degree centrality, $d^-/(n-1)$ | `in_degree_centrality` |
| $C_{out}$ | out-degree centrality, $d^+/(n-1)$ | `out_degree_centrality` |
| $C_{btw}$ | betweenness, **directed** normalisation | `betweenness_centrality(normalized=True)` |
| $\phi$ | fan-out weight, **linear** | — |

Three corrections carried into the manuscript: φ is **linear** (the manuscript also states
a quadratic form the code never implemented; they coincide only for the maximum-out-degree
node); degree centrality divides by $(n-1)$, not $2(n-1)$; eigenvector centrality is
**L2**-normalised.

The metric is **retained in full** as a comparator. It is not being removed because it is
expected to fail — a metric that fails a fair test is a result.

---

## 3. Weight protocol (unchanged: cross-arch)

Tune $(w_{in}, w_{out}, w_{btw})$ on **Social Network only**, grid step 0.05 (231
triplets); freeze to `centrality/output/tuned_weights.lock.json`; evaluate **once** on
**Hotel Reservation**. The tuning-set ρ is not a result and is reported only as "maximum
over 231 triplets". Enforced in code: `--protocol` is required, re-tuning over an existing
lockfile is refused, and a second evaluation is refused.

---

## 4. Analysis set — gateway exclusion (unchanged from v2)

Services with **in-degree 0 in the SDG** are excluded from all quantitative correlation
analysis. Such a service receives traffic only from the external load generator, which is
not a graph node, so it has **`ancestor_count` = 0 by construction** and cannot vary on
the primary predictor. Killing it also takes the whole application down, leaving the
outcome undefined.

| Architecture | Excluded | Analysis n |
|---|---|---:|
| Social Network | `nginx-web-server` | **11** |
| Hotel Reservation | `frontend` | **7** |

Both remain in the paper as **qualitative examples, explicitly labelled**:
*"excluded from correlation analysis — sole entry point; has no ancestors by construction,
and its failure leaves the outcome measure undefined."*

Implemented as `measurement/blast_radius.is_gateway`.

> This costs Hotel Reservation its highest-fan-out service (`frontend`, out-degree 5).
> That is a scope limitation to state, not a result.

---

## 5. Predictors **[v3 — primary changed]**

`ancestor_count` is the **PRIMARY predictor**. All others are comparators. None may be
dropped after seeing results.

Implementation: `centrality/hybrid_weight_optimizer.ancestor_count(G)` is defined as
`descendant_count(G.reverse(copy=False))` — the ancestors of *v* in *G* are exactly the
descendants of *v* in reversed *G*, so there is a single traversal implementation rather
than two. Verified against `nx.ancestors` in `tests/test_structural_metrics.py`.

| # | Predictor | Role | Note |
|---:|---|---|---|
| 1 | **`ancestor_count`** | **PRIMARY** | transitive callers; the predictor the causal chain supports |
| 2 | Hybrid criticality | comparator **under test** | §2; hypothesised anti-predictive (H1b) |
| 3 | Degree | comparator | `degree_centrality` |
| 4 | In-degree | comparator | direct callers |
| 5 | Out-degree | comparator | fan-out; predicted *not* to work |
| 6 | Betweenness | comparator | directed |
| 7 | Closeness | comparator | — |
| 8 | Eigenvector | comparator | L2 |
| 9 | PageRank | comparator | α = 0.85 |
| 10 | Composite | comparator | mean of 7 normalised ranks, ties `method="min"` |
| 11 | Descendant count | comparator | reachable set |
| 12 | Dominator subtree size | comparator | nodes disconnected on failure |

### 5.1 Degenerate predictors, declared in advance **[v3]**

A predictor that is **constant** across an architecture's analysis set has an undefined
Spearman ρ. This is a degeneracy of the graph, **not a null result**, and such a pair is
excluded from the test family so it does not dilute the FDR correction. Computed by
`tools/compute_test_family.py` from `data/analysis/predictor_table.csv`:

| Predictor | Architecture | Distinct levels | Status |
|---|---|---:|---|
| In-degree | Hotel Reservation | **1** (every non-gateway service has in-degree 1) | **undefined — excluded** |
| Eigenvector | Social Network | **1** (all 0.0; the reconstructed SDG is a DAG) | **undefined — excluded** |

Both are **reported in the paper as undefined, with the reason**, never as ρ = 0 and never
silently omitted.

### 5.2 Tie structure, declared in advance **[v3]**

`ancestor_count` on the analysis sets (`_audit/PREDICTOR_TABLE.txt`):

| Architecture | n | Values | Distinct levels |
|---|---:|---|---:|
| Social Network | 11 | 1, 2, 2, 2, 2, 2, 3, 3, 3, 4, 4 | **4** |
| Hotel Reservation | 7 | 1, 1, 1, 1, 1, 2, 2 | **2** |

Ties cap the attainable ρ. See §7.2 for the consequence.

---

## 6. Outcomes

### 6.1 Per-service metric semantics **[v3 — Q3 FIXED]**

**This was a measurement bug and it is fixed at source.**

Before: `compute_latency_percentiles` took **root-span** durations from whatever traces it
was handed, and `get_traces_in_window(service=X)` returns every trace that *touches* X.
"Service X's p95" was therefore the **end-to-end p95 of X's trace cohort**. Error rate had
the identical defect: a trace counted as errored if *any* span errored, so a failure
anywhere on a path marked every service on that path.

After (`measurement/metrics_collector.select_spans`): a service's percentiles come from
the **server spans emitted by that service**. Client spans are excluded — a client span
emitted by X measures a *callee's* latency as observed by X, so counting it would
re-attribute a downstream service's slowness to X. Error rate is attributed to the service
whose own spans carry the error tag, with the denominator being the traces that service
actually appears in. If a service's spans carry no `span.kind` tag at all, the code fails
open to all of that service's spans and the sample count discloses it.

End-to-end root-span percentiles are still used **for the gateway only**, where they are
the correct quantity, and are labelled `scope = "end_to_end_root"` in the returned dict so
the two can never be confused again.

**Validation** (`tools/validate_per_service_p95.py`, output in `_audit/Q3_VALIDATION.txt`),
on a real 1644-trace / 16 970-span Hotel Reservation corpus:

| Service | OLD p95 (root-span) | NEW p95 (own spans) | Ratio |
|---|---:|---:|---:|
| geo | 15.90 | 0.55 | 28.9× |
| rate | 15.90 | 2.61 | 6.1× |
| reservation | 15.90 | 2.63 | 6.1× |
| search | 15.90 | 6.17 | 2.6× |
| profile | 15.24 | 1.75 | 8.7× |
| recommendation | 4.39 | 0.14 | 31.4× |
| frontend (gateway) | 14.66 | 14.66 | 1.0× |

Four services reported the **identical number, 15.90 ms**, under the old rule. Their own
spans differ by up to 4.8× among themselves and by 105× across the set.

**Validation against the pilot's misclassification.** The old rule's flagged set is
deterministic: it is the faulted service's *trace cohort*. In the HR workload the search
path emits one trace containing exactly
`{frontend, geo, profile, rate, reservation, search}`. The rule therefore predicts the
flagged set `{frontend, geo, profile, rate, reservation}`. Both HR search latency pilot
runs flagged **exactly that set — an exact match, in both runs** — including `profile` and
`reservation`, which are **neither ancestors nor descendants of `search`** and were flagged
purely for sharing a trace.

> **Stated limit of this validation.** The pilot's own fault-window spans were **not
> persisted** — Jaeger ran with in-memory storage and the per-run JSON stores only
> aggregates — so the corrected per-service p95 **cannot be recomputed for those runs**.
> What is shown above is that the old number was *structurally incapable* of separating
> these services, and that it predicts the observed flagged set exactly. A direct
> measurement of corrected per-service p95 under a live latency fault requires a fresh
> run. **[v3] The campaign runner therefore persists raw spans for every run** (§9), so
> this class of question is never again unanswerable after the fact.
>
> The 14 pilot runs are reclassified as **method development**. Their A/D/U columns are
> not comparable to campaign data and will not be pooled with it. The kill-fault ancestor
> result (§1.3) is unaffected: under kill, descendants stop appearing in traces at all, so
> the affected set was driven by error rate on services that were still receiving traffic,
> not by inherited percentiles.

### 6.2 Blast radius — three columns, never one

For every service flagged as degraded during the fault window, classify its graph relation
to the faulted node and store all three counts separately
(`measurement/blast_radius.classify_affected`):

| Column | Meaning |
|---|---|
| **`ancestor_affected_count`** | **PRIMARY OUTCOME.** Degraded services that are transitive callers of the faulted node. |
| `descendant_affected_count` | Degraded transitive callees. Expected ≈ 0 for kill faults. |
| `unrelated_affected_count` | Neither — shared-resource or synchronous-fan-out contention. |

They are **never summed into a single total**.

### 6.3 Recovery time $T_{rec}$ (unchanged from v2)

> Elapsed seconds **from fault REMOVAL** — the restart command returning, or the netem
> rule expiring — until Δp95, Δp99, Δerror-rate and downstream-affected-count are
> **simultaneously** within **10%** of their pre-fault baseline and **hold** for a **5 s**
> confirmation period.

- Measured from removal, not injection: v1 measured from injection, which made $T_{rec}$ =
  `fault_duration` + restart + convergence and floored it at ~34 s. Re-basing the 8 pilot
  runs moved them from 42–56 s to **8.5–22.1 s**.
- Tolerance is **one-sided**; an empty or thin window is "no signal", never "recovered";
  a window never reaches back before the fault instant.
- **Tolerance stays at 10%.** No exception is made for the censored runs; the cold-cache
  hypothesis for one of them is a footnote in `_audit/PILOT_FINDINGS.md` §A4 and **is not
  a rule exception**.

**Censoring.** Not recovered within **180 s** ⇒ `recovery_time_s = None`,
`recovery_censored = True`, `recovery_observed_until_s` records follow-up. **Never filled
with a number.**

**No clustering at the poll floor.** Measured over 14 pilot runs: kill $T_{rec}$ took 9
distinct values spanning 13.84–56.47 s against an effective resolution of 1.44 s, with 0
of 9 at or near the floor. Latency likewise. The measurement resolves genuine variation
rather than quantising to the poll interval.

### 6.4 Sampling (unchanged from v2)

- **Lagged probe window:** query `[now − 15 s, now − 5 s]`, not `[now − 10 s, now]`.
  Jaeger flushes spans in batches; a window ending at "now" samples a partially-written
  interval.
- **Minimum 20 traces** per sample before its percentiles may vote for recovery.
- Nominal poll 1 s; **measured effective resolution 1.4–2.4 s** (each iteration issues
  `1 + N_services` Jaeger queries). The paper reports the measured figure.

Verified by 2 confirmation runs on the exact condition that exhibited the defect:

| | median traces/sample | thin samples voting "recovered" | $T_{rec}$ |
|---|---:|---:|---:|
| before | 13, 18 | **6, 4** | 8.48, 9.84 |
| after | **38, 34** | **0, 0** | 13.84, 16.47 |

$T_{rec}$ is *larger* after the fix because the old values declared recovery early on
1–17-trace windows.

### 6.5 Which indicator is valid for which fault type

**Δp95 is invalid as a severity measure for kill faults.** Every HR kill produced Δp95 of
**−44 to −53 ms** while 51–56% of requests were failing: when a service dies its requests
fail fast, so the surviving latency distribution is dominated by fast failures and p95
*drops*. The sign is determined by the architecture, not by chance — across 10 kill runs
it is perfectly split:

| Application | n | Δp95 under kill |
|---|---:|---|
| Hotel Reservation | 4 | **all negative** (−44.0 to −53.4 ms) |
| Social Network | 6 | **all positive** (+1716 to +8867 ms) |

HR's Go services refuse the connection and return HTTP 500 in ~5 ms, so the tail *shrinks*;
SN's Thrift clients block until timeout, so the tail *inflates*. **Δp95 must never be
pooled across architectures for kill faults.**

Conversely, error rate is **identically 0.000** in all latency runs — nothing fails, so it
carries no signal.

| Fault type | Primary indicator | Secondary | Not valid |
|---|---|---|---|
| **kill** | **error rate** (0.154–0.560, signal in 10/10) | $T_{rec}$ | **Δp95** — sign flips by architecture |
| **latency** | **Δp95** (130–185× baseline, positive 2/2) | $T_{rec}$ | **error rate** — identically 0.000 |

No single indicator is valid across both fault types. The analysis runs **per fault type
with its own primary indicator**, and never pools indicators across fault types or (for
kill Δp95) across architectures.

---

## 7. Statistical plan **[v3 — family recalculated]**

**Primary test.** Spearman ρ between each predictor and each primary outcome, **per
architecture** and **per fault type**, at the **service level** (n = 11 SN, n = 7 HR),
aggregating repetitions by the **median**.

**All p-values come from exact permutation tests** (exact enumeration where n! permits,
otherwise 10 000 permutations), **never** the asymptotic Spearman approximation. With
HR's 5/2 tie structure the asymptotic test has a measured false-positive rate of **0.097**
against a nominal 0.05.

**Censoring.** $T_{rec}$ is censored, so its confirmatory test is survival-based:
Kaplan–Meier by predictor tercile, **log-rank**, and **Cox proportional hazards** with the
predictor as a continuous covariate (hazard ratio + 95% CI) as the primary inferential
result. Spearman ρ is reported alongside, computed on uncensored observations only and
**labelled biased toward fast recoveries**. If under 10% of observations are censored,
Spearman is promoted to primary — that threshold is fixed here, in advance.

### 7.1 Multiple comparisons **[v3]**

Family sizes are **computed, not asserted**, by `tools/compute_test_family.py`:

| | |
|---|---:|
| Predictors | 12 |
| Architectures | 2 |
| Naive (predictor × architecture) pairs | 24 |
| Dropped as constant (§5.1) | 2 |
| **Testable pairs** | **22** |
| Confirmatory outcomes (`ancestor_affected_count`, $T_{rec}$) | 2 |
| **Confirmatory family — kill faults** | **44 tests** |
| **Replication family — latency faults** | **44 tests, corrected separately** |

Each family is corrected by **Benjamini–Hochberg FDR at q = 0.05** *within* the family.

**Why split rather than pool.** Pooling both fault types gives one family of 88 and
roughly halves every per-test threshold. The hypothesis is about how a service *failing*
propagates, and **kill is the canonical failure**; latency is a different failure mode with
a different primary indicator (Δp95 rather than error rate), so it is a **preregistered
replication** rather than 44 more tests of the same question. **This split is declared
before any campaign data exists and may not be revised afterwards.** If the confirmatory
and replication families disagree, both are reported and the disagreement is the finding.

**Exploratory family.** Δp95, Δp99, Δerror, `descendant_affected_count`,
`unrelated_affected_count` — corrected separately and **labelled exploratory** wherever
they appear.

**Effect size.** ρ with bootstrap BCa 95% CI (10 000 resamples); hazard ratio with 95% CI.
A significant result whose CI crosses a negligible effect is reported as **inconclusive**,
not as support.

### 7.2 Power — stated, not hedged

n = 11 and n = 7 services. **This study is underpowered at the service level and says so
plainly.** Increasing repetitions does not help: the unit of analysis is the service, and
there are only 11 and 7.

| | n | `ancestor_count` levels | best attainable ρ | permutation FPR at α = 0.05 |
|---|---:|---:|---:|---:|
| Social Network | 11 | 4 | 0.941 (p < 0.0001) | 0.054 |
| **Hotel Reservation** | **7** | **2** | **0.791 (p = 0.034)** | **0.097** |

**Hotel Reservation is held-out and DIRECTIONAL ONLY [v3, decision Q1].** Even a *perfect*
HR result is barely significant. HR is **never reported as confirmatory**, in any section,
for any predictor. All HR inference uses exact permutation tests. This is a structural
limit of two-benchmark designs and belongs in Limitations, not in a hedge.

---

## 8. Data collection plan **[v3 — CPU dropped]**

**Campaign = kill + latency only. CPU stress is out of scope [decision Q2].**

`pumba stress --cpu 2` produced only **1.86–2.03×** baseline p95 against latency's
**130–185×**; its blast classification **flipped between two runs of the same condition**
(A/D/U = 0/2/0 vs 1/0/0), i.e. noise-dominated at that effect size; and 1 of 2 runs
censored. It would have consumed ~90 runs and 4–5 h for the weakest signal. The paper
states CPU as out of scope **with these measured numbers**, not as an unexplained omission.

**Target: 5 repetitions per (service × fault type), balanced.**

| Architecture | Services faulted | Fault types | Reps | Runs |
|---|---:|---:|---:|---:|
| Social Network | 11 (gateway excluded) | 2 (kill, latency) | 5 | **110** |
| Hotel Reservation | 7 (gateway excluded) | 2 (kill, latency) | 5 | **70** |
| | | | | **180** |

The total is unchanged from v2's recommended option — v2's 180 already assumed kill +
latency. Dropping CPU removes the 270-run alternative, not runs from the plan.

- **Balance is mandatory.** Prior batches were unbalanced precisely on the services
  carrying the headline claims. A failed run is **re-run**, never topped up unevenly.
- Faults: Pumba `kill --signal SIGKILL`; `netem delay --time 500 --jitter 100`.
  netem is launched with `Popen` and the runner waits for that process before recording
  the removal instant — running it synchronously let the rule expire before the fault
  window began (`_quarantine/QUARANTINE_LOG.md` item 10).
- Protocol per run: 60 s warm-up → baseline → 30 s fault → recovery probe to 180 s → 20 s
  cooldown. **This is what will actually run**; the manuscript's stated protocol was never
  what the code did.
- **A run with `telemetry_ok = False` is discarded and re-run**, never analysed as zeros.
- The runner holds a PID lockfile and refuses to start concurrently — the defect that
  corrupted 3 SN pilot runs (`_quarantine/QUARANTINE_LOG.md` item 9).
- **[v3] Raw spans are persisted per run** (§9), so any future definitional change can be
  replayed instead of re-run.

**Measured timing.** Median run 116 s, mean 133 s over 14 pilot runs (max 244 s, censored).

| Scope | Runs | Estimated pure run time | Realistic with swaps / seeding / re-runs |
|---|---:|---:|---:|
| **kill + latency** | **180** | **~6.7 h** | **8–11 h** |

One stack at a time is a hard constraint (`_audit/MEMORY_CEILING.md`).

---

## 9. Campaign execution requirements **[v3 — new]**

The campaign runs unattended for 8–11 h, so these are preregistered properties of the
runner, not implementation details:

1. **Manifest-driven.** Every `(app, service, fault_type, repetition)` combination is
   enumerated up front with a status of `pending` / `running` / `done` / `failed` /
   `censored`. The manifest is the single source of truth for what has run.
2. **Resumable.** A combination already marked `done` is never re-run. Re-launching after
   an interruption continues rather than restarting.
3. **Crash-isolated.** A failure in one run — exception, dead container, unresponsive
   stack — is logged in full, marked `failed`, the stack is restored to a clean state, and
   the campaign continues to the next combination. One bad run never aborts the campaign.
4. **Single-stack enforcement.** `RunLock` guarantees one stack and one fault injection at
   a time.
5. **Append-only progress log**, readable without interrupting the process.
6. **Raw spans persisted per run**, so a definitional change can be replayed offline.

A failed combination is re-run to preserve balance (§8); a **censored** combination is a
**legitimate observation**, not a failure, and is never re-run to obtain a number.

---

## 10. Reporting commitments

1. **If the result is null, it is reported as null.** If the hybrid metric does not beat
   in-degree on the held-out architecture after FDR correction, the paper says the fan-out
   correction did not predict impact under this measurement setup. No predictor redefined,
   no fault type dropped, no service excluded, no outcome swapped to improve it.
2. **[v3] The hypothesis reversal is reported prominently**, in its own section, including:
   that the corrected causal direction **contradicts the hybrid metric's premise**; that
   `compose-post-service` — the paper's central "false negative" — has the **lowest
   `ancestor_count` in its analysis set and ranks 11/11 on the primary predictor while
   ranking 1/11 on the hybrid metric**; and that H1b predicts the hybrid metric is
   anti-predictive.
3. **Every number is produced by a script reading `data/raw/`, `data/pilot/` or
   `data/campaign/`**, with script and commit recorded. No number is typed into the
   manuscript by hand.
4. **All 44 confirmatory and all 44 replication tests are reported**, significant or not,
   with corrected p-values, plus the 2 excluded degenerate pairs and why.
5. **Deviations from this document are listed** in a "Deviations from preregistration"
   section with dates and reasons.
6. **The audit is cited.** The paper states that an earlier analysis was withdrawn after
   fabricated data was found, and what changed.
7. **[v3] The measurement bugs are disclosed**, with the pilot runs affected: the
   root-span per-service metric defect (§6.1), the blocking-`pumba` defect
   (`_quarantine/QUARANTINE_LOG.md` item 10), and the concurrent-run contamination
   (item 9).
8. **The structural result stands on its own.** That classical composite ranking and the
   fan-out hybrid disagree about high-fan-out orchestrators is reproducible from
   `data/graphs/` alone and needs no fault-injection data. If H1 is null this becomes the
   paper's main claim.

---

## 11. Decisions closed since v2 **[v3]**

| Question | Decision | Where it lands |
|---|---|---|
| **Q1 — Hotel Reservation's role** | **Held-out, directional only.** Exact permutation tests throughout; the asymptotic Spearman p-value is never used (measured FPR 0.097 at n = 7). **HR is never reported as confirmatory.** | §3, §7.2 |
| **Q2 — Fault types** | **Drop CPU entirely. Campaign = kill + latency.** | §8 |
| **Q3 — Per-service metric semantics** | **Fixed at source**, for percentiles *and* error rate. Validated against a real 16 970-span corpus and against both HR latency pilot runs by exact flagged-set prediction. The 14 pilot runs become **method development** and are not pooled with campaign data. | §6.1 |
| **Primary predictor** | **`ancestor_count`**, implemented by graph reversal reusing `descendant_count`. | §5 |
| **Comparators** | Hybrid, degree, in-degree, out-degree, betweenness, closeness, eigenvector, PageRank, composite, descendant count, dominator subtree size — all retained, none droppable post hoc. | §5 |
| **Gateways** | Excluded from quantitative correlation; retained as labelled qualitative examples. | §4 |
| **$T_{rec}$** | From fault removal; 10% tolerance unchanged; min-trace floor and lagged window retained. | §6.3, §6.4 |
| **FDR family** | **44 confirmatory (kill) + 44 replication (latency)**, corrected separately, derived by `tools/compute_test_family.py`. | §7.1 |

### One decision this document makes that v2 did not put to you

The **confirmatory / replication split** (§7.1) is mine, not one you specified. The
alternative is a single pooled family of 88 tests, which is more conservative but roughly
halves every per-test threshold on an already underpowered design. If you prefer pooling,
change §7.1 before locking — **it cannot be changed after the campaign starts.**

---

| | |
|---|---|
| **Locked by** | ______________________ |
| **Date** | ______________________ |
| **Commit at lock** | ______________________ |
