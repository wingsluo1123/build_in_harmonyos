"""Reproduce the controlling-terminal failure and verify a mode-aware fix."""

import subprocess


BINARY = "/tmp/tty-mode-fixture"


def run(*command: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, timeout=10)
    print("COMMAND", " ".join(command), "EXIT", result.returncode)
    print((result.stdout + result.stderr).strip())
    return result


legacy = run("setsid", BINARY, "--legacy")
assert legacy.returncode == 2
assert "control terminal required" in legacy.stderr

batch = run("setsid", BINARY, "--batch")
assert batch.returncode == 0
assert batch.stdout.strip() == "batch payload"

headless_interactive = run("setsid", BINARY, "--interactive")
assert headless_interactive.returncode == 2

pty_interactive = run("script", "-qec", f"{BINARY} --interactive", "/dev/null")
assert pty_interactive.returncode == 0
assert "interactive ready" in pty_interactive.stdout
print("PASS mode-aware /dev/tty handling across headless and PTY execution")
