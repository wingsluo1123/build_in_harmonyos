#!/bin/sh
# test_package/test_sn.sh -- sn 0.3.8 package verification (OHOS).
#
# Drives the 14 packaged binaries in their deterministic no-network,
# no-spool error paths:
#   - 9 management tools: `tool -h` -> rc=1 + "Usage:" banner
#   - 5 spool-dependent tools: `tool -h` -> rc=2 + "Can't find spool
#     directory" (SNROOT default /var/spool/news baked in at compile time;
#     the spool check precedes any port binding or daemonization)
#
# Local OHOS-guest emulation (WSL qemu, QEMU_LD_PREFIX set): the guest's
# musl predates the __fd_chk fortify symbol that the OHOS sys/select.h
# FD_SET/FD_CLR macros call, so 8 of the 14 binaries fail relocation on
# the bare guest.  The guest ships libfdchkshim.so exporting __fd_chk
# for exactly this; preload it.  On the device the full OHOS musl exports
# __fd_chk (openharmony third_party_musl libc.map.txt), so the block is a
# no-op there (QEMU_LD_PREFIX unset).
#
# Usage: test_sn.sh [pkg_bin_dir]

set -u

PASS=0
FAIL=0

BIN_DIR=${1:-}
if [ -z "$BIN_DIR" ]; then
    # locate the package bin dir on the conanrun PATH
    IFS=:
    for d in $PATH; do
        if [ -x "$d/snscan" ]; then BIN_DIR=$d; break; fi
    done
    unset IFS
fi
if [ -z "$BIN_DIR" ] || [ ! -x "$BIN_DIR/snscan" ]; then
    echo "FAIL: packaged sn binaries not found (bin dir: ${BIN_DIR:-<none>})"
    exit 1
fi
echo "[test] bin dir: $BIN_DIR"

# local qemu guest only: provide __fd_chk (see header)
if [ -n "${QEMU_LD_PREFIX:-}" ] && [ -f "${QEMU_LD_PREFIX}/lib/libfdchkshim.so" ]; then
    if [ -n "${LD_PRELOAD:-}" ]; then
        LD_PRELOAD="${LD_PRELOAD}:${QEMU_LD_PREFIX}/lib/libfdchkshim.so"
    else
        LD_PRELOAD="${QEMU_LD_PREFIX}/lib/libfdchkshim.so"
    fi
    export LD_PRELOAD
    echo "[test] qemu guest detected; preloading libfdchkshim.so"
fi

check() {
    # $1=binary  $2=want_rc  $3=want_substring ; rest=args
    name=$1; want_rc=$2; want_sub=$3; shift 3
    out=$("$BIN_DIR/$name" "$@" 2>&1)
    rc=$?
    first=$(printf '%s\n' "$out" | head -n 1)
    if [ "$rc" -eq "$want_rc" ] && printf '%s' "$out" | grep -qF "$want_sub"; then
        echo "OK: $name rc=$rc :: $first"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name rc=$rc want_rc=$want_rc :: $first"
        FAIL=$((FAIL + 1))
    fi
}

# 9 management tools: -h -> rc=1 + Usage banner
check snexpire   1 "Usage:snexpire" -h
check snsend     1 "Usage: snsend [-rcnva]" -h
check snget      1 "Usage:snget" -h
check sngetd     1 "Usage:sngetd" -h
check snfetch    1 "Usage:snfetch" -h
check snnewgroup 1 "Usage:snnewgroup" -h
check sndelgroup 1 "Usage:sndelgroup" -h
check snlockf    1 "Usage: snlockf (no arguments or options)" -h
check snsplit    1 "Usage: snsplit" -h

# 5 spool-dependent tools: -h hits the spool check first -> rc=2
check snprimedb  2 "Can't find spool directory" -h
check snscan     2 "Can't find spool directory" -h
check snntpd     2 "Can't find spool directory" -h
check snmail     2 "Can't find spool directory" -h
check sndumpdb   2 "Can't find spool directory" -h

echo "sn test_package summary: PASS=$PASS FAIL=$FAIL TOTAL=$((PASS + FAIL))"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
