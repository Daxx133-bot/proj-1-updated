# III. Problem Statement and Hypotheses

> **Drafting note (not rendered).** Definitions restate PREREGISTRATION_v3_LOCKED.md §1.4, §2
> and §6.2 (ledger 14.1). A paragraph written `$$ ... $$` renders as a numbered display
> equation.

## A. Call Graph, Faults and Outcome

Let *G* = (*V*, *E*) be the directed call graph of an application, where *V* is the set of
services and an edge (*u*, *v*) ∈ *E* means that *u* calls *v* under the traced workload, and
let *u* ⇝ *v* denote a directed path from *u* to *v* in *G*. The ancestors of a service are the
services from which it can be reached, and its descendants are the services it can reach:

$$ anc(*v*) = {*u* ∈ *V* : *u* ⇝ *v*, *u* ≠ *v*} $$

$$ desc(*v*) = {*u* ∈ *V* : *v* ⇝ *u*, *u* ≠ *v*} $$

A fault *f* ∈ {kill, latency} applied to service *v* either terminates its process or delays
its network traffic (Section IV-F). In repetition *r*, the degraded set
*D*<sub>r</sub>(*v*, *f*) contains the services other than *v* whose own latency or error
rate crosses the degradation rule of Section IV-H during the fault window. The degraded set is
split into three disjoint parts by graph relation to the faulted service:

$$ *D*<sub>r</sub><sup>A</sup> = *D*<sub>r</sub> ∩ anc(*v*), *D*<sub>r</sub><sup>D</sup> = *D*<sub>r</sub> ∩ desc(*v*) $$

$$ *D*<sub>r</sub><sup>U</sup> = *D*<sub>r</sub> ∖ (anc(*v*) ∪ desc(*v*)) $$

The primary outcome of a service is the median over its repetitions of the number of degraded
ancestors, *Y*(*v*, *f*) = median<sub>r</sub> |*D*<sub>r</sub><sup>A</sup>(*v*, *f*)|, the number of
degraded callers. The counts of degraded descendants and of degraded
unrelated services are recorded separately and are never added to it, because a combined count
would discard the direction in which a failure travels.

## B. Predictors

The primary predictor is the number of transitive callers, *X*(*v*) = |anc(*v*)|, the caller count. The comparator of interest is the hybrid criticality metric of the original
proposal:

$$ HC(*v*) = *w*<sub>in</sub>*C*<sub>in</sub>(*v*) + *w*<sub>out</sub>*C*<sub>out</sub>(*v*)φ(*v*) + *w*<sub>btw</sub>*C*<sub>btw</sub>(*v*) $$

$$ φ(*v*) = *d*<sup>+</sup>(*v*) / max<sub>u</sub> *d*<sup>+</sup>(*u*) $$

Here *C*<sub>in</sub> and *C*<sub>out</sub> are in-degree and out-degree centrality,
*C*<sub>btw</sub> is betweenness with directed normalisation, *d*<sup>+</sup> is out-degree,
and the weights are *w*<sub>in</sub> = 0.4 %[id:hybrid_w_in], *w*<sub>out</sub> = 0.4
%[id:hybrid_w_out] and *w*<sub>btw</sub> = 0.2 %[id:hybrid_w_btw] (Section IV-D). The fan-out
weight φ is linear in out-degree, so the metric rewards services that call many others. Ten
further graph measures are kept as comparators. Each test pairs one predictor with one outcome
across the services of one application, with the gateway excluded (Section IV-C).

## C. Hypotheses

The hypotheses are those of the locked preregistration. H2 below carries the label H1b in that document, where the name H2 belongs to a structural
observation that is not tested here.

H1, the primary hypothesis, states that the caller count *X* predicts *Y*, whereas neither
out-degree nor descendant count predicts it, and neither does the hybrid metric. It is tested as
a positive Spearman rank correlation between *X* and *Y*:

$$ H1: ρ(*X*, *Y*) > 0 $$

H2 is directional. It states that the fan-out premise points the wrong way, so that the
hybrid metric is not positively associated with the outcome:

$$ H2: ρ(HC, *Y*) ≤ 0 $$

Under the null hypothesis of each test there is no monotone association between predictor and
outcome. Every p-value is two-sided and comes from a permutation test, and it is corrected
with the Benjamini-Hochberg procedure within its family (Section IV-I). Kill faults form the
confirmatory family, and latency faults repeat every test as a separate replication family.
