#!/usr/bin/env bash
# Consumer test: drive the packaged keydb-server through the packaged keydb-cli.
set -eu

KEYDB_SERVER="${KEYDB_SERVER:-keydb-server}"
KEYDB_CLI="${KEYDB_CLI:-keydb-cli}"
PORT=$((20000 + ($$ % 20000)))
WORK_ROOT="${TMPDIR:-$PWD}"
WORK_DIR="$WORK_ROOT/keydb-test-$$"
PIDFILE="$WORK_DIR/keydb.pid"
LOGFILE="$WORK_DIR/keydb.log"

cleanup() {
    "$KEYDB_CLI" -h 127.0.0.1 -p "$PORT" shutdown nosave >/dev/null 2>&1 || true
    if [ -f "$PIDFILE" ]; then
        kill "$(cat "$PIDFILE")" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT INT TERM
mkdir -p "$WORK_DIR"

server_version=$("$KEYDB_SERVER" --version)
case "$server_version" in
    *6.3.4*) ;;
    *) echo "unexpected keydb-server version: $server_version" >&2; exit 1 ;;
esac

"$KEYDB_SERVER" \
    --bind 127.0.0.1 \
    --protected-mode no \
    --port "$PORT" \
    --save "" \
    --appendonly no \
    --daemonize yes \
    --pidfile "$PIDFILE" \
    --dir "$WORK_DIR" \
    --logfile "$LOGFILE"

attempt=0
reply=""
while [ "$attempt" -lt 50 ]; do
    reply=$("$KEYDB_CLI" -h 127.0.0.1 -p "$PORT" --raw ping 2>/dev/null || true)
    [ "$reply" = "PONG" ] && break
    attempt=$((attempt + 1))
    sleep 0.1
done
[ "$reply" = "PONG" ] || {
    echo "keydb-server did not become ready" >&2
    cat "$LOGFILE" >&2 || true
    exit 1
}

reply=$("$KEYDB_CLI" -h 127.0.0.1 -p "$PORT" --raw set harmonyos keydb-6.3.4)
[ "$reply" = "OK" ] || { echo "SET failed: $reply" >&2; exit 1; }

reply=$("$KEYDB_CLI" -h 127.0.0.1 -p "$PORT" --raw get harmonyos)
[ "$reply" = "keydb-6.3.4" ] || { echo "GET failed: $reply" >&2; exit 1; }

reply=$("$KEYDB_CLI" -h 127.0.0.1 -p "$PORT" --raw del harmonyos)
[ "$reply" = "1" ] || { echo "DEL failed: $reply" >&2; exit 1; }

echo "keydb 6.3.4 service test passed"
