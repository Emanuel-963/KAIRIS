#!/usr/bin/env bash
# Run the retrospective release validation inside a Linux cgroup v2 limit.
set -euo pipefail

python="$1"
output="$2"
requested_gib="$3"
cgroup_path="$(sed -n 's/^0:://p' /proc/self/cgroup)"
cgroup="/sys/fs/cgroup${cgroup_path}"
limit="$(cat "$cgroup/memory.max")"
swap="$(cat "$cgroup/memory.swap.max")"
[[ "$limit" == "$((requested_gib * 1024 * 1024 * 1024))" && "$swap" == "0" ]]

status=0
"$python" scripts/run_release_validation.py --output "$output" || status=$?
mkdir -p "$output/evidence"
"$python" - "$output/evidence/memory_evidence.json" "$cgroup" "$status" <<'PY'
import sys
import json
from pathlib import Path

from core.artifact_io import atomic_write_text

output, cgroup, status = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
events = dict(
    line.split() for line in (cgroup / "memory.events").read_text().splitlines()
)
payload = {
    "environment": "Linux cgroup v2",
    "memory_limit_bytes": int((cgroup / "memory.max").read_text()),
    "swap_limit_bytes": int((cgroup / "memory.swap.max").read_text()),
    "memory_peak_bytes": int((cgroup / "memory.peak").read_text()),
    "memory_events": {name: int(value) for name, value in events.items()},
    "validation_exit_code": status,
}
atomic_write_text(output, json.dumps(payload, indent=2) + "\n")
print(json.dumps(payload, indent=2))
if payload["memory_events"]["oom"] or payload["memory_events"]["oom_kill"]:
    sys.exit(1)
PY
exit "$status"
