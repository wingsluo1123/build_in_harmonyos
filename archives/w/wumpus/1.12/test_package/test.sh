#!/data/service/hnp/bin/bash
set -euo pipefail
export LC_ALL=C

if [ -n "${WUMPUS_TEST_EVIDENCE_DIR:-}" ]; then
    evidence_root=$WUMPUS_TEST_EVIDENCE_DIR
    mkdir -p "$evidence_root"
    tmp=$(mktemp -d "$evidence_root/run.XXXXXX")
    printf 'EVIDENCE_RUN_DIR=%s\n' "$tmp"
else
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
fi

wumpus=$(command -v wumpus)
superhack=$(command -v superhack)
python3 - "$tmp" "$wumpus" "$superhack" <<'PY'
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

out = Path(sys.argv[1])
programs = {
    "wumpus": {
        "binary": sys.argv[2],
        "probe": b"n\n",
        "banner": b"HUNT THE WUMPUS",
        "status": re.compile(rb"^YOU ARE IN ROOM\s+(\d+)\s*$", re.I | re.M),
        "exits": re.compile(rb"^TUNNELS LEAD TO\s+([0-9 ]+)\s*$", re.I | re.M),
        "action": lambda room: f"n\nM\n{room}\n".encode("ascii"),
        "invalid": b"NOT POSSIBLE",
    },
    "superhack": {
        "binary": sys.argv[3],
        "probe": b"",
        "banner": b"Hunt the Superhack",
        "status": re.compile(rb"^You are in room\s+(\d+)\.", re.I | re.M),
        "exits": re.compile(rb"^You are in room\s+\d+\.\s+Exits lead to\s+([0-9, ]+)\.", re.I | re.M),
        "action": lambda room: f"m {room}\n".encode("ascii"),
        "invalid": b"You can't get there from here!",
    },
}

def write_run(name: str, label: str, data: bytes, rc, stdout: bytes, stderr: bytes, error=None):
    (out / f"{name}.{label}.stdin").write_bytes(data)
    (out / f"{name}.{label}.stdout").write_bytes(stdout)
    (out / f"{name}.{label}.stderr").write_bytes(stderr)
    (out / f"{name}.{label}.rc").write_text("" if rc is None else f"{rc}\n", encoding="ascii")
    if error:
        (out / f"{name}.{label}.error").write_text(error + "\n", encoding="utf-8")
    return {"label": label, "return_code": rc, "stdout": stdout, "stderr": stderr, "error": error}

def capture(name: str, label: str, spec, data: bytes):
    try:
        proc = subprocess.run(
            [spec["binary"], "-s", "123"], input=data, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=20, check=False,
        )
        return write_run(name, label, data, proc.returncode, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        if isinstance(stdout, str): stdout = stdout.encode("utf-8", "replace")
        if isinstance(stderr, str): stderr = stderr.encode("utf-8", "replace")
        return write_run(name, label, data, None, stdout, stderr, "timeout after 20 seconds")
    except OSError as exc:
        return write_run(name, label, data, None, b"", str(exc).encode("utf-8", "replace"), f"{type(exc).__name__}: {exc}")

def statuses(spec, stdout: bytes):
    return [int(match.group(1)) for match in spec["status"].finditer(stdout)]

def exits(spec, stdout: bytes):
    match = spec["exits"].search(stdout)
    if not match:
        return []
    return [int(token) for token in re.findall(rb"\d+", match.group(1))]

def check(name: str, label: str, passed: bool):
    print(f"{'PASS' if passed else 'FAIL'} {name}: {label}")
    return passed

all_passed = True
assertion_count = 0
for name, spec in programs.items():
    probe = capture(name, "probe", spec, spec["probe"])
    probe_rooms = statuses(spec, probe["stdout"])
    initial = probe_rooms[-1] if probe_rooms else None
    legal_exits = exits(spec, probe["stdout"])
    valid_topology = (
        initial is not None and len(legal_exits) == 3 and len(set(legal_exits)) == 3
        and all(1 <= room <= 20 and room != initial for room in legal_exits)
    )

    attempts = []
    chosen = None
    selected = None
    if valid_topology:
        for destination in legal_exits:
            attempt = capture(name, f"try-{destination}", spec, spec["action"](destination))
            attempt_rooms = statuses(spec, attempt["stdout"])
            attempt_exits = exits(spec, attempt["stdout"])
            attempt["same_initial_topology"] = bool(
                attempt_rooms and attempt_rooms[0] == initial and attempt_exits == legal_exits
            )
            attempt["no_invalid_notice"] = spec["invalid"] not in attempt["stdout"]
            attempts.append(attempt)
            if (
                attempt["return_code"] == 1 and attempt["stderr"] == b""
                and attempt["no_invalid_notice"] and attempt["same_initial_topology"]
                and attempt_rooms and attempt_rooms[-1] == destination
            ):
                chosen, selected = destination, attempt
                break

    repeat = capture(name, f"repeat-{chosen}", spec, spec["action"](chosen)) if chosen is not None else None
    selected_rooms = statuses(spec, selected["stdout"]) if selected else []
    repeat_rooms = statuses(spec, repeat["stdout"]) if repeat else []

    checks = [
        ("probe_eof_rc_is_1", probe["return_code"] == 1),
        ("probe_stderr_empty", probe["stderr"] == b""),
        ("expected_banner_present", spec["banner"] in probe["stdout"]),
        ("initial_room_and_three_legal_exits_parsed", valid_topology),
        ("all_attempt_exit_codes_are_normal", bool(attempts) and all(a["return_code"] in (0, 1) for a in attempts)),
        ("all_attempt_stderr_empty", bool(attempts) and all(a["stderr"] == b"" for a in attempts)),
        ("all_attempts_omit_invalid_move_notice", bool(attempts) and all(a["no_invalid_notice"] for a in attempts)),
        ("all_attempts_repeat_probe_topology", bool(attempts) and all(a["same_initial_topology"] for a in attempts)),
        ("selected_destination_is_listed_neighbor", chosen in legal_exits if chosen is not None else False),
        ("post_move_state_is_selected_room", bool(selected_rooms and selected_rooms[-1] == chosen and chosen != initial)),
        ("selected_action_eof_rc_is_1", bool(selected and selected["return_code"] == 1)),
        ("selected_action_stderr_empty", bool(selected and selected["stderr"] == b"")),
        ("repeat_eof_rc_is_1", bool(repeat and repeat["return_code"] == 1)),
        ("repeat_stderr_empty", bool(repeat and repeat["stderr"] == b"")),
        ("repeat_stdout_identical", bool(selected and repeat and selected["stdout"] == repeat["stdout"])),
        ("repeat_stderr_identical", bool(selected and repeat and selected["stderr"] == repeat["stderr"])),
        ("repeat_state_starts_at_probe_and_ends_at_selected_room", bool(repeat_rooms and repeat_rooms[0] == initial and repeat_rooms[-1] == chosen)),
    ]
    for label, passed in checks:
        assertion_count += 1
        all_passed = check(name, label, passed) and all_passed
    tried = ",".join(str(a["label"].removeprefix("try-")) for a in attempts) or "none"
    print(f"INFO {name}: start_room={initial}; legal_exits={legal_exits}; tried={tried}; selected={chosen}")

print(f"SUMMARY assertions={assertion_count} expected=34 result={'PASS' if all_passed and assertion_count == 34 else 'FAIL'}")
for path in sorted(out.iterdir()):
    if path.is_file():
        print(f"SHA256 {path.name} {hashlib.sha256(path.read_bytes()).hexdigest()}")
raise SystemExit(0 if all_passed and assertion_count == 34 else 1)
PY
