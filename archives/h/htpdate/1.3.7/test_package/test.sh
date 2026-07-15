#!/system/bin/sh
set -euo pipefail 2>/dev/null || set -eu
# htpdate test: verify binary is installed and reports its version
htpdate -v
