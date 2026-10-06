#!/usr/bin/env python3
"""
init_hotel_data.py — Seed Data for DeathStarBench Hotel Reservation
====================================================================
Generates seed HTTP traffic against the Hotel Reservation application to:
  1. Register users in the user service database
  2. Make hotel search queries (triggers geo + rate + profile services)
  3. Make hotel reservations (triggers reservation + user services)
  4. Fetch recommendations (triggers recommendation service)

This is needed BEFORE running fault injection because Jaeger must have
traces of all 8 services in its index (needed for SDG construction).

Hotel Reservation API Endpoints (Go/gRPC behind HTTP gateway on port 5000):
  GET  /hotels?inDate=2015-04-09&outDate=2015-04-10&lat=37.7749&lon=-122.4194
  GET  /recommendations?require=dis&lat=38.0235&lon=-122.095
  GET  /user?username=Cornell_1
  POST /reservation  (JSON body with customerName, hotelId, inDate, outDate, roomNumber)

Usage:
    python infra/init_hotel_data.py [--base-url URL] [--requests N]
"""

import argparse
import random
import sys
import time
from pathlib import Path

import requests

DEFAULT_BASE_URL = "http://localhost:5000"

# DSB Hotel Reservation comes pre-seeded with Cornell_N users (1-500)
# and hotel IDs 1-80 in MongoDB. We only need to make queries to warm up traces.
SAMPLE_USERS = [f"Cornell_{i}" for i in range(1, 51)]
SAMPLE_HOTELS = list(range(1, 21))

# Hotel coordinates (subset of pre-seeded DSB hotel locations)
HOTEL_LOCATIONS = [
    (37.7867, -122.4112),  # San Francisco
    (37.7794, -122.4062),
    (38.0235, -122.095),   # Other Bay Area
    (37.6879, -122.4702),
    (37.3382, -121.8863),  # San Jose
]

DATE_PAIRS = [
    ("2015-04-09", "2015-04-10"),
    ("2015-04-10", "2015-04-11"),
    ("2015-04-11", "2015-04-12"),
    ("2015-04-12", "2015-04-13"),
]


def search_hotels(base_url: str, lat: float, lon: float,
                  in_date: str, out_date: str, session: requests.Session) -> bool:
    """GET /hotels — triggers frontend → search → geo + rate + profile."""
    try:
        r = session.get(
            f"{base_url}/hotels",
            params={
                "inDate": in_date,
                "outDate": out_date,
                "lat": str(lat),
                "lon": str(lon),
            },
            timeout=10,
        )
        return r.status_code < 500
    except requests.RequestException:
        return False


def get_recommendations(base_url: str, lat: float, lon: float,
                         session: requests.Session) -> bool:
    """GET /recommendations — triggers frontend → recommendation."""
    try:
        r = session.get(
            f"{base_url}/recommendations",
            params={
                "require": random.choice(["dis", "rate", "price"]),
                "lat": str(lat),
                "lon": str(lon),
            },
            timeout=10,
        )
        return r.status_code < 500
    except requests.RequestException:
        return False


def get_user(base_url: str, username: str, session: requests.Session) -> bool:
    """GET /user — triggers frontend → user."""
    try:
        r = session.get(
            f"{base_url}/user",
            params={"username": username},
            timeout=10,
        )
        return r.status_code < 500
    except requests.RequestException:
        return False


def make_reservation(base_url: str, username: str, hotel_id: int,
                      in_date: str, out_date: str, session: requests.Session) -> bool:
    """POST /reservation — triggers frontend → reservation → user."""
    try:
        r = session.post(
            f"{base_url}/reservation",
            json={
                "customerName": username,
                "hotelId": str(hotel_id),
                "inDate": in_date,
                "outDate": out_date,
                "roomNumber": random.randint(1, 100),
            },
            timeout=10,
        )
        return r.status_code < 500
    except requests.RequestException:
        return False


def wait_for_hotel(base_url: str, timeout: int = 60) -> bool:
    """Wait for Hotel frontend to become reachable."""
    print(f"[INFO] Waiting for Hotel frontend at {base_url}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(base_url, timeout=5)
            if r.status_code < 500:
                print(f"[INFO] Hotel frontend is up.")
                return True
        except requests.RequestException:
            pass
        time.sleep(3)
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Seed data for DeathStarBench Hotel Reservation"
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL,
        help=f"Hotel frontend URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--requests", type=int, default=200,
        help="Total number of seed requests to make (default: 200)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Hotel Reservation Data Seeding")
    print("=" * 60)
    print(f"  Target:   {args.base_url}")
    print(f"  Requests: {args.requests}")
    print("=" * 60)

    # Check connectivity
    if not wait_for_hotel(args.base_url):
        print(f"[ERROR] Hotel frontend not reachable at {args.base_url}")
        print("[HINT] Run `python infra/setup_hotel_env.py` first.")
        sys.exit(1)

    session = requests.Session()
    session.headers["User-Agent"] = "DSB-Seeder/1.0"

    success = 0
    fail = 0
    n = args.requests

    print(f"\n[INFO] Sending {n} mixed requests to seed all service traces...")
    for i in range(n):
        lat, lon = random.choice(HOTEL_LOCATIONS)
        in_date, out_date = random.choice(DATE_PAIRS)
        user = random.choice(SAMPLE_USERS)
        hotel_id = random.choice(SAMPLE_HOTELS)

        # Weighted mix: 50% search, 20% recommend, 20% user, 10% reservation
        roll = random.random()
        if roll < 0.50:
            ok = search_hotels(args.base_url, lat, lon, in_date, out_date, session)
        elif roll < 0.70:
            ok = get_recommendations(args.base_url, lat, lon, session)
        elif roll < 0.90:
            ok = get_user(args.base_url, user, session)
        else:
            ok = make_reservation(args.base_url, user, hotel_id, in_date, out_date, session)

        if ok:
            success += 1
        else:
            fail += 1

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{n} requests ({success} ok, {fail} failed)")

        # Small delay to avoid overwhelming the stack
        time.sleep(0.05)

    print(f"\n[OK] Seeding complete: {success}/{n} requests successful.")
    if fail > n * 0.3:
        print(f"[WARNING] High failure rate ({fail}/{n}). Check Hotel stack health.")

    print("\n[INFO] Traces should now appear in Jaeger at http://localhost:16687")
    print("[INFO] Next step: python infra/health_check_hotel.py")


if __name__ == "__main__":
    main()
