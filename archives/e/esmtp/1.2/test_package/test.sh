#!/data/service/hnp/bin/bash
# test_package/test.sh — protocol-level functional test for the esmtp binary.
# Runs inside the conanrun env (PATH contains the installed bin/).
set -uo pipefail

fail() { echo "❌ $*"; exit 1; }
log()  { echo "[test] $*"; }

# NOTE: /tmp is read-only on OHOS — use $TMPDIR/$HOME/tmp for scratch space.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH" || fail "cannot create scratch root $SCRATCH"
TESTDIR="$SCRATCH/esmtp-test-$$"
mkdir -p "$TESTDIR" || fail "cannot create $TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

# ── 1) informational long options (patch 0001) ──────────────────────────────
log "esmtp --version"
ver=$(esmtp --version) || fail "esmtp --version exited non-zero"
echo "$ver" | grep -q "esmtp 1.2" || fail "--version printed unexpected value: $ver"
log "✅ --version OK ($ver)"

log "esmtp --help"
help=$(esmtp --help) || fail "esmtp --help exited non-zero"
echo "$help" | grep -q "usage:" || fail "--help printed unexpected value: $help"
log "✅ --help OK"

# ── 2) end-to-end relay over a loopback non-privileged TCP port ─────────────
python3 - "$TESTDIR" <<'PYEOF' &
import os
import socket
import sys

outdir = sys.argv[1]
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 0))            # kernel picks a non-privileged port
srv.listen(1)
srv.settimeout(45)
with open(os.path.join(outdir, "port"), "w", encoding="utf-8") as fh:
    fh.write(str(srv.getsockname()[1]))

conn, _ = srv.accept()
conn.settimeout(45)
transcript = open(os.path.join(outdir, "transcript.log"), "w", encoding="utf-8")


def send(line):
    conn.sendall((line + "\r\n").encode("utf-8"))


send("220 localhost ESMTP ready")
buf = b""
indata = False
while True:
    chunk = conn.recv(4096)
    if not chunk:
        break
    buf += chunk
    while b"\r\n" in buf:
        raw, buf = buf.split(b"\r\n", 1)
        text = raw.decode("utf-8", "replace")
        transcript.write(text + "\n")
        transcript.flush()
        if indata:
            if text == ".":
                indata = False
                send("250 2.0.0 Ok: queued")
            continue
        upper = text.upper()
        if upper.startswith("EHLO"):
            send("250-localhost")
            send("250-8BITMIME")
            send("250 SIZE 10000000")
        elif upper.startswith("HELO"):
            send("250 localhost")
        elif upper.startswith("MAIL FROM"):
            send("250 2.1.0 Ok")
        elif upper.startswith("RCPT TO"):
            send("250 2.1.5 Ok")
        elif upper.startswith("DATA"):
            indata = True
            send("354 End data with <CR><LF>.<CR><LF>")
        elif upper.startswith("RSET"):
            send("250 2.0.0 Ok")
        elif upper.startswith("NOOP"):
            send("250 2.0.0 Ok")
        elif upper.startswith("QUIT"):
            send("221 2.0.0 Bye")
            transcript.close()
            sys.exit(0)
        else:
            send("502 5.5.2 Command not implemented")
transcript.close()
PYEOF
SERVER_PID=$!

for _ in $(seq 1 100); do
    [ -s "$TESTDIR/port" ] && break
    sleep 0.1
done
[ -s "$TESTDIR/port" ] || fail "local SMTP listener never published its port"
PORT=$(cat "$TESTDIR/port")
log "local ESMTP listener on 127.0.0.1:$PORT (loopback, non-privileged TCP)"

cat > "$TESTDIR/esmtprc" <<CFGEOF
hostname = 127.0.0.1:$PORT
starttls = disabled
CFGEOF

printf 'From: sender@example.com\r\nTo: rcpt@example.com\r\nSubject: esmtp loopback probe\r\n\r\nesmtp body line\r\n' \
    > "$TESTDIR/msg"

log "esmtp -C esmtprc -f sender@example.com rcpt@example.com"
if command -v timeout >/dev/null 2>&1; then
    timeout 30 esmtp -C "$TESTDIR/esmtprc" -f sender@example.com rcpt@example.com \
        < "$TESTDIR/msg" 2>"$TESTDIR/esmtp.err"
else
    esmtp -C "$TESTDIR/esmtprc" -f sender@example.com rcpt@example.com \
        < "$TESTDIR/msg" 2>"$TESTDIR/esmtp.err"
fi
rc=$?
if [ "$rc" -ne 0 ]; then
    echo "--- esmtp stderr ---"; cat "$TESTDIR/esmtp.err"
    fail "esmtp delivery exited with $rc"
fi
log "✅ esmtp exited 0"

wait "$SERVER_PID" || fail "local SMTP listener did not finish cleanly"
log "server transcript:"; cat "$TESTDIR/transcript.log"

for marker in "EHLO" "MAIL FROM" "RCPT TO" "DATA" "QUIT"; do
    grep -qi "$marker" "$TESTDIR/transcript.log" || fail "transcript is missing $marker"
done
grep -q "esmtp body line" "$TESTDIR/transcript.log" || fail "message body never reached the listener"
log "✅ end-to-end ESMTP session OK (EHLO/MAIL FROM/RCPT TO/DATA/QUIT over loopback)"
