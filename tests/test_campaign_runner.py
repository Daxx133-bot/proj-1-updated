"""Unit tests for tools/run_campaign.py.

No Docker, no Jaeger, no faults: `one_run` and the stack lifecycle are replaced with
fakes, and what is tested is the bookkeeping -- which is the part that has to be right for
an 8-11 hour unattended process. The fake results below are hand-written control values,
not measurements.

The tests marked `integration` below drive the campaign runner far enough to reach
its stack-lifecycle helpers, which shell out to `docker compose` with the working
directory set to `<repo parent>/DeathStarBench/<app>`. They therefore require Docker
and a separate DeathStarBench checkout at commit 6ecb097, placed as a sibling of this
repository, and they fail with NotADirectoryError without it. Deselect them with
`pytest -m "not integration"`.
"""

from __future__ import annotations

import json

import pytest

from tools import run_campaign as rc


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    """Point every path the module writes to at a temp directory."""
    monkeypatch.setattr(rc, "CAMPAIGN_DIR", tmp_path)
    monkeypatch.setattr(rc, "MANIFEST", tmp_path / "manifest.json")
    monkeypatch.setattr(rc, "PROGRESS_LOG", tmp_path / "progress.log")
    monkeypatch.setattr(rc, "RESULTS_DIR", tmp_path / "runs")
    monkeypatch.setattr(rc, "FAILURES_DIR", tmp_path / "failures")
    monkeypatch.setattr(rc, "LOCK", tmp_path / ".campaign.lock")
    # Stack lifecycle is a no-op that always succeeds unless a test says otherwise.
    monkeypatch.setattr(rc, "stack_up", lambda app: True)
    monkeypatch.setattr(rc, "stack_down", lambda app: None)
    monkeypatch.setattr(rc, "restore_stack", lambda app: True)
    monkeypatch.setattr(rc.time, "sleep", lambda s: None)
    return tmp_path


def ok_result(recovered=True, telemetry=True):
    return {
        "timestamp": "2026-09-25T10:00:00+00:00",
        "telemetry_ok": telemetry,
        "recovery_censored": not recovered,
        "recovery_time_s": 12.3 if recovered else None,
        "ancestor_affected_count": 2, "descendant_affected_count": 0,
        "unrelated_affected_count": 0,
        "fault_error_rate": 0.4, "fault_p95_ms": 50.0, "baseline_p95_ms": 40.0,
        "baseline_trace_count": 500 if telemetry else 0,
        "fault_trace_count": 500 if telemetry else 0,
    }


def run_main(monkeypatch, argv, one_run_impl):
    monkeypatch.setattr(rc, "one_run", one_run_impl)
    monkeypatch.setattr(rc.sys, "argv", ["run_campaign.py", *argv])
    return rc.main()


# ── manifest shape ───────────────────────────────────────────────────────────

def test_manifest_enumerates_180_runs_excluding_gateways(campaign):
    doc = rc.build_manifest()
    assert doc["total_runs"] == 180
    ids = {r["id"] for r in doc["runs"]}
    assert len(ids) == 180, "combinations must be unique"
    assert not any("nginx-web-server" in i for i in ids)
    assert not any(i.startswith("hotelreservation|frontend|") for i in ids)
    assert {r["fault_type"] for r in doc["runs"]} == {"kill", "latency"}
    assert {r["repetition"] for r in doc["runs"]} == {1, 2, 3, 4, 5}


def test_ordering_is_repetition_major_so_interruption_leaves_it_balanced(campaign):
    doc = rc.build_manifest()
    reps = [r["repetition"] for r in doc["runs"]]
    assert reps == sorted(reps), "all rep-1 runs must precede any rep-2 run"
    first_36 = doc["runs"][:36]
    assert {r["repetition"] for r in first_36} == {1}


def test_build_manifest_refuses_to_clobber_an_existing_one(campaign):
    rc.build_manifest()
    with pytest.raises(SystemExit):
        rc.build_manifest()
    rc.build_manifest(force=True)      # explicit override is allowed


def test_manifest_write_is_atomic_and_leaves_no_temp_file(campaign):
    rc.build_manifest()
    assert (campaign / "manifest.json").exists()
    assert not (campaign / "manifest.json.tmp").exists()


# ── resumability ─────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_completed_combinations_are_never_re_run(campaign, monkeypatch):
    rc.build_manifest()
    seen = []

    def fake(app, svc, rep, cfg, args, ft):
        seen.append(f"{app}|{svc}|{ft.value}|{rep}")
        return ok_result()

    assert run_main(monkeypatch, ["--max-runs", "3"], fake) == 0
    assert len(seen) == 3
    first = list(seen)

    # Resume: the same three must not appear again.
    seen.clear()
    assert run_main(monkeypatch, ["--max-runs", "3"], fake) == 0
    assert len(seen) == 3
    assert not (set(seen) & set(first))

    doc = json.loads((campaign / "manifest.json").read_text(encoding="utf-8"))
    assert rc.counts(doc)["done"] == 6
    assert rc.counts(doc)["pending"] == 174


@pytest.mark.integration
def test_a_censored_run_is_terminal_and_is_not_re_run(campaign, monkeypatch):
    rc.build_manifest()
    calls = []

    def fake(app, svc, rep, cfg, args, ft):
        calls.append(1)
        return ok_result(recovered=False)

    run_main(monkeypatch, ["--max-runs", "1"], fake)
    doc = json.loads((campaign / "manifest.json").read_text(encoding="utf-8"))
    assert doc["runs"][0]["status"] == "censored"

    run_main(monkeypatch, ["--max-runs", "1"], fake)
    doc = json.loads((campaign / "manifest.json").read_text(encoding="utf-8"))
    assert doc["runs"][0]["status"] == "censored"
    assert doc["runs"][1]["status"] == "censored"
    assert len(calls) == 2, "the second launch must move on, not repeat run 1"


@pytest.mark.integration
def test_a_run_left_in_running_by_a_dead_process_is_reset_to_pending(campaign, monkeypatch):
    rc.build_manifest()
    doc = rc.load_manifest()
    doc["runs"][0]["status"] = "running"
    rc.write_manifest(doc)

    seen = []

    def fake(app, svc, rep, cfg, args, ft):
        seen.append(f"{app}|{svc}|{ft.value}|{rep}")
        return ok_result()

    run_main(monkeypatch, ["--max-runs", "1"], fake)
    doc = rc.load_manifest()
    assert doc["runs"][0]["status"] == "done"
    assert seen == [doc["runs"][0]["id"]], "the interrupted run is redone, not skipped"


# ── crash isolation ──────────────────────────────────────────────────────────

@pytest.mark.integration
def test_an_exception_marks_failed_and_the_campaign_continues(campaign, monkeypatch):
    rc.build_manifest()
    n = {"i": 0}

    def fake(app, svc, rep, cfg, args, ft):
        n["i"] += 1
        if n["i"] == 2:
            raise RuntimeError("container went away")
        return ok_result()

    assert run_main(monkeypatch, ["--max-runs", "4"], fake) == 0
    doc = rc.load_manifest()
    c = rc.counts(doc)
    assert c["done"] == 3 and c["failed"] == 1
    assert doc["runs"][1]["status"] == "failed"
    assert "container went away" in doc["runs"][1]["error"]
    assert n["i"] == 4, "the campaign ran every combination it was given"


@pytest.mark.integration
def test_a_failure_writes_a_full_traceback_to_disk(campaign, monkeypatch):
    rc.build_manifest()

    def fake(app, svc, rep, cfg, args, ft):
        raise ValueError("boom")

    run_main(monkeypatch, ["--max-runs", "1"], fake)
    files = list((campaign / "failures").glob("*.txt"))
    assert len(files) == 1
    assert "ValueError: boom" in files[0].read_text(encoding="utf-8")


@pytest.mark.integration
def test_a_helper_calling_sys_exit_does_not_abort_the_campaign(campaign, monkeypatch):
    """run_pilot's helpers raise SystemExit; that must not kill an 8-hour run."""
    rc.build_manifest()
    n = {"i": 0}

    def fake(app, svc, rep, cfg, args, ft):
        n["i"] += 1
        if n["i"] == 1:
            raise SystemExit("[FAIL] no running container matches 'x'")
        return ok_result()

    assert run_main(monkeypatch, ["--max-runs", "2"], fake) == 0
    doc = rc.load_manifest()
    assert doc["runs"][0]["status"] == "failed"
    assert doc["runs"][1]["status"] == "done"


@pytest.mark.integration
def test_zero_telemetry_is_failed_not_recorded_as_zeros(campaign, monkeypatch):
    rc.build_manifest()
    run_main(monkeypatch, ["--max-runs", "1"],
             lambda *a: ok_result(telemetry=False))
    doc = rc.load_manifest()
    assert doc["runs"][0]["status"] == "failed"
    assert "telemetry_ok=False" in doc["runs"][0]["error"]


@pytest.mark.integration
def test_retry_failed_resets_only_failed_entries(campaign, monkeypatch):
    rc.build_manifest()
    n = {"i": 0}

    def flaky(app, svc, rep, cfg, args, ft):
        n["i"] += 1
        return ok_result(telemetry=n["i"] != 1)

    run_main(monkeypatch, ["--max-runs", "2"], flaky)
    doc = rc.load_manifest()
    assert rc.counts(doc)["failed"] == 1 and rc.counts(doc)["done"] == 1

    run_main(monkeypatch, ["--retry-failed", "--max-runs", "1"],
             lambda *a: ok_result())
    doc = rc.load_manifest()
    assert rc.counts(doc)["failed"] == 0
    assert rc.counts(doc)["done"] == 2
    assert doc["runs"][0]["attempts"] == 2


@pytest.mark.integration
def test_an_unrecoverable_stack_pauses_rather_than_producing_garbage(campaign, monkeypatch):
    rc.build_manifest()
    monkeypatch.setattr(rc, "restore_stack", lambda app: False)
    n = {"i": 0}

    def fake(app, svc, rep, cfg, args, ft):
        n["i"] += 1
        raise RuntimeError("stack is wedged")

    assert run_main(monkeypatch, ["--max-runs", "5"], fake) == 2
    assert n["i"] == 1, "it must stop after the first unrecoverable failure"
    doc = rc.load_manifest()
    assert rc.counts(doc)["pending"] == 179, "the manifest stays resumable"


@pytest.mark.integration
def test_ctrl_c_returns_the_in_flight_run_to_pending(campaign, monkeypatch):
    rc.build_manifest()

    def fake(app, svc, rep, cfg, args, ft):
        raise KeyboardInterrupt

    assert run_main(monkeypatch, ["--max-runs", "3"], fake) == 130
    doc = rc.load_manifest()
    assert rc.counts(doc)["pending"] == 180
    assert rc.counts(doc)["running"] == 0


# ── progress log and dry run ─────────────────────────────────────────────────

@pytest.mark.integration
def test_progress_log_gets_one_line_per_run_with_running_totals(campaign, monkeypatch):
    rc.build_manifest()
    run_main(monkeypatch, ["--max-runs", "2"], lambda *a: ok_result())
    lines = (campaign / "progress.log").read_text(encoding="utf-8").strip().split("\n")
    run_lines = [ln for ln in lines if "DONE" in ln]
    assert len(run_lines) == 2
    assert "done=1" in run_lines[0] and "done=2" in run_lines[1]
    assert any("CAMPAIGN START" in ln for ln in lines)
    assert any("CAMPAIGN STOP" in ln for ln in lines)


def test_dry_run_starts_nothing(campaign, monkeypatch):
    rc.build_manifest()
    called = []
    assert run_main(monkeypatch, ["--dry-run"],
                    lambda *a: called.append(1) or ok_result()) == 0
    assert called == []
    doc = rc.load_manifest()
    assert rc.counts(doc)["pending"] == 180
    assert not (campaign / "runs").exists()


@pytest.mark.integration
def test_run_lock_refuses_a_second_concurrent_campaign(campaign, monkeypatch):
    rc.build_manifest()
    (campaign / ".campaign.lock").write_text("pid=999", encoding="utf-8")
    with pytest.raises(SystemExit):
        run_main(monkeypatch, ["--max-runs", "1"], lambda *a: ok_result())


@pytest.mark.integration
def test_all_stacks_are_brought_down_before_the_first_run(campaign, monkeypatch):
    """Two stacks collide on Jaeger's port and cannot co-reside under the memory ceiling.

    A previous runner that died between stack_up and stack_down leaves one up, so the
    campaign must not assume a clean host.
    """
    rc.build_manifest()
    downed = []
    monkeypatch.setattr(rc, "compose",
                        lambda app, *cmd, timeout=600: downed.append((app, cmd)))
    run_main(monkeypatch, ["--max-runs", "1"], lambda *a: ok_result())
    assert {app for app, _ in downed} == set(rc.APPS), "every app must be brought down"
    assert all(cmd[0] == "down" for _, cmd in downed)


@pytest.mark.integration
def test_pre_clean_failure_does_not_abort_the_campaign(campaign, monkeypatch):
    import subprocess as sp

    rc.build_manifest()

    def boom(app, *cmd, timeout=600):
        raise sp.TimeoutExpired(cmd="docker compose down", timeout=600)

    monkeypatch.setattr(rc, "compose", boom)
    assert run_main(monkeypatch, ["--max-runs", "1"], lambda *a: ok_result()) == 0
    assert rc.counts(rc.load_manifest())["done"] == 1
