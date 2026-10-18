#!/bin/sh
# test_package consumer test for musicpc 0.35 (mpc, HarmonyOS PC).
#
# Usage: test.sh <path-to-packaged-mpc-binary>
#
# Execution model (set by test_package/conanfile.py from the ELF header):
#   native   — the binary matches the test host (CI HarmonyOS PC worker):
#              exec it directly.
#   emulated — foreign-architecture host (x86_64 Linux dev box cross-building
#              for OHOS aarch64): MPC_RUNNER=qemu-aarch64, exec'd against the
#              OHOS guest sysroot (MPC_GUEST_ROOT) with the fortify shim
#              (MPC_GUEST_PRELOAD) preloaded in the guest via -E (so the host
#              loader never sees the aarch64 shim). The shim provides
#              __fd_chk(), which OHOS <sys/select.h> injects into FD_SET and
#              which the emulated guest libc does not implement; without it
#              libmpdclient.so.2 dies with "Error relocating ... __fd_chk:
#              symbol not found". Precedent: archives/t/tasksh/1.2.0,
#              archives/a/array-hash/0.7.2.
#
# Every assertion executes the installed mpc binary and checks observable
# stdout/stderr plus the exit code. No MPD server runs on the test host, so
# the connection path is expected to stop at the libmpdclient layer with
# "MPD error: Connection refused" (src/util.c printErrorAndExit). The grepped
# strings come from the upstream sources:
#   src/main.c print_usage()     -> "Usage: mpc [options] <command>" / "mpc version: "VERSION""
#   src/main.c print_help()      -> 'unknown command "%s"'
#   src/main.c mpc_table[]       -> "Display status"
#   src/util.c printErrorAndExit -> "MPD error: %s"
set -u

MPC_BIN="$1"

# Command prefix for the emulated model. No quoting inside CMD_PREFIX on
# purpose: the paths are space-free by construction and the prefix is meant
# to word-split (POSIX sh has no arrays).
CMD_PREFIX=""
if [ -n "${MPC_RUNNER:-}" ]; then
    CMD_PREFIX="$MPC_RUNNER -L $MPC_GUEST_ROOT"
    if [ -n "${MPC_GUEST_PRELOAD:-}" ]; then
        CMD_PREFIX="$CMD_PREFIX -E LD_PRELOAD=$MPC_GUEST_PRELOAD"
    fi
fi

pass=0

# run_mpc <args...> — run the packaged mpc, guarded by timeout(1) when
# available. The guarded commands all terminate promptly (no server: the
# connect path fails with ECONNREFUSED immediately; help/unknown-command
# return before any connection), so the guard is belt-and-braces.
run_mpc() {
    if command -v timeout >/dev/null 2>&1; then
        timeout 30 $CMD_PREFIX "$MPC_BIN" "$@"
    else
        $CMD_PREFIX "$MPC_BIN" "$@"
    fi
}

# 1. unknown command: exits 1 and prints the compiled-in version string
out=$(run_mpc nosuchcommand 2>&1); rc=$?
[ "$rc" = "1" ] || { echo "FAIL 1: mpc nosuchcommand exit=$rc out=[$out]"; exit 1; }
echo "$out" | grep -qF 'unknown command "nosuchcommand"' || { echo "FAIL 1: unknown-command message missing in [$out]"; exit 1; }
echo "$out" | grep -qF 'mpc version: 0.35' || { echo "FAIL 1: version string missing in [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 1: unknown command + VERSION macro -> [$out]"

# 2. help: exits 0 and prints the usage line plus the command table
out=$(run_mpc help 2>&1); rc=$?
[ "$rc" = "0" ] || { echo "FAIL 2: mpc help exit=$rc out=[$out]"; exit 1; }
echo "$out" | grep -qF 'Usage: mpc [options] <command>' || { echo "FAIL 2: usage line missing in [$out]"; exit 1; }
echo "$out" | grep -qF 'Display status' || { echo "FAIL 2: command table missing in [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 2: mpc help -> usage + command table"

# 3. status with no MPD server: reaches the libmpdclient connection layer
out=$(run_mpc status 2>&1); rc=$?
[ "$rc" = "1" ] || { echo "FAIL 3: expected exit 1, got $rc out=[$out]"; exit 1; }
echo "$out" | grep -qF 'MPD error: Connection refused' || { echo "FAIL 3: libmpdclient layer not reached in [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 3: status -> libmpdclient connection layer"

# 4. -h/-p (host/port) global options are parsed and passed to
#    libmpdclient. (mpc's option style: -h is the host, -p the port;
#    -P is the password - src/options.c.)
out=$(run_mpc -h 127.0.0.1 -p 6600 status 2>&1); rc=$?
[ "$rc" = "1" ] || { echo "FAIL 4: expected exit 1, got $rc out=[$out]"; exit 1; }
echo "$out" | grep -qF 'MPD error: Connection refused' || { echo "FAIL 4: libmpdclient layer not reached in [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 4: -h/-p options -> libmpdclient connection layer"

echo "test musicpc 0.35: $pass/4 checks PASS"
[ "$pass" = "4" ] || exit 1
exit 0
