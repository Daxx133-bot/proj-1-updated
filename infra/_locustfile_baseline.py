
"""Auto-generated Locust load test for DeathStarBench Social Network."""
import random
import string
from locust import HttpUser, task, between


class SocialNetworkUser(HttpUser):
    """Simulates a user performing social network operations."""
    # Wait between 0.5 and 1.5 seconds between tasks
    wait_time = between(0.5, 1.5)

    def _random_string(self, length=8):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    @task(3)
    def compose_post(self):
        """Compose a new post (most common operation)."""
        self.client.post(
            "/wrk2-api/post/compose",
            data={
                "username": f"user_{random.randint(1, 962)}",
                "user_id": str(random.randint(1, 962)),
                "text": f"Load test post {self._random_string(16)}",
                "media_ids": "[]",
                "media_types": "[]",
                "post_type": "0",
            },
        )

    @task(5)
    def read_home_timeline(self):
        """Read home timeline (most frequent read operation)."""
        self.client.get(
            "/wrk2-api/home-timeline/read",
            params={
                "user_id": str(random.randint(1, 962)),
                "start": "0",
                "stop": "10",
            },
        )

    @task(2)
    def read_user_timeline(self):
        """Read a specific user\'s timeline."""
        self.client.get(
            "/wrk2-api/user-timeline/read",
            params={
                "user_id": str(random.randint(1, 962)),
                "start": "0",
                "stop": "10",
            },
        )
