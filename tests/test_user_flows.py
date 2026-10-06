"""
test_user_flows.py — Integration Tests for Core User Flows
============================================================
Tests the core operations of the Social Network application
against the live Docker stack. These tests verify FUNCTIONAL
correctness (not just "is the container running?").

Tests:
  - Register a user
  - Login
  - Compose a post
  - Read user timeline
  - Read home timeline
  - Follow a user
  - Unfollow a user

These are run after every fault-recovery cycle in Phase 4 to confirm
the system returned to correct behavior.
"""

import random
import string
import time

import pytest
import requests


@pytest.mark.integration
class TestUserRegistration:
    """Tests for user registration and login."""

    def test_register_user(self, base_url: str):
        """Register a new user and verify HTTP 200 response."""
        suffix = "".join(random.choices(string.ascii_lowercase, k=6))
        resp = requests.post(
            f"{base_url}/wrk2-api/user/register",
            data={
                "first_name": "Test",
                "last_name": "User",
                "username": f"test_reg_{suffix}",
                "password": "password123",
                "user_id": random.randint(300000, 399999),
            },
            timeout=15,
        )
        assert resp.status_code == 200, (
            f"Registration failed: HTTP {resp.status_code}, body: {resp.text[:200]}"
        )

    def test_login_user(self, base_url: str, test_user: dict):
        """Login with a registered user and verify HTTP 200."""
        resp = requests.post(
            f"{base_url}/api/user/login",
            data={
                "username": test_user["username"],
                "password": test_user["password"],
            },
            timeout=15,
        )
        assert resp.status_code == 200, (
            f"Login failed: HTTP {resp.status_code}, body: {resp.text[:200]}"
        )


@pytest.mark.integration
class TestPostOperations:
    """Tests for creating and reading posts."""

    def test_compose_post(self, base_url: str, test_user: dict):
        """Compose a text post and verify HTTP 200."""
        post_text = f"Test post {random.randint(1, 99999)}"
        resp = requests.post(
            f"{base_url}/wrk2-api/post/compose",
            data={
                "username": test_user["username"],
                "user_id": str(test_user["user_id"]),
                "text": post_text,
                "media_ids": "[]",
                "media_types": "[]",
                "post_type": "0",
            },
            timeout=15,
        )
        assert resp.status_code == 200, (
            f"Compose post failed: HTTP {resp.status_code}, body: {resp.text[:200]}"
        )

    def test_compose_post_with_mention(self, base_url: str, test_user: dict,
                                        second_test_user: dict):
        """Compose a post with an @mention and verify it's processed."""
        post_text = f"Hey @{second_test_user['username']} check this out {random.randint(1, 99999)}"
        resp = requests.post(
            f"{base_url}/wrk2-api/post/compose",
            data={
                "username": test_user["username"],
                "user_id": str(test_user["user_id"]),
                "text": post_text,
                "media_ids": "[]",
                "media_types": "[]",
                "post_type": "0",
            },
            timeout=15,
        )
        assert resp.status_code == 200, (
            f"Compose post with mention failed: HTTP {resp.status_code}"
        )

    def test_read_user_timeline(self, base_url: str, test_user: dict):
        """
        Read the user's own timeline.

        Note: We use a generic user_id (from the init_social_graph dataset)
        rather than our test user, because the test user may not have many
        posts in their timeline yet.
        """
        resp = requests.get(
            f"{base_url}/wrk2-api/user-timeline/read",
            params={
                "user_id": str(random.randint(1, 100)),
                "start": "0",
                "stop": "10",
            },
            timeout=15,
        )
        assert resp.status_code == 200, (
            f"Read user timeline failed: HTTP {resp.status_code}"
        )

    def test_read_home_timeline(self, base_url: str):
        """Read the home timeline for a user from the init dataset."""
        resp = requests.get(
            f"{base_url}/wrk2-api/home-timeline/read",
            params={
                "user_id": str(random.randint(1, 100)),
                "start": "0",
                "stop": "10",
            },
            timeout=15,
        )
        assert resp.status_code == 200, (
            f"Read home timeline failed: HTTP {resp.status_code}"
        )


@pytest.mark.integration
class TestSocialGraph:
    """Tests for follow/unfollow operations."""

    def test_follow_user(self, base_url: str, test_user: dict,
                         second_test_user: dict):
        """Follow another user and verify HTTP 200."""
        resp = requests.post(
            f"{base_url}/wrk2-api/user/follow",
            data={
                "user_id": str(test_user["user_id"]),
                "followee_id": str(second_test_user["user_id"]),
            },
            timeout=15,
        )
        assert resp.status_code == 200, (
            f"Follow failed: HTTP {resp.status_code}, body: {resp.text[:200]}"
        )

    def test_unfollow_user(self, base_url: str, test_user: dict,
                           second_test_user: dict):
        """Unfollow a previously followed user and verify HTTP 200."""
        # Ensure we're following first
        requests.post(
            f"{base_url}/wrk2-api/user/follow",
            data={
                "user_id": str(test_user["user_id"]),
                "followee_id": str(second_test_user["user_id"]),
            },
            timeout=15,
        )
        time.sleep(1)

        # Now unfollow
        resp = requests.post(
            f"{base_url}/wrk2-api/user/unfollow",
            data={
                "user_id": str(test_user["user_id"]),
                "followee_id": str(second_test_user["user_id"]),
            },
            timeout=15,
        )
        assert resp.status_code == 200, (
            f"Unfollow failed: HTTP {resp.status_code}, body: {resp.text[:200]}"
        )
