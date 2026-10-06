"""Unit tests for the Q3 per-service latency/error attribution fix.

Fixtures below are hand-written trace structures, not synthetic measurements: they
exist to pin down which spans the code selects, not to stand in for data.

The scenario throughout is the one that produced the pilot's misclassification:
    frontend -> search -> geo
with `geo` slow. Under the old root-span rule, "search's p95" and "frontend's p95"
were both the end-to-end trace duration, so a slow leaf made its ancestors look
degraded -- and any unrelated service on the same trace too.
"""

from __future__ import annotations

from measurement.metrics_collector import (
    compute_error_rate,
    compute_latency_percentiles,
    select_spans,
)


def _span(span_id, svc_pid, duration_ms, kind="server", parent=None, error=False):
    tags = [{"key": "span.kind", "type": "string", "value": kind}]
    if error:
        tags.append({"key": "error", "type": "bool", "value": True})
    return {
        "spanID": span_id,
        "processID": svc_pid,
        "operationName": "op",
        "duration": int(duration_ms * 1000),
        "startTime": 0,
        "tags": tags,
        "references": ([{"refType": "CHILD_OF", "spanID": parent}] if parent else []),
    }


def slow_leaf_trace(trace_id="t", geo_ms=900.0, search_own_ms=910.0, e2e_ms=920.0):
    """frontend -> search -> geo, with geo the actual source of the latency."""
    return {
        "traceID": trace_id,
        "processes": {
            "p1": {"serviceName": "frontend"},
            "p2": {"serviceName": "search"},
            "p3": {"serviceName": "geo"},
        },
        "spans": [
            _span("a", "p1", e2e_ms),                              # frontend server (root)
            _span("b", "p1", e2e_ms - 2, kind="client", parent="a"),
            _span("c", "p2", search_own_ms, parent="b"),           # search server
            _span("d", "p2", geo_ms + 1, kind="client", parent="c"),
            _span("e", "p3", geo_ms, parent="d"),                  # geo server
        ],
    }


def test_root_span_scope_is_end_to_end_not_per_service():
    traces = [slow_leaf_trace()]
    assert compute_latency_percentiles(traces)["scope"] == "end_to_end_root"
    assert compute_latency_percentiles(traces, service="geo")["scope"] == (
        "service_server_spans:geo"
    )


def test_per_service_p95_uses_only_that_services_server_spans():
    traces = [slow_leaf_trace(geo_ms=900.0, search_own_ms=910.0, e2e_ms=920.0)]
    assert compute_latency_percentiles(traces, service="geo")["p95_ms"] == 900.0
    assert compute_latency_percentiles(traces, service="search")["p95_ms"] == 910.0
    assert compute_latency_percentiles(traces, service="frontend")["p95_ms"] == 920.0
    # The old behaviour: every service inherited the same end-to-end number.
    assert compute_latency_percentiles(traces)["p95_ms"] == 920.0


def test_client_spans_are_excluded_so_callee_latency_is_not_reattributed():
    """search emits a 901ms client span waiting on geo; that is geo's latency, not search's."""
    traces = [slow_leaf_trace(geo_ms=900.0, search_own_ms=5.0, e2e_ms=910.0)]
    spans = select_spans(traces, "search")
    assert len(spans) == 1
    assert compute_latency_percentiles(traces, service="search")["p95_ms"] == 5.0


def test_unrelated_service_on_the_same_trace_is_not_dragged_up():
    """A fast service sharing a trace with a slow one keeps its own fast p95."""
    trace = slow_leaf_trace(geo_ms=900.0)
    trace["processes"]["p4"] = {"serviceName": "rate"}
    trace["spans"].append(_span("f", "p4", 4.0, parent="b"))
    per_service = compute_latency_percentiles([trace], service="rate")
    assert per_service["p95_ms"] == 4.0
    assert compute_latency_percentiles([trace])["p95_ms"] > 900.0


def test_service_absent_from_traces_yields_zero_count_not_a_borrowed_number():
    traces = [slow_leaf_trace()]
    res = compute_latency_percentiles(traces, service="reservation")
    assert res["count"] == 0
    assert res["p95_ms"] == 0.0


def test_fails_open_to_all_spans_when_span_kind_tags_are_absent():
    trace = {
        "traceID": "t",
        "processes": {"p1": {"serviceName": "geo"}},
        "spans": [{"spanID": "a", "processID": "p1", "duration": 7000,
                   "startTime": 0, "tags": [], "references": []}],
    }
    assert compute_latency_percentiles([trace], service="geo")["p95_ms"] == 7.0


def test_error_rate_is_attributed_to_the_service_that_errored():
    trace = slow_leaf_trace()
    trace["spans"][4]["tags"].append({"key": "error", "type": "bool", "value": True})
    assert compute_error_rate([trace], service="geo") == 1.0
    assert compute_error_rate([trace], service="search") == 0.0
    # Trace-level: the whole trace counts as errored, which is the misattribution.
    assert compute_error_rate([trace]) == 1.0


def test_error_rate_denominator_is_traces_the_service_appears_in():
    with_geo = slow_leaf_trace("t1")
    with_geo["spans"][4]["tags"].append({"key": "error", "type": "bool", "value": True})
    without_geo = {
        "traceID": "t2",
        "processes": {"p1": {"serviceName": "frontend"}},
        "spans": [_span("a", "p1", 5.0)],
    }
    # geo appears in 1 of 2 traces and errored in it -> 1.0, not 0.5.
    assert compute_error_rate([with_geo, without_geo], service="geo") == 1.0


# ── The latency-degradation rule and its absolute floor ──────────────────────
#
# Amendment 1 to Preregistration v3 (2026-09-26). A purely multiplicative threshold
# produces false positives once percentiles are genuinely per-service: measured on real
# baseline spans, `url-shorten-service` moved 0.02 -> 0.06 ms (3.00x) between two
# FAULT-FREE windows. The values below are those measurements.

from measurement.metrics_collector import (  # noqa: E402
    DEGRADATION_FACTOR,
    DEGRADATION_FLOOR_MS,
    latency_degraded,
)


def test_floor_is_one_millisecond_and_factor_is_two():
    assert DEGRADATION_FLOOR_MS == 1.0
    assert DEGRADATION_FACTOR == 2.0


def test_the_observed_false_positive_is_now_rejected():
    """url-shorten-service, the descendant the rehearsal wrongly flagged."""
    assert latency_degraded(0.02, 0.07) is False        # 3.50x but only +0.05 ms
    assert latency_degraded(0.02, 0.06) is False        # baseline-only drift, 3.00x


def test_a_large_relative_move_below_the_floor_is_rejected():
    """Any sub-millisecond service can exceed 2x on noise; the floor is what stops it."""
    assert latency_degraded(0.02, 0.98) is False        # 49x, +0.96 ms -> still below
    assert latency_degraded(0.40, 0.90) is False        # 2.25x, +0.50 ms


def test_a_real_effect_still_passes():
    assert latency_degraded(14.50, 1972.13) is True     # HR frontend under netem
    assert latency_degraded(0.50, 2.00) is True         # 4.00x and +1.50 ms
    assert latency_degraded(10.0, 21.0) is True         # 2.10x and +11.0 ms


def test_the_relative_condition_is_still_required():
    """Meeting the floor alone is not enough -- a big absolute move on a slow service."""
    assert latency_degraded(100.0, 150.0) is False      # +50 ms but only 1.50x
    assert latency_degraded(100.0, 201.0) is True       # 2.01x and +101 ms


def test_exactly_at_the_floor_counts_and_just_under_does_not():
    assert latency_degraded(1.0, 2.0) is False          # 2.00x is not > 2.00x
    assert latency_degraded(1.0, 2.0001) is True        # just over both
    # 0.5 and 1.5 are exactly representable in binary, so the difference is exactly 1.0.
    # Do not use e.g. (0.4, 1.4) here: 1.4 - 0.4 evaluates to 0.9999999999999999, so the
    # >= comparison fails. The boundary is inherently fuzzy at float precision, which is
    # harmless -- a real effect clears 1.0 ms by orders of magnitude, and the smallest
    # genuine effect ever measured is +36.7 ms -- but the test must not assert an equality
    # binary arithmetic cannot deliver.
    assert latency_degraded(0.5, 1.5) is True           # 3.00x and exactly +1.0 ms
    assert latency_degraded(0.5, 1.4999) is False       # +0.9999 ms


def test_a_missing_or_nonpositive_baseline_makes_no_claim():
    assert latency_degraded(0.0, 500.0) is False
    assert latency_degraded(None, 500.0) is False
    assert latency_degraded(5.0, None) is False
    assert latency_degraded(-1.0, 500.0) is False


def test_percentiles_are_not_rounded_before_comparison():
    """Rounding to 2dp put the quantisation step at 0.01 ms -- the size of the signal."""
    # Three spans of 1, 2 and 1000 microseconds: the p95 interpolates to a value that
    # 2dp rounding would flatten.
    trace = {
        "traceID": "t",
        "processes": {"p1": {"serviceName": "tiny"}},
        "spans": [
            _span("a", "p1", 0.001), _span("b", "p1", 0.002), _span("c", "p1", 1.000),
        ],
    }
    p95 = compute_latency_percentiles([trace], service="tiny")["p95_ms"]
    assert p95 != round(p95, 2), "value must retain precision beyond 2 decimals"
