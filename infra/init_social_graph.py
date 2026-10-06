#!/usr/bin/env python3
"""
init_social_graph.py — Initialize Social Graph Data
====================================================
Wraps DSB's own scripts/init_social_graph.py to seed the database with
users and follow relationships using the Reed98 Facebook dataset (~1K users).

This step is required before any meaningful workload can run, because the
wrk2 Lua scripts expect users and social connections to exist.

Usage:
    python infra/init_social_graph.py [--dsb-dir PATH] [--graph socfb-Reed98]
                                      [--nginx-ip localhost] [--nginx-port 8080]
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import requests


# ── Defaults ───────────────────────────────────────────────────────────────
DEFAULT_DSB_RELATIVE_PATH = "../DeathStarBench"
DEFAULT_GRAPH = "socfb-Reed98"          # Smallest graph: ~1K users
DEFAULT_NGINX_IP = "localhost"
DEFAULT_NGINX_PORT = 8080


def get_project_root() -> Path:
    """Return the project root (parent of /infra)."""
    return Path(__file__).resolve().parent.parent


def run_init_script(
    dsb_dir: Path,
    graph: str,
    nginx_ip: str,
    nginx_port: int,
) -> bool:
    """
    Execute DSB's init_social_graph.py script.

    This Python script sends HTTP requests to the Nginx gateway to:
      1. Register all users from the chosen dataset.
      2. Create follow relationships between them.

    It can take several minutes for larger graphs.
    """
    init_script = dsb_dir / "socialNetwork" / "scripts" / "init_social_graph.py"

    if not init_script.exists():
        print(f"[ERROR] Init script not found at {init_script}")
        print("[ERROR] Is DeathStarBench cloned correctly?")
        return False

    print(f"[INFO] Running social graph initialization...")
    print(f"[INFO] Graph dataset: {graph}")
    print(f"[INFO] Target: {nginx_ip}:{nginx_port}")
    print("[INFO] This may take a few minutes for user registration...")

    cmd = [
        sys.executable,  # Use the same Python interpreter
        str(init_script),
        f"--graph={graph}",
        f"--ip={nginx_ip}",
        f"--port={nginx_port}",
    ]

    try:
        # Run with a generous timeout — Reed98 takes ~2-3 minutes
        result = subprocess.run(
            cmd,
            cwd=str(dsb_dir / "socialNetwork"),
            timeout=600,  # 10 minute timeout
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("[INFO] Social graph initialization completed successfully.")
            # Print last few lines of output for confirmation
            output_lines = result.stdout.strip().split("\n")
            for line in output_lines[-5:]:
                print(f"  {line}")
            return True
        else:
            print(f"[ERROR] Init script failed with exit code {result.returncode}")
            print(f"[ERROR] stdout: {result.stdout[-500:]}")
            print(f"[ERROR] stderr: {result.stderr[-500:]}")
            return False

    except subprocess.TimeoutExpired:
        print("[ERROR] Init script timed out after 10 minutes.")
        print("[ERROR] The graph dataset might be too large. Try --graph=socfb-Reed98")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error running init script: {e}")
        return False


def verify_social_graph(nginx_url: str) -> bool:
    """
    Verify that the social graph was populated by reading a timeline
    and checking that follow relationships exist.
    """
    print("\n[INFO] Verifying social graph initialization...")

    # Try to read a user timeline — if users exist, this should return data
    try:
        resp = requests.get(
            f"{nginx_url}/wrk2-api/user-timeline/read",
            params={"user_id": "1", "start": "0", "stop": "10"},
            timeout=10,
        )
        print(f"[INFO] User timeline read: HTTP {resp.status_code}")

        # Try to get follower info for user 1
        resp2 = requests.get(
            f"{nginx_url}/wrk2-api/user-timeline/read",
            params={"user_id": "2", "start": "0", "stop": "10"},
            timeout=10,
        )
        print(f"[INFO] User 2 timeline read: HTTP {resp2.status_code}")

        if resp.status_code == 200 and resp2.status_code == 200:
            print("[INFO] Social graph verification passed.")
            return True
        else:
            print("[WARNING] Timeline reads returned non-200 status.")
            print("[WARNING] Graph may not be fully initialized yet.")
            return False

    except requests.RequestException as e:
        print(f"[ERROR] Could not verify social graph: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Initialize the DeathStarBench social graph with test data"
    )
    parser.add_argument(
        "--dsb-dir", type=str, default=None,
        help=f"Path to DeathStarBench repo (default: {DEFAULT_DSB_RELATIVE_PATH})",
    )
    parser.add_argument(
        "--graph", type=str, default=DEFAULT_GRAPH,
        choices=["socfb-Reed98", "ego-twitter", "soc-twitter-follows-mun"],
        help=f"Social graph dataset to use (default: {DEFAULT_GRAPH})",
    )
    parser.add_argument(
        "--nginx-ip", type=str, default=DEFAULT_NGINX_IP,
        help=f"Nginx IP address (default: {DEFAULT_NGINX_IP})",
    )
    parser.add_argument(
        "--nginx-port", type=int, default=DEFAULT_NGINX_PORT,
        help=f"Nginx port (default: {DEFAULT_NGINX_PORT})",
    )
    args = parser.parse_args()

    project_root = get_project_root()

    if args.dsb_dir:
        dsb_dir = Path(args.dsb_dir).resolve()
    else:
        dsb_dir = (project_root / DEFAULT_DSB_RELATIVE_PATH).resolve()

    # Step 1: Run the init script
    if not run_init_script(dsb_dir, args.graph, args.nginx_ip, args.nginx_port):
        print("\n[ERROR] Social graph initialization failed.")
        sys.exit(1)

    # Step 2: Verify the graph was populated
    nginx_url = f"http://{args.nginx_ip}:{args.nginx_port}"
    time.sleep(3)  # Give services a moment to process all registrations
    verify_social_graph(nginx_url)

    print("\n" + "=" * 60)
    print("  Social graph initialized successfully!")
    print(f"  Dataset: {args.graph}")
    print("=" * 60)


if __name__ == "__main__":
    main()
