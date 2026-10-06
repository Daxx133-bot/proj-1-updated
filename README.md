# Identifying Failure-Prone Microservices Using Graph Centrality Metrics

This repository contains a fault-injection study testing whether dependency-graph
centrality predicts how far a microservice failure spreads. We reconstructed service
dependency graphs from distributed traces for two DeathStarBench applications (Social
Network and Hotel Reservation), then ran a preregistered campaign of 180 fault-injection
runs — every non-gateway service, two fault types (process kill and 500 ms network delay),
five repetitions each, fully balanced — and measured which other services degraded. The
analysis plan, including the hypotheses, the primary predictor and outcome, the test
statistic and the multiple-comparisons correction, was written and locked before any
campaign data was collected.

## Outcome

**The preregistered confirmatory test was null after correction.** The primary test
(Social Network, `ancestor_count` versus measured `ancestor_affected_count`, kill faults)
gives rho = 0.785 with an uncorrected permutation p of 0.0080, which becomes a
Benjamini-Hochberg adjusted p of 0.3451 across the 44-test confirmatory family. **None of
the 44 confirmatory tests, and none of the 44 replication-family tests, is significant at
q = 0.05.** The hybrid criticality metric that this work set out to evaluate has a negative
correlation with measured blast radius in all four architecture-by-fault cells and is
distinguishable from zero in none of them.

The study also records a structural observation that required no inference: no descendant
of a faulted service degraded in 179 of the 180 runs, and the service-level median
descendant count is zero for every service in every condition. Because that outcome has no
variance, it cannot be expressed as a correlation, and 88 of the 154 attempted exploratory
tests are undefined rather than null.

`paper/CLAIMS_LEDGER.md` is the authority on what these data do and do not support. It
marks every claim the manuscript might make as SUPPORTED, UNSUPPORTED or POST-HOC, and
names the `paper/numbers.csv` row backing each supported one. Claims marked UNSUPPORTED
there should not be made from this repository's results.

## What this copy is

This is a reduced copy, assembled for review. It contains the files needed to reproduce the
paper's numbers, tables and figures, and nothing else. `share_manifest.txt` lists every
included file together with the script that consumes it; a file with no consumer was not
copied.

Three categories of material were deliberately left out, and the "Audit history" section
below says what they are. The complete original repository, including all of it and the
full git history of the work, is archived locally and available on request.

**Commit hashes cited anywhere in this copy — including `5976178` for the campaign and the
`commit` column of `paper/numbers.csv` — refer to that archived original repository.** This
copy has its own, new history beginning at a single initial commit, so those hashes will not
resolve here.

## Directory map

| Path | Contents |
|---|---|
| `data/campaign/` | The 180 campaign run records, one JSON per run, plus the run manifest. |
| `data/spans/` | Raw Jaeger spans persisted per run, gzipped, for both the baseline and the fault window. 366 files, ~53 MB. These make every metric definition replayable without re-running the experiment. |
| `data/graphs/` | The two frozen service dependency graphs reconstructed from traces. Every structural predictor is computed from these. |
| `data/pilot/` | Pilot runs that precede the campaign. Two of them (the 2026-09-26 Hotel Reservation latency runs) back Figure 4; the rest support the absolute-floor threshold evidence. |
| `data/analysis/` | The predictor table derived from the graphs, used to size the test family. |
| `analysis/final/` | The preregistered analysis and its outputs, plus the supplementary leave-one-out, exact-p and blind-recomputation checks. |
| `paper/` | Everything the manuscript cites. `numbers.csv` holds one row per citable number with its source file and producing script; `tables/` and `figures/` hold the table- and figure-ready outputs; `draft/` holds the section drafts; `CLAIMS_LEDGER.md` holds the claim-by-claim verdict. |
| `_audit/` | The audit report, the confirmatory analysis report, and the frozen v3 preregistration. |
| `_quarantine/` | `QUARANTINE_LOG.md`, which records what was withdrawn and why, and `QUARANTINE_INDEX.txt`, a one-line-per-file listing of the withdrawn material. The withdrawn files themselves are not in this copy. |
| `tools/`, `measurement/`, `centrality/`, `faultinjection/`, `infra/`, `sdg/` | The campaign runner, the metric collection and blast-radius code, the centrality implementation, the fault specifications, the stack and load-generation scripts, and the expected-service manifest. |
| `tests/` | The test suite. |

## Reproducing the results

Two of the three stages need only the data in this copy. Only data collection needs Docker.

### Offline — no Docker required

These read exclusively from inside this folder and write only inside it.

```bash
python -m pip install -r requirements.txt

# Unit tests. 100 selected; 37 marked `integration` are deselected.
python -m pytest -q -m "not integration"

# Rebuild every number, table and figure the paper cites, from analysis/final/
python paper/build_all.py

# Re-run the full preregistered analysis from the 180 campaign run records.
# Rewrites analysis/final/*.csv, analysis/final/figures/ and _audit/CONFIRMATORY_ANALYSIS.md.
python analysis/final/run_confirmatory_analysis.py

# Supplementary checks, independent of each other
python analysis/final/leave_one_out.py        # post-hoc leave-one-out sensitivity
python analysis/final/exact_p_supplement.py   # exact-enumeration p-values
python analysis/final/blind_recompute.py      # independent recomputation from raw spans
python paper/check_draft_ids.py               # verifies the drafting markers in paper/draft/
```

`paper/build_all.py` regenerates `paper/numbers.csv`, `numbers.tex`, `numbers.json`,
`tables/`, `figures/` and `INDEX.csv`, then checks that every claim in
`paper/CLAIMS_LEDGER.md` resolves to a real row. It fails if any does not.

Timings: `run_confirmatory_analysis.py` takes about a minute; `leave_one_out.py` and
`blind_recompute.py` take several minutes each, the first because it enumerates permutations
exactly and the second because it reads all 366 span files; the rest are faster.

### Data collection — requires Docker

Re-running the campaign needs Docker, roughly 8 GB of memory available to the Docker VM, and
a separate DeathStarBench checkout (see below). **This stage is not verified here**, because
it needs the live stacks:

```bash
python tools/run_campaign.py --status        # inspect the run manifest
python tools/run_campaign.py --max-runs 1    # execute a single pending run
```

## Tests

The suite contains 137 tests. 37 are marked `integration` and are deselected by the command
above, leaving **100 that run against this copy alone** and cover the statistics, the metric
definitions, the blast-radius rule and the container-resolution logic.

**The 37 integration tests require Docker and a separate DeathStarBench clone at commit
`6ecb097`, placed as a sibling of this folder.** 23 of them drive the live benchmark stacks.
The other 14, in `tests/test_campaign_runner.py`, are written against fakes and need no
running containers, but they drive the campaign runner far enough to reach its
stack-lifecycle helpers, which shell out to `docker compose` with the working directory set
to `<parent>/DeathStarBench/<app>`. Without that directory they fail with
`NotADirectoryError`, which is why they carry the marker. The expected layout is:

```
<parent>/
├── microservice-failure-analysis/    this folder
└── DeathStarBench/                   separate clone, commit 6ecb097
```

With that checkout present, run the whole suite by dropping the filter: `python -m pytest -q`.

## Environment

- **Python 3.11 or newer.** Developed and verified on 3.13.2.
- **Packages:** `pip install -r requirements.txt`, which pins the direct dependencies
  including **numpy** and **statsmodels**. Verified with numpy 2.1.2, pandas 2.2.3,
  scipy 1.14.1, statsmodels 0.14.6, matplotlib 3.9.2, networkx 3.6.1, pytest 9.0.3.
  `statsmodels` provides the Cox and log-rank models; `lifelines` is not required.
- **Docker** is required only for data collection and for the 37 tests marked `integration`.
  The offline analysis does not use it.
- **DeathStarBench is not included** and must be cloned separately, as a sibling folder, at
  commit `6ecb097` (`6ecb09706140f8730b5385c08f1386c654c3c526`). The two compose override
  files in `infra/` pin the Jaeger version and the port assignments; Hotel Reservation is
  reached on host port 16687 rather than the default 16686.

## Audit history

An earlier version of this analysis was withdrawn. A self-audit of the pipeline found that
part of what the earlier manuscript presented as experimental findings had not been
measured: impact values and recovery times were produced by code drawing from hard-coded
numeric ranges, and the metric weights carrying the headline correlation had been selected by
a grid search maximising that same correlation against the same outcome the manuscript then
reported, with no held-out data.

That earlier work is a real part of this project's history and is not disowned here. Its
results were withdrawn in full, and the files were **not deleted**: they were moved to a
quarantine directory in the original repository, where each of 13 numbered items is
documented with what was removed and why. The audit findings themselves are in
`_audit/AUDIT_REPORT.md`, which is included.

**Three categories of material are not included in this copy:**

1. **Withdrawn material.** The quarantined scripts and data. `_quarantine/QUARANTINE_LOG.md`
   and `_quarantine/QUARANTINE_INDEX.txt` are included so that what was withdrawn remains
   inspectable, but the 74 withdrawn files themselves are not copied.
2. **Superseded measurement batches.** Earlier real measurement runs, including the 18–20
   September controlled batches and the `EVIDENCE_FREEZE/` forensic snapshot of them. These
   are genuine measurements, not fabrications. They were collected under the older
   per-service metric definition, which attributed each trace's end-to-end latency to every
   service on that trace, so they are not comparable to the corrected outcome definitions the
   paper uses. They are superseded, not invalid as records.
3. **Supporting audit artifacts.** Gate outputs, validation dumps and run logs. The
   human-readable reports are included; the machine outputs behind them are not.

**Nothing from the withdrawn material is used in the current results.** The measurement
pipeline, the metric implementation and the analysis were rebuilt, and the campaign in
`data/campaign/` was collected fresh under the locked preregistration. The metric weights are
now fixed a priori in `centrality/metric_constants.py`, with written reasoning for each, and
are never fitted to outcome data. Deviations from the locked plan are logged in
`PREREGISTRATION.md` §12 and tabulated in `paper/tables/tbl_deviations.csv`; there are nine,
and the 17 runs invalidated across them were quarantined and re-collected rather than
analysed or dropped.

The campaign was collected at commit `5976178` of the archived original repository.

## Reading order

For an assessor: `paper/CLAIMS_LEDGER.md` first, then
`_audit/preregistration_versions/PREREGISTRATION_v3_LOCKED.md` for what was committed to in
advance, then `_audit/CONFIRMATORY_ANALYSIS.md` for the full analysis narrative, then
`paper/draft/` for the manuscript sections. `paper/numbers.csv` connects any number in those
documents back to the file and script that produced it, and `share_manifest.txt` connects
every file in this copy to the script that needs it.
