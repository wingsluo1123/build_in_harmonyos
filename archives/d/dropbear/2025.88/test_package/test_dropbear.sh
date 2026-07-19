#!/usr/bin/env bash
set -euo pipefail

dropbear=${1:?dropbear binary path is required}
dbclient=${2:?dbclient binary path is required}
dropbearkey=${3:?dropbearkey binary path is required}
dropbearconvert=${4:?dropbearconvert binary path is required}

for binary in "$dropbear" "$dbclient" "$dropbearkey" "$dropbearconvert"; do
    if [[ ! -f "$binary" || ! -x "$binary" ]]; then
        printf 'dropbear test binary is not executable: %s\n' "$binary" >&2
        exit 1
    fi
done

tmpdir="$(mktemp -d "${HOME:-/root}/dropbear-test.XXXXXX")"
server_pid=""

cleanup() {
    if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
        kill "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
    fi
    rm -rf "$tmpdir"
}
trap cleanup EXIT HUP INT TERM

check_help() {
    label=$1
    binary=$2
    output="$tmpdir/${label}-help.log"
    set +e
    "$binary" -h >"$output" 2>&1
    status=$?
    set -e
    if ! grep -qi 'usage' "$output"; then
        printf '%s -h failed with exit code %s\n' "$label" "$status" >&2
        cat "$output" >&2
        return 1
    fi
}

check_help dropbear "$dropbear"
check_help dbclient "$dbclient"
check_help dropbearkey "$dropbearkey"
check_help dropbearconvert "$dropbearconvert"

if ! grep -Eq '(^|[[:space:]])-D[[:space:]]+.*authorized_keys' \
    "${tmpdir}/dropbear-help.log"; then
    printf '%s\n' "dropbear was built without the -D authorized_keys option" >&2
    cat "${tmpdir}/dropbear-help.log" >&2
    exit 1
fi

home="$tmpdir/home"
ssh_dir="$home/.ssh"
mkdir -p "$ssh_dir"
chmod 700 "$home" "$ssh_dir"

hostkey="$tmpdir/hostkey"
clientkey="$ssh_dir/id_dropbear"
authorized_keys="$ssh_dir/authorized_keys"
"$dropbearkey" -t ecdsa -f "$hostkey" >/dev/null 2>&1
"$dropbearkey" -t ecdsa -f "$clientkey" 2>/dev/null \
    | awk '/^ecdsa/{print; exit}' > "$authorized_keys"
chmod 600 "$clientkey" "$authorized_keys"
test -s "$authorized_keys"

port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
log="$tmpdir/dropbear.log"
# Use a private authorized_keys directory instead of the test runner's home.
HOME="$home" "$dropbear" -F -E -D "$ssh_dir" \
    -p "127.0.0.1:$port" -r "$hostkey" > "$log" 2>&1 &
server_pid=$!

success=0
for _ in $(seq 1 50); do
    if output="$(HOME="$home" "$dbclient" -y -i "$clientkey" \
        -p "$port" 127.0.0.1 "printf dropbear-ok" 2>"$tmpdir/client.log")" \
        && [[ "$output" == "dropbear-ok" ]]; then
        success=1
        break
    fi
    if ! kill -0 "$server_pid" 2>/dev/null; then
        cat "$log" >&2
        cat "$tmpdir/client.log" >&2 || true
        exit 1
    fi
    sleep 0.1
done

if [[ "$success" != 1 ]]; then
    cat "$log" >&2
    cat "$tmpdir/client.log" >&2 || true
    exit 1
fi
