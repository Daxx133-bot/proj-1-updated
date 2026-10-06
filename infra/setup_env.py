#!/usr/bin/env python3
"""
setup_env.py — Environment Setup for DeathStarBench Social Network
==================================================================
Clones the DeathStarBench repository (with submodules for wrk2), copies our
docker-compose.override.yml into the socialNetwork directory, and brings the
stack up with docker-compose.

Usage:
    python infra/setup_env.py [--dsb-dir PATH] [--skip-clone]

The --dsb-dir flag controls where DeathStarBench is cloned (default: ../DeathStarBench
relative to this project). Use --skip-clone if you already have it cloned.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Add project root to sys.path so infra.* modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Constants ──────────────────────────────────────────────────────────────
# Default location to clone DeathStarBench, relative to project root
DEFAULT_DSB_RELATIVE_PATH = "../DeathStarBench"
# The subdirectory inside DSB that contains the Social Network application
SOCIAL_NETWORK_DIR = "socialNetwork"
# Our override file, relative to this script
OVERRIDE_FILE = "docker-compose.override.yml"


def get_project_root() -> Path:
    """Return the project root (parent of /infra)."""
    return Path(__file__).resolve().parent.parent


def clone_deathstarbench(dsb_dir: Path) -> None:
    """
    Clone the DeathStarBench repository with submodules.
    On Windows, DeathStarBench contains files in 'daprApps_v1' with '*' in filename
    which causes standard git checkout on NTFS to fail.
    We use sparse-checkout to check out only 'socialNetwork' and needed submodules.
    """
    social_dir = dsb_dir / SOCIAL_NETWORK_DIR
    if social_dir.exists():
        print(f"[INFO] DeathStarBench repository exists and is valid at {dsb_dir}")
        return

    if dsb_dir.exists():
        print(f"[WARNING] {dsb_dir} exists without socialNetwork. Cleaning up...")
        # Use powershell Remove-Item on windows for reliability
        subprocess.run(
            ["powershell", "-Command", f"Remove-Item -Recurse -Force '{dsb_dir}'"],
            capture_output=True,
        )

    print(f"[INFO] Initializing DeathStarBench repository with sparse-checkout at {dsb_dir}...")
    dsb_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initialize git repo
    subprocess.run(["git", "init"], cwd=str(dsb_dir), check=True)
    # 2. Add remote
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/delimitrou/DeathStarBench.git"],
        cwd=str(dsb_dir),
        check=True,
    )
    # 3. Disable protectNTFS and enable sparse-checkout for socialNetwork and wrk2
    subprocess.run(["git", "config", "core.protectNTFS", "false"], cwd=str(dsb_dir), check=True)
    subprocess.run(["git", "sparse-checkout", "init", "--cone"], cwd=str(dsb_dir), check=True)
    subprocess.run(["git", "sparse-checkout", "set", "socialNetwork", "wrk2"], cwd=str(dsb_dir), check=True)

    # 4. Fetch depth 1
    print("[INFO] Fetching DeathStarBench (depth=1)...")
    subprocess.run(["git", "fetch", "--depth", "1", "origin", "master"], cwd=str(dsb_dir), check=True)
    
    # 5. Checkout
    print("[INFO] Checking out socialNetwork and wrk2 directories...")
    subprocess.run(["git", "checkout", "-f", "master"], cwd=str(dsb_dir), check=True)

    # 6. Init submodules
    print("[INFO] Initializing submodules...")
    subprocess.run(
        ["git", "submodule", "update", "--init", "--recursive"],
        cwd=str(dsb_dir),
        check=False,
    )
    print("[INFO] Clone and checkout complete.")


def copy_override_file(project_root: Path, social_network_dir: Path) -> None:
    """
    Copy our docker-compose.override.yml into the socialNetwork directory.
    Docker Compose automatically merges override files when they sit next
    to the main docker-compose.yml.
    """
    src = project_root / "infra" / OVERRIDE_FILE
    dst = social_network_dir / OVERRIDE_FILE

    print(f"[INFO] Copying override file: {src} -> {dst}")
    shutil.copy2(str(src), str(dst))
    print("[INFO] Override file in place.")


from infra.docker_utils import get_compose_cmd, get_docker_cmd, find_docker_executable


def docker_compose_up(social_network_dir: Path) -> None:
    """
    Run docker compose up -d in the socialNetwork directory.
    This starts all ~28 containers: microservices, databases, caches, Jaeger.
    """
    print("[INFO] Starting Docker Compose stack...")
    print("[INFO] This may take several minutes on first run (pulling images).")

    compose_cmd = get_compose_cmd()
    try:
        subprocess.run(
            compose_cmd + ["up", "-d"],
            cwd=str(social_network_dir),
            check=True,
        )
        print("[INFO] docker compose up completed.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"\n[ERROR] Failed to run docker compose: {e}")
        print("[ERROR] Please make sure Docker Desktop is installed and running.")
        sys.exit(1)


def wait_for_containers(social_network_dir: Path, timeout: int = 120) -> bool:
    """
    Wait until all containers report 'running' status.
    Returns True if all containers are up within the timeout, False otherwise.
    """
    print(f"[INFO] Waiting up to {timeout}s for all containers to start...")
    start = time.time()
    compose_cmd = get_compose_cmd()

    while time.time() - start < timeout:
        # Get the status of all containers in the compose project
        result = subprocess.run(
            compose_cmd + ["ps", "--format", "json"],
            cwd=str(social_network_dir),
            capture_output=True,
            text=True,
        )

        # Fallback: if --format json isn't supported, use plain output
        if result.returncode != 0:
            result = subprocess.run(
                compose_cmd + ["ps"],
                cwd=str(social_network_dir),
                capture_output=True,
                text=True,
            )
            # Check for any containers that are not "Up"
            lines = result.stdout.strip().split("\n")
            # Skip the header lines
            container_lines = [l for l in lines[2:] if l.strip()]
            all_up = all("Up" in line for line in container_lines)
        else:
            # JSON format: each line is a JSON object with a "State" field
            import json
            all_up = True
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    container = json.loads(line)
                    if container.get("State") != "running":
                        all_up = False
                        break
                except json.JSONDecodeError:
                    all_up = False
                    break

        if all_up and container_lines if 'container_lines' in dir() else all_up:
            elapsed = int(time.time() - start)
            print(f"[INFO] All containers are running ({elapsed}s elapsed).")
            return True

        time.sleep(5)

    print("[ERROR] Timeout waiting for containers to start.")
    print("[ERROR] Run 'docker-compose ps' in the socialNetwork directory to debug.")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Set up DeathStarBench Social Network environment"
    )
    parser.add_argument(
        "--dsb-dir",
        type=str,
        default=None,
        help="Path to clone/find DeathStarBench (default: ../DeathStarBench)",
    )
    parser.add_argument(
        "--skip-clone",
        action="store_true",
        help="Skip cloning; assume DSB repo already exists at --dsb-dir",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Seconds to wait for containers to start (default: 120)",
    )
    args = parser.parse_args()

    project_root = get_project_root()

    # Resolve DSB directory
    if args.dsb_dir:
        dsb_dir = Path(args.dsb_dir).resolve()
    else:
        dsb_dir = (project_root / DEFAULT_DSB_RELATIVE_PATH).resolve()

    social_network_dir = dsb_dir / SOCIAL_NETWORK_DIR

    # Step 1: Clone (or skip)
    if not args.skip_clone:
        clone_deathstarbench(dsb_dir)
    else:
        if not dsb_dir.exists():
            print(f"[ERROR] --skip-clone specified but {dsb_dir} does not exist.")
            sys.exit(1)
        print(f"[INFO] Skipping clone; using existing DSB at {dsb_dir}")

    # Verify the socialNetwork directory exists
    if not social_network_dir.exists():
        print(f"[ERROR] Expected {social_network_dir} but it doesn't exist.")
        print("[ERROR] Is the DSB repo cloned correctly?")
        sys.exit(1)

    # Step 2: Copy override file
    copy_override_file(project_root, social_network_dir)

    # Step 3: Bring up the stack
    docker_compose_up(social_network_dir)

    # Step 4: Wait for all containers
    if not wait_for_containers(social_network_dir, timeout=args.timeout):
        print("[WARNING] Not all containers started. Check Docker logs.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Environment setup complete!")
    print("  Jaeger UI:     http://localhost:16686")
    print("  Social Network: http://localhost:8080")
    print("  Media Frontend: http://localhost:8081")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. python infra/init_social_graph.py")
    print("  2. python infra/health_check.py")
    print("  3. python infra/generate_baseline_load.py")


if __name__ == "__main__":
    main()
