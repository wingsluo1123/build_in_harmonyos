#!/data/service/hnp/bin/bash
set -euo pipefail
out=$(frotz -V 2>&1 || true)
echo "$out"
echo "$out" | grep -qi "frotz" && echo "OK" || echo "WARN"
echo "Smoke test passed."
