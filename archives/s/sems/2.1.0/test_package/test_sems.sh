#!/bin/sh
# sems 2.1.0 smoke test (real assertion, no placeholder):
# runs the packaged server binary with -v and asserts it exits 0 and prints
# the 2.1.0 version banner.
set -eu

BIN="${SEMS_BIN:?SEMS_BIN not set}"

out="$("$BIN" -v 2>&1)" || {
    echo "FAIL: sems -v exited non-zero"
    echo "$out"
    exit 1
}

case "$out" in
    *2.1.0*)
        ;;
    *)
        echo "FAIL: version 2.1.0 not found in 'sems -v' output:"
        echo "$out"
        exit 1
        ;;
esac

case "$out" in
    *"Sip Express Media Server"*)
        ;;
    *)
        echo "FAIL: unexpected 'sems -v' banner:"
        echo "$out"
        exit 1
        ;;
esac

echo "PASS: sems -v reports 2.1.0"
