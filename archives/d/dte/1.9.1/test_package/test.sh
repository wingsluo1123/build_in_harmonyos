#!/data/service/hnp/bin/bash
# test_package/test.sh — dte smoke tests + termios raw-mode pty probe
set -euo pipefail

echo "[test] dte -V"
dte -V

echo "[test] dte -h"
dte -h > /dev/null

echo "[test] dte -B (list built-in configs)"
dte -B > /dev/null

echo "[test] dte -b rc (dump embedded rc config)"
dte -b rc > /dev/null

echo "[test] termios raw-mode probe (pty, TIOCGWINSZ/TIOCSWINSZ)"
if command -v python3 > /dev/null 2>&1; then
    python3 pty_probe.py
else
    echo "[test] SKIP: python3 not available on this worker"
fi

echo "[test] all smoke tests passed"
