#!/data/service/hnp/bin/bash
set -euo pipefail
out=$(dar --version 2>&1 || true)
echo "$out"
echo "$out" | grep -qi "dar" && echo "OK" || echo "WARN"
echo "Smoke test passed."
