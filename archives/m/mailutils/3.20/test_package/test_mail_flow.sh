#!/bin/sh
# End-to-end consumer: create a mailbox, deliver with putmail, read it back
# with the packaged mail and readmsg programs.
# Usage: sh test_mail_flow.sh <package_folder>
set -eu

PKG="$1"
TMPBASE="${TMPDIR:-/tmp}"
if [ "$(uname -s)" = "HarmonyOS" ] \
    && [ -d /data/storage/el2/base/cache ] \
    && [ -w /data/storage/el2/base/cache ]; then
    TMPBASE=/data/storage/el2/base/cache
fi
WORK="$(mktemp -d "$TMPBASE/mailutils-mail-flow.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

fail() { echo "MAIL FLOW FAILED: $*" >&2; exit 1; }
checks=0
pass() { checks=$((checks + 1)); echo "ok   - $*"; }

export HOME="$WORK"
export USER=mailutils-test
export LOGNAME=mailutils-test
export LC_ALL=C

message="$WORK/message.eml"
mailbox="$WORK/inbox.mbox"
cat >"$message" <<'EOF'
From sender@example.test Sat Jan  1 00:00:00 2022
From: sender@example.test
To: recipient@example.test
Subject: mailutils-harmony-e2e-7c35
Date: Sat, 1 Jan 2022 00:00:00 +0000
Content-Type: text/plain; charset=UTF-8

mailutils-harmony-body-4e91
EOF

if ! deliver="$("$PKG/bin/putmail" "$mailbox" <"$message" 2>&1)"; then
    printf '%s\n' "$deliver" >&2
    fail "putmail could not deliver the message into a new mailbox"
fi
[ -s "$mailbox" ] || fail "putmail did not create a non-empty mailbox"
pass "putmail created the mailbox and delivered the message"

if ! output="$("$PKG/bin/mail" -n -f "$mailbox" -p 2>&1)"; then
    printf '%s\n' "$output" >&2
    fail "packaged mail could not read the delivered mailbox"
fi
pass "packaged mail read the delivered mailbox"

printf '%s\n' "$output" | grep -Fq 'Subject: mailutils-harmony-e2e-7c35' \
    || fail "message subject missing from mail output"
pass "mail output contains the delivered subject"

printf '%s\n' "$output" | grep -Fq 'mailutils-harmony-body-4e91' \
    || fail "message body missing from mail output"
pass "mail output contains the delivered body"

if ! read_out="$("$PKG/bin/readmsg" -h -f "$mailbox" 1 2>&1)"; then
    printf '%s\n' "$read_out" >&2
    fail "packaged readmsg could not read message 1"
fi
printf '%s\n' "$read_out" | grep -Fq 'Subject: mailutils-harmony-e2e-7c35' \
    || fail "message subject missing from readmsg output"
pass "readmsg output contains the delivered subject"
printf '%s\n' "$read_out" | grep -Fq 'mailutils-harmony-body-4e91' \
    || fail "message body missing from readmsg output"
pass "readmsg output contains the delivered body"

[ "$checks" -eq 6 ] || fail "expected 6 checks, ran $checks"
echo "CONSUMER E2E PASSED ($checks/$checks checks)"
