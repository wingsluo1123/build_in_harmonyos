#!/bin/sh
# kio-fuse 5.1.1 consumer test: execute the packaged libexec/kio-fuse
# daemon inside the conanrun runtime environment (LD_LIBRARY_PATH already
# carries the dependency libraries); prepend the OHOS system and SDK
# library paths and provide a writable HOME / XDG_RUNTIME_DIR.
#
# usage: sh test_kio_fuse.sh <daemon> <workdir> <run_binary>
#   daemon      packaged libexec/kio-fuse path
#   workdir     writable scratch directory (test build folder)
#   run_binary  1 = also execute the daemon, 0 = cross-target, static only
#
# 12 assertions: daemon presence (1); --version exit/output (3); --help
# exit/output (3); -f <mnt> real start: exit status, three dynamic-loader
# failure patterns, and mount handling evidence (5).

set -u

DAEMON="$1"
WORK="$2"
RUN_BINARY="${3:-1}"

[ -d "$WORK" ] || { echo "workdir not found: $WORK"; exit 1; }

ASSERT=0
PASS=0
FAIL=0

ok()  { ASSERT=$((ASSERT+1)); PASS=$((PASS+1)); echo "PASS[$ASSERT] $1"; }
bad() { ASSERT=$((ASSERT+1)); FAIL=$((FAIL+1)); echo "FAIL[$ASSERT] $1"; }

# ---- daemon presence -------------------------------------------------------
if [ -x "$DAEMON" ]; then
    ok "daemon executable: $DAEMON"
else
    bad "daemon missing or not executable: $DAEMON"
fi

# ---- runtime environment ---------------------------------------------------
LD_LIBRARY_PATH="/system/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
for d in /data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib; do
    [ -d "$d" ] && LD_LIBRARY_PATH="$d:$LD_LIBRARY_PATH"
done
export LD_LIBRARY_PATH

HOME="$WORK/test-home"
XDG_RUNTIME_DIR="$WORK/xdg-runtime"
mkdir -p "$HOME" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
export HOME XDG_RUNTIME_DIR
export QT_QPA_PLATFORM=offscreen

if [ "$RUN_BINARY" != 1 ]; then
    echo "run_binary=$RUN_BINARY (cross-target): daemon execution skipped"
    echo "kio-fuse consumer test (static only): PASS=$PASS FAIL=$FAIL"
    if [ "$FAIL" -eq 0 ]; then
        exit 0
    fi
    exit 1
fi

# ---- 1. --version ----------------------------------------------------------
"$DAEMON" --version >"$WORK/version.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
    ok "--version exit 0"
else
    bad "--version exit $rc"
fi

if grep -q "KIO FUSE version 5.1.1" "$WORK/version.out"; then
    ok "--version prints the upstream version line"
else
    bad "--version missing 'KIO FUSE version 5.1.1'"
fi

if grep -q "FUSE library version 3.18.2" "$WORK/version.out"; then
    ok "--version prints the static libfuse version"
else
    bad "--version missing 'FUSE library version 3.18.2'"
fi

head -3 "$WORK/version.out"

# ---- 2. --help -------------------------------------------------------------
"$DAEMON" --help >"$WORK/help.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
    ok "--help exit 0"
else
    bad "--help exit $rc"
fi

if grep -q "Usage:" "$WORK/help.out"; then
    ok "--help prints the usage text"
else
    bad "--help missing 'Usage:'"
fi

if grep -q "[-]-disable-filejob-io" "$WORK/help.out"; then
    ok "--help lists --disable-filejob-io"
else
    bad "--help missing --disable-filejob-io"
fi

# ---- 3. -f <mountpoint>: real daemon start ---------------------------------
MNT="$WORK/mnt"
mkdir -p "$MNT"
"$DAEMON" -f "$MNT" >"$WORK/mnt.out" 2>&1 &
dpid=$!

# kill -0 also reports zombies, so prefer the /proc state when readable.
alive() {
    _p="$1"
    if [ -r "/proc/$_p/stat" ]; then
        _s="$(cut -d' ' -f3 < "/proc/$_p/stat" 2>/dev/null)"
        [ "$_s" != "Z" ]
    else
        kill -0 "$_p" 2>/dev/null
    fi
}

n=0
while [ "$n" -lt 180 ]; do
    alive "$dpid" || break
    sleep 1
    n=$((n+1))
done

STAYED=0
if alive "$dpid"; then
    STAYED=1
    kill -9 "$dpid" 2>/dev/null
fi
wait "$dpid" 2>/dev/null
rc=$?

if [ "$rc" -ne 0 ]; then
    if [ "$STAYED" -eq 1 ]; then
        ok "-f stayed up 180s serving the mount (killed; rc=$rc)"
    else
        ok "-f exited non-zero (rc=$rc) - sandbox denied the kernel mount"
    fi
else
    bad "-f exited 0 without serving: mount path returned success and quit"
fi

for pat in "error while loading shared libraries" "undefined symbol" "symbol lookup error"; do
    if grep -q "$pat" "$WORK/mnt.out"; then
        bad "runtime linking broken: $pat"
    else
        ok "no loader failure: $pat"
    fi
done

if [ "$STAYED" -eq 1 ]; then
    ok "mount handling: daemon kept serving until killed"
elif grep -q "fuse" "$WORK/mnt.out"; then
    ok "mount handling: libfuse denied the kernel mount with diagnostics"
elif [ "$rc" -gt 128 ]; then
    ok "mount handling: mount(2) killed by signal (rc=$rc)"
else
    bad "mount handling: non-zero exit with no libfuse diagnostics (rc=$rc)"
fi

head -5 "$WORK/mnt.out"

# ---- summary ---------------------------------------------------------------
echo "kio-fuse consumer test: PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -eq 0 ]; then
    echo "kio-fuse 5.1.1 test_package: OK"
    exit 0
fi
exit 1
