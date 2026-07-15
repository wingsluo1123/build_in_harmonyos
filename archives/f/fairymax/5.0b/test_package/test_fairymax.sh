#!/bin/sh
# R34: Test must actually exercise the tested package's binary
# fairymax is a chess engine using XBoard protocol — test by sending
# XBoard commands and checking the engine greeting response.
set -euo pipefail

PREFIX="${1:-}"

fail=0

# Test fairymax
output=$(printf "xboard\nprotover 2\nquit\n" | timeout 5 "${PREFIX}fairymax" 2>&1) || true
case "$output" in
    *Fairy-Max*5.0b*)
        echo "PASS: fairymax binary responds correctly"
        ;;
    *)
        echo "FAIL: unexpected output from fairymax"
        echo "  output: $output"
        fail=1
        ;;
esac

# Test shamax
output=$(printf "xboard\nprotover 2\nquit\n" | timeout 5 "${PREFIX}shamax" 2>&1) || true
case "$output" in
    *ShaMax*5.0b*)
        echo "PASS: shamax binary responds correctly"
        ;;
    *)
        echo "FAIL: unexpected output from shamax"
        echo "  output: $output"
        fail=1
        ;;
esac

# Test maxqi
# Test maxqi — non-zero exit from timeout/engine is expected; output is validated by case below
output=$(printf "xboard\nprotover 2\nquit\n" | timeout 5 "${PREFIX}maxqi" 2>&1) || true
case "$output" in
    *MaxQi*)
        echo "PASS: maxqi binary responds correctly"
        ;;
    *)
        echo "FAIL: unexpected output from maxqi"
        echo "  output: $output"
        fail=1
        ;;
esac

exit $fail

l
