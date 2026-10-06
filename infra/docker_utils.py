"""
docker_utils.py — Helper to locate Docker binary and execute Docker commands
=============================================================================
Provides cross-platform resolution for Docker and Docker Compose executables,
especially on Windows where Docker Desktop bin directories might not be in
the active shell process's PATH yet.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def find_docker_executable() -> str:
    """Find the docker executable in PATH or standard installation locations."""
    # 1. Standard PATH lookup
    docker_in_path = shutil.which("docker")
    if docker_in_path:
        return docker_in_path

    # 2. Known Windows Docker Desktop installation locations
    candidate_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop" / "resources" / "bin" / "docker.exe",
        Path("C:/Program Files/Docker/Docker/resources/bin/docker.exe"),
        Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Local" / "Programs" / "DockerDesktop" / "resources" / "bin" / "docker.exe",
    ]

    for p in candidate_paths:
        if p.exists():
            # Inject its parent dir into PATH for child processes
            bin_dir = str(p.parent)
            if bin_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            return str(p)

    return "docker"


def get_docker_cmd() -> list[str]:
    """Return the base command for calling docker."""
    return [find_docker_executable()]


def get_compose_cmd() -> list[str]:
    """Return the compose command ('docker compose' or 'docker-compose')."""
    docker_exe = find_docker_executable()

    # Try 'docker compose'
    try:
        res = subprocess.run([docker_exe, "compose", "version"], capture_output=True, text=True)
        if res.returncode == 0:
            return [docker_exe, "compose"]
    except Exception:
        pass

    # Try standalone 'docker-compose'
    dc = shutil.which("docker-compose")
    if dc:
        return [dc]

    return [docker_exe, "compose"]
