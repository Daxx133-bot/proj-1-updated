# 5. Discussion

## 5.1 Why fan-out points the wrong way

The direction of propagation is the result we would defend with the least hesitation. In 179
of 180 runs %[id:descendant_affected_runs_zero] no descendant of the faulted service degraded,
and the service-level median of degraded descendants was zero for every service under both
fault types %[id:descendant_affected_count_constant_at]. The set of services that degraded
also barely depended on how the fault was delivered. For 17 of the 18
%[id:fault_invariant_services_all] %[id:fault_invariant_services_all_total] services, the five
per-run counts were identical whether the service was killed or slowed down.

The reading we find most plausible is that a caller suffers while it waits on a dependency
that has died or slowed, whereas a callee simply receives fewer requests and has nothing to
wait for. Our measurements fit that reading, but they do not test it. The degradation rule
asks only whether a service's own latency or error rate rose past a threshold, and it never
observes waiting directly, so the mechanism remains an interpretation.

If the reading is right, a fan-out ranking scores the wrong end of each edge. The
composition service in Social Network is the clearest case. It calls 7
%[id:composepost_out_degree] services and the fan-out metric ranks it first, yet when it was
faulted it had exactly one degraded caller in each of its 10 %[id:composepost_runs_total]
runs, and in a post-hoc breakdown that caller was always the gateway
%[id:composepost_runs_only_gateway_ancestor]. Across all services, the metric's correlation
with degraded callers was negative in every cell and separable from zero in none (§4.2). We
read that as an absence of support for the fan-out premise. The data cannot show a negative
relationship.

## 5.2 A predictor that sits close to its outcome

The caller count correlates with degraded callers partly by construction, since the outcome
counts a subset of the predictor. Whenever every ancestor of a faulted service degrades, the
two are equal. That happened for every Hotel Reservation service %[id:saturation_hr_kill_service]
and for ten of the eleven Social Network services %[id:saturation_sn_kill_service].

A post-hoc breakdown of the degraded ancestors makes the point sharper. In all 180 %[id:gw_runs_gateway_degraded_all] %[id:gw_runs_all] runs the gateway was one of them, and in both applications every analysable service has the gateway among its graph ancestors %[id:gw_sn_services_gateway_ancestor] %[id:gw_hr_services_gateway_ancestor] %[id:gw_sn_services_gateway_ancestor]
%[id:gw_hr_services_gateway_ancestor]. Every measured ancestor count therefore includes one
unit that is the same for every service. What remains to be explained comes from the
intermediate callers, and in Social Network only `user-service` departs from its graph
count in a consistent way. It has 4 %[id:userservice_ancestor_count] graph ancestors and
registered 2 %[id:userservice_measured] degraded ancestors in all five kill runs
%[id:userservice_runs_departing]. Its two ancestors that degraded sit on request paths the
workload exercises, and its other two showed no degradation in any run. We formed that explanation after seeing
the data and have not tested it.

The leave-one-out check, also post hoc, shows what follows from this. With `user-service`
withheld, the Social Network correlation becomes 1.000 %[id:loo_userservice_rho]. A reader
can fairly treat the Social Network result as resting on one service's worth of independent
information. We think the lesson extends past this study in one narrow sense: any structural
predictor tested against a structurally defined outcome needs a saturation measure reported
next to the correlation, or the correlation cannot be interpreted.

## 5.3 What users would see

The preregistered outcome counts degraded services. It says nothing about how many requests
fail. To get closer to what a user experiences, we looked after the fact at the gateway's
end-to-end error rate under kill faults. This analysis is exploratory and descriptive, and
none of its tests enters a preregistered family.

Gateway error followed the request mix. For each faulted service we summed the Locust task
weights of the request types whose traces pass through it, and divided by the total weight.
The rank correlation between that share and the median gateway error was 0.788
%[id:uf_sn_rho_err_weight_share] on Social Network and 0.964 %[id:uf_hr_rho_err_weight_share]
on Hotel Reservation. These are descriptive values with no p-value attached. In Hotel
Reservation, killing `reservation`, which sits on request types carrying 0.727
%[id:uf_hr_reservation_weight_share] of the weight, gave a median gateway error rate of
0.7340 %[id:uf_hr_reservation_err_median]. Killing `recommendation`, with a share of 0.091
%[id:uf_hr_recommendation_weight_share], gave 0.0860 %[id:uf_hr_recommendation_err_median].
The mix does not explain everything. The Social Network services reached only through the
compose request all share a weight of 0.300 %[id:uf_sn_compose_post_service_weight_share],
and their median error rates still range from 0.1692 %[id:uf_sn_unique_id_service_err_median]
to 0.2571 %[id:uf_sn_compose_post_service_err_median].

The hybrid metric's exploratory correlation with gateway error on Social Network was 0.786
%[id:uf_test_sn_hybrid_rho], not significant after correction within its family
(adjusted p = 0.0913 %[id:uf_test_sn_hybrid_bh_p]). Splitting the metric into its weighted
terms shows where that association comes from. The in-degree term alone has a rank
correlation of 0.715 %[id:uf_sn_rho_err_term_in] with gateway error, the fan-out term 0.310
%[id:uf_sn_rho_err_term_fanout] and the betweenness term 0.229 %[id:uf_sn_rho_err_term_btw].
The association the metric shows here follows the count of direct callers more closely than the fan-out correction, so it lends that correction no support.

## 5.4 Lessons about measurement

Two measurement choices mattered more than we expected when we planned the study. The first
is where latency is attributed. Charging each trace's end-to-end latency to every service on
the trace makes services on a shared path indistinguishable. In the pilot comparison of
§3.5 that shortcut flagged five non-faulted services where per-service attribution flagged
one %[fig:fig_q3_artifact — paper/figures/fig_q3_artifact_data.csv]. The correction was in
place before the campaign began, so we cannot say what an uncorrected campaign would have
concluded. The pilot shows how it would have behaved.

The second is that per-service attribution is only as good as the instrumentation behind
it. Social Network's spans carry no span-kind tag, so its per-service latency drew on all of
a service's spans, and 49.7% %[id:sn_spans_selected_client_pct] of those were client spans.
A post-hoc replay limited to server spans altered 2 %[id:replay_runs_changed] of the 110 %[id:replay_runs] run outcomes and none of the service-level medians %[id:replay_service_medians_changed]
%[id:replay_service_medians_changed]. We were fortunate that the change was this small. A
study that depends on span semantics should check them before collecting data, which we did
not do.

## 5.5 Implications for practitioners

For a team that has to rank services before running any experiment, our data favour looking
up the graph at callers over looking down it at callees. That recommendation rests on the
propagation pattern and on the lack of support for fan-out. The preregistered test of the
caller ranking itself did not reach significance, so we do not claim it predicts failure
impact. In both applications, the post-hoc breakdown of §5.2 found the gateway in every caller count, and in the exploratory analysis of §5.3 the user-visible error rate tracked how much traffic passed through the failed service. A ranking that weights
callers by the traffic they carry may therefore be worth testing, as a new preregistered
hypothesis. We did not test it.

The applications are benchmarks, and we did not configure or study containment mechanisms such as retries with back-off or circuit breakers, which could change how far a failure travels. Larger applications would also lift the ceiling
that eleven services place on any correlation, and a direct check that injected faults have
been removed would close the gap described in §6.5.
