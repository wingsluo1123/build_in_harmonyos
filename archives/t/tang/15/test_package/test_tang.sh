#!/bin/sh
set -eux

bindir=$1
daemon_dir=$2
workdir=$3
db="$workdir/db"
mkdir -p "$db"

pid=
cleanup() {
    rc=$1
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    fi
    if [ "$rc" -eq 0 ]; then
        rm -rf "$workdir"
    else
        echo "Consumer test failed; preserving diagnostics at $workdir" >&2
    fi
    trap - EXIT
    exit "$rc"
}
trap 'cleanup $?' EXIT

"$daemon_dir/tangd-keygen" "$db"
keys=$(find "$db" -type f -name '*.jwk' | wc -l | tr -d ' ')
[ "$keys" = 2 ]
for key in "$db"/*.jwk; do
    mode=$(stat -c %a "$key")
    [ "$mode" = 440 ]
done

port=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')
"$daemon_dir/tangd" -p "$port" -l "$db" >"$workdir/tangd.log" 2>&1 &
pid=$!

ready=0
i=0
while [ "$i" -lt 60 ]; do
    if python3 - "$port" <<'PY'
import socket
import sys
try:
    with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=1):
        pass
except OSError:
    sys.exit(1)
PY
    then
        ready=1
        break
    fi
    i=$((i + 1))
    sleep 1
done
[ "$ready" = 1 ]

thumbprint=$("$bindir/tang-show-keys" "$port")
[ -n "$thumbprint" ]
[ -f "$db/$thumbprint.jwk" ]
echo "Tang installed CLI and daemon passed on port $port (key $thumbprint)."
