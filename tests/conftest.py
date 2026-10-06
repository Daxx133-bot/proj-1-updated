"""
conftest.py — Pytest Fixtures for Integration Tests
=====================================================
Provides shared fixtures for all test modules:
  - base_url: Nginx gateway URL
  - jaeger_url: Jaeger query URL
  - test_user: A registered test user (created once per session)
"""

import random
import string
import time

import pytest
import requests


# ── Configuration ──────────────────────────────────────────────────────────

def pytest_addoption(parser):
    """Add custom CLI options for the test suite."""
    parser.addoption(
        "--nginx-url", default="http://localhost:8080",
        help="Nginx gateway URL",
    )
    parser.addoption(
        "--jaeger-url", default="http://localhost:16686",
        help="Jaeger query URL",
    )


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def base_url(request) -> str:
    """Nginx gateway URL, configurable via --nginx-url."""
    return request.config.getoption("--nginx-url")


@pytest.fixture(scope="session")
def jaeger_url(request) -> str:
    """Jaeger query URL, configurable via --jaeger-url."""
    return request.config.getoption("--jaeger-url")


@pytest.fixture(scope="session")
def registered_test_users(base_url: str) -> dict:
    """
    Register two test users and establish a mutual follow connection.
    This ensures that both users always have at least one follower and one followee,
    preventing upstream Redis ZADD syntax errors on empty sets during tests.
    """
    suffix1 = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    user_id1 = random.randint(100000, 499999)
    user1 = {
        "username": f"pytest_user_{suffix1}",
        "password": "testpass123",
        "user_id": user_id1,
        "first_name": "Pytest",
        "last_name": "User1",
    }

    suffix2 = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    user_id2 = random.randint(500000, 999999)
    user2 = {
        "username": f"pytest_user2_{suffix2}",
        "password": "testpass456",
        "user_id": user_id2,
        "first_name": "Pytest",
        "last_name": "User2",
    }

    # Register user 1
    resp = requests.post(
        f"{base_url}/wrk2-api/user/register",
        data={
            "first_name": user1["first_name"],
            "last_name": user1["last_name"],
            "username": user1["username"],
            "password": user1["password"],
            "user_id": user1["user_id"],
        },
        timeout=15,
    )
    assert resp.status_code == 200, f"Failed to register test user 1: {resp.text}"

    # Register user 2
    resp = requests.post(
        f"{base_url}/wrk2-api/user/register",
        data={
            "first_name": user2["first_name"],
            "last_name": user2["last_name"],
            "username": user2["username"],
            "password": user2["password"],
            "user_id": user2["user_id"],
        },
        timeout=15,
    )
    assert resp.status_code == 200, f"Failed to register test user 2: {resp.text}"

    time.sleep(1)

    # Establish mutual follow
    resp1 = requests.post(
        f"{base_url}/wrk2-api/user/follow",
        data={
            "user_id": str(user1["user_id"]),
            "followee_id": str(user2["user_id"]),
        },
        timeout=15,
    )
    resp2 = requests.post(
        f"{base_url}/wrk2-api/user/follow",
        data={
            "user_id": str(user2["user_id"]),
            "followee_id": str(user1["user_id"]),
        },
        timeout=15,
    )
    assert resp1.status_code == 200, f"Follow 1 failed: {resp1.text}"
    assert resp2.status_code == 200, f"Follow 2 failed: {resp2.text}"

    time.sleep(1)
    return {"user1": user1, "user2": user2}


@pytest.fixture(scope="session")
def test_user(registered_test_users: dict) -> dict:
    """Return the first registered test user."""
    return registered_test_users["user1"]


@pytest.fixture(scope="session")
def second_test_user(registered_test_users: dict) -> dict:
    """Return the second registered test user."""
    return registered_test_users["user2"]

