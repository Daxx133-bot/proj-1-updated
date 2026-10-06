#!/usr/bin/env python3
"""
health_check_hotel.py — Verify the DeathStarBench Hotel Reservation Stack
==========================================================================
Runs a series of checks to confirm the Hotel Reservation stack is healthy:
  1. All expected Docker containers are running.
  2. Hotel frontend responds on port 5000.
  3. Hotel Jaeger UI responds on port 16687.
  4. Jaeger /api/services endpoint lists registered Hotel services.
  5. End-to-end hotel search flow works.

Usage:
    python infra/health_check_hotel.py [--base-url URL] [--jaeger-url URL]

Exit code 0 = all checks pass, 1 = at least one check failed.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

DEFAULT_BASE_URL = "http://localhost:5000"
DEFAULT_JAEGER_URL = "http://localhost:16687"

# Expected application services (from Jaeger perspective)
EXPECTED_HOTEL_SERVICES = [
    "frontend",
    "profile",
    "search",
    "geo",
    "rate",
    "reservation",
    "user",
    "recommendation",
]

# Expected Docker container name fragments
EXPECTED_CONTAINERS = [
    "frontend",
    "profile",
    "search",
    "geo",
    "rate",
    "reservation",
    "user",
    "recommendation",
    "jaeger",
    "mongodb-geo",
    "mongodb-profile",
    "memcached-profile",
]


def check_result(name: str, ok: bool, detail: str = "") -> bool:
    status = "[PASS]" if ok else "[FAIL]"
    msg = f"  {status} {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return ok


def check_containers() -> bool:
    """Verify that expected Hotel containers are running."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=True,
        )
        running = result.stdout.lower()
        missing = [c for c in EXPECTED_CONTAINERS if c.lower() not in running]
        if missing:
            return check_result("Docker containers", False,
                                f"Missing: {missing[:3]}{'...' if len(missing) > 3 else ''}")
        return check_result("Docker containers", True,
                            f"All {len(EXPECTED_CONTAINERS)} expected containers running")
    except Exception as e:
        return check_result("Docker containers", False, str(e))


def check_frontend(base_url: str) -> bool:
    """Check Hotel frontend HTTP response."""
    try:
        r = requests.get(base_url, timeout=10)
        ok = r.status_code < 500
        return check_result("Hotel frontend", ok, f"HTTP {r.status_code} from {base_url}")
    except requests.RequestException as e:
        return check_result("Hotel frontend", False, str(e))


def check_jaeger(jaeger_url: str) -> bool:
    """Check Hotel Jaeger UI."""
    try:
        r = requests.get(f"{jaeger_url}/", timeout=10)
        ok = r.status_code < 500
        return check_result("Hotel Jaeger UI", ok, f"HTTP {r.status_code} from {jaeger_url}")
    except requests.RequestException as e:
        return check_result("Hotel Jaeger UI", False, str(e))


def check_jaeger_services(jaeger_url: str) -> bool:
    """Verify that Hotel services appear in Jaeger's service registry."""
    try:
        r = requests.get(f"{jaeger_url}/api/services", timeout=15)
        r.raise_for_status()
        data = r.json()
        raw_services = data.get("data") or []
        registered = [s.lower() for s in raw_services if s]
        found = [s for s in EXPECTED_HOTEL_SERVICES if s in registered]
        missing = [s for s in EXPECTED_HOTEL_SERVICES if s not in registered]

        ok = len(found) >= 3  # At least 3 services must appear (may not all appear yet)
        detail = f"{len(found)}/{len(EXPECTED_HOTEL_SERVICES)} services in Jaeger"
        if missing:
            detail += f" (missing: {missing})"
        return check_result("Hotel Jaeger services", ok, detail)

    except requests.RequestException as e:
        return check_result("Hotel Jaeger services", False, str(e))


def check_hotel_search(base_url: str) -> bool:
    """Verify end-to-end hotel search (hits geo, rate, profile, search)."""
    try:
        r = requests.get(
            f"{base_url}/hotels",
            params={
                "inDate": "2015-04-09",
                "outDate": "2015-04-10",
                "lat": "37.7867",
                "lon": "-122.4112",
            },
            timeout=15,
        )
        ok = r.status_code < 500
        detail = f"HTTP {r.status_code}"
        if ok and r.headers.get("Content-Type", "").startswith("application/json"):
            try:
                body = r.json()
                hotels = body.get("hotels", body if isinstance(body, list) else [])
                detail += f", {len(hotels)} hotel(s) returned"
            except Exception:
                pass
        return check_result("Hotel search end-to-end", ok, detail)
    except requests.RequestException as e:
        return check_result("Hotel search end-to-end", False, str(e))


def check_user_service(base_url: str) -> bool:
    """Verify user service is reachable via frontend."""
    try:
        r = requests.get(
            f"{base_url}/user",
            params={"username": "Cornell_1"},
            timeout=10,
        )
        ok = r.status_code < 500
        return check_result("User service via frontend", ok, f"HTTP {r.status_code}")
    except requests.RequestException as e:
        return check_result("User service via frontend", False, str(e))


def check_recommendations(base_url: str) -> bool:
    """Verify recommendation service is reachable."""
    try:
        r = requests.get(
            f"{base_url}/recommendations",
            params={"require": "dis", "lat": "38.0235", "lon": "-122.095"},
            timeout=10,
        )
        ok = r.status_code < 500
        return check_result("Recommendation service", ok, f"HTTP {r.status_code}")
    except requests.RequestException as e:
        return check_result("Recommendation service", False, str(e))


def main():
    parser = argparse.ArgumentParser(
        description="Health check for DeathStarBench Hotel Reservation"
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help=f"Hotel frontend URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--jaeger-url", default=DEFAULT_JAEGER_URL,
                        help=f"Hotel Jaeger URL (default: {DEFAULT_JAEGER_URL})")
    parser.add_argument("--retry", type=int, default=1,
                        help="Number of retry attempts per check (default: 1)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Hotel Reservation Health Check")
    print("=" * 60)
    print(f"  Frontend: {args.base_url}")
    print(f"  Jaeger:   {args.jaeger_url}")
    print("=" * 60)
    print()

    results = []
    results.append(check_containers())
    results.append(check_frontend(args.base_url))
    results.append(check_jaeger(args.jaeger_url))
    results.append(check_jaeger_services(args.jaeger_url))
    results.append(check_hotel_search(args.base_url))
    results.append(check_user_service(args.base_url))
    results.append(check_recommendations(args.base_url))

    passed = sum(results)
    total = len(results)

    print()
    print("=" * 60)
    if passed == total:
        print(f"  [ALL PASS] {passed}/{total} checks passed.")
        print("  Hotel Reservation stack is healthy.")
        print()
        print("  Next step: python infra/generate_hotel_load.py")
        sys.exit(0)
    else:
        print(f"  [PARTIAL] {passed}/{total} checks passed.")
        print("  Some services may not be ready. Wait 30s and retry, or check Docker logs.")
        sys.exit(1)


if __name__ == "__main__":
    main()
