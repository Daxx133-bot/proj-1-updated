# 2. Related Work — topic outline and citation placeholders

Not prose. This lists the prior-work categories the section needs and what each must
establish. **No citation is supplied.** Every entry carries a `[CITATION NEEDED: ...]`
placeholder to be filled only with a verified source, showing exact title, authors, venue,
year and a DOI or resolvable link. Nothing in this file may be converted into a citation
without that verification.

## 2.1 Graph centrality and critical-node identification

| ¶ | Must establish | Placeholder |
|---|---|---|
| 1 | The classical result that a small number of highly connected nodes dominate structure and flow in real networks; this is the origin of the hub intuition the paper tests. | `[CITATION NEEDED: scale-free networks / preferential attachment and hub dominance]` |
| 2 | Formal definitions of the centrality measures used as comparators, in particular betweenness, closeness, eigenvector and PageRank, and their standard normalisations. | `[CITATION NEEDED: network centrality measures — formal treatment]` |
| 3 | That centrality-based ranking is undirected or direction-agnostic in much of its classical form, which is precisely the assumption a dependency graph violates, since a call edge is directed and failure propagates against it. | `[CITATION NEEDED: directed-graph centrality / asymmetric influence measures]` |

## 2.2 Centrality applied to software and service dependency graphs

| ¶ | Must establish | Placeholder |
|---|---|---|
| 4 | Prior work that ranks software components or services by graph centrality to predict fault impact, change risk or maintenance effort. This is the closest prior art and the work the paper's premise inherits from. | `[CITATION NEEDED: graph centrality for software dependency risk / fault-proneness]` |
| 5 | Prior work proposing composite or weighted centrality metrics for service criticality, and how those weights are chosen. Needed to position our a-priori-weight commitment against the common practice of fitting weights. | `[CITATION NEEDED: composite/weighted criticality metrics for microservices]` |
| 6 | Whether any prior work validates such rankings against measured failure impact rather than against another structural measure or expert judgement. If the honest answer is that validation is rare, say so and cite what exists. | `[CITATION NEEDED: empirical validation of criticality rankings against measured impact]` |

## 2.3 Failure propagation and cascading failure in distributed systems

| ¶ | Must establish | Placeholder |
|---|---|---|
| 7 | Models of cascading failure in networked systems, and specifically the direction such models assume propagation takes. This frames our §4.5 result. | `[CITATION NEEDED: cascading failure models in networked systems]` |
| 8 | Mechanisms by which a dependency failure reaches a caller in practice: synchronous blocking, connection-pool and thread-pool exhaustion, timeout and retry amplification. Needed to explain why callers degrade and callees do not. | `[CITATION NEEDED: synchronous dependency failure / resource exhaustion in service meshes]` |
| 9 | Resilience mechanisms that arrest propagation — circuit breakers, bulkheads, retries with backoff, load shedding — since their absence from our benchmarks is a stated limitation (§5.3). | `[CITATION NEEDED: circuit breakers and bulkhead patterns for failure isolation]` |

## 2.4 Chaos engineering and fault injection

| ¶ | Must establish | Placeholder |
|---|---|---|
| 10 | The chaos-engineering methodology of deliberate fault injection into running systems, and its use for empirical resilience assessment. | `[CITATION NEEDED: chaos engineering — principles and practice]` |
| 11 | Fault-injection tooling and the specific fault models we use, process kill and network delay via traffic control. | `[CITATION NEEDED: container fault injection tooling / netem-based network fault emulation]` |
| 12 | Prior fault-injection studies that quantify blast radius, and how they define and measure it. Needed to position our three-way ancestor/descendant/unrelated classification. | `[CITATION NEEDED: empirical blast-radius measurement in microservice fault injection]` |

## 2.5 Distributed tracing, dependency-graph extraction and measurement semantics

| ¶ | Must establish | Placeholder |
|---|---|---|
| 13 | Distributed tracing with propagated context and parent–child spans, which is what makes trace-based graph reconstruction possible. | `[CITATION NEEDED: distributed tracing — Dapper-style context propagation]` |
| 14 | Prior work reconstructing service dependency graphs from traces, and any that notes the gap between documented and observed topology. Supports §3.1 and §5.6. | `[CITATION NEEDED: trace-derived service dependency graph extraction]` |
| 15 | Work on latency attribution in traces, in particular the distinction between end-to-end request latency and a service's own service time. If prior work has documented the trace-cohort attribution artifact we describe in §3.5, it must be cited here; if it has not, that is a contribution and the section should say so carefully rather than claiming novelty by omission. | `[CITATION NEEDED: per-service latency attribution / critical path analysis in distributed traces]` |
| 16 | Tail-latency characterisation and percentile-based SLO measurement, which motivates p95 as the indicator. | `[CITATION NEEDED: tail latency in large-scale online services]` |

## 2.6 Benchmarks

| ¶ | Must establish | Placeholder |
|---|---|---|
| 17 | The benchmark suite the two applications come from, its design goals and its representativeness claims, plus the specific commit we pinned. | `[CITATION NEEDED: microservice benchmark suite used for both applications]` |

## 2.7 Research methodology

| ¶ | Must establish | Placeholder |
|---|---|---|
| 18 | Preregistration as a method for separating confirmatory from exploratory analysis, and the reasoning about researcher degrees of freedom that motivates it. Supports §3.8 and §6. | `[CITATION NEEDED: preregistration and researcher degrees of freedom]` |
| 19 | The multiple-comparisons procedure used, and the rationale for controlling false discovery rate rather than family-wise error. | `[CITATION NEEDED: Benjamini–Hochberg false discovery rate control]` |
| 20 | Permutation and bootstrap inference for small samples with heavy ties, justifying our departure from asymptotic p-values. | `[CITATION NEEDED: permutation tests and BCa bootstrap for small-sample rank statistics]` |

## Leads to verify, not citations

The project's own earlier report (`report_sections_2_3.pdf`, in the repository) cites works
that appear to match categories 1, 2, 10, 13 and 17 above. Those are **leads only**. They are
recorded here so the search is not started from nothing, and none may be entered in the
reference list until its exact title, authors, venue, year and DOI have been independently
verified. We have not verified them and therefore do not reproduce their bibliographic
details here.

## Constraints carried into this section

- Related Work makes no empirical claim about our data, so it cites no `numbers.csv` id.
- The only claim about our own contribution that may appear here is in ¶15, and it must be
  phrased as a gap we did not find rather than a gap that does not exist.
- If a category returns no verifiable source, the category is dropped from the section
  rather than filled with an approximate match.
