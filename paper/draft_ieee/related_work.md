# II. Related Work

## A. Graph Measures as Risk Indicators

Centrality has well-established definitions. Freeman's treatment separated several distinct
ideas of what makes a node central, some based on a node's direct ties and some on the
shortest paths that pass through it, and gave them normalised forms that are still in use
[@freeman1978]. Path-based measures were expensive to compute on large graphs until Brandes
published a fast algorithm for betweenness [@brandes2001]. NetworkX 3.6.1
%[id:version_networkx] (https://networkx.org), the graph library used in this study
[@hagberg2008], implements that algorithm.

Software engineering adopted these measures early. Zimmermann and Nagappan computed network
measures on the dependency graph of a software system and found that they helped predict
which components would contain defects [@zimmermann2008]. That work and the present study
share a premise, that a component's position in a dependency graph says something about its
risk. The outcomes differ. A defect count describes where bugs accumulate over a release,
while this study asks how far a run-time failure spreads once it has happened, which is a
property of the call pattern under load and not of the code alone.

## B. Fault Injection and Chaos Engineering

Deliberately injecting faults into a running system is now a standard way to learn how it
behaves under stress. Basiri and colleagues describe the practice as it developed at Netflix,
where engineers run controlled experiments on production systems to build confidence that
they tolerate failure [@basiri2016]. For microservices specifically, Gremlin offered a
framework for systematic resilience testing, injecting faults between services and checking
whether the application handles them as intended [@heorhiadi2016]. Lineage-driven fault
injection takes a different route. It reasons backwards from how a correct result was produced
to choose the faults most likely to expose a bug, so that fewer experiments are wasted
[@alvaro2015].

The use of fault injection in this study is narrower than any of these. It does not search for
bugs or validate fallbacks. Two fault types are injected into each service in turn, in a fixed
and balanced design, and the counts of degraded services serve as the outcome of a structural
prediction. The faults are a measuring instrument here.

## C. Call Graphs from Traces

Distributed tracing makes it possible to recover a service graph from what the system actually
does. Dapper established the model most tracing systems still follow: a request carries a trace
context across service boundaries, and each unit of work is recorded as a span with a parent,
so a request becomes a tree of spans [@sigelman2010]. Reading parent and child spans from
different services gives a caller-callee edge, which is how the graphs in this study were
built.

Graphs built this way depend on the traffic that produced them. Luo and colleagues analysed
call graphs from Alibaba's production traces and found them to be highly dynamic, changing from
one request to the next [@luo2021]. The benchmark graphs here are small and the workload is
fixed, so far less variation appears, but the same dependence on traffic affects the predictor,
as Section VII-F explains. The observed Hotel Reservation graph already differs from the one the
benchmark documents.

## D. Root-Cause Localisation

A large body of work starts from the other end of the problem. Given an anomaly that is already
happening, root-cause localisation tries to find the service responsible. MicroRCA is one
example. It builds a graph of the running system and ranks candidate services by how their
behaviour relates to the observed performance problem [@wu2020]. An industrial survey by Zhou
and colleagues documents how hard such diagnosis is in practice, and contributes a benchmark
system with injected faults for studying it [@zhou2021].

These methods use the graph after the fact, together with live metrics. The question here comes
earlier: whether graph structure alone, before any fault occurs, indicates which services will
do the most damage when they fail. The two problems share the dependency graph but ask
different things of it. The propagation direction reported in Section V-F may still be of
interest to diagnosis work, though no diagnosis method was studied.

## E. Preregistration and Multiple Testing

Preregistration separates the analyses planned before data are seen from those devised
afterwards, so that a reader can tell a test of a prediction from a search through the data
[@nosek2018]. Every hypothesis and analysis choice in this study was locked before the
campaign, every later departure was logged, and each post hoc analysis is labelled as such.
With 44 %[id:conf_family_size] %[id:repl_family_size] tests in each family, some correction for
multiple testing was unavoidable. The false discovery rate is controlled with the
Benjamini-Hochberg procedure [@benjamini1995], applied separately within each family, which
keeps the expected proportion of false positives among reported discoveries at the chosen
level while giving up less power than a family-wise correction would.
