#!/bin/sh
# Consumer smoke tests for the packaged vile executable.

set -eu

bindir=${1:-}
vile="$bindir/vile"

if [ ! -x "$vile" ]; then
    echo "FAIL: packaged vile executable is missing or not executable: $vile" >&2
    exit 1
fi

version_out=$("$vile" -V)
case "$version_out" in
    *"vile version 9.8za"*)
        echo "ok: F1 vile_version (rc=0, output contains vile version 9.8za)"
        ;;
    *)
        echo "FAIL: F1 vile_version (unexpected output: $version_out)" >&2
        exit 1
        ;;
esac

usage_out=$("$vile" -x 2>&1)
case "$usage_out" in
    *"usage: vile"*)
        echo "ok: F2 vile_usage (rc=0, output contains usage: vile)"
        ;;
    *)
        echo "FAIL: F2 vile_usage (unexpected output: $usage_out)" >&2
        exit 1
        ;;
esac

echo "VILE_TEST_PACKAGE_RESULT=pass"
