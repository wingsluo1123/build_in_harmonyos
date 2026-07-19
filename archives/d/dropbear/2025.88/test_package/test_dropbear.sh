#!/usr/bin/env bash
set -euo pipefail

for program in dropbear dbclient dropbearkey dropbearconvert; do
    command -v "$program" >/dev/null
    output="$($program -h 2>&1 || true)"
    printf '%s\n' "$output" | grep -qi 'usage'
done

dropbear_help="$(dropbear -h 2>&1 || true)"
if ! printf '%s\n' "$dropbear_help" \
    | grep -Eq '(^|[[:space:]])-D[[:space:]]+.*authorized_keys'; then
    printf '%s\n' "dropbear was built without the -D authorized_keys option" >&2
    exit 1
fi

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

home="$tmpdir/home"
ssh_dir="$home/.ssh"
mkdir -p "$ssh_dir"
chmod 700 "$home" "$ssh_dir"

hostkey="$tmpdir/hostkey"
clientkey="$ssh_dir/id_dropbear"
authorized_keys="$ssh_dir/authorized_keys"
dropbearkey -t ecdsa -f "$hostkey" >/dev/null 2>&1
dropbearkey -t ecdsa -f "$clientkey" 2>/dev/null \
    | awk '/^ecdsa/{print; exit}' > "$authorized_keys"
chmod 600 "$clientkey" "$authorized_keys"
test -s "$authorized_keys"

port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
log="$tmpdir/dropbear.log"
# Use a private authorized_keys directory instead of the test runner's home.
HOME="$home" dropbear -F -E -D "$ssh_dir" \
    -p "127.0.0.1:$port" -r "$hostkey" > "$log" 2>&1 &
server_pid=$!

success=0
for _ in $(seq 1 50); do
    if output="$(HOME="$home" dbclient -y -i "$clientkey" \
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
