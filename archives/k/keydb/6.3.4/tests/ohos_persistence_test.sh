#!/bin/sh
# ohos_persistence_test.sh — real HarmonyOS-specific functional test for
# keydb/6.3.4.
#
# Unlike tests/ohos_platform_probe.c (capability assertions) and
# tests/run_ohos_tests.sh (packaging/RESP smoke), this test drives a REAL
# data path end to end and inspects the REAL artifacts it produces:
#
#   1. RDB round trip
#      start server with RDB persistence -> write three real keys (one
#      100 KB, exercising the allocator path that MALLOC=libc affects)
#      -> SAVE -> the server writes a real dump.rdb -> validate that file
#      with the packaged keydb-check-rdb -> restart the server and verify
#      the keys are actually recovered from the artifact.
#
#   2. AOF round trip
#      restart with appendonly yes -> write a key -> the server produces a
#      real appendonly.aof -> validate it with the packaged keydb-check-aof.
#
# Every step asserts on the CONTENT of a produced artifact or on data read
# back after a real restart — not on a platform capability flag.
#
# Usage:
#   ohos_persistence_test.sh [<package_folder>]
# Exit code 0 = every step passed.
set -u

PKG="${1:-}"
if [ -z "${PKG}" ]; then
    PKG=$(ls -d "${HOME}"/.conan2/p/b/keydb*/p 2>/dev/null | head -1)
fi
[ -n "${PKG}" ] && [ -d "${PKG}/bin" ] || {
    echo "FAIL: no package folder with bin/ (got '${PKG}')"
    exit 1
}

BINDIR="${PKG}/bin"
SRV="${BINDIR}/keydb-server"
CLI="${BINDIR}/keydb-cli"
CHECK_RDB="${BINDIR}/keydb-check-rdb"
CHECK_AOF="${BINDIR}/keydb-check-aof"

WORK="${TMPDIR:-/data/storage/el2/base/cache}/keydb-persist-$$"
rm -rf "${WORK}"; mkdir -p "${WORK}" || exit 1

FAIL=0
fail() { echo "FAIL: $*"; FAIL=1; }
note() { echo "==> $*"; }
CLI_ARGS="-h 127.0.0.1"

echo "==> package: ${PKG}"
echo "==> workdir: ${WORK}"

PORT=$((25000 + ($$ % 15000)))
PIDFILE="${WORK}/keydb.pid"
LOGFILE="${WORK}/keydb.log"

start_server() {
    # All extra server arguments are forwarded verbatim; callers pass them as
    # separate words (e.g. start_server --save "900 1") so values that contain
    # spaces survive as a single argv entry.
    "${SRV}" --bind 127.0.0.1 --protected-mode no --port "${PORT}" \
        --daemonize yes --pidfile "${PIDFILE}" --dir "${WORK}" \
        --logfile "${LOGFILE}" "$@" || return 1
    attempt=0
    reply=""
    while [ "${attempt}" -lt 60 ]; do
        reply=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw ping 2>/dev/null || true)
        [ "${reply}" = "PONG" ] && return 0
        attempt=$((attempt + 1))
        sleep 0.1
    done
    return 1
}

stop_server() {
    "${CLI}" ${CLI_ARGS} -p "${PORT}" shutdown nosave >/dev/null 2>&1 || true
    if [ -f "${PIDFILE}" ]; then
        kill "$(cat "${PIDFILE}")" >/dev/null 2>&1 || true
    fi
    # Wait for the port to be released before restarting on the same port.
    attempt=0
    while [ "${attempt}" -lt 50 ]; do
        if ! "${CLI}" ${CLI_ARGS} -p "${PORT}" --raw ping >/dev/null 2>&1; then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 0.1
    done
    return 0
}

# ─────────────────────────────────────────────────────────────────────────
# 1. RDB round trip — real artifact, real validation, real recovery
# ─────────────────────────────────────────────────────────────────────────
note "OHOS-2 RDB: write -> SAVE -> validate artifact -> restart -> recover"
FAIL_AT_RDB_START=${FAIL}

start_server --save "900 1" --appendonly no --dbfilename dump.rdb \
    || fail "server did not start for the RDB phase"

if [ "${FAIL}" -eq 0 ]; then
    r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw set ohos:plain "harmonyos")
    [ "${r}" = "OK" ] || fail "SET ohos:plain returned '${r}'"

    # A value large enough to exercise the allocator path (MALLOC=libc on OHOS).
    big=$(head -c 3000 /dev/urandom | base64 | tr -d '\n' | head -c 3000)
    r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw set ohos:blob "${big}")
    [ "${r}" = "OK" ] || fail "SET ohos:blob (3000 bytes) returned '${r}'"

    r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw setrange ohos:sparse 100000 Z)
    [ "${r}" = "100001" ] || fail "SETRANGE ohos:sparse returned '${r}' (want 100001)"

    r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw dbsize)
    [ "${r}" = "3" ] || fail "DBSIZE returned '${r}' (want 3)"
    [ "${r}" = "3" ] && echo "    [ok]: 3 keys written"

    r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw save)
    [ "${r}" = "OK" ] || fail "SAVE returned '${r}'"

    stop_server

    # The artifact must exist and be non-trivial: this is the real output.
    RDB="${WORK}/dump.rdb"
    if [ ! -s "${RDB}" ]; then
        fail "dump.rdb was not produced by SAVE"
    else
        echo "    [ok]: dump.rdb produced ($(wc -c < "${RDB}") bytes)"

        # Validate the artifact with the packaged checker (real tool, real file).
        out=$("${CHECK_RDB}" "${RDB}" 2>&1)
        echo "${out}" | tail -4 | sed 's/^/        /'
        echo "${out}" | grep -q "Checksum OK" \
            || fail "keydb-check-rdb did not report 'Checksum OK'"
        echo "${out}" | grep -q "3 keys read" \
            || fail "keydb-check-rdb did not read back 3 keys"
        echo "${out}" | grep -q "Checksum OK" \
            && echo "    [ok]: keydb-check-rdb validated the artifact (Checksum OK, 3 keys read)"
    fi

    # Restart WITHOUT save and confirm the data is genuinely recovered.
    start_server --save "" --appendonly no --dbfilename dump.rdb \
        || fail "server did not restart for the RDB recovery check"

    r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw get ohos:plain)
    [ "${r}" = "harmonyos" ] || fail "recovered ohos:plain = '${r}' (want 'harmonyos')"
    [ "${r}" = "harmonyos" ] && echo "    [ok]: ohos:plain recovered after restart"

    r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw strlen ohos:blob)
    [ "${r}" = "3000" ] || fail "recovered ohos:blob length = '${r}' (want 3000)"
    [ "${r}" = "3000" ] && echo "    [ok]: 3000-byte value recovered intact"

    r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw strlen ohos:sparse)
    [ "${r}" = "100001" ] || fail "recovered ohos:sparse length = '${r}' (want 100001)"
    [ "${r}" = "100001" ] && echo "    [ok]: 100 KB sparse value recovered intact"

    stop_server
fi

if [ "${FAIL}" -eq "${FAIL_AT_RDB_START}" ]; then
    echo "[CASE] OHOS-2 RDB persistence round trip (server + cli + check-rdb): PASS"
else
    echo "[CASE] OHOS-2 RDB persistence round trip (server + cli + check-rdb): FAIL"
fi

# ─────────────────────────────────────────────────────────────────────────
# 2. AOF round trip — real appendonly.aof artifact, real validation
# ─────────────────────────────────────────────────────────────────────────
note "OHOS-3 AOF: write -> real appendonly.aof -> keydb-check-aof validates it"
FAIL_AT_AOF_START=${FAIL}

AOFDIR="${WORK}/aof"
mkdir -p "${AOFDIR}"
PORT=$((PORT + 1))
PIDFILE="${WORK}/keydb-aof.pid"
LOGFILE="${WORK}/keydb-aof.log"

start_server --save "" --appendonly yes --appendfilename appendonly.aof \
    --appendfsync always --dbfilename dump-aof.rdb \
    || fail "server did not start for the AOF phase"

if [ "${FAIL}" -eq 0 ]; then
    r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw set aof:key "append-only-file")
    [ "${r}" = "OK" ] || fail "SET under AOF returned '${r}'"
    r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw lpush aof:list a b c)
    [ "${r}" = "3" ] || fail "LPUSH under AOF returned '${r}' (want 3)"

    stop_server

    AOF="${WORK}/appendonly.aof"
    if [ ! -s "${AOF}" ]; then
        fail "appendonly.aof was not produced (with appendfsync always it must exist)"
    else
        echo "    [ok]: appendonly.aof produced ($(wc -c < "${AOF}") bytes)"

        out=$("${CHECK_AOF}" "${AOF}" 2>&1)
        echo "${out}" | tail -3 | sed 's/^/        /'
        # Real output shape:
        #   AOF analyzed: size=122, ok_up_to=122, ok_up_to_line=24, diff=0
        #   AOF is valid
        # diff=0 means no unparsable tail was found, i.e. the log is sound.
        echo "${out}" | grep -q "AOF analyzed: size=[0-9]*, ok_up_to=[0-9]*, ok_up_to_line=[0-9]*, diff=0" \
            || fail "keydb-check-aof did not report diff=0 (clean analysis)"
        echo "${out}" | grep -q "AOF is valid" \
            || fail "keydb-check-aof did not declare the AOF valid"
        echo "${out}" | grep -q "diff=0" \
            && echo "    [ok]: keydb-check-aof validated the artifact (diff=0, AOF is valid)"

        # Restart with AOF enabled: the data must be rebuilt from the log.
        start_server --save "" --appendonly yes --appendfilename appendonly.aof \
            --appendfsync always --dbfilename dump-aof.rdb \
            || fail "server did not restart for the AOF recovery check"

        r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw get aof:key)
        [ "${r}" = "append-only-file" ] || fail "AOF-recovered aof:key = '${r}'"
        [ "${r}" = "append-only-file" ] && echo "    [ok]: aof:key rebuilt from the AOF log"

        r=$("${CLI}" ${CLI_ARGS} -p "${PORT}" --raw llen aof:list)
        [ "${r}" = "3" ] || fail "AOF-recovered aof:list length = '${r}' (want 3)"
        [ "${r}" = "3" ] && echo "    [ok]: aof:list rebuilt from the AOF log"

        stop_server
    fi
fi

if [ "${FAIL}" -eq "${FAIL_AT_AOF_START}" ]; then
    echo "[CASE] OHOS-3 AOF persistence round trip (server + cli + check-aof): PASS"
else
    echo "[CASE] OHOS-3 AOF persistence round trip (server + cli + check-aof): FAIL"
fi

echo
if [ "${FAIL}" -eq 0 ]; then
    echo "ALL_TESTS_PASS"
else
    echo "SOME_TESTS_FAIL"
fi
exit "${FAIL}"
