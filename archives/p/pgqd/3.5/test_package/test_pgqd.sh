#!/data/service/hnp/bin/bash
# test_package/test_pgqd.sh — end-to-end consumer test for pgqd on OHOS.
#
# This is not a smoke test.  It provisions a throwaway PostgreSQL cluster on
# the device and then drives the installed pgqd binary through the whole
# consumer flow:
#
#   1. pgqd -V / --ini              — CLI surface of the installed package
#   2. initdb + pg_ctl start        — a live database to talk to
#   3. pgqd -d <ini>                — real daemonise: pidfile + logfile
#   4. assert it connected          — no libpq failure while "auto-detecting dbs"
#   5. pgqd -r <ini>                — SIGHUP reload
#   6. pgqd -s <ini>                — SIGINT stop, process and pidfile gone
#
# Step 4 is the meaningful one: pgqd links libpq and queries pg_database at
# startup, so "connected to a live server" is observable from the absence of
# `connection error: PQconnectPoll` in its log — the exact line it emits when
# the server is unreachable.
set -eu

BIN_ROOT="$1"
PG_BIN="${2:-}"
PGQD="$BIN_ROOT/bin/pgqd"
# OHOS /system/bin/sh (mksh) cannot drive ELF binaries; the conanfile passes
# CONFIG_SHELL, and the upstream harness is started through the same bash.
BASH_BIN="${CONFIG_SHELL:-/data/service/hnp/bin/bash}"
command -v "$BASH_BIN" >/dev/null 2>&1 || BASH_BIN="$(command -v bash || echo /bin/bash)"

test -x "$PGQD" || { echo "FAIL: pgqd binary missing at $PGQD"; exit 1; }

# The conanfile hands over the PostgreSQL tool directory of the test-only
# postgresql tool_require; put it first so initdb/pg_ctl/createdb resolve.
if [ -n "$PG_BIN" ] && [ -d "$PG_BIN" ]; then
    PATH="$PG_BIN:$PATH"
    export PATH
fi

for tool in initdb pg_ctl createdb psql; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "FAIL: $tool not on PATH — PostgreSQL tools are unavailable"
        exit 1
    }
done

WORK="${TMPDIR:-$HOME/tmp}/pgqd-e2e-$$"
PGDATA="$WORK/pgdata"
INI="$WORK/pgqd.ini"
LOG="$WORK/pgqd.log"
PIDFILE="$WORK/pgqd.pid"
PORT="${PGQD_E2E_PORT:-$(( (RANDOM % 2000) + 15000 ))}"
PGUSER_NAME="pgqd_e2e"

PG_STARTED=0
cleanup() {
    if [ "$PG_STARTED" = "1" ]; then
        pg_ctl -D "$PGDATA" -m immediate stop >/dev/null 2>&1 || true
    fi
    rm -rf "$WORK"
}
trap cleanup EXIT

rm -rf "$WORK"
mkdir -p "$WORK"

die() { echo "FAIL: $*"; exit 1; }

# ── 1. CLI surface of the installed binary ────────────────────────────────
VERSION_OUT="$("$PGQD" -V)"
echo "[1] pgqd -V -> $VERSION_OUT"
echo "$VERSION_OUT" | grep -q "pgqd version 3.5" || die "unexpected version output"

INI_OUT="$("$PGQD" --ini)"
echo "$INI_OUT" | grep -q '^\[pgqd\]' || die "--ini did not print a [pgqd] section"
echo "$INI_OUT" | grep -q 'base_connstr' || die "--ini output is missing base_connstr"
echo "[1] ok: version banner and sample config"

# ── 2. A real database on the device ──────────────────────────────────────
# Failure of initdb/pg_ctl here is retried by the caller (test_package's
# conanfile.py), which backs off and re-runs the whole flow.  Retrying inside
# this script is deliberately avoided: the detection and the backoff would both
# need to fork, which is exactly what is unavailable when the worker is starved.
echo "[2] initdb + start PostgreSQL on 127.0.0.1:$PORT"
initdb -D "$PGDATA" -U "$PGUSER_NAME" --auth=trust --encoding=UTF8 \
    >"$WORK/initdb.log" 2>&1 || { cat "$WORK/initdb.log"; die "initdb failed"; }
pg_ctl -D "$PGDATA" -l "$WORK/postgres.log" -w \
    -o "-p $PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=" start \
    >"$WORK/pgctl.log" 2>&1 || {
        cat "$WORK/pgctl.log"
        cat "$WORK/postgres.log" 2>/dev/null
        die "pg_ctl start failed"
    }
PG_STARTED=1
# Readiness is probed with psql on purpose: pg_isready links the conan libpq
# (18.x, protocol 3.2) and reports "no attempt" against a 16.x server, while a
# plain psql round-trip works.
READY=0
for _ in $(seq 1 30); do
    if psql -h 127.0.0.1 -p "$PORT" -U "$PGUSER_NAME" -d postgres -At -c "select 1" \
        >/dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 1
done
if [ "$READY" != "1" ]; then
    cat "$WORK/pgctl.log" 2>/dev/null
    cat "$WORK/postgres.log" 2>/dev/null
    die "server not accepting connections on 127.0.0.1:$PORT"
fi
createdb -h 127.0.0.1 -p "$PORT" -U "$PGUSER_NAME" db1 || {
    cat "$WORK/postgres.log" 2>/dev/null
    die "createdb failed"
}
echo "[2] ok: live PostgreSQL cluster (db1 created)"

# ── 3. Real daemon run against that database ──────────────────────────────
cat >"$INI" <<EOF
[pgqd]
logfile = $LOG
pidfile = $PIDFILE
base_connstr = host=127.0.0.1 port=$PORT user=$PGUSER_NAME
syslog = 0
check_period = 2
maint_period = 4
ticker_period = 1
stats_period = 2
EOF

echo "[3] pgqd -d (daemonise)"
"$PGQD" -d "$INI" || die "pgqd -d failed"
for _ in $(seq 1 20); do
    [ -s "$PIDFILE" ] && break
    sleep 0.5
done
[ -s "$PIDFILE" ] || die "pgqd did not write its pidfile ($PIDFILE)"
DAEMON_PID="$(cat "$PIDFILE")"
kill -0 "$DAEMON_PID" 2>/dev/null || die "pidfile lists pid $DAEMON_PID but it is not running"
for _ in $(seq 1 20); do
    [ -s "$LOG" ] && grep -q "Starting pgqd 3.5" "$LOG" && break
    sleep 0.5
done
grep -q "Starting pgqd 3.5" "$LOG" || { cat "$LOG"; die "daemon never logged its startup banner"; }
echo "[3] ok: daemonised as pid $DAEMON_PID, logfile and pidfile written"

# ── 4. It really talked to the database ───────────────────────────────────
sleep 3
grep -q "auto-detecting dbs" "$LOG" || { cat "$LOG"; die "pgqd never reached its database scan"; }
if grep -q "connection error" "$LOG"; then
    cat "$LOG"
    die "pgqd could not reach the live PostgreSQL server"
fi
grep -qE "^\{ticks:|LOG \{ticks:" "$LOG" || { cat "$LOG"; die "daemon did not report its tick loop"; }
echo "[4] ok: scanned pg_database on the live server, no libpq errors"

# ── 5. SIGHUP reload ──────────────────────────────────────────────────────
echo "[5] pgqd -r (SIGHUP reload)"
"$PGQD" -r "$INI" || die "pgqd -r failed"
for _ in $(seq 1 20); do
    grep -q "Got SIGHUP" "$LOG" && break
    sleep 0.5
done
grep -q "Got SIGHUP" "$LOG" || { cat "$LOG"; die "daemon did not re-read its config on SIGHUP"; }
echo "[5] ok: daemon reloaded configuration in place"

# ── 6. SIGINT stop ────────────────────────────────────────────────────────
echo "[6] pgqd -s (SIGINT stop)"
"$PGQD" -s "$INI" || die "pgqd -s failed"
for _ in $(seq 1 20); do
    kill -0 "$DAEMON_PID" 2>/dev/null || break
    sleep 0.5
done
kill -0 "$DAEMON_PID" 2>/dev/null && die "daemon $DAEMON_PID survived SIGINT"
grep -q "Got SIGINT" "$LOG" || { cat "$LOG"; die "daemon did not log the SIGINT shutdown"; }
echo "[6] ok: daemon stopped cleanly on SIGINT"

# ── 7. The upstream suite's runnable cases, on the same cluster ────────────
# upstream_tests.sh is a byte-for-byte copy of the upstream tests/test.sh
# (sha256 checked in notes.md); it is staged into a throwaway layout so that
# its own `PGQD=../pgqd` resolves to the installed binary.  Reusing the cluster
# already running above keeps a CI run at one PostgreSQL instance instead of
# two — the workers fail to fork when process pressure gets high.
echo "[7] upstream tests/test.sh — the 4 cases runnable without PgQ"
UP="$WORK/upstream"
mkdir -p "$UP/tests"
cp "$(dirname "$0")/upstream_tests.sh" "$UP/tests/test.sh"
ln -sf "$PGQD" "$UP/pgqd"
# test.sh reads PGHOST/PGPORT/PGUSER for its own dropdb/createdb/psql preamble
export PGHOST=127.0.0.1
export PGPORT="$PORT"
export PGUSER="$PGUSER_NAME"
export LANG=C LC_ALL=C
for case in test_version test_show_ini test_stop test_reload; do
    "$BASH_BIN" "$UP/tests/test.sh" "$case" || die "upstream case $case failed"
done
echo "[7] ok: 4/4 runnable upstream cases passed against the live cluster"

echo "PASS: pgqd end-to-end consumer flow + upstream runnable cases completed on OHOS"
