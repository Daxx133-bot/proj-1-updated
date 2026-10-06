#!/usr/bin/env python3
"""
fault_config.py — Fault Type Definitions and Experiment Configuration
======================================================================
Defines the fault types (kill, latency, CPU stress), their parameters,
and the overall experiment configuration.

This module is imported by fault_runner.py. It uses dataclasses for
clean configuration management.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FaultType(Enum):
    """
    Types of faults that can be injected.

    KILL:    Stop the container entirely (SIGKILL). Simulates a crash.
    LATENCY: Inject network delay via tc netem. Simulates network degradation.
    CPU:     CPU stress via stress-ng. Simulates resource contention.
    """
    KILL = "kill"
    LATENCY = "latency"
    CPU = "cpu"


from infra.docker_utils import find_docker_executable


@dataclass
class FaultSpec:
    """
    Specification for a single fault injection.

    Attributes:
        fault_type:       Type of fault to inject.
        duration_seconds: How long the fault should last (for latency/CPU).
                          For KILL, this is ignored (container is killed and
                          restarted after measurement).
        latency_ms:       For LATENCY type: how many ms of delay to add.
        latency_jitter_ms: For LATENCY type: jitter around the delay.
        cpu_workers:      For CPU type: number of CPU stress workers.
    """
    fault_type: FaultType
    duration_seconds: int = 60
    latency_ms: int = 500
    latency_jitter_ms: int = 100
    cpu_workers: int = 4

    def pumba_command(self, container_name: str) -> list[str]:
        """
        Generate the Pumba Docker command for this fault.

        Pumba runs as a Docker container itself, mounting the Docker socket
        to manipulate other containers.

        Returns:
            List of command-line arguments for subprocess.run().
        """
        docker_exe = find_docker_executable()
        base = [
            docker_exe, "run", "--rm",
            "-v", "/var/run/docker.sock:/var/run/docker.sock",
            "ghcr.io/alexei-led/pumba",
        ]

        if self.fault_type == FaultType.KILL:
            # Kill the target container with SIGKILL
            return base + [
                "kill",
                "--signal", "SIGKILL",
                container_name,
            ]

        elif self.fault_type == FaultType.LATENCY:
            # Inject network latency via tc netem
            return base + [
                "netem",
                "--duration", f"{self.duration_seconds}s",
                "delay",
                "--time", str(self.latency_ms),
                "--jitter", str(self.latency_jitter_ms),
                container_name,
            ]

        elif self.fault_type == FaultType.CPU:
            # Use Pumba's built-in stress subcommand.
            # This avoids requiring stress-ng to be installed inside each container
            # (DSB containers do NOT ship with stress-ng by default).
            # Pumba stress runs as a sidecar container and manages CPU pressure
            # on the target container from the outside via cgroups.
            return base + [
                "stress",
                "--duration", f"{self.duration_seconds}s",
                "--pull-image",
                f"--stressors=--cpu {self.cpu_workers} --timeout {self.duration_seconds}s",
                container_name,
            ]

        else:
            raise ValueError(f"Unknown fault type: {self.fault_type}")

    def description(self) -> str:
        """Human-readable description of this fault."""
        if self.fault_type == FaultType.KILL:
            return "Container kill (SIGKILL)"
        elif self.fault_type == FaultType.LATENCY:
            return (f"Network latency injection: {self.latency_ms}ms "
                    f"(±{self.latency_jitter_ms}ms jitter) "
                    f"for {self.duration_seconds}s")
        elif self.fault_type == FaultType.CPU:
            return (f"CPU stress (Pumba built-in): {self.cpu_workers} workers "
                    f"for {self.duration_seconds}s")
        return str(self.fault_type)


@dataclass
class ExperimentConfig:
    """
    Overall experiment configuration.

    Attributes:
        services:          List of service names to fault-inject.
                           If empty, all SDG services are used.
        fault_types:       Which fault types to run (default: kill + latency).
        repetitions:       How many times to repeat each fault per service.
        warmup_seconds:    Load warm-up period before injecting faults.
        fault_duration:    How long each fault lasts (seconds).
        cooldown_seconds:  Wait time between fault runs for recovery.
        load_rate:         Requests per second during experiment.
        load_mode:         Load generator mode ("wrk2" or "locust").
        nginx_url:         URL of the Nginx gateway.
        jaeger_url:        URL of Jaeger query service.
        dsb_dir:           Path to DeathStarBench repository.
        output_dir:        Where to save measurement results.
    """
    services: list[str] = field(default_factory=list)
    fault_types: list[FaultType] = field(
        default_factory=lambda: [FaultType.KILL, FaultType.LATENCY]
    )
    repetitions: int = 3
    warmup_seconds: int = 30
    fault_duration: int = 60
    cooldown_seconds: int = 30
    load_rate: int = 50
    load_mode: str = "locust"

    # ── Recovery probing (measurement/recovery_probe.py) ───────────────────
    # max_wait is deliberately far above the old 60 s cap: at 60 s a genuine recovery
    # was indistinguishable from a timeout, and the timeout value was written to disk
    # as if it were a measurement (the 61.07 s figure). Generous here costs wall time;
    # too tight silently fabricates data.
    recovery_max_wait_s: float = 180.0
    recovery_poll_interval_s: float = 3.0
    recovery_tolerance: float = 0.10     # "within 10% of baseline"
    nginx_url: str = "http://localhost:8080"
    jaeger_url: str = "http://localhost:16686"
    dsb_dir: str = ""
    output_dir: str = ""

    def total_runs(self) -> int:
        """Total number of experiment runs."""
        return len(self.services) * len(self.fault_types) * self.repetitions

    def estimated_time_minutes(self) -> float:
        """Rough upper bound on total experiment time.

        Assumes the worst case for recovery probing (every run censored at
        recovery_max_wait_s). Typical runs recover far sooner, so real wall time will
        be well under this.
        """
        per_run = (
            self.warmup_seconds + self.fault_duration + self.cooldown_seconds + 30
            + self.recovery_max_wait_s
        )
        return (self.total_runs() * per_run) / 60.0


# ── Default fault specs ────────────────────────────────────────────────────

DEFAULT_KILL_SPEC = FaultSpec(
    fault_type=FaultType.KILL,
)

DEFAULT_LATENCY_SPEC = FaultSpec(
    fault_type=FaultType.LATENCY,
    duration_seconds=60,
    latency_ms=500,
    latency_jitter_ms=100,
)

DEFAULT_CPU_SPEC = FaultSpec(
    fault_type=FaultType.CPU,
    duration_seconds=60,
    cpu_workers=2,    # 2 workers is sufficient to saturate without risking OOM
)

# Map fault type to its default spec
DEFAULT_SPECS = {
    FaultType.KILL: DEFAULT_KILL_SPEC,
    FaultType.LATENCY: DEFAULT_LATENCY_SPEC,
    FaultType.CPU: DEFAULT_CPU_SPEC,
}

# ── Services that should NOT be fault-injected ─────────────────────────────
# Infrastructure services that would break the experiment if killed.
EXCLUDED_SERVICES = {
    "jaeger-agent",
    "jaeger-query",
    "jaeger",
    # Storage backends (not in the SDG, but listing for safety)
    "social-graph-mongodb",
    "social-graph-redis",
    "home-timeline-redis",
    "compose-post-redis",
    "post-storage-mongodb",
    "post-storage-memcached",
    "user-timeline-mongodb",
    "user-timeline-redis",
    "user-mongodb",
    "user-memcached",
    "url-shorten-mongodb",
    "url-shorten-memcached",
    "user-mention-memcached",
    "media-mongodb",
    "media-memcached",
    "media-frontend",
}
