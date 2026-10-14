#!/bin/sh
# test_package/test.sh — functional smoke test for the packaged rtnppd binaries.
# Runs inside the conanrun env (PATH includes the installed bin/).
#
# rtnppd/tnpppage/testq are privileged-network daemons/clients: bare runs
# would daemonize or block on sockets, so the smoke test only exercises the
# deterministic startup paths (usage/getopt handling, all exit(1) before any
# network or config access — verified against rtnppd.c/tnpppage.c/testq.c)
# plus the OHOS cross-build properties of the packaged artifacts.
#
# Only bash, od, tr and grep are used. On OHOS the PATH picks up the toybox
# tools in /system/bin, and toybox grep refuses to search binary files (it
# ignores -a), so the ELF string checks render the bytes as text with
# `od -An -t c | tr -d ' \n'` and match the resulting stream.
set -u

# HMBS sandbox: /tmp may be read-only; prefer injected TMPDIR/TMP/TEMP.
WORK_TMP="${TMPDIR:-${TMP:-${TEMP:-}}}"
if [ -z "$WORK_TMP" ] || [ ! -d "$WORK_TMP" ] || [ ! -w "$WORK_TMP" ]; then
    WORK_TMP="$(pwd)/.tmp"
    mkdir -p "$WORK_TMP" 2>/dev/null || WORK_TMP="$(dirname "$0")/.tmp"
    mkdir -p "$WORK_TMP" 2>/dev/null || true
fi

RTNPPD="$(command -v rtnppd || true)"
TNPPPAGE="$(command -v tnpppage || true)"
TESTQ="$(command -v testq || true)"
if [ -z "$RTNPPD" ] || [ ! -x "$RTNPPD" ]; then
    echo "FAIL: rtnppd not found on PATH"
    exit 1
fi
if [ -z "$TNPPPAGE" ] || [ ! -x "$TNPPPAGE" ]; then
    echo "FAIL: tnpppage not found on PATH"
    exit 1
fi
if [ -z "$TESTQ" ] || [ ! -x "$TESTQ" ]; then
    echo "FAIL: testq not found on PATH"
    exit 1
fi

# Test 1 (functional): rtnppd executes and reports its usage banner.
# `-h` is not a valid option, so getopt takes the '?' path: usage() prints
# "rtnppd v1.7b ... Usage: ..." and main() exits 1 before daemonizing.
out="$("$RTNPPD" -h < /dev/null 2>&1)"
rc=$?
if [ "$rc" -ne 1 ]; then
    echo "FAIL: rtnppd -h exited $rc (want 1); output was: [$out]"
    exit 1
fi
case "$out" in
    *"rtnppd v1.7b"*|*"Usage:"*)
        echo "PASS: rtnppd executes and prints its usage banner" ;;
    *)
        echo "FAIL: rtnppd -h printed no usage banner; output was: [$out]"
        exit 1 ;;
esac

# Test 2 (functional): tnpppage executes and reports its usage banner.
# With no arguments the mandatory TNPP-address/pager-id check fails:
# usage() prints "tnpppage v1.2b ... Usage: ..." and main() exits 1.
out="$("$TNPPPAGE" < /dev/null 2>&1)"
rc=$?
if [ "$rc" -ne 1 ]; then
    echo "FAIL: tnpppage (no args) exited $rc (want 1); output was: [$out]"
    exit 1
fi
case "$out" in
    *"tnpppage"*|*"Usage:"*)
        echo "PASS: tnpppage executes and prints its usage banner" ;;
    *)
        echo "FAIL: tnpppage printed no usage banner; output was: [$out]"
        exit 1 ;;
esac

# Test 3 (functional): testq executes and reports its usage text.
# With no arguments it prints the testq usage to stderr and exits 1.
out="$("$TESTQ" < /dev/null 2>&1)"
rc=$?
if [ "$rc" -ne 1 ]; then
    echo "FAIL: testq (no args) exited $rc (want 1); output was: [$out]"
    exit 1
fi
case "$out" in
    *"testq"*)
        echo "PASS: testq executes and prints its usage text" ;;
    *)
        echo "FAIL: testq printed no usage text; output was: [$out]"
        exit 1 ;;
esac

# Test 4 (OHOS-specific): every packaged binary is an AArch64 ELF —
# i.e. it was really built for the OHOS target.
# e_machine at ELF offset 18 (2 bytes, little-endian) must be 0xB7.
for bin in "$RTNPPD" "$TNPPPAGE" "$TESTQ"; do
    machine="$(od -An -t x1 -j 18 -N 2 "$bin" | tr -d ' \n')"
    if [ "$machine" != "b700" ]; then
        echo "FAIL: unexpected ELF e_machine for $bin: $machine (want b700 = AArch64)"
        exit 1
    fi
done
echo "PASS: all three binaries are AArch64 ELF (e_machine AArch64)"

# Test 5 (OHOS-specific): every packaged binary targets the OHOS/musl
# runtime — the dynamic loader string is unique to that target.
for bin in "$RTNPPD" "$TNPPPAGE" "$TESTQ"; do
    if ! od -An -t c "$bin" | tr -d ' \n' | grep -qF "ld-musl-aarch64.so.1"; then
        echo "FAIL: $bin is not linked against the OHOS/musl loader"
        exit 1
    fi
done
echo "PASS: all three binaries use the OHOS/musl loader"
echo "=== All rtnppd smoke tests passed ==="
