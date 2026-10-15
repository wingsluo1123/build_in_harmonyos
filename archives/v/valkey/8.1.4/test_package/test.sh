#!/usr/bin/env bash
set -euo pipefail

VALKEY_SERVER="${VALKEY_SERVER:-valkey-server}"
VALKEY_SENTINEL="${VALKEY_SENTINEL:-valkey-sentinel}"
VALKEY_CLI="${VALKEY_CLI:-valkey-cli}"
VALKEY_BENCHMARK="${VALKEY_BENCHMARK:-valkey-benchmark}"
VALKEY_CHECK_RDB="${VALKEY_CHECK_RDB:-valkey-check-rdb}"
VALKEY_CHECK_AOF="${VALKEY_CHECK_AOF:-valkey-check-aof}"

BASE_PORT=$((24000 + ($$ % 4000)))
MAIN_PORT=$BASE_PORT
RDB_PORT=$((BASE_PORT + 1))
AOF_PORT=$((BASE_PORT + 2))
MASTER_PORT=$((BASE_PORT + 3))
REPLICA_PORT=$((BASE_PORT + 4))
SENTINEL_PORT=$((BASE_PORT + 5))
DEAD_PORT=$((BASE_PORT + 9))

# Every generated artefact goes to a per-run directory so that a second
# (reverse-verification) invocation can never read the first run's output.
WORK_ROOT="${TMPDIR:-$PWD}"
WORK_DIR="$WORK_ROOT/valkey-test-$$"
mkdir -p "$WORK_DIR"
PIDS=""
ASSERTIONS=0

cleanup() {
    for pid in $PIDS; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

assert_eq() {
    expected=$1
    actual=$2
    label=$3
    [ "$actual" = "$expected" ] || fail "$label: expected '$expected', got '$actual'"
    ASSERTIONS=$((ASSERTIONS + 1))
}

assert_contains() {
    value=$1
    needle=$2
    label=$3
    case "$value" in
        *"$needle"*) ;;
        *) fail "$label: '$needle' not found in '$value'" ;;
    esac
    ASSERTIONS=$((ASSERTIONS + 1))
}

assert_file() {
    [ -s "$1" ] || fail "$2: missing or empty file $1"
    ASSERTIONS=$((ASSERTIONS + 1))
}

assert_command() {
    command -v "$1" >/dev/null 2>&1 || fail "packaged command not found: $1"
    ASSERTIONS=$((ASSERTIONS + 1))
}

start_server() {
    port=$1
    shift
    dir="$WORK_DIR/server-$port"
    mkdir -p "$dir"
    (
        cd "$dir"
        "$VALKEY_SERVER" --port "$port" --daemonize no --save '' \
            --dir "$dir" "$@" >"$dir/server.log" 2>&1 &
        echo $! >"$dir/pid"
    )
    PIDS="$PIDS $(cat "$dir/pid")"
    ready=0
    for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
        if cli_at "$port" ping >/dev/null 2>&1; then
            ready=1
            break
        fi
        sleep 1
    done
    [ "$ready" = 1 ] || fail "server on port $port did not become ready (see $dir/server.log)"
}

cli_at() {
    port=$1
    shift
    "$VALKEY_CLI" -h 127.0.0.1 -p "$port" --raw "$@"
}

for cmd in "$VALKEY_SERVER" "$VALKEY_SENTINEL" "$VALKEY_CLI" \
    "$VALKEY_BENCHMARK" "$VALKEY_CHECK_RDB" "$VALKEY_CHECK_AOF"; do
    assert_command "$cmd"
done

# --- version handshake -------------------------------------------------------
assert_contains "$("$VALKEY_SERVER" --version)" "8.1.4" "valkey-server version"
assert_contains "$("$VALKEY_CLI" --version)" "8.1.4" "valkey-cli version"

start_server "$MAIN_PORT"
assert_eq "PONG" "$(cli_at "$MAIN_PORT" ping)" "ping"
assert_eq "2" "$(cli_at "$MAIN_PORT" echo 2)" "echo"

# --- data types --------------------------------------------------------------
assert_eq "OK" "$(cli_at "$MAIN_PORT" set k1 v1)" "set"
assert_eq "v1" "$(cli_at "$MAIN_PORT" get k1)" "get"
assert_eq "OK" "$(cli_at "$MAIN_PORT" set k2 v2 nx)" "set nx on free key"
assert_eq "" "$(cli_at "$MAIN_PORT" set k2 v3 nx)" "set nx on existing key (null reply)"
assert_eq "v2" "$(cli_at "$MAIN_PORT" get k2)" "set nx did not overwrite the existing key"
assert_eq "5" "$(cli_at "$MAIN_PORT" append k1 abc)" "append returns the new length"
assert_eq "v1abc" "$(cli_at "$MAIN_PORT" get k1)" "appended value"
assert_eq "string" "$(cli_at "$MAIN_PORT" type k1)" "type string"

assert_eq "2" "$(cli_at "$MAIN_PORT" lpush list b a)" "lpush"
assert_eq "a" "$(cli_at "$MAIN_PORT" lindex list 0)" "lindex"
assert_eq "list" "$(cli_at "$MAIN_PORT" type list)" "type list"
assert_eq "b" "$(cli_at "$MAIN_PORT" rpop list)" "rpop"

assert_eq "1" "$(cli_at "$MAIN_PORT" sadd set alpha)" "sadd new"
assert_eq "0" "$(cli_at "$MAIN_PORT" sadd set alpha)" "sadd duplicate"
assert_eq "1" "$(cli_at "$MAIN_PORT" sismember set alpha)" "sismember"
assert_eq "set" "$(cli_at "$MAIN_PORT" type set)" "type set"

assert_eq "1" "$(cli_at "$MAIN_PORT" hset hash f1 v1)" "hset new"
assert_eq "v1" "$(cli_at "$MAIN_PORT" hget hash f1)" "hget"
assert_eq "hash" "$(cli_at "$MAIN_PORT" type hash)" "type hash"

assert_eq "1" "$(cli_at "$MAIN_PORT" zadd zset 1 one)" "zadd"
assert_eq "one" "$(cli_at "$MAIN_PORT" zrange zset 0 0)" "zrange"
assert_eq "zset" "$(cli_at "$MAIN_PORT" type zset)" "type zset"

assert_eq "1" "$(cli_at "$MAIN_PORT" incr counter)" "incr"
assert_eq "7" "$(cli_at "$MAIN_PORT" incrby counter 6)" "incrby"

# --- expiry ------------------------------------------------------------------
assert_eq "OK" "$(cli_at "$MAIN_PORT" set ephem vpx EX 100)" "set with expiry"
assert_eq "1" "$(cli_at "$MAIN_PORT" expire ephem 500)" "expire"
ttl="$(cli_at "$MAIN_PORT" ttl ephem)"
[ "$ttl" -gt 0 ] || fail "ttl(ephem) should be positive, got '$ttl'"
ASSERTIONS=$((ASSERTIONS + 1))
assert_eq "-1" "$(cli_at "$MAIN_PORT" ttl k1)" "ttl on volatile-less key"
assert_eq "-2" "$(cli_at "$MAIN_PORT" ttl absent-key)" "ttl on missing key"

# --- transactions / scripting ------------------------------------------------
txout="$(printf 'MULTI\nSET tx1 a\nINCR txcounter\nEXEC\n' | "$VALKEY_CLI" -h 127.0.0.1 -p "$MAIN_PORT" --pipe 2>&1)"
# --pipe reports a summary (it streams commands without echoing replies).
assert_contains "$txout" "errors: 0" "multi/exec through --pipe reports no errors"
assert_contains "$txout" "replies: 4" "multi/exec through --pipe sent all four commands"
assert_eq "1" "$(cli_at "$MAIN_PORT" get txcounter)" "transactional incr result"
assert_eq "3" "$(cli_at "$MAIN_PORT" eval "return 1+2" 0)" "lua eval"
assert_eq "bar" "$(cli_at "$MAIN_PORT" eval "return ARGV[1]" 0 bar)" "lua argv"

# --- invalid input (negative) ------------------------------------------------
if cli_at "$DEAD_PORT" ping >"$WORK_DIR/dead.out" 2>&1; then
    fail "valkey-cli must not succeed against the closed port $DEAD_PORT"
fi
ASSERTIONS=$((ASSERTIONS + 1))
assert_contains "$(cat "$WORK_DIR/dead.out")" "Could not connect" "negative connection output"
badout="$(cli_at "$MAIN_PORT" set onlyonearg 2>&1 || true)"
assert_contains "$badout" "wrong number of arguments" "arity error"
assert_contains "$(cli_at "$MAIN_PORT" incr k1 2>&1)" "not an integer" "incr on a string value"

# --- persistence: RDB + check-rdb -------------------------------------------
start_server "$RDB_PORT" --save ''
assert_eq "OK" "$(cli_at "$RDB_PORT" set persist rdbvalue)" "rdb fixture set"
assert_eq "OK" "$(cli_at "$RDB_PORT" config set save '60 1')" "rdb enable save"
assert_eq "Background saving started" "$(cli_at "$RDB_PORT" bgsave)" "bgsave accepted"
saved=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
    if [ -s "$WORK_DIR/server-$RDB_PORT/dump.rdb" ]; then
        saved=1
        break
    fi
    sleep 1
done
[ "$saved" = 1 ] || fail "no RDB snapshot produced"
ASSERTIONS=$((ASSERTIONS + 1))
assert_file "$WORK_DIR/server-$RDB_PORT/dump.rdb" "dump.rdb"
assert_contains "$(cli_at "$RDB_PORT" info persistence)" "rdb_last_bgsave_status:ok" "RDB last bgsave status is ok"
rdbout="$WORK_DIR/check-rdb.out"
if "$VALKEY_CHECK_RDB" "$WORK_DIR/server-$RDB_PORT/dump.rdb" >"$rdbout" 2>&1; then
    ASSERTIONS=$((ASSERTIONS + 1))
else
    fail "check-rdb rejected a valid dump: $(head -c 300 "$rdbout")"
fi
assert_file "$rdbout" "check-rdb output"
rdblower="$(tr 'A-Z' 'a-z' < "$rdbout")"
case "$rdblower" in
    *error*|*invalid*|*short\ read*) fail "check-rdb reported a problem: $(head -c 300 "$rdbout")" ;;
    *rdb*) ASSERTIONS=$((ASSERTIONS + 1)) ;;
    *) fail "check-rdb output unrecognised: $(head -c 300 "$rdbout")" ;;
esac

# a corrupt dump must be rejected by the same checker
printf 'REDIS0099garbage' > "$WORK_DIR/corrupt.rdb"
if "$VALKEY_CHECK_RDB" "$WORK_DIR/corrupt.rdb" >"$WORK_DIR/corrupt.out" 2>&1; then
    fail "check-rdb accepted a corrupt dump"
fi
ASSERTIONS=$((ASSERTIONS + 1))
assert_file "$WORK_DIR/corrupt.out" "corrupt dump diagnostics"

# --- persistence: AOF + check-aof -------------------------------------------
start_server "$AOF_PORT" --save '' --appendonly no
assert_eq "OK" "$(cli_at "$AOF_PORT" config set appendonly yes)" "enable aof"
aof_ready=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
    if [ "$(cli_at "$AOF_PORT" config get appendonly | tail -n 1)" = "yes" ]; then
        aof_ready=1
        break
    fi
    sleep 1
done
[ "$aof_ready" = 1 ] || fail "appendonly never became active"
ASSERTIONS=$((ASSERTIONS + 1))
assert_eq "OK" "$(cli_at "$AOF_PORT" set aofkey aofvalue)" "aof fixture set"
assert_eq "Background append only file rewriting started" "$(cli_at "$AOF_PORT" bgrewriteaof)" "bgrewriteaof accepted"
aof_path=""
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
    aof_path="$(ls "$WORK_DIR/server-$AOF_PORT"/appendonlydir/*.manifest 2>/dev/null | head -n 1 || true)"
    if [ -n "$aof_path" ] && [ -s "$aof_path" ]; then
        break
    fi
    sleep 1
done
assert_file "${aof_path:-$WORK_DIR/server-$AOF_PORT/missing.manifest}" "rewritten multi-part AOF manifest"
aofout="$WORK_DIR/check-aof.out"
if "$VALKEY_CHECK_AOF" "$aof_path" >"$aofout" 2>&1; then
    ASSERTIONS=$((ASSERTIONS + 1))
else
    fail "check-aof rejected a valid base AOF: $(head -c 300 "$aofout")"
fi
assert_file "$aofout" "check-aof output"

# --- replication -------------------------------------------------------------
start_server "$MASTER_PORT" --save ''
start_server "$REPLICA_PORT" --save '' --replicaof 127.0.0.1 "$MASTER_PORT"
assert_eq "OK" "$(cli_at "$MASTER_PORT" set repl base)" "master write"
synced=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
    if [ "$(cli_at "$REPLICA_PORT" get repl)" = "base" ]; then
        synced=1
        break
    fi
    sleep 1
done
[ "$synced" = 1 ] || fail "replica never synchronised the master key"
ASSERTIONS=$((ASSERTIONS + 1))
assert_contains "$(cli_at "$MASTER_PORT" info replication)" "connected_slaves:1" "master sees one replica"
role_line="$(cli_at "$REPLICA_PORT" info replication | tr -d '\r' | grep '^role:' | head -n 1)"
case "$(printf '%s' "$role_line" | tr 'A-Z' 'a-z')" in
    role:replica*|role:slave*) ASSERTIONS=$((ASSERTIONS + 1)) ;;
    *) fail "unexpected replica role line: '$role_line'" ;;
esac
assert_eq "OK" "$(cli_at "$MASTER_PORT" set repl2 second)" "second master write"
raised=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
    if [ "$(cli_at "$MASTER_PORT" wait 1 2000)" != "" ]; then
        raised=1
        break
    fi
    sleep 1
done
[ "$raised" = 1 ] || fail "WAIT returned nothing"
ASSERTIONS=$((ASSERTIONS + 1))
replica_write="$(cli_at "$REPLICA_PORT" set readonly nope 2>&1 || true)"
assert_contains "$replica_write" "READONLY" "replica rejects writes with a READONLY error"

# --- sentinel ----------------------------------------------------------------
SENT_DIR="$WORK_DIR/sentinel"
mkdir -p "$SENT_DIR"
cat > "$SENT_DIR/sentinel.conf" <<CONF
port $SENTINEL_PORT
dir $SENT_DIR
sentinel monitor mymaster 127.0.0.1 $MASTER_PORT 1
sentinel down-after-milliseconds mymaster 2000
sentinel resolve-hostnames no
CONF
(
    cd "$SENT_DIR"
    "$VALKEY_SENTINEL" "$SENT_DIR/sentinel.conf" --daemonize no >"$SENT_DIR/sentinel.log" 2>&1 &
    echo $! >"$SENT_DIR/pid"
)
PIDS="$PIDS $(cat "$SENT_DIR/pid")"
sready=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
    if cli_at "$SENTINEL_PORT" ping >/dev/null 2>&1; then
        sready=1
        break
    fi
    sleep 1
done
[ "$sready" = 1 ] || fail "sentinel did not start (see $SENT_DIR/sentinel.log)"
ASSERTIONS=$((ASSERTIONS + 1))
assert_contains "$(cli_at "$SENTINEL_PORT" info sentinel)" "mymaster" "sentinel tracks mymaster"
assert_eq "$MASTER_PORT" "$(cli_at "$SENTINEL_PORT" sentinel get-master-addr-by-name mymaster | tail -n 1)" "sentinel master port"

# --- benchmark load ----------------------------------------------------------
benchout="$WORK_DIR/benchmark.txt"
"$VALKEY_BENCHMARK" -h 127.0.0.1 -p "$MAIN_PORT" -t set -n 500 -c 10 -d 32 -P 4 \
    --csv >"$benchout" 2>&1 || fail "valkey-benchmark failed"
assert_file "$benchout" "benchmark csv"
assert_contains "$(cat "$benchout")" "SET" "benchmark reports the SET run"
assert_contains "$(cat "$benchout")" "rps" "benchmark reports the rps column"

# --- ACL / pubsub / cluster command surface ---------------------------------
assert_eq "OK" "$(cli_at "$MAIN_PORT" acl setuser z44 on '>z44pass' +@all)" "acl setuser"
assert_eq "PONG" "$("$VALKEY_CLI" -h 127.0.0.1 -p "$MAIN_PORT" --user z44 --pass z44pass --raw ping)" "auth as acl user"
assert_eq "1" "$(cli_at "$MAIN_PORT" acl deluser z44)" "acl deluser removes one user"
subout="$WORK_DIR/pubsub.txt"
( cli_at "$MAIN_PORT" subscribe news >"$subout" 2>&1 & echo $! >>"$WORK_DIR/pids" )
sleep 2
assert_eq "1" "$(cli_at "$MAIN_PORT" publish news hello)" "publish receiver count"
sleep 2
assert_contains "$(cat "$subout")" "hello" "subscriber received the payload"
# A standalone (non-cluster) instance answers CLUSTER INFO with an explicit
# "cluster support disabled" error; either reply proves the command surface.
clusterout="$(cli_at "$MAIN_PORT" cluster info 2>&1 || true)"
case "$clusterout" in
    *cluster_enabled*|*"cluster support disabled"*) ASSERTIONS=$((ASSERTIONS + 1)) ;;
    *) fail "cluster info surface: unexpected output '$clusterout'" ;;
esac
assert_contains "$(cli_at "$MAIN_PORT" client list)" "addr=127.0.0.1" "client list reports the connection"

# --- shutdown ----------------------------------------------------------------
assert_contains "$(cli_at "$MAIN_PORT" config get maxmemory-policy)" "noeviction" "config get works"
cli_at "$MAIN_PORT" shutdown nosave >/dev/null 2>&1 || true
cli_at "$RDB_PORT" shutdown nosave >/dev/null 2>&1 || true
cli_at "$AOF_PORT" shutdown nosave >/dev/null 2>&1 || true
cli_at "$MASTER_PORT" shutdown nosave >/dev/null 2>&1 || true
cli_at "$REPLICA_PORT" shutdown nosave >/dev/null 2>&1 || true
cli_at "$SENTINEL_PORT" shutdown nosave >/dev/null 2>&1 || true

echo "valkey consumer test passed: $ASSERTIONS assertions"
