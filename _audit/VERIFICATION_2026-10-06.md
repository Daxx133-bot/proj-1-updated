# Verification notes, 2026-10-06

A read-only verification of the repository against its own statements, followed by
integrity fixes. The material findings are recorded as deviations 10, 11 and 12
(`PREREGISTRATION.md` §12, `analysis/final/deviations.csv`). This file records the
remaining facts the verification established, each with its source. None of them changes
a stored outcome or a locked output.

## 1. Runs invalidated and re-collected: 17

Source: `data/campaign/manifest.json` → `amendments[].runs_reset`.

| Amendment | Manifest date (UTC) | Runs reset and re-collected | Originals preserved at |
|---|---|---:|---|
| 1 | 2026-09-26 04:58:56 | 3 (Social Network kill rep 1: compose-post, home-timeline, media) | `_quarantine/data/campaign/runs_pre_amendment1/` |
| 2 | 2026-09-26 06:29:54 | 3 (Hotel Reservation kill rep 1: reservation, search, user) | `_quarantine/data/campaign/runs_mistargeted` |
| 3 | 2026-09-26 13:07:43 | 11 (Social Network latency rep 1, all 11 services) | `_quarantine/data/campaign/runs_leaked_netem` |

The total is 3 + 3 + 11 = 17, matching `deviations_runs_invalidated` in `paper/numbers.csv`.

There was also one interrupted attempt that was not a reset:
`hotelreservation|rate|latency|1` has `attempts: 2` in the manifest (deviation 12). It
produced no run record and is not counted in the 17.

## 2. Campaign duration: 8.5 h vs ~9.3 h

The two figures measure from different start points. Neither is an error.

| Figure | Where it appears | Start | End | Span |
|---|---|---|---|---|
| 8.5 h | `paper/numbers.csv` `campaign_duration_hours`, from `analysis/final/run_level_data.csv` | 05:02:52 UTC, the end-timestamp of the first **kept** run (`socialnetwork\|compose-post-service\|kill\|1`, re-collected after amendment 1) | 13:35:12 UTC, the end-timestamp of the last kept run | 8.539 h |
| ~9.3 h | `PREREGISTRATION.md` closing table, "04:19-13:35 UTC" | 04:19:40 UTC, the first `CAMPAIGN START` in `data/campaign/progress.log`, which launched the pre-launch rehearsal | 13:35 UTC | ~9.27 h |

The rehearsal produced 3 runs, ending at 04:22:41, 04:25:10 and 04:28:24 UTC. They were
invalidated by amendment 1 and quarantined (`_quarantine/QUARANTINE_LOG.md` item 11).

A run's `timestamp` is written when its result is assembled, at the end of the run
(`tools/run_pilot.py`, the `"timestamp"` field of the result dict). The first kept run's
baseline window opened at 05:00:52 UTC, so measured from first activity to last
end-timestamp the kept runs span 8.57 h.

## 3. The degradation rule: latency branch shared, error-rate branch written out three times

**Latency branch.** Defined once, in `measurement.metrics_collector.latency_degraded`
(`measurement/metrics_collector.py:255`). It is imported and called by:

- the runner, through `compute_blast_radius` (line 338);
- the recovery probe (`measurement/recovery_probe.py:316`);
- the offline replay tool (`tools/analyze_live_spans.py:85`).

**Error-rate branch.** Not a shared function. The same comparison, fault error rate >
baseline + 0.05, is written inline in three modules:

| Module | Line | Threshold source |
|---|---|---|
| `measurement/metrics_collector.py` | 346 | `ERROR_RATE_ABS_THRESHOLD` (defined at 252, = 0.05) |
| `measurement/recovery_probe.py` | 320 | parameter `error_rate_abs_threshold`, whose default is the literal `0.05` at line 143; the runner does not override it |
| `tools/analyze_live_spans.py` | 94 | imports `ERROR_RATE_ABS_THRESHOLD` |

All three use the same value, so no stored outcome is affected. Deviation 1's statement
that the rule is "implemented once … and shared" is accurate for the latency branch only.

**Figure code.** `paper/make_figures.py:40` hardcodes `FACTOR, FLOOR_MS = 2.0, 1.0` for the
Q3 figure's flags rather than importing the constants. The values are the same.

## 4. The Q3 figure: three services with identical baseline p95, not four

Source: `paper/figures/fig_q3_artifact_data.csv`.

**What the figure uses.** Two **pilot** runs, not campaign runs:

- `data/pilot/pilot_hotelreservation_search_latency_rep1_2026-09-26T04-11-53.112863+00-00.json`
- `data/pilot/pilot_hotelreservation_search_latency_rep2_2026-09-26T04-14-37.596034+00-00.json`

**What the data shows.** Under the end-to-end ("old") scope, three services share an
identical baseline p95 in each run: `geo`, `rate` and `search` (16.4329 ms in rep 1,
15.9145 ms in rep 2). The same three also share an identical fault-window p95. No other
service matches, including at two decimal places.

**What the draft says.** `paper/draft/method.md` (line 158) says "four services report an
identical baseline p95 to two decimal places". That does not match the data. The draft line
has not been changed in this session and remains to be corrected.

**How the "old" scope is computed.** The column is reconstructed inside
`paper/make_figures.py` (`q3_scopes`, line 188): every service present in a trace is
charged that trace's root-span duration. It is not the original pre-Q3 code path, which
computed root-span percentiles over the traces Jaeger returned for each service.

## 5. Commit hashes

The working repository holds every commit cited in `paper/numbers.csv` and the documents.
The share copy (`microservice-failure-analysis-share-clean`) is a single fresh commit and
holds none of them; its README says so.
