#!/usr/bin/env python3
"""
health_check.py — Verify the DeathStarBench Social Network Stack
================================================================
Runs a series of checks to confirm the entire stack is healthy:
  1. All expected Docker containers are running.
  2. Nginx gateway responds on port 8080.
  3. Jaeger UI responds on port 16686.
  4. Jaeger's /api/services endpoint returns registered services.
  5. Core user flows work: register → login → compose post → read timeline.

Usage:
    python infra/health_check.py [--nginx-url URL] [--jaeger-url URL]

Exit code 0 = all checks pass, 1 = at least one check failed.
"""

import argparse
import json
import random
import string
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import requests

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Default endpoints ──────────────────────────────────────────────────────
DEFAULT_NGINX_URL = "http://localhost:8080"
DEFAULT_JAEGER_URL = "http://localhost:16686"

# ── Expected microservice containers (service names from docker-compose) ──
# These are the application-level services we care about for the experiment.
# Storage backends (MongoDB, Redis, Memcached) are also checked but listed
# separately so we can distinguish failures.
EXPECTED_APP_SERVICES = [
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
    "media-frontend",
]

EXPECTED_INFRA_SERVICES = [
    "jaeger-agent",
    "social-graph-mongodb",
    "social-graph-redis",
    "home-timeline-redis",
    "post-storage-mongodb",
    "post-storage-memcached",
    "user-timeline-mongodb",
    "user-timeline-redis",
    "user-mongodb",
    "user-memcached",
    "url-shorten-mongodb",
    "url-shorten-memcached",
    "media-mongodb",
    "media-memcached",
]


def random_string(length: int = 8) -> str:
    """Generate a random alphanumeric string for unique test data."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


from infra.docker_utils import find_docker_executable


class HealthChecker:
    """
    Runs all health checks and tracks pass/fail status.
    Each check method returns True on success, False on failure,
    and prints its own status messages.
    """

    def __init__(self, nginx_url: str, jaeger_url: str):
        self.nginx_url = nginx_url.rstrip("/")
        self.jaeger_url = jaeger_url.rstrip("/")
        self.results: list[tuple[str, bool, str]] = []  # (name, passed, detail)

    def _record(self, name: str, passed: bool, detail: str = "") -> bool:
        """Record a check result and print status."""
        status = "PASS" if passed else "FAIL"
        msg = f"  [{status}] {name}"
        if detail:
            msg += f" - {detail}"
        print(msg)
        self.results.append((name, passed, detail))
        return passed

    # ── Check 1: Docker containers ─────────────────────────────────────
    def check_containers(self) -> bool:
        """Verify all expected containers are running via docker ps."""
        print("\n=== Container Status ===")
        try:
            docker_exe = find_docker_executable()
            result = subprocess.run(
                [docker_exe, "ps", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True,
            )
            running = set(result.stdout.strip().split("\n"))
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return self._record("Docker connectivity", False, str(e))

        self._record("Docker connectivity", True, f"{len(running)} containers running")

        all_ok = True
        # Check application services
        for svc in EXPECTED_APP_SERVICES:
            # Container names may have a project prefix, so do a substring match
            found = any(svc in name for name in running)
            self._record(f"Container: {svc}", found,
                         "running" if found else "NOT FOUND")
            if not found:
                all_ok = False

        # Check infrastructure services (informational — don't fail hard)
        for svc in EXPECTED_INFRA_SERVICES:
            found = any(svc in name for name in running)
            self._record(f"Container: {svc}", found,
                         "running" if found else "NOT FOUND (infra)")
            if not found:
                all_ok = False

        return all_ok

    # ── Check 2: Nginx gateway ─────────────────────────────────────────
    def check_nginx(self) -> bool:
        """Verify Nginx responds on port 8080."""
        print("\n=== Nginx Gateway ===")
        try:
            resp = requests.get(self.nginx_url, timeout=10)
            # DSB's Nginx returns a page or 200 on root; any response is fine
            return self._record(
                "Nginx reachable", True,
                f"HTTP {resp.status_code}"
            )
        except requests.RequestException as e:
            return self._record("Nginx reachable", False, str(e))

    # ── Check 3: Jaeger UI ─────────────────────────────────────────────
    def check_jaeger_ui(self) -> bool:
        """Verify Jaeger UI responds on port 16686."""
        print("\n=== Jaeger Tracing ===")
        try:
            resp = requests.get(self.jaeger_url, timeout=10)
            return self._record(
                "Jaeger UI reachable", True,
                f"HTTP {resp.status_code}"
            )
        except requests.RequestException as e:
            return self._record("Jaeger UI reachable", False, str(e))

    # ── Check 4: Jaeger has services ───────────────────────────────────
    def check_jaeger_services(self) -> bool:
        """
        Query Jaeger's /api/services to see if any microservices have
        reported traces. This may be empty right after startup — that's
        expected. We just confirm the API works.
        """
        try:
            resp = requests.get(
                f"{self.jaeger_url}/api/services", timeout=10
            )
            data = resp.json()
            services = data.get("data") or []
            return self._record(
                "Jaeger /api/services", True,
                f"{len(services)} services registered: {services}"
            )
        except requests.RequestException as e:
            return self._record("Jaeger /api/services", False, str(e))

    # ── Check 5: User flows ────────────────────────────────────────────
    def check_user_flows(self) -> bool:
        """
        Exercise core user flows against the live stack:
          1. Register a test user
          2. Login to get credentials
          3. Compose a post
          4. Read the user's timeline
        """
        print("\n=== User Flow Validation ===")
        # Generate unique test user to avoid conflicts
        username = f"healthcheck_{random_string()}"
        password = "testpass123"
        first_name = "Health"
        last_name = "Check"

        # 5a. Register user
        try:
            resp = requests.post(
                f"{self.nginx_url}/wrk2-api/user/register",
                data={
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "password": password,
                    "user_id": random.randint(100000, 999999),
                },
                timeout=15,
            )
            reg_ok = resp.status_code == 200
            self._record("Register user", reg_ok,
                         f"HTTP {resp.status_code}, user={username}")
        except requests.RequestException as e:
            self._record("Register user", False, str(e))
            return False

        # Small delay for the registration to propagate through services
        time.sleep(1)

        # 5b. Login
        try:
            resp = requests.post(
                f"{self.nginx_url}/api/user/login",
                data={
                    "username": username,
                    "password": password,
                },
                timeout=15,
            )
            login_ok = resp.status_code == 200
            self._record("Login user", login_ok,
                          f"HTTP {resp.status_code}")
        except requests.RequestException as e:
            self._record("Login user", False, str(e))
            return False

        # 5c. Compose post
        try:
            post_text = f"Health check post {random_string(16)}"
            resp = requests.post(
                f"{self.nginx_url}/wrk2-api/post/compose",
                data={
                    "username": username,
                    "user_id": str(random.randint(100000, 999999)),
                    "text": post_text,
                    "media_ids": "[]",
                    "media_types": "[]",
                    "post_type": "0",
                },
                timeout=15,
            )
            post_ok = resp.status_code == 200
            self._record("Compose post", post_ok,
                         f"HTTP {resp.status_code}")
        except requests.RequestException as e:
            self._record("Compose post", False, str(e))
            return False

        # Small delay for the post to propagate to timeline services
        time.sleep(1)

        # 5d. Read user timeline
        try:
            resp = requests.get(
                f"{self.nginx_url}/wrk2-api/user-timeline/read",
                params={
                    "user_id": str(random.randint(1, 100)),
                    "start": "0",
                    "stop": "10",
                },
                timeout=15,
            )
            timeline_ok = resp.status_code == 200
            self._record("Read user timeline", timeline_ok,
                         f"HTTP {resp.status_code}")
        except requests.RequestException as e:
            self._record("Read user timeline", False, str(e))
            return False

        return all([reg_ok, login_ok, post_ok, timeline_ok])

    # ── Summary ────────────────────────────────────────────────────────
    def run_all(self) -> bool:
        """Run all checks and print a summary."""
        print("=" * 60)
        print("  DeathStarBench Social Network - Health Check")
        print("=" * 60)

        self.check_containers()
        self.check_nginx()
        self.check_jaeger_ui()
        self.check_jaeger_services()
        self.check_user_flows()

        # Summary
        total = len(self.results)
        passed = sum(1 for _, p, _ in self.results if p)
        failed = total - passed

        print("\n" + "=" * 60)
        print(f"  Results: {passed}/{total} checks passed, {failed} failed")
        print("=" * 60)

        if failed > 0:
            print("\n  Failed checks:")
            for name, p, detail in self.results:
                if not p:
                    print(f"    [FAIL] {name}: {detail}")
            return False

        print("\n  All checks passed! The stack is ready for experiments.")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Health check for the DeathStarBench Social Network stack"
    )
    parser.add_argument(
        "--nginx-url", default=DEFAULT_NGINX_URL,
        help=f"Nginx gateway URL (default: {DEFAULT_NGINX_URL})",
    )
    parser.add_argument(
        "--jaeger-url", default=DEFAULT_JAEGER_URL,
        help=f"Jaeger UI URL (default: {DEFAULT_JAEGER_URL})",
    )
    args = parser.parse_args()

    checker = HealthChecker(args.nginx_url, args.jaeger_url)
    success = checker.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
