"""
record_testbed.py -- record the host facts the repository did not already hold.

Read-only. Queries the Windows host (CIM), the Docker Desktop install record (registry,
per-user uninstall key) and the Docker Compose client, and writes the answers, with the date
of the query, to data/environment/testbed.txt. Values recorded elsewhere before the campaign
(Docker VM memory, container counts, host RAM: _audit/MEMORY_CEILING.md) are not re-queried.

These are measured on the day this script runs, not on the campaign days (2026-09-25/26).
The manuscript labels them "measured on <date>". No absolute user path is written.

Run (Windows): python tools/record_testbed.py
"""
from __future__ import annotations

import datetime
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "environment" / "testbed.txt"

QUERIES = [
    ("host_os", "(Get-CimInstance Win32_OperatingSystem).Caption"),
    ("host_os_version", "(Get-CimInstance Win32_OperatingSystem).Version"),
    ("cpu_model", "(Get-CimInstance Win32_Processor).Name"),
    ("cpu_cores", "(Get-CimInstance Win32_Processor).NumberOfCores"),
    ("cpu_logical_processors", "(Get-CimInstance Win32_Processor).NumberOfLogicalProcessors"),
    ("docker_desktop_version",
     "(Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*' "
     "-ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like 'Docker Desktop*' })"
     ".DisplayVersion"),
    ("docker_compose_version", "docker compose version"),
]


def run(cmd: str) -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def main() -> int:
    today = datetime.date.today().isoformat()
    lines = ["# Host and Docker facts, queried read-only by tools/record_testbed.py.",
             "# measured_on is the query date, not the campaign date (2026-09-25/26).",
             "measured_on = %s" % today]
    for key, cmd in QUERIES:
        val = run(cmd)
        if key == "docker_compose_version":
            m = re.search(r"v?(\d+\.\d+\.\d+)", val)
            val = m.group(1) if m else ""
        if re.search(r"[A-Za-z]:\\Users\\|/Users/", val):
            raise SystemExit("refusing to record a user path for %s" % key)
        lines.append("%s = %s" % (key, val if val else "NOT FOUND"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(OUT.read_text(encoding="utf-8"))
    extract_vm_record()
    return 0


VM_SRC = ROOT / "_audit" / "MEMORY_CEILING.md"
VM_OUT = ROOT / "data" / "environment" / "docker_vm.txt"
VM_LINES = [r"^\*\*Date:\*\*", r"WSL2 backend", r"^Host = ", r"^\| SN graph reconstruction",
            r"^\| HR graph reconstruction"]


def extract_vm_record():
    """Copy, verbatim, the lines of the pre-campaign Docker VM record the paper cites.
    _audit/MEMORY_CEILING.md is not in the public copy; this extract is."""
    if not VM_SRC.is_file():
        print("%s not present; docker_vm.txt left as it is" % VM_SRC.name)
        return
    src = VM_SRC.read_text(encoding="utf-8").splitlines()
    keep = []
    for pat in VM_LINES:
        hits = [l for l in src if re.search(pat, l)]
        if len(hits) != 1:
            raise SystemExit("expected one line matching %r in %s" % (pat, VM_SRC.name))
        keep.append(hits[0])
    if any(re.search(r"[A-Za-z]:\\|/Users/|AppData", l) for l in keep):
        raise SystemExit("refusing to copy a path")
    VM_OUT.write_text("# Lines copied verbatim from _audit/MEMORY_CEILING.md by "
                      "tools/record_testbed.py.\n" + "\n".join(keep) + "\n",
                      encoding="utf-8", newline="\n")
    print(VM_OUT.read_text(encoding="utf-8").encode("ascii", "replace").decode())


if __name__ == "__main__":
    raise SystemExit(main())
