"""Regression tests for compose-service -> container resolution and stack completeness.

Both defects here were found by the 2026-09-26 campaign, not by a test, and both were
silent: the run recorded one service and faulted another, and the stack passed its health
check while missing a service. See _quarantine/QUARANTINE_LOG.md item 12.

The container listings below are the real `docker ps` output shapes from the Hotel
Reservation and Social Network stacks, not invented ones.
"""

from __future__ import annotations

import subprocess

import pytest

from tools import run_campaign as rc
from tools import run_pilot as rp

# Real Hotel Reservation container set. Note the project prefix: "hotelreservation-".
# The substring "reservation" occurs in EVERY one of these names.
HR = [
    "hotelreservation-frontend-1",
    "hotelreservation-geo-1",
    "hotelreservation-profile-1",
    "hotelreservation-rate-1",
    "hotelreservation-recommendation-1",
    "hotelreservation-reservation-1",
    "hotelreservation-search-1",
    "hotelreservation-user-1",
    "hotelreservation-jaeger-1",
    "hotelreservation-consul-1",
    "hotelreservation-mongodb-geo-1",
    "hotelreservation-memcached-rate-1",
]

SN = [
    "socialnetwork-compose-post-service-1",
    "socialnetwork-user-service-1",
    "socialnetwork-user-timeline-service-1",
    "socialnetwork-user-mention-service-1",
    "socialnetwork-media-service-1",
    "socialnetwork-media-frontend-1",
    "socialnetwork-nginx-thrift-1",
]


def fake_docker(monkeypatch, names, label_of=None):
    """Emulate `docker ps` with a compose-service label filter.

    `label_of` maps container name -> compose service. Defaults to stripping the project
    prefix and the `-1` replica suffix, which is what Compose actually does.
    """
    def default_label(n: str) -> str:
        body = n.split("-", 1)[1] if "-" in n else n
        return body.rsplit("-", 1)[0] if body.rsplit("-", 1)[-1].isdigit() else body

    label_of = label_of or {n: default_label(n) for n in names}

    def fake_run(cmd, **kwargs):
        wanted = None
        for i, a in enumerate(cmd):
            if a == "--filter" and i + 1 < len(cmd):
                f = cmd[i + 1]
                if f.startswith("label=com.docker.compose.service="):
                    wanted = f.split("=", 2)[2]
        lines = []
        for n in names:
            lab = label_of[n]
            if wanted is None or lab == wanted:
                lines.append(f"{n}\t{lab}")
        return subprocess.CompletedProcess(cmd, 0, "\n".join(lines) + "\n", "")

    monkeypatch.setattr(rp.subprocess, "run", fake_run)


# ── the defect ───────────────────────────────────────────────────────────────

def test_reservation_resolves_to_reservation_not_geo(monkeypatch):
    """THE BUG: the project prefix "hotelreservation-" contains "reservation".

    Substring matching made every container a candidate and min(key=len) picked
    `hotelreservation-geo-1`, so the campaign SIGKILLed geo and logged it as a
    reservation fault.
    """
    fake_docker(monkeypatch, HR)
    assert rp.container_for("reservation", "docker") == "hotelreservation-reservation-1"


@pytest.mark.parametrize("service", [
    "frontend", "geo", "profile", "rate", "recommendation", "reservation", "search", "user",
])
def test_every_hotel_reservation_service_resolves_to_its_own_container(monkeypatch, service):
    fake_docker(monkeypatch, HR)
    assert rp.container_for(service, "docker") == f"hotelreservation-{service}-1"


@pytest.mark.parametrize("service", [
    "compose-post-service", "user-service", "user-timeline-service",
    "user-mention-service", "media-service",
])
def test_social_network_services_are_not_confused_with_each_other(monkeypatch, service):
    """`user-service` must not match `user-timeline-service`, and `media-service` must
    not match `media-frontend`."""
    fake_docker(monkeypatch, SN)
    assert rp.container_for(service, "docker") == f"socialnetwork-{service}-1"


def test_infrastructure_containers_are_never_selected(monkeypatch):
    """`geo` must resolve to the service, not to `mongodb-geo`."""
    fake_docker(monkeypatch, HR)
    assert rp.container_for("geo", "docker") == "hotelreservation-geo-1"
    assert rp.container_for("rate", "docker") == "hotelreservation-rate-1"


def test_a_missing_service_raises_instead_of_falling_back(monkeypatch):
    fake_docker(monkeypatch, [n for n in HR if "geo" not in n])
    with pytest.raises(SystemExit, match="no running container has compose label"):
        rp.container_for("geo", "docker")


def test_an_ambiguous_match_refuses_to_guess(monkeypatch):
    """Two containers claiming the same compose service must stop the run, not pick one.

    The previous implementation silently returned the shortest name, which is how a fault
    landed on the wrong service without anything being logged.
    """
    names = HR + ["hotelreservation-geo-2"]
    labels = {n: ("geo" if n.startswith("hotelreservation-geo") else
                  (n.split("-", 1)[1].rsplit("-", 1)[0])) for n in names}
    fake_docker(monkeypatch, names, label_of=labels)
    with pytest.raises(SystemExit, match="Refusing to guess"):
        rp.container_for("geo", "docker")


# ── stack completeness ───────────────────────────────────────────────────────

def test_missing_services_reports_graph_services_that_are_not_running(monkeypatch):
    monkeypatch.setattr(rc, "running_services",
                        lambda app: {"frontend", "profile", "rate", "recommendation",
                                     "reservation", "search", "user", "jaeger"})
    assert rc.missing_services("hotelreservation") == ["geo"]


def test_missing_services_is_empty_when_the_stack_is_complete(monkeypatch):
    full = set(rc.load_graph(rc.APPS["hotelreservation"]["graph"]).nodes())
    monkeypatch.setattr(rc, "running_services", lambda app: full | {"jaeger", "consul"})
    assert rc.missing_services("hotelreservation") == []


def test_a_partial_stack_is_not_healthy_even_when_jaeger_and_gateway_answer(monkeypatch):
    """The silent failure: the gateway keeps serving happily with `geo` dead."""
    class Resp:
        ok = True
        status_code = 200

        @staticmethod
        def json():
            return {"data": ["frontend"]}

    monkeypatch.setattr(rc.requests, "get", lambda *a, **k: Resp())
    monkeypatch.setattr(rc, "missing_services", lambda app: ["geo"])
    monkeypatch.setattr(rc.time, "sleep", lambda s: None)
    logged = []
    monkeypatch.setattr(rc, "log_progress", logged.append)
    assert rc.stack_healthy("hotelreservation", timeout_s=1.0) is False
    assert any("geo" in ln for ln in logged), "the missing service must be named in the log"


def test_a_complete_stack_is_healthy(monkeypatch):
    class Resp:
        ok = True
        status_code = 200

        @staticmethod
        def json():
            return {"data": ["frontend"]}

    monkeypatch.setattr(rc.requests, "get", lambda *a, **k: Resp())
    monkeypatch.setattr(rc, "missing_services", lambda app: [])
    monkeypatch.setattr(rc.time, "sleep", lambda s: None)
    assert rc.stack_healthy("hotelreservation", timeout_s=5.0) is True


# ── graph name vs compose service name ───────────────────────────────────────
#
# A service's identity in a trace is whatever it reports to Jaeger, which need not equal
# the compose service that runs it. The Social Network gateway reports "nginx-web-server"
# but is the compose service "nginx-thrift". Conflating the two made the stack-completeness
# check declare the gateway permanently missing and abort the campaign on a healthy stack.

def test_social_network_gateway_maps_to_its_compose_service():
    assert rp.compose_service("socialnetwork", "nginx-web-server") == "nginx-thrift"


def test_every_other_social_network_service_maps_to_itself():
    for svc in ["compose-post-service", "media-service", "user-service",
                "user-timeline-service", "post-storage-service"]:
        assert rp.compose_service("socialnetwork", svc) == svc


def test_hotel_reservation_names_are_all_identity():
    for svc in ["frontend", "geo", "profile", "rate", "recommendation",
                "reservation", "search", "user"]:
        assert rp.compose_service("hotelreservation", svc) == svc


def test_missing_services_translates_before_comparing(monkeypatch):
    """A complete SN stack reports 'nginx-thrift'; nothing may be called missing."""
    graph = set(rc.load_graph(rc.APPS["socialnetwork"]["graph"]).nodes())
    running = {rp.compose_service("socialnetwork", g) for g in graph}
    monkeypatch.setattr(rc, "running_services", lambda app: running)
    assert rc.missing_services("socialnetwork") == []


def test_missing_services_reports_the_gateway_by_its_graph_name(monkeypatch):
    """When nginx-thrift really is down, the report names it as the graph knows it."""
    graph = set(rc.load_graph(rc.APPS["socialnetwork"]["graph"]).nodes())
    running = {rp.compose_service("socialnetwork", g) for g in graph} - {"nginx-thrift"}
    monkeypatch.setattr(rc, "running_services", lambda app: running)
    assert rc.missing_services("socialnetwork") == ["nginx-web-server"]


def test_preflight_rejects_a_graph_service_with_no_compose_counterpart(monkeypatch):
    """Fail at launch, not 28 minutes in."""
    import subprocess as sp

    def fake_run(cmd, **kwargs):
        return sp.CompletedProcess(cmd, 0, "frontend\ngeo\n", "")

    monkeypatch.setattr(rc.subprocess, "run", fake_run)
    monkeypatch.setattr(rc, "find_docker_executable", lambda: "docker")
    problems = rc.preflight_service_names()
    assert problems, "a compose file missing most services must be rejected"
    assert any("compose_aliases" in p for p in problems), "must say how to fix it"
