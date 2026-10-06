#!/usr/bin/env python3
"""
setup_hotel_env.py — Environment Setup for DeathStarBench Hotel Reservation
============================================================================
Extends the existing DeathStarBench sparse-checkout to include hotelReservation,
copies our hotel-compose.override.yml into hotelReservation/, and brings the
Hotel stack up with docker-compose.

The Hotel Reservation stack listens on:
  - Port 5000:  HTTP frontend (hotel search, reservation, user APIs)
  - Port 16687: Jaeger UI (to avoid collision with Social Network on 16686)

This script is designed to run AFTER setup_env.py has already cloned the DSB
repo. It adds hotelReservation to the existing sparse-checkout.

Usage:
    python infra/setup_hotel_env.py [--dsb-dir PATH] [--skip-clone]

Options:
    --dsb-dir PATH   Path to the DeathStarBench repo (default: ../DeathStarBench)
    --skip-clone     Skip git sparse-checkout update (repo already has hotelReservation/)
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HOTEL_DIR = "hotelReservation"
OVERRIDE_FILE = "hotel-compose.override.yml"
DEFAULT_DSB_RELATIVE_PATH = "../DeathStarBench"


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def extend_sparse_checkout(dsb_dir: Path) -> None:
    """Add hotelReservation to the existing DSB sparse-checkout."""
    hotel_dir = dsb_dir / HOTEL_DIR
    if hotel_dir.exists():
        print(f"[INFO] hotelReservation already exists at {hotel_dir}")
        return

    print(f"[INFO] Adding hotelReservation to sparse-checkout at {dsb_dir}...")

    try:
        # Extend sparse-checkout to include hotelReservation
        subprocess.run(
            ["git", "sparse-checkout", "add", "hotelReservation"],
            cwd=str(dsb_dir), check=True,
        )
        # Force checkout of the new path
        subprocess.run(
            ["git", "checkout", "-f", "master"],
            cwd=str(dsb_dir), check=True,
        )
        print("[INFO] hotelReservation checked out successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Git sparse-checkout failed: {e}")
        print("[INFO] Trying manual git checkout as fallback...")
        try:
            subprocess.run(
                ["git", "checkout", "master", "--", "hotelReservation"],
                cwd=str(dsb_dir), check=True,
            )
        except subprocess.CalledProcessError as e2:
            print(f"[ERROR] Fallback also failed: {e2}")
            print("[HINT] Manually run: cd <dsb-dir> && git sparse-checkout add hotelReservation")
            sys.exit(1)


def copy_override_file(project_root: Path, hotel_dir: Path) -> None:
    """Copy our hotel-compose.override.yml into the hotelReservation directory."""
    src = project_root / "infra" / OVERRIDE_FILE
    dst = hotel_dir / "docker-compose.override.yml"

    if not src.exists():
        print(f"[ERROR] Override file not found: {src}")
        sys.exit(1)

    shutil.copy2(src, dst)
    print(f"[INFO] Copied {src.name} -> {dst}")


def bring_up_stack(hotel_dir: Path) -> None:
    """Start the Hotel Reservation Docker Compose stack."""
    from infra.docker_utils import get_compose_cmd
    compose_cmd = get_compose_cmd()

    print(f"[INFO] Starting Hotel Reservation stack from {hotel_dir}...")
    try:
        subprocess.run(
            compose_cmd + ["up", "-d", "--remove-orphans"],
            cwd=str(hotel_dir),
            check=True,
        )
        print("[INFO] Docker Compose up issued. Waiting for containers to start...")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] docker compose up failed: {e}")
        sys.exit(1)


def wait_for_stack(timeout: int = 120) -> bool:
    """Poll the Hotel frontend until it responds or timeout expires."""
    import requests
    url = "http://localhost:5000"
    print(f"[INFO] Waiting for Hotel frontend at {url} (timeout={timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code < 500:
                print(f"[INFO] Hotel frontend is up! (status={r.status_code})")
                return True
        except requests.RequestException:
            pass
        time.sleep(5)
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] Still waiting...")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Deploy DeathStarBench Hotel Reservation for experiments"
    )
    parser.add_argument(
        "--dsb-dir", type=str, default=None,
        help="Path to DeathStarBench repo (default: ../DeathStarBench relative to project root)",
    )
    parser.add_argument(
        "--skip-clone", action="store_true",
        help="Skip git sparse-checkout update (use if hotelReservation/ already exists)",
    )
    args = parser.parse_args()

    project_root = get_project_root()
    dsb_dir = Path(args.dsb_dir) if args.dsb_dir else (
        project_root / DEFAULT_DSB_RELATIVE_PATH
    ).resolve()
    hotel_dir = dsb_dir / HOTEL_DIR

    print("=" * 60)
    print("  Hotel Reservation Environment Setup")
    print("=" * 60)
    print(f"  DSB dir:   {dsb_dir}")
    print(f"  Hotel dir: {hotel_dir}")
    print(f"  Ports:     HTTP=5000, Jaeger=16687")
    print("=" * 60)

    if not dsb_dir.exists():
        print(f"[ERROR] DeathStarBench directory not found: {dsb_dir}")
        print("[HINT] Run `python infra/setup_env.py` first to clone DSB.")
        sys.exit(1)

    # Step 1: Extend sparse-checkout
    if not args.skip_clone:
        extend_sparse_checkout(dsb_dir)
    else:
        print("[INFO] Skipping sparse-checkout update (--skip-clone).")

    if not hotel_dir.exists():
        print(f"[ERROR] hotelReservation directory still not found: {hotel_dir}")
        sys.exit(1)

    # Step 2: Copy override file
    copy_override_file(project_root, hotel_dir)

    # Step 3: Bring up stack
    bring_up_stack(hotel_dir)

    # Step 4: Wait for healthy
    ok = wait_for_stack(timeout=120)
    if ok:
        print("\n[OK] Hotel Reservation stack is ready.")
        print("  Frontend:  http://localhost:5000")
        print("  Jaeger UI: http://localhost:16687")
        print("\n  Next step: python infra/health_check_hotel.py")
    else:
        print("\n[WARNING] Hotel frontend did not respond within timeout.")
        print("[HINT] Check: docker ps | grep hotel")
        print("[HINT] Check logs: docker compose -f hotelReservation/docker-compose.yml logs frontend")


if __name__ == "__main__":
    main()
