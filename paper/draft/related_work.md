# 2. Related Work

## 2.1 Graph measures as risk indicators

Centrality has well-established definitions. Freeman's treatment separated several distinct
ideas of what makes a node central, some based on a node's direct ties and some on the
shortest paths that pass through it, and gave them normalised forms that are still in use
[@freeman1978]. Path-based measures were expensive to compute on large graphs until Brandes
published a fast algorithm for betweenness, which is the one NetworkX, the library we use,
implements [@brandes2001].

Software engineering adopted these measures early. Zimmermann and Nagappan computed network
measures on the dependency graph of a software system and found that they helped predict
which components would contain defects [@zimmermann2008]. That work and ours share a premise,
that a component's position in a dependency graph says something about its risk. The
outcomes differ. A defect count describes where bugs accumulate over a release, while we ask
how far a run-time failure spreads once it has happened, which is a property of the call
pattern under load and not of the code alone. We are not aware of work that tests a
centrality ranking of microservices against failure propagation measured in a controlled,
preregistered campaign, though related ideas appear in the root-cause literature discussed
in §2.4.

## 2.2 Fault injection and chaos engineering

Deliberately injecting faults into a running system is now a standard way to learn how it
behaves under stress. Basiri and colleagues describe the practice as it developed at Netflix,
where engineers run controlled experiments on production systems to build confidence that
they tolerate failure [@basiri2016]. For microservices specifically, Gremlin offered a
framework for systematic resilience testing, injecting faults between services and checking
whether the application handles them as intended [@heorhiadi2016]. Lineage-driven fault
injection takes a different route. It reasons backwards from how a correct result was
produced to choose the faults most likely to expose a bug, so that fewer experiments are
wasted [@alvaro2015].

Our use of fault injection is narrower than any of these. We do not search for bugs or
validate fallbacks. We inject two fault types into each service in turn, in a fixed and
balanced design, and use the counts of degraded services as the outcome of a structural
prediction. The faults are a measuring instrument here.

## 2.3 Call graphs from traces

Distributed tracing makes it possible to recover a service graph from what the system
actually does. Dapper established the model most tracing systems still follow: a request
carries a trace context across service boundaries, and each unit of work is recorded as a
span with a parent, so a request becomes a tree of spans [@sigelman2010]. Reading parent and
child spans from different services gives a caller-callee edge, which is how we built our
graphs.

Graphs built this way depend on the traffic that produced them. Luo and colleagues analysed
call graphs from Alibaba's production traces and found them to be highly dynamic, changing
from one request to the next [@luo2021]. Our benchmark graphs are small and our workload is
fixed, so we see far less variation, but the same dependence on traffic affects our
predictor, as §6.6 explains. The Hotel Reservation graph we observed already differs from
the one the benchmark documents.

## 2.4 Root-cause localisation

A large body of work starts from the other end of the problem. Given an anomaly that is
already happening, root-cause localisation tries to find the service responsible. MicroRCA
is one example. It builds a graph of the running system and ranks candidate services by how
their behaviour relates to the observed performance problem [@wu2020]. An industrial survey
by Zhou and colleagues documents how hard such diagnosis is in practice, and contributes a
benchmark system with injected faults for studying it [@zhou2021].

These methods use the graph after the fact, together with live metrics. Our question comes
earlier: whether graph structure alone, before any fault occurs, indicates which services
will do the most damage when they fail. The two problems share the dependency graph but ask different things of it. The propagation direction we observe in §4.5 may still be of interest to diagnosis work, though we did not study any diagnosis method.

## 2.5 Preregistration and multiple testing

Preregistration separates the analyses planned before data are seen from those devised
afterwards, so that a reader can tell a test of a prediction from a search through the data
[@nosek2018]. We locked every hypothesis and analysis choice before the campaign, logged every later departure, and label each post-hoc analysis as such. With
44 %[id:conf_family_size] %[id:repl_family_size] tests in each family, some correction for multiple testing was unavoidable. We control
the false discovery rate with the Benjamini-Hochberg procedure [@benjamini1995], applied
separately within each family, which keeps the expected proportion of false positives among
reported discoveries at the chosen level while giving up less power than a family-wise
correction would.
