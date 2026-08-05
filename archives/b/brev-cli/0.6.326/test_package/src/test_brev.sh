#!/usr/bin/zsh
# test_package/src/test_brev.sh
#
# L1/L2 smoke test for the brev-cli application package (shell wrapper).
#
# The test verifies the installed brev binary responds to --version
# with the expected version string.
#
# Usage:
#   BREV_BIN=/path/to/brev zsh test_brev.sh
#   zsh test_brev.sh          # looks up brev on PATH
#
# Exit codes:
#   0 — brev --version printed a string containing the expected version
#   1 — brev not found, version mismatch, or placeholder binary detected
#   2 — brev --version exited non-zero
set -euo pipefail

BREV_BIN="${BREV_BIN:-}"
if [ -z "$BREV_BIN" ]; then
    if command -v brev >/dev/null 2>&1; then
        BREV_BIN="$(command -v brev)"
    else
        echo "FAIL: brev binary not found (set BREV_BIN or add brev to PATH)" >&2
        exit 1
    fi
fi

EXPECTED_VERSION="0.6.326"
out="$("$BREV_BIN" --version 2>&1)" || rc=$?
rc="${rc:-0}"

if [ "$rc" -ne 0 ]; then
    echo "FAIL: brev --version exited with $rc" >&2
    echo "output: $out" >&2
    exit 2
fi

case "$out" in
    *"[PLACEHOLDER]"*)
        # R9: conanfile.py builds a C placeholder when the Go toolchain is
        # unavailable; a placeholder must never pass as a genuine build.
        echo "FAIL: brev --version output contains placeholder marker (R9: no fake pass)" >&2
        echo "output: $out" >&2
        exit 1
        ;;
esac

case "$out" in
    *"$EXPECTED_VERSION"*)
        echo "PASS: brev --version output contains $EXPECTED_VERSION"
        exit 0
        ;;
    *)
        echo "FAIL: brev --version output does not contain $EXPECTED_VERSION" >&2
        echo "output: $out" >&2
        exit 1
        ;;
esac
