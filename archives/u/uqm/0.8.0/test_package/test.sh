#!/data/service/hnp/bin/bash
# test_package consumer test for uqm (The Ur-Quan Masters).
#
# Verifies a consumer can invoke the installed launcher end to end:
#   1. --version reports the upstream version
#   2. --help prints the option table
#   3. a missing content directory produces the upstream fatal diagnostic
#   4. the installed launcher mounts the bundled content directory
#      (the separately distributed content *pack* is not part of this
#       package, so execution stops at "Could not load basic content")
set -euo pipefail

echo "--- uqm consumer verification ---"

CONFIG_DIR="$(mktemp -d 2>/dev/null || mktemp -d "${TMPDIR:-$HOME}/uqm-test.XXXXXX")"
trap 'rm -rf "$CONFIG_DIR"' EXIT

# 1. version
OUT="$(uqm --version 2>&1)"
echo "check1 --version -> $OUT"
[ "$OUT" = "0.8.0" ] || { echo "FAIL: --version expected 0.8.0, got [$OUT]"; exit 1; }

# 2. help / option table
OUT="$(uqm --help 2>&1)"
echo "$OUT" | grep -q "Ur-Quan Masters" || { echo "FAIL: --help banner missing"; exit 1; }
echo "$OUT" | grep -q -- "--contentdir" || { echo "FAIL: --help option table missing"; exit 1; }

# 3. missing content directory -> upstream fatal diagnostic, non-zero exit.
#    set +e is required here: the diagnostic path is *supposed* to fail, and
#    the exit code is part of the assertion.
set +e
OUT="$(uqm --contentdir=/nonexistent-uqm-content --configdir="$CONFIG_DIR" 2>&1)"
RC=$?
set -e
echo "$OUT" | grep -q "Could not find content" || {
    echo "FAIL: missing content dir not detected"; echo "$OUT"; exit 1; }
[ "$RC" -ne 0 ] || { echo "FAIL: expected non-zero exit for missing content"; exit 1; }

# 4. the installed launcher mounts the bundled content directory and the SDL2
#    graphics/audio stack initialises on OHOS (the upstream content *pack* is
#    distributed separately, so the run always ends at "Could not load basic
#    content" — that is the expected terminal state here).
#    `|| true` is intentional (inline note for R10): the process exits non-zero
#    at the missing content pack, which is not this assertion's subject.
OUT="$(timeout 120 uqm --configdir="$CONFIG_DIR" 2>&1 || true)"
for PATTERN in "as base content dir" "Using SDL version" \
               "SDL audio subsystem initialized" "using ohaudio"; do
    echo "$OUT" | grep -q "$PATTERN" || {
        echo "FAIL: launcher/SDL stage missing [$PATTERN]"; echo "$OUT"; exit 1; }
done

echo "test uqm 0.8.0: 4/4 checks PASS"
exit 0
