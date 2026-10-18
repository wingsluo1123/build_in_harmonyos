#!/system/bin/sh
#
# swaks consumer test driver (POSIX sh).
#
# usage: test_swaks.sh <packaged-swaks> <work-dir>
#
# Drives the packaged CLI against the loopback SMTP sink mock_smtp.pl and
# asserts on both swaks' own output and the SMTP transcript the sink recorded.
# Nothing here is a stub: every scenario either completes a real SMTP
# transaction or proves that swaks reports what the server actually answered.

set -u

SWAKS=$1
WORK=$2
MOCK_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MOCK="$MOCK_DIR/mock_smtp.pl"

SENDER="swaks-sender@ohos.test"
RCPT="swaks-rcpt@ohos.test"
HELO_NAME="swaks-ohos-test"
SUBJECT="OpenHarmony swaks consumer test"
BODY="swaks-ohos-payload-marker"
SMTP_TIMEOUT="20s"

PASS_COUNT=0
FAIL_COUNT=0
SINK_PID=""
SINK_PORT=""

pass() { PASS_COUNT=$((PASS_COUNT + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); printf 'FAIL: %s\n' "$1" >&2; }

cleanup() {
    if [ -n "$SINK_PID" ]; then
        kill "$SINK_PID" 2>/dev/null || true
        wait "$SINK_PID" 2>/dev/null || true
        SINK_PID=""
    fi
}
trap cleanup EXIT

assert_contains() {
    # <label> <haystack> <needle>
    case "$2" in
        *"$3"*) pass "$1" ;;
        *)
            fail "$1 -- output did not contain: $3"
            printf '%s\n' "$2" | sed -n '1,15p' >&2
            ;;
    esac
}

assert_transcript() {
    # <label> <transcript-file> <fixed-string>
    if grep -F -q -e "$3" "$2" 2>/dev/null; then
        pass "$1"
    else
        fail "$1 -- '$3' is missing from $2"
        sed -n '1,25p' "$2" >&2
    fi
}

start_sink() {
    # <ready-file> <transcript-file> [extra mock arguments...]
    ready=$1
    transcript=$2
    shift 2
    rm -f "$ready" "$transcript"
    "$PERL" "$MOCK" --listen 127.0.0.1:0 --ready-file "$ready" --transcript "$transcript" "$@" \
        >"$WORK/sink.out" 2>"$WORK/sink.err" &
    SINK_PID=$!
    tries=0
    while [ ! -s "$ready" ]; do
        tries=$((tries + 1))
        if [ "$tries" -gt 20 ]; then
            fail "SMTP sink never became ready"
            sed -n '1,20p' "$WORK/sink.err" >&2
            cleanup
            return 1
        fi
        sleep 1
    done
    SINK_PORT=$(sed -n 's/^PORT=\([0-9][0-9]*\).*$/\1/p' "$ready" | head -n 1)
    if [ -z "$SINK_PORT" ]; then
        fail "could not read the sink port from $ready"
        cleanup
        return 1
    fi
    return 0
}

printf '=== swaks consumer test ===\n'
printf 'swaks: %s\nwork dir: %s\nsink: %s\n' "$SWAKS" "$WORK" "$MOCK"

# ── 0. the staged artifact is a real executable entry point ──────────────
if [ ! -f "$SWAKS" ]; then
    printf 'FAIL: packaged CLI missing: %s\n' "$SWAKS" >&2
    exit 1
fi
if [ ! -x "$SWAKS" ]; then
    printf 'FAIL: packaged CLI is not executable (chmod did not stick): %s\n' "$SWAKS" >&2
    exit 1
fi

first_line=$(sed -n '1p' "$SWAKS")
assert_contains "upstream portable shebang is preserved" "$first_line" '#!/usr/bin/env perl'

# E037: the shebang only works when the platform provides /usr/bin/env.
if [ -x /usr/bin/env ]; then
    pass "/usr/bin/env exists, so '#!/usr/bin/env perl' can be honoured (E037)"
else
    fail "/usr/bin/env is missing, the upstream shebang cannot be honoured (E037)"
fi

# ── 1. the declared perl runtime requirement reaches PATH ────────────────
PERL=""
if command -v perl >/dev/null 2>&1; then
    PERL=$(command -v perl)
fi
if [ -n "$PERL" ]; then
    pass "perl runtime requirement is on PATH ($PERL)"
else
    printf 'FAIL: perl is not on PATH -- the run=True requirement did not propagate\n' >&2
    exit 1
fi

if "$PERL" -MPod::Usage -e 'exit 0' >/dev/null 2>&1; then
    pass "perl provides Pod::Usage, the hard 'use' at the top of the swaks script"
else
    fail "perl lacks Pod::Usage: the swaks script cannot even compile without it"
fi

# ── 2. CLI surface ──────────────────────────────────────────────────────
version_out=$("$SWAKS" --version 2>&1)
version_rc=$?
if [ "$version_rc" -eq 0 ]; then
    pass "swaks --version exits 0"
else
    fail "swaks --version exited $version_rc"
fi
assert_contains "swaks --version reports the packaged version" "$version_out" "swaks version 20240103.0"

help_out=$("$SWAKS" --help 2>&1)
help_rc=$?
if [ "$help_rc" -eq 0 ]; then
    pass "swaks --help exits 0"
else
    fail "swaks --help exited $help_rc (Pod::Usage or Pod::Text unavailable?)"
fi
assert_contains "swaks --help renders the built-in documentation" "$help_out" "Swiss Army Knife"

support_out=$("$SWAKS" --support 2>&1)
printf -- '--- swaks --support ---\n%s\n--- end ---\n' "$support_out"
socket_ok=0
case "$support_out" in
    *"IPv4/v6 Socket Transport supported"*) socket_ok=1 ;;
esac
case "$support_out" in
    *"Legacy IPv4 Socket Transport supported"*) socket_ok=1 ;;
esac
if [ "$socket_ok" -eq 1 ]; then
    pass "--support reports a usable internet socket transport"
else
    fail "--support reports no internet socket transport"
fi

# ── 3. full ESMTP transaction over a loopback TCP socket ────────────────
TRANSCRIPT_SOCKET="$WORK/transcript-socket.txt"
if start_sink "$WORK/ready-socket" "$TRANSCRIPT_SOCKET"; then
    pass "loopback SMTP sink is listening on port $SINK_PORT"

    socket_out=$("$SWAKS" --server "127.0.0.1:$SINK_PORT" --helo "$HELO_NAME" \
        --from "$SENDER" --to "$RCPT" \
        --header "Subject: $SUBJECT" --body "$BODY" \
        --timeout "$SMTP_TIMEOUT" 2>&1)
    socket_rc=$?
    printf -- '--- swaks socket transaction (exit %s) ---\n%s\n--- end ---\n' "$socket_rc" "$socket_out"

    if [ "$socket_rc" -eq 0 ]; then
        pass "socket transaction completed with exit 0"
    else
        fail "socket transaction exited $socket_rc"
    fi
    assert_contains "swaks echoes the sink banner" "$socket_out" "mock-smtp-ohos"
    assert_contains "swaks echoes the sink's queue confirmation" "$socket_out" "queued as MOCK1"

    assert_transcript "client sent EHLO $HELO_NAME" "$TRANSCRIPT_SOCKET" "EHLO $HELO_NAME"
    assert_transcript "client sent MAIL FROM:<$SENDER>" "$TRANSCRIPT_SOCKET" "MAIL FROM:<$SENDER>"
    assert_transcript "client sent RCPT TO:<$RCPT>" "$TRANSCRIPT_SOCKET" "RCPT TO:<$RCPT>"
    assert_transcript "client sent the Subject header" "$TRANSCRIPT_SOCKET" "Subject: $SUBJECT"
    assert_transcript "client sent the body payload" "$TRANSCRIPT_SOCKET" "$BODY"
    if grep -q '^\.$' "$TRANSCRIPT_SOCKET" 2>/dev/null; then
        pass "client terminated DATA with a single dot"
    else
        fail "DATA terminator is missing from the transcript"
    fi
    if grep -q '^QUIT$' "$TRANSCRIPT_SOCKET" 2>/dev/null; then
        pass "client closed the session with QUIT"
    else
        fail "QUIT is missing from the transcript"
    fi
    cleanup
fi

# ── 4. rejected recipient: swaks must report the server's 550 ───────────
TRANSCRIPT_REJECT="$WORK/transcript-reject.txt"
if start_sink "$WORK/ready-reject" "$TRANSCRIPT_REJECT" --reject-rcpt; then
    reject_out=$("$SWAKS" --server "127.0.0.1:$SINK_PORT" --helo "$HELO_NAME" \
        --from "$SENDER" --to "$RCPT" \
        --header "Subject: $SUBJECT" --body "$BODY" \
        --timeout "$SMTP_TIMEOUT" 2>&1)
    reject_rc=$?
    printf -- '--- swaks rejected-recipient transaction (exit %s) ---\n%s\n--- end ---\n' "$reject_rc" "$reject_out"

    if [ "$reject_rc" -ne 0 ]; then
        pass "swaks exits non-zero when the server rejects the recipient"
    else
        fail "swaks exited 0 although the sink answered 550 to RCPT TO"
    fi
    assert_contains "swaks surfaces the sink's 550 reply" "$reject_out" "550"
    assert_contains "swaks surfaces the rejection reason" "$reject_out" "mailbox unavailable"
    assert_transcript "the rejection came from the sink's RCPT handler" "$TRANSCRIPT_REJECT" "RCPT TO:<$RCPT>"
    cleanup
fi

# ── 5. pipe transport (needs IPC::Open2) ────────────────────────────────
case "$support_out" in
    *"Pipe Transport supported"*)
        TRANSCRIPT_PIPE="$WORK/transcript-pipe.txt"
        rm -f "$TRANSCRIPT_PIPE"
        # swaks hands --pipe to open2(): a command without shell
        # metacharacters is exec'd directly, so only quote when a path really
        # needs it.
        case "$PERL$MOCK$TRANSCRIPT_PIPE" in
            *" "*)
                PIPE_CMD="'$PERL' '$MOCK' --stdio --transcript '$TRANSCRIPT_PIPE'"
                ;;
            *)
                PIPE_CMD="$PERL $MOCK --stdio --transcript $TRANSCRIPT_PIPE"
                ;;
        esac
        pipe_out=$("$SWAKS" --pipe "$PIPE_CMD" --helo "$HELO_NAME" \
            --from "$SENDER" --to "$RCPT" \
            --header "Subject: $SUBJECT" --body "$BODY" \
            --timeout "$SMTP_TIMEOUT" 2>&1)
        pipe_rc=$?
        printf -- '--- swaks pipe transaction (exit %s) ---\n%s\n--- end ---\n' "$pipe_rc" "$pipe_out"

        if [ "$pipe_rc" -eq 0 ]; then
            pass "pipe transaction completed with exit 0"
        else
            fail "pipe transaction exited $pipe_rc"
        fi
        if [ -f "$TRANSCRIPT_PIPE" ]; then
            assert_transcript "pipe transport delivered MAIL FROM:<$SENDER>" "$TRANSCRIPT_PIPE" "MAIL FROM:<$SENDER>"
            assert_transcript "pipe transport delivered the body payload" "$TRANSCRIPT_PIPE" "$BODY"
        else
            fail "pipe transcript was never written"
        fi
        ;;
    *)
        printf 'SKIP: --support does not report "Pipe Transport supported"; pipe scenario not executed\n'
        ;;
esac

# ── summary ─────────────────────────────────────────────────────────────
printf 'swaks consumer test: %s passed, %s failed\n' "$PASS_COUNT" "$FAIL_COUNT"
if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi
printf 'SWAKS_CONSUMER_TEST_RESULT PASS=%s FAIL=%s\n' "$PASS_COUNT" "$FAIL_COUNT"
exit 0
