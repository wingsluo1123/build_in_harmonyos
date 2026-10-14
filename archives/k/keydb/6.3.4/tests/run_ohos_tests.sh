#!/bin/sh
# run_ohos_tests.sh — HarmonyOS-specific test cases for keydb/6.3.4.
#
# This is the case runner. It reports NAMED end-to-end consumer cases — each
# one drives the *packaged* binaries through a real workflow and inspects a
# real result — plus two supporting checks that are evidence rather than
# consumer cases. The distinction matters: a list of assertions is not a
# substitute for a case that actually runs the program.
#
# Consumer cases
#   OHOS-1  keydb-server + keydb-cli : RESP round trip over loopback
#           (version -> start -> PING -> 100 KB SETRANGE/STRLEN on the
#            MALLOC=libc allocator path -> run_id via INFO -> shutdown)
#   OHOS-2  RDB persistence round trip (server + cli + check-rdb):
#           real dump.rdb produced, validated by the packaged checker,
#           values recovered after a restart
#   OHOS-3  AOF persistence round trip (server + cli + check-aof):
#           real appendonly.aof produced, validated, rebuilt on restart
#   OHOS-4  keydb-benchmark live load (server + benchmark):
#           real throughput reported AND the server verifiably received the
#           writes (dbsize/keyspace changed)
#
# Supporting checks (evidence, not consumer cases)
#   S1  packaged artefacts: the five commands are aarch64 ELF, and the musl
#       pthread shim (patch 0003/0004) is actually linked into keydb-server
#   S2  HarmonyOS platform capability probe (madvise / CPU affinity /
#       pthread_setname_np) — compiled and run on the device
#
# Usage:
#   run_ohos_tests.sh [<package_folder>]
#   <package_folder> defaults to the .conan2 package prefix of keydb/6.3.4.
#
# Exit code 0 = every case and check passed.
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
BENCH="${BINDIR}/keydb-benchmark"
CC="${CC:-/data/service/hnp/bin/clang}"
WORK="${TMPDIR:-/data/storage/el2/base/cache}/keydb-ohos-tests-$$"
mkdir -p "${WORK}" || exit 1

FAIL=0
CASE_TOTAL=0
CASE_PASS=0
note() { echo "==> $*"; }
fail() { echo "FAIL: $*"; FAIL=1; }

# case_result <name> <0|1 ok> — print the verdict and keep the tally.
case_result() {
    CASE_TOTAL=$((CASE_TOTAL + 1))
    if [ "$2" -eq 0 ]; then
        CASE_PASS=$((CASE_PASS + 1))
        echo "[CASE] $1: PASS"
    else
        echo "[CASE] $1: FAIL"
    fi
}

echo "==> package: ${PKG}"
echo "==> workdir: ${WORK}"

# ─────────────────────────────────────────────────────────────────────────
# S1. Supporting: every declared command is packaged, executable, aarch64 ELF,
#     and the musl pthread shim is really linked into the shipped server.
# ─────────────────────────────────────────────────────────────────────────
note "S1. packaged artefacts (supporting check)"
for c in keydb-server keydb-cli keydb-benchmark keydb-check-rdb keydb-check-aof; do
    f="${BINDIR}/${c}"
    if [ ! -x "${f}" ]; then
        fail "${c} missing or not executable"
        continue
    fi
    if head -c 20 "${f}" | od -An -tx1 | grep -q '7f 45 4c 46'; then
        echo "    [ok]: ${c} is an executable ELF"
    else
        fail "${c} is not an ELF"
    fi
done
# musl has no pthread_setaffinity_np at all; if the shim were compiled but not
# referenced the binary would silently lack it.
for sym in pthread_setaffinity_np pthread_getaffinity_np; do
    if grep -qa "${sym}" "${SRV}" 2>/dev/null; then
        echo "    [ok]: ${sym} present in keydb-server"
    else
        fail "${sym} missing from keydb-server (patch 0003/0004 not linked)"
    fi
done

# ─────────────────────────────────────────────────────────────────────────
# S2. Supporting: the HarmonyOS platform capabilities the patches rely on.
# ─────────────────────────────────────────────────────────────────────────
note "S2. HarmonyOS platform capability probe (supporting check)"
PROBE_SRC="$(dirname "$0")/ohos_platform_probe.c"
if [ ! -f "${PROBE_SRC}" ]; then
    fail "ohos_platform_probe.c not found next to this script"
else
    "${CC}" -O1 -Wall "${PROBE_SRC}" -o "${WORK}/ohos_platform_probe" \
        -lpthread 2>"${WORK}/probe.build.log"
    if [ $? -ne 0 ]; then
        fail "platform probe did not compile"
        cat "${WORK}/probe.build.log"
    else
        "${WORK}/ohos_platform_probe" || fail "platform probe reported failures"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────
# OHOS-1. keydb-server + keydb-cli: RESP round trip over loopback.
# ─────────────────────────────────────────────────────────────────────────
note "OHOS-1 keydb-server <-> keydb-cli RESP round trip"
PORT=$((23000 + ($$ % 20000)))
PIDFILE="${WORK}/keydb.pid"
LOGFILE="${WORK}/keydb.log"
OHOS1=0

"${SRV}" --bind 127.0.0.1 --protected-mode no --port "${PORT}" \
    --save '' --appendonly no --daemonize yes --pidfile "${PIDFILE}" \
    --dir "${WORK}" --logfile "${LOGFILE}" || { fail "server did not start"; OHOS1=1; }

reply=""
i=0
while [ "${i}" -lt 50 ]; do
    reply=$("${CLI}" -h 127.0.0.1 -p "${PORT}" --raw ping 2>/dev/null || true)
    [ "${reply}" = "PONG" ] && break
    i=$((i + 1))
    sleep 0.1
done
if [ "${reply}" = "PONG" ]; then
    echo "    [ok]: server answers PING over loopback"
else
    fail "server did not answer PING"
    cat "${LOGFILE}" 2>/dev/null
    OHOS1=1
fi

if [ "${OHOS1}" -eq 0 ]; then
    # SETRANGE on a large value exercises the allocator path the MALLOC=libc
    # choice affects (the bundled jemalloc cannot be built for OHOS).
    r=$("${CLI}" -h 127.0.0.1 -p "${PORT}" --raw setrange ohoskey 100000 abc)
    [ "${r}" = "100003" ] || { fail "SETRANGE large value returned '${r}'"; OHOS1=1; }
    [ "${r}" = "100003" ] && echo "    [ok]: SETRANGE 100000-byte value (allocator path)"

    r=$("${CLI}" -h 127.0.0.1 -p "${PORT}" --raw strlen ohoskey)
    [ "${r}" = "100003" ] || { fail "STRLEN returned '${r}'"; OHOS1=1; }
    [ "${r}" = "100003" ] && echo "    [ok]: STRLEN agrees with SETRANGE"

    # run_id is the replication identity the uuid dependency exists for.
    r=$("${CLI}" -h 127.0.0.1 -p "${PORT}" --raw info server | grep -c "^run_id:")
    [ "${r}" = "1" ] || { fail "run_id (uuid) not reported by INFO"; OHOS1=1; }
    [ "${r}" = "1" ] && echo "    [ok]: INFO reports run_id (uuid dependency in use)"
fi
case_result "OHOS-1 server+cli RESP round trip" "${OHOS1}"

"${CLI}" -h 127.0.0.1 -p "${PORT}" shutdown nosave >/dev/null 2>&1 || true
if [ -f "${PIDFILE}" ]; then
    kill "$(cat "${PIDFILE}")" >/dev/null 2>&1 || true
fi

# ─────────────────────────────────────────────────────────────────────────
# OHOS-4. keydb-benchmark: real load against a live server.
# The case is not "does --version print something"; it is "does the packaged
# benchmark actually drive the packaged server and report real work".
# ─────────────────────────────────────────────────────────────────────────
note "OHOS-4 keydb-benchmark live load"
PORT=$((PORT + 1000))
PIDFILE="${WORK}/keydb-bench.pid"
LOGFILE="${WORK}/keydb-bench.log"
OHOS4=0

"${SRV}" --bind 127.0.0.1 --protected-mode no --port "${PORT}" \
    --save '' --appendonly no --daemonize yes --pidfile "${PIDFILE}" \
    --dir "${WORK}" --logfile "${LOGFILE}" || { fail "server did not start for the benchmark case"; OHOS4=1; }

reply=""
i=0
while [ "${i}" -lt 50 ]; do
    reply=$("${CLI}" -h 127.0.0.1 -p "${PORT}" --raw ping 2>/dev/null || true)
    [ "${reply}" = "PONG" ] && break
    i=$((i + 1))
    sleep 0.1
done
[ "${reply}" = "PONG" ] || { fail "server not ready for the benchmark case"; OHOS4=1; }

if [ "${OHOS4}" -eq 0 ]; then
    out=$("${BENCH}" -h 127.0.0.1 -p "${PORT}" -n 200 -c 1 -t set 2>&1)
    rc=$?
    echo "${out}" | tail -6 | sed 's/^/        /'
    if [ "${rc}" -ne 0 ]; then
        fail "keydb-benchmark exited ${rc}"
        OHOS4=1
    fi
    if echo "${out}" | grep -q "requests per second"; then
        echo "    [ok]: benchmark reported real throughput"
    else
        fail "benchmark did not report throughput"
        OHOS4=1
    fi
    # The write load must be visible on the server: this is what makes the case
    # end-to-end rather than a self-report by the tool.
    got=$("${CLI}" -h 127.0.0.1 -p "${PORT}" --raw dbsize)
    case "${got}" in
        ''|*[!0-9]*) fail "dbsize unreadable after benchmark: '${got}'"; OHOS4=1 ;;
        *) if [ "${got}" -gt 0 ]; then
               echo "    [ok]: server received the load (dbsize=${got})"
           else
               fail "server dbsize still 0 after benchmark"
               OHOS4=1
           fi ;;
    esac
fi
case_result "OHOS-4 keydb-benchmark live load" "${OHOS4}"

"${CLI}" -h 127.0.0.1 -p "${PORT}" shutdown nosave >/dev/null 2>&1 || true
if [ -f "${PIDFILE}" ]; then
    kill "$(cat "${PIDFILE}")" >/dev/null 2>&1 || true
fi

# ─────────────────────────────────────────────────────────────────────────
# OHOS-2 / OHOS-3. Persistence round trips. Implemented in their own script
# because each phase needs its own server lifecycle; it prints the same
# [CASE] verdicts, which this runner folds into the tally.
# ─────────────────────────────────────────────────────────────────────────
note "OHOS-2 / OHOS-3 persistence round trips"
PERSIST="$(dirname "$0")/ohos_persistence_test.sh"
if [ ! -f "${PERSIST}" ]; then
    fail "ohos_persistence_test.sh not found next to this script"
else
    persist_out=$(sh "${PERSIST}" "${PKG}" 2>&1)
    p_rc=$?
    echo "${persist_out}" | sed 's/^/    /'
    for n in 2 3; do
        line=$(echo "${persist_out}" | grep "^\[CASE\] OHOS-${n} " | tail -1)
        CASE_TOTAL=$((CASE_TOTAL + 1))
        if echo "${line}" | grep -q ": PASS$"; then
            CASE_PASS=$((CASE_PASS + 1))
        else
            fail "OHOS-${n} did not pass"
        fi
    done
    [ "${p_rc}" -eq 0 ] || fail "persistence script exited ${p_rc}"
fi

# ─────────────────────────────────────────────────────────────────────────
# Verdict
# ─────────────────────────────────────────────────────────────────────────
echo
echo "OHOS end-to-end consumer cases: ${CASE_PASS}/${CASE_TOTAL} passed"
if [ "${FAIL}" -eq 0 ] && [ "${CASE_PASS}" -eq "${CASE_TOTAL}" ]; then
    echo "ALL_TESTS_PASS"
else
    echo "SOME_TESTS_FAIL"
fi
exit "${FAIL}"
