"""
hotel_expected_services.py — Expected Services for Hotel Reservation Benchmark
==============================================================================
Defines the Hotel Reservation application's expected service names (as they
appear in Jaeger traces) and the storage/infrastructure services to exclude
from the Service Dependency Graph and fault injection experiments.

Hotel Reservation Architecture (from DSB paper Fig. 6):
  frontend
      ├── search → geo + rate + profile
      ├── recommendation
      ├── reservation → user
      └── user (direct)

Storage backends (MongoDB, Memcached) are NOT instrumented with OpenTracing
and do not appear in Jaeger traces.
"""

# Services that SHOULD appear in Jaeger traces (Go gRPC microservices)
HOTEL_EXPECTED_SERVICES = {
    "frontend",
    "profile",
    "search",
    "geo",
    "rate",
    "reservation",
    "user",
    "recommendation",
}

# Storage backends and infrastructure NOT included in the SDG
HOTEL_EXCLUDED_SERVICES = {
    # Jaeger (monitoring infrastructure)
    "jaeger",
    # Memcached caches
    "memcached-profile",
    "memcached-rate",
    "memcached-reserve",
    # MongoDB backends
    "mongodb-geo",
    "mongodb-profile",
    "mongodb-rate",
    "mongodb-reservation",
    "mongodb-user",
    "mongodb-recommendation",
    # Consul (service discovery, not traced)
    "consul",
    # TLS proxy (if present)
    "tls",
}

# Human-readable architecture description (used in RESULTS.md generation)
HOTEL_ARCHITECTURE_DESCRIPTION = """
The Hotel Reservation application (Gan et al., 2019) is a Go/gRPC microservice
benchmark representing an online hotel booking platform. It comprises 8 application
microservices deployed via Docker Compose:

  - frontend:       HTTP gateway, routes requests to backend RPC services
  - search:         Finds hotels by geographic proximity (calls geo + rate + profile)
  - geo:            Geolocation service (nearest hotels by lat/lon)
  - rate:           Returns room rates for given hotels and dates
  - profile:        Returns hotel profiles (descriptions, photos, amenities)
  - recommendation: Returns hotel recommendations (by distance, rate, or price)
  - reservation:    Books hotel rooms (calls user for authentication)
  - user:           User authentication and profile management

Storage backends (MongoDB × 6, Memcached × 3) are excluded from the SDG as
they are not instrumented with OpenTracing in the upstream DSB implementation.
"""

# Service dependency graph structure (expected edges for sanity check)
# Format: (caller, callee)
HOTEL_EXPECTED_EDGES = [
    ("frontend", "search"),
    ("frontend", "recommendation"),
    ("frontend", "user"),
    ("frontend", "reservation"),
    ("search", "geo"),
    ("search", "rate"),
    ("search", "profile"),
    ("reservation", "user"),
]
