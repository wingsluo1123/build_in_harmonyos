#!/data/service/hnp/bin/bash
# Consumer end-to-end test for sircbot.
#
# Runs in the conanrun environment, so `sircbot` and `sircbot-send` below are
# the binaries installed by the package under test.  The test drives the real
# business flow:
#
#   fake IRC server  <--  sircbot daemon  <--  sircbot-send  <--  stdin
#   inbound PRIVMSG  -->  hook script in $SIRCBOT_HOOKSDIR/<channel>/
#
# and asserts on the observable business output (the PRIVMSG that reached the
# IRC server line by line, and the arguments the hook received).
#
# `set -u` only, on purpose: this is a multi-assertion harness that must run
# every check and report the total before failing, so `-e` (abort on first
# failure) and `pipefail` are deliberately omitted.  Exit status is decided by
# the FAILED counter at the end of the script.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
BASE="${TMPDIR:-$HOME/tmp}"
mkdir -p "$BASE" 2>/dev/null || BASE="$HERE"
WORK="$(mktemp -d "$BASE/sircbot-consumer.XXXXXX" 2>/dev/null)" || {
    WORK="$HERE/.consumer-work"
    rm -rf "$WORK"
    mkdir -p "$WORK"
}

CHANNEL='#testchan'
PORTFILE="$WORK/port"
IRCD_LOG="$WORK/ircd.log"
HOOK_LOG="$WORK/hook.log"
DAEMON_LOG="$WORK/sircbot.log"

RUNDIR="$WORK/run"
HOOKDIR="$WORK/hooks"
mkdir -p "$RUNDIR" "$HOOKDIR/$CHANNEL"

export SIRCBOT_RUNDIR="$RUNDIR"
export SIRCBOT_HOOKSDIR="$HOOKDIR"
export SIRCBOT_E2E_HOOKLOG="$HOOK_LOG"

FAILED=0
IRCD_PID=""
DAEMON_PID=""

cleanup() {
    [ -n "$DAEMON_PID" ] && kill "$DAEMON_PID" 2>/dev/null
    [ -n "$IRCD_PID" ] && kill "$IRCD_PID" 2>/dev/null
    sleep 1
    [ -n "$DAEMON_PID" ] && kill -9 "$DAEMON_PID" 2>/dev/null
    [ -n "$IRCD_PID" ] && kill -9 "$IRCD_PID" 2>/dev/null
    return 0
}
trap cleanup EXIT

check() {
    if [ "$1" = "0" ]; then
        echo "PASS: $2"
    else
        echo "FAIL: $2"
        FAILED=$((FAILED + 1))
    fi
}

wait_for() {  # wait_for <seconds> <grep-pattern> <file>
    local i=0
    local n=$(( $1 * 4 ))
    while [ "$i" -lt "$n" ]; do
        if [ -f "$3" ] && grep -q "$2" "$3" 2>/dev/null; then
            return 0
        fi
        sleep 0.25
        i=$((i + 1))
    done
    return 1
}

echo "--- sircbot consumer end-to-end test ---"
echo "workdir: $WORK"

# --------------------------------------------------------------------------
# Hooks in the channel directory.  Each executable hook appends its own marker,
# so the line counts in the hook log are falsifiable evidence: a hook that is
# missed, or run twice, changes them.
# --------------------------------------------------------------------------
cat > "$HOOKDIR/$CHANNEL/record.sh" <<'HOOK'
#!/bin/sh
echo "HOOK-ARGS sender=[$1] message=[$2] channel=[$3]" >> "$SIRCBOT_E2E_HOOKLOG"
HOOK
chmod 0755 "$HOOKDIR/$CHANNEL/record.sh"
cat > "$HOOKDIR/$CHANNEL/second.sh" <<'HOOK'
#!/bin/sh
echo "HOOK-SECOND" >> "$SIRCBOT_E2E_HOOKLOG"
HOOK
chmod 0755 "$HOOKDIR/$CHANNEL/second.sh"
# Not executable: its marker must never reach the log.
cat > "$HOOKDIR/$CHANNEL/not-executable.sh" <<'HOOK'
#!/bin/sh
echo "HOOK-SHOULD-NOT-RUN" >> "$SIRCBOT_E2E_HOOKLOG"
HOOK
chmod 0644 "$HOOKDIR/$CHANNEL/not-executable.sh"
: > "$HOOK_LOG"

# --------------------------------------------------------------------------
# 1. peer IRC server
# --------------------------------------------------------------------------
python3 "$HERE/fakeircd.py" --portfile "$PORTFILE" --log "$IRCD_LOG" \
    --channel "$CHANNEL" --inject-after 8 \
    --inject-text ":alice!u@h PRIVMSG $CHANNEL :hello-from-irc" &
IRCD_PID=$!

PORT=""
for _ in $(seq 1 40); do
    if [ -s "$PORTFILE" ]; then PORT="$(cat "$PORTFILE")"; break; fi
    sleep 0.25
done
if [ -z "$PORT" ]; then
    echo "FAIL: fake IRC server never reported a port"
    cat "$IRCD_LOG" 2>/dev/null
    echo "consumer test: FAILED"
    exit 1
fi
echo "peer IRC server listening on 127.0.0.1:$PORT"

# --------------------------------------------------------------------------
# 2. the installed daemon, started the documented way (daemon mode, pidfile)
# --------------------------------------------------------------------------
sircbot -l "$DAEMON_LOG" -s 127.0.0.1 -p "$PORT" -n testnick "$CHANNEL" &
sleep 3

if [ -s "$RUNDIR/sircbot.pid" ]; then
    DAEMON_PID="$(cat "$RUNDIR/sircbot.pid")"
fi
check "$([ -n "$DAEMON_PID" ] && kill -0 "$DAEMON_PID" 2>/dev/null; echo $?)" \
      "daemon started and wrote its pidfile ($RUNDIR/sircbot.pid)"

# The daemon must have reached the IRC handshake and joined the channel.
wait_for 15 'JOIN #testchan' "$IRCD_LOG"
check "$?" "daemon completed the IRC handshake and joined $CHANNEL"

# --------------------------------------------------------------------------
# 3. the per-channel socket must exist somewhere the client can reach it.
#    HarmonyOS refuses pathname AF_UNIX binds, so an abstract-namespace entry
#    (leading '@' in /proc/net/unix) is the expected shape there; a pathname
#    socket node is equally acceptable on platforms that allow it.
# --------------------------------------------------------------------------
wait_for 10 "testchan" /proc/net/unix
ABSTRACT_OK=$?
PATHNAME_OK=1
[ -S "$RUNDIR/$CHANNEL" ] && PATHNAME_OK=0
if [ "$ABSTRACT_OK" = "0" ] || [ "$PATHNAME_OK" = "0" ]; then
    check 0 "channel socket is reachable (abstract=$([ "$ABSTRACT_OK" = 0 ] && echo yes || echo no), pathname=$([ "$PATHNAME_OK" = 0 ] && echo yes || echo no))"
else
    check 1 "channel socket is reachable"
fi

# --------------------------------------------------------------------------
# 4. outbound direction: stdin -> sircbot-send -> daemon -> PRIVMSG
# --------------------------------------------------------------------------
printf 'hello-from-iot\n' | sircbot-send "$CHANNEL"
check "$?" "sircbot-send accepted the message from stdin"

wait_for 20 'PRIVMSG #testchan :hello-from-iot' "$IRCD_LOG"
check "$?" "message reached the IRC server as 'PRIVMSG #testchan :hello-from-iot'"

# --------------------------------------------------------------------------
# 5. inbound direction: PRIVMSG from the channel -> hook script
# --------------------------------------------------------------------------
wait_for 20 'HOOK-ARGS sender=\[alice\] message=\[hello-from-irc\] channel=\[#testchan\]' "$HOOK_LOG"
check "$?" "inbound PRIVMSG executed the channel hook with (sender, message, channel)"

# Every executable hook must run exactly once, and the non-executable one must
# not run at all.  These counts can really fail: a skipped or repeated hook
# changes them, and unlike a "no such string in the log" check they do not pass
# by construction.
ARGS_N=$(grep -c '^HOOK-ARGS ' "$HOOK_LOG")
SECOND_N=$(grep -c '^HOOK-SECOND$' "$HOOK_LOG")
SKIP_N=$(grep -c '^HOOK-SHOULD-NOT-RUN$' "$HOOK_LOG")
echo "hook markers: args=$ARGS_N second=$SECOND_N non-exec=$SKIP_N (expect 1/1/0)"
if [ "$ARGS_N" = "1" ] && [ "$SECOND_N" = "1" ] && [ "$SKIP_N" = "0" ]; then
    check 0 "directory walk ran both executable hooks exactly once and skipped the non-executable one"
else
    check 1 "directory walk ran both executable hooks exactly once and skipped the non-executable one"
fi

# --------------------------------------------------------------------------
echo "--- peer IRC server transcript ---"
cat "$IRCD_LOG"
echo "--- hook log ---"
cat "$HOOK_LOG"

cleanup
trap - EXIT

if [ "$FAILED" -ne 0 ]; then
    echo "consumer test: FAILED ($FAILED check(s))"
    exit 1
fi
echo "consumer test: all checks PASS"
exit 0
