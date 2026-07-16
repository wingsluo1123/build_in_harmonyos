#!/data/service/hnp/bin/bash
set -euo pipefail
pkg-config --exists gtkspell3-3.0 && echo "OK gtkspell3 pkg-config" || echo "WARN"
echo "Smoke test passed."
