"""
test_service_health.py — Service Health Integration Tests
===========================================================
Parametrized tests that verify each expected container is running
and Jaeger is receiving traces. These serve as a quick sanity check
that the stack is operational.
"""

import subprocess

import pytest
import requests


# ── Expected Docker containers (application services) ──────────────────────
# These must all be running for the experiment to produce valid results.
EXPECTED_CONTAINERS = [
    "nginx-thrift",
    "compose-post-service",
    "post-storage-service",
    "user-timeline-service",
    "home-timeline-service",
    "social-graph-service",
    "user-service",
    "text-service",
    "unique-id-service",
    "url-shorten-service",
    "user-mention-service",
    "media-service",
]


from infra.docker_utils import find_docker_executable


def get_running_containers() -> set[str]:
    """Get the set of currently running Docker container names."""
    try:
        docker_exe = find_docker_executable()
        result = subprocess.run(
            [docker_exe, "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=True,
        )
        return set(result.stdout.strip().split("\n"))
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()


@pytest.mark.integration
class TestContainerHealth:
    """Verify all expected containers are running."""

    @pytest.fixture(scope="class")
    def running_containers(self) -> set[str]:
        """Cache the list of running containers for all tests in this class."""
        return get_running_containers()

    @pytest.mark.parametrize("service", EXPECTED_CONTAINERS)
    def test_container_running(self, service: str, running_containers: set[str]):
        """
        Verify that the given service's container is running.

        Container names may have a project prefix (e.g., "socialnetwork-"),
        so we do a substring match.
        """
        found = any(service in name for name in running_containers)
        assert found, (
            f"Container for '{service}' is NOT running. "
            f"Running containers: {sorted(running_containers)}"
        )


@pytest.mark.integration
class TestJaegerHealth:
    """Verify Jaeger is operational and receiving traces."""

    def test_jaeger_ui_reachable(self, jaeger_url: str):
        """Jaeger UI should respond with HTTP 200."""
        resp = requests.get(jaeger_url, timeout=10)
        assert resp.status_code == 200, (
            f"Jaeger UI not reachable: HTTP {resp.status_code}"
        )

    def test_jaeger_has_services(self, jaeger_url: str):
        """
        Jaeger should have at least one non-jaeger service registered.
        This confirms that the application services are sending traces.
        """
        resp = requests.get(f"{jaeger_url}/api/services", timeout=10)
        assert resp.status_code == 200, (
            f"Jaeger /api/services failed: HTTP {resp.status_code}"
        )

        data = resp.json()
        services = data.get("data") or []

        # Filter out jaeger's own service
        app_services = [s for s in services if "jaeger" not in s.lower()]

        assert len(app_services) > 0, (
            f"No application services registered in Jaeger. "
            f"Services found: {services}. "
            f"Have you generated load? Run generate_baseline_load.py first."
        )

    def test_jaeger_has_recent_traces(self, jaeger_url: str):
        """
        Jaeger should have traces from the last 5 minutes.
        This confirms that tracing is actively working, not just historically.
        """
        # Get any service
        resp = requests.get(f"{jaeger_url}/api/services", timeout=10)
        services = resp.json().get("data") or []
        app_services = [s for s in services if "jaeger" not in s.lower()]

        if not app_services:
            pytest.skip("No services in Jaeger; skipping trace recency check")

        # Query recent traces for the first service
        resp = requests.get(
            f"{jaeger_url}/api/traces",
            params={
                "service": app_services[0],
                "lookback": "5m",
                "limit": 5,
            },
            timeout=30,
        )
        assert resp.status_code == 200

        traces = resp.json().get("data") or []
        assert len(traces) > 0, (
            f"No traces found in the last 5 minutes for '{app_services[0]}'. "
            f"Is load being generated?"
        )
