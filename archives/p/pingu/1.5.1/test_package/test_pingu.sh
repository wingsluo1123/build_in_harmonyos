#!/usr/bin/env bash
# pingu 1.5.1 — executable test of the packaged binaries.
#
# Upstream has no automated test suite (no tests/ directory, no check/test
# target in the hand written configure and Makefiles), so these cases are the
# verification that the shipped executables behave as documented:
#
#   T1  pingu -V                       version banner + exit 0
#   T2  pingu -h                       usage text + exit 1
#   T3  pingu -d -c <missing config>   configuration error path + exit 1
#   T4  pinguctl -a <missing socket>   administration socket error path + exit 1
#   T5  mtu                            usage text + exit 3
#   T6  ELF/musl check (OHOS specific) binaries are OHOS/musl builds, the
#                                      netlink glue was linked in and libev
#                                      resolves through the musl loader
set -u

PASS=0
FAIL=0
SKIP=0

ok()   { PASS=$((PASS + 1)); echo "PASS [$1] $2"; }
bad()  { FAIL=$((FAIL + 1)); echo "FAIL [$1] $2"; }
skip() { SKIP=$((SKIP + 1)); echo "SKIP [$1] $2"; }

tmpdir=$(mktemp -d) || exit 1
trap 'rm -rf "$tmpdir"' EXIT

for bin in pingu pinguctl mtu; do
    if ! command -v "$bin" >/dev/null 2>&1; then
        echo "FAIL [setup] $bin not found in PATH"
        exit 1
    fi
done

# ── T1: version banner ───────────────────────────────────────────────
out=$(pingu -V 2>&1)
rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q '^pingu 1\.5'; then
    ok T1 "pingu -V -> '$out'"
else
    bad T1 "pingu -V -> rc=$rc output='$out'"
fi

# ── T2: usage text ───────────────────────────────────────────────────
out=$(pingu -h 2>&1)
rc=$?
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -q 'usage: pingu \[-dhiv\]'; then
    ok T2 "pingu -h prints usage and exits 1"
else
    bad T2 "pingu -h -> rc=$rc output='$out'"
fi

# ── T3: missing configuration file ───────────────────────────────────
out=$(pingu -d -c "$tmpdir/absent.conf" 2>&1)
rc=$?
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -q 'absent.conf: No such file or directory'; then
    ok T3 "pingu -d -c <missing> reports the configuration error and exits 1"
else
    bad T3 "pingu -d -c <missing> -> rc=$rc output='$out'"
fi

# ── T4: administration socket error path ─────────────────────────────
out=$(pinguctl -a "$tmpdir/absent.ctl" 2>&1)
rc=$?
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -q 'absent.ctl: No such file or directory'; then
    ok T4 "pinguctl -a <missing socket> reports the socket error and exits 1"
else
    bad T4 "pinguctl -a <missing> -> rc=$rc output='$out'"
fi

# ── T5: mtu helper usage ─────────────────────────────────────────────
out=$(mtu 2>&1)
rc=$?
if [ "$rc" -eq 3 ] && printf '%s' "$out" | grep -q 'usage: mtu -i <mtu-size> <host>' \
        && printf '%s' "$out" | grep -q ' -D '; then
    ok T5 "mtu without arguments prints usage and exits 3"
else
    bad T5 "mtu -> rc=$rc output='$out'"
fi

# ── T6: OHOS platform check ──────────────────────────────────────────
# The recipe builds for musl-based OpenHarmony: the interpreter must be the
# musl loader, the netlink translation units touched by the UAPI patch must be
# linked into the daemon, and libev must be a dynamic NEEDED entry that the
# musl loader resolves (already proven by T1 running successfully).
readelf_bin=""
for candidate in readelf llvm-readelf; do
    if command -v "$candidate" >/dev/null 2>&1; then
        readelf_bin="$candidate"
        break
    fi
done

if [ -z "$readelf_bin" ]; then
    skip T6 "no readelf/llvm-readelf available to inspect the binaries"
else
    pingu_bin=$(command -v pingu)
    interp=$("$readelf_bin" -l "$pingu_bin" 2>/dev/null | grep -o '/lib/ld-musl-[a-z0-9_-]*\.so\.1' | head -1)
    needed=$("$readelf_bin" -d "$pingu_bin" 2>/dev/null | grep -c 'NEEDED.*libev\.so')
    netlink_sym=$("$readelf_bin" -s "$pingu_bin" 2>/dev/null | grep -c 'pingu_netlink')
    if [ -n "$interp" ] && [ "$needed" -ge 1 ] && [ "$netlink_sym" -ge 1 ]; then
        ok T6 "OHOS/musl build: interpreter=$interp, NEEDED libev.so, netlink glue linked"
    else
        bad T6 "interpreter='$interp' libev NEEDED=$needed netlink symbols=$netlink_sym"
    fi
fi

echo "----"
echo "pingu test summary: PASS=$PASS FAIL=$FAIL SKIP=$SKIP"
[ "$FAIL" -eq 0 ]
