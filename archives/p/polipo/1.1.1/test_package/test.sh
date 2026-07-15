#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for polipo executable
set -euo pipefail

echo "[step] polipo -h"
polipo -h && echo "[ok] polipo -h passed" || {
    echo "[fail] polipo -h failed"
    exit 1
}
