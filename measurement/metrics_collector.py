#!/usr/bin/env python3
"""
metrics_collector.py — Collect Blast Radius Metrics from Jaeger Traces
========================================================================
During a fault injection experiment, this module collects metrics from
Jaeger traces to quantify the "blast radius" — how much damage the fault
caused to the overall system.

Metrics collected:
  1. Tail latency (p95, p99) — from root span durations during baseline
     vs. fault windows.
  2. Error rate — fraction of traces with error tags during each window.
  3. Blast radius (downstream affected count) — number of distinct services
     showing degradation (latency > 2× baseline or new errors) during fault.
  4. Recovery time — measured externally by the fault runner.

Usage:
    This module is imported by fault_runner.py, not run standalone.
"""

import time
from typing import Any

import numpy as np
import requests


DEFAULT_JAEGER_URL = "http://localhost:16686"


def get_traces_in_window(
    jaeger_url: str,
    service: str,
    start_time_us: int,
    end_time_us: int,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """
    Fetch traces from Jaeger within a specific time window.

    Jaeger's /api/traces endpoint supports start/end parameters
    in microseconds since epoch.

    Args:
        jaeger_url: Jaeger query URL.
        service: Service name to query traces for.
        start_time_us: Window start (microseconds since epoch).
        end_time_us: Window end (microseconds since epoch).
        limit: Maximum traces to fetch.

    Returns:
        List of trace dicts from Jaeger.
    """
    try:
        resp = requests.get(
            f"{jaeger_url}/api/traces",
            params={
                "service": service,
                "start": start_time_us,
                "end": end_time_us,
                "limit": limit,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data") or []
    except requests.RequestException as e:
        print(f"  [WARNING] Failed to fetch traces for {service}: {e}")
        return []


def span_service_map(trace: dict[str, Any]) -> dict[str, str]:
    """Map a trace's processID -> serviceName, using Jaeger's `processes` block."""
    return {
        pid: proc.get("serviceName", "")
        for pid, proc in (trace.get("processes") or {}).items()
    }


def _span_kind(span: dict[str, Any]) -> str | None:
    for tag in span.get("tags", []):
        if tag.get("key") == "span.kind":
            return tag.get("value")
    return None


def _is_root(span: dict[str, Any]) -> bool:
    refs = span.get("references", [])
    return not any(r.get("refType") == "CHILD_OF" for r in refs)


def select_spans(
    traces: list[dict[str, Any]],
    service: str | None = None,
) -> list[dict[str, Any]]:
    """Select the spans whose durations define a latency measurement.

    `service is None`  -> ROOT spans only. This is END-TO-END trace latency and is
                          only meaningful as a system-wide number.

    `service = "geo"`  -> the SERVER spans emitted by `geo` itself. A server span's
                          duration is the time `geo` took to handle one request,
                          including whatever it spent waiting on its own callees.
                          Client spans are excluded: a client span emitted by `geo`
                          measures a *callee's* latency as observed by geo, so
                          counting it would re-attribute a downstream service's
                          slowness to geo. If a service's spans carry no `span.kind`
                          tag at all, every span it emitted is used (fail-open), and
                          the caller can detect this via the returned `count`.

    Why this function exists (Q3, 2026-09-25)
    -----------------------------------------
    The original `compute_latency_percentiles` took ROOT-span durations for whatever
    trace set it was handed. Because `get_traces_in_window(service=X)` returns every
    trace that *touches* X, "service X's p95" was in fact the end-to-end p95 of all
    traces passing through X. Every service on a hot path therefore inherited the
    same number, so a slow leaf made its ancestors AND its unrelated path-mates all
    look degraded. That is what produced the 2 spuriously "affected" DESCENDANTS in
    the HR search latency pilot runs. Per-service percentiles must come from spans
    belonging to that service only.
    """
    out: list[dict[str, Any]] = []
    for trace in traces:
        if service is None:
            out.extend(s for s in trace.get("spans", []) if _is_root(s))
            continue
        pmap = span_service_map(trace)
        mine = [s for s in trace.get("spans", [])
                if pmap.get(s.get("processID")) == service]
        server = [s for s in mine if _span_kind(s) == "server"]
        kinded = any(_span_kind(s) is not None for s in mine)
        out.extend(server if kinded else mine)
    return out


def compute_latency_percentiles(
    traces: list[dict[str, Any]],
    service: str | None = None,
) -> dict[str, float]:
    """
    Compute p50, p95 and p99 latency in milliseconds.

    Args:
        traces:  List of Jaeger trace dicts.
        service: If given, percentiles are computed from the SERVER spans emitted by
                 that service, i.e. that service's own request-handling latency.
                 If omitted, percentiles come from root spans and are END-TO-END
                 latency for the whole trace — never attribute those to a service.

    Returns:
        Dict with keys: p50_ms, p95_ms, p99_ms, mean_ms, count, scope
    """
    spans = select_spans(traces, service)
    scope = "end_to_end_root" if service is None else f"service_server_spans:{service}"

    if not spans:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0,
                "mean_ms": 0.0, "count": 0, "scope": scope}

    durations_ms = [float(s.get("duration", 0)) / 1000.0 for s in spans]

    return {
        # NOT rounded. These values are compared against a threshold with a 1.0 ms
        # absolute floor (see latency_degraded), and rounding to 2 decimals put the
        # quantisation step at 0.01 ms -- comparable to the whole signal for services
        # whose own-span p95 is 0.02 ms. Round at the point of display, never before a
        # comparison.
        "p50_ms": float(np.percentile(durations_ms, 50)),
        "p95_ms": float(np.percentile(durations_ms, 95)),
        "p99_ms": float(np.percentile(durations_ms, 99)),
        "mean_ms": float(np.mean(durations_ms)),
        "count": len(durations_ms),
        "scope": scope,
    }


def _span_has_error(span: dict[str, Any]) -> bool:
    for tag in span.get("tags", []):
        key, value = tag.get("key", ""), tag.get("value")
        if key == "error" and value is True:
            return True
        if key == "http.status_code" and isinstance(value, int) and value >= 500:
            return True
    return False


def compute_error_rate(
    traces: list[dict[str, Any]],
    service: str | None = None,
) -> float:
    """
    Compute an error rate in [0.0, 1.0].

    Args:
        traces:  List of Jaeger trace dicts.
        service: If given, only spans emitted by that service are inspected, and the
                 denominator is the number of traces in which that service actually
                 appears. Without this filter a trace is "errored" if ANY span in it
                 errored, so a failure anywhere on a path marks every service on that
                 path as errored — the same misattribution as the p95 bug (Q3).
                 If omitted, the trace-level (end-to-end) error rate is returned.
    """
    if not traces:
        return 0.0

    if service is None:
        errored = sum(1 for t in traces
                      if any(_span_has_error(s) for s in t.get("spans", [])))
        return round(errored / len(traces), 4)

    denom = 0
    errored = 0
    for trace in traces:
        pmap = span_service_map(trace)
        mine = [s for s in trace.get("spans", [])
                if pmap.get(s.get("processID")) == service]
        if not mine:
            continue
        denom += 1
        if any(_span_has_error(s) for s in mine):
            errored += 1

    if denom == 0:
        return 0.0
    return round(errored / denom, 4)


# ── The latency-degradation rule ──────────────────────────────────────────────
#
# A service counts as latency-affected only when BOTH conditions hold:
#
#     p95_fault > DEGRADATION_FACTOR * p95_baseline        (relative)
#     p95_fault - p95_baseline >= DEGRADATION_FLOOR_MS      (absolute)
#
# WHY THE ABSOLUTE FLOOR EXISTS (amendment 1 to Preregistration v3, 2026-09-26)
# ----------------------------------------------------------------------------
# The relative condition alone was safe only for as long as "service X's p95" was
# secretly the END-TO-END p95 of X's trace cohort -- tens of milliseconds for every
# service, where sub-millisecond noise could never produce a 2x move. Once percentiles
# became genuinely per-service (Q3 fix, v3 6.1), 8 of 20 services landed in the
# 0.02-0.58 ms range, and a purely multiplicative threshold there has no physical
# meaning: `url-shorten-service` moved 0.02 -> 0.06 ms (3.00x) between two FAULT-FREE
# baseline windows, with nothing running (tools/check_threshold_floor.py).
#
# The error-rate branch of the same rule already carried an absolute floor
# (+0.05 absolute). This is its latency counterpart. 1.0 ms is ~100x the microsecond
# quantisation of a Jaeger duration, exceeds every observed baseline-to-baseline drift,
# and sits far below the smallest genuine effect measured in any pilot run (+36.7 ms).
DEGRADATION_FACTOR = 2.0
DEGRADATION_FLOOR_MS = 1.0
ERROR_RATE_ABS_THRESHOLD = 0.05


def latency_degraded(
    baseline_p95_ms: float,
    fault_p95_ms: float,
    degradation_factor: float = DEGRADATION_FACTOR,
    floor_ms: float = DEGRADATION_FLOOR_MS,
) -> bool:
    """True when a service's own p95 rose both proportionally and materially.

    Both arguments must be FULL-PRECISION milliseconds. Passing values already rounded
    for display reintroduces the quantisation this floor exists to defeat.

    A non-positive baseline means there is nothing to compare against, so no claim of
    degradation is made -- the caller decides whether that is "no signal" or "idle".
    """
    if baseline_p95_ms is None or fault_p95_ms is None:
        return False
    if baseline_p95_ms <= 0:
        return False
    return (fault_p95_ms > degradation_factor * baseline_p95_ms
            and fault_p95_ms - baseline_p95_ms >= floor_ms)


def compute_blast_radius(
    jaeger_url: str,
    all_services: list[str],
    faulted_service: str,
    baseline_latencies: dict[str, dict[str, float]],
    fault_start_us: int,
    fault_end_us: int,
    degradation_factor: float = DEGRADATION_FACTOR,
    degradation_floor_ms: float = DEGRADATION_FLOOR_MS,
) -> tuple[int, list[str]]:
    """
    Compute the blast radius: how many OTHER services were affected
    by the fault on `faulted_service`.

    A service is considered "affected" if during the fault window:
      - Its p95 latency exceeds `degradation_factor × baseline_p95` AND rises by at
        least `degradation_floor_ms` in absolute terms (see `latency_degraded`)
      - OR its error rate increases above baseline

    Args:
        jaeger_url: Jaeger query URL.
        all_services: List of all service names in the SDG.
        faulted_service: The service that was faulted (excluded from count).
        baseline_latencies: Dict of service → latency stats from baseline.
        fault_start_us: Fault window start (microseconds since epoch).
        fault_end_us: Fault window end (microseconds since epoch).
        degradation_factor: Threshold multiplier for latency degradation.
        degradation_floor_ms: Minimum absolute p95 increase, in milliseconds.

    Returns:
        Tuple of (affected_count, list_of_affected_service_names).
    """
    affected: list[str] = []

    for service in all_services:
        # Skip the faulted service itself — we're measuring collateral damage
        if service == faulted_service:
            continue

        # Skip infrastructure services
        if "jaeger" in service.lower() or "mongo" in service.lower() \
                or "redis" in service.lower() or "memcached" in service.lower():
            continue

        # Get fault-window traces for this service
        fault_traces = get_traces_in_window(
            jaeger_url, service, fault_start_us, fault_end_us
        )

        if not fault_traces:
            continue

        # Compute fault-window metrics
        # Q3: per-service percentiles, from this service's own server spans.
        fault_latency = compute_latency_percentiles(fault_traces, service=service)

        # Get baseline metrics for this service
        baseline = baseline_latencies.get(service, {})
        baseline_p95 = baseline.get("p95_ms", 0.0)

        # Check if latency degraded beyond threshold
        if latency_degraded(baseline_p95, fault_latency["p95_ms"],
                            degradation_factor, degradation_floor_ms):
            affected.append(service)
            continue

        # Check if error rate increased
        fault_error = compute_error_rate(fault_traces, service=service)
        baseline_error = baseline.get("error_rate", 0.0)
        if fault_error > baseline_error + ERROR_RATE_ABS_THRESHOLD:
            affected.append(service)

    return len(affected), affected


def collect_baseline_metrics(
    jaeger_url: str,
    all_services: list[str],
    window_seconds: int = 30,
) -> dict[str, dict[str, float]]:
    """
    Collect baseline latency and error rate for all services.

    Queries Jaeger for traces from the last `window_seconds` seconds,
    which should represent the steady-state baseline.

    Args:
        jaeger_url: Jaeger query URL.
        all_services: List of service names.
        window_seconds: How many seconds of baseline to measure.

    Returns:
        Dict of service → {"p95_ms": ..., "p99_ms": ..., "error_rate": ...}
    """
    now_us = int(time.time() * 1_000_000)
    start_us = now_us - (window_seconds * 1_000_000)

    baselines: dict[str, dict[str, float]] = {}

    for service in all_services:
        traces = get_traces_in_window(jaeger_url, service, start_us, now_us)

        if traces:
            latency = compute_latency_percentiles(traces, service=service)
            error_rate = compute_error_rate(traces, service=service)
            baselines[service] = {
                "p50_ms": latency["p50_ms"],
                "p95_ms": latency["p95_ms"],
                "p99_ms": latency["p99_ms"],
                "mean_ms": latency["mean_ms"],
                "span_count": latency["count"],
                "trace_count": len(traces),
                "error_rate": error_rate,
                "scope": latency["scope"],
            }
        else:
            baselines[service] = {
                "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0,
                "mean_ms": 0.0, "span_count": 0, "trace_count": 0,
                "error_rate": 0.0, "scope": f"service_server_spans:{service}",
            }

    return baselines


def collect_fault_window_metrics(
    jaeger_url: str,
    primary_service: str,
    fault_start_us: int,
    fault_end_us: int,
) -> dict[str, float]:
    """
    Collect metrics for the primary measurement service during the fault window.

    We typically measure using the top-level service (nginx-web-server)
    to get end-to-end impact, but also capture per-service data.

    Args:
        jaeger_url: Jaeger query URL.
        primary_service: Service to measure (usually nginx or the gateway).
        fault_start_us: Fault window start.
        fault_end_us: Fault window end.

    Returns:
        Dict with p95_ms, p99_ms, error_rate, trace_count.
    """
    traces = get_traces_in_window(
        jaeger_url, primary_service, fault_start_us, fault_end_us
    )

    # Deliberately END-TO-END: `primary_service` is the gateway, so root-span
    # duration IS the user-visible request latency. Never reuse this for a
    # non-gateway service -- see select_spans() (Q3).
    latency = compute_latency_percentiles(traces)
    error_rate = compute_error_rate(traces)

    return {
        "p95_ms": latency["p95_ms"],
        "p99_ms": latency["p99_ms"],
        "mean_ms": latency["mean_ms"],
        "error_rate": error_rate,
        "trace_count": latency["count"],
    }
