#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for qpage 3.3 (installed client + local mock SNPP server).
#
# Env:
#   QPAGE_BIN  path to the installed qpage executable
#   MOCK_SNPP  path to the compiled mock SNPP server
#   REDIR_SO   path to the compiled connect() port-redirect shim
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -u

QPAGE="${QPAGE_BIN:?QPAGE_BIN must point to the installed qpage}"
MOCK="${MOCK_SNPP:?MOCK_SNPP must point to the mock SNPP server}"
REDIR="${REDIR_SO:?REDIR_SO must point to the connect() redirect shim}"

WORK="${TMPDIR:-.}/qpage-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
MPID=""
cleanup() {
	[ -n "$MPID" ] && kill "$MPID" 2>/dev/null
	rm -rf "$WORK"
}
trap cleanup EXIT

checks=0
fails=0

check_eq() { # check_eq <name> <actual> <expected>
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		fails=$((fails + 1))
	fi
}

contains() { # contains <name> <file> <needle>
	checks=$((checks + 1))
	if grep -q -F -- "$3" "$2" 2>/dev/null; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (missing '$3' in $2)"
		fails=$((fails + 1))
	fi
}

# ---- CLI behaviour (no network) ----
out="$WORK/version.out"; timeout 20 "$QPAGE" -v > "$out" 2>&1; rc=$?
check_eq "qpage -v exits 0" "$rc" 0
contains "qpage -v prints the version banner" "$out" "QuickPage v3.3"

out="$WORK/usage.out"; timeout 20 "$QPAGE" -h > "$out" 2>&1
contains "qpage -h prints the version banner" "$out" "QuickPage v3.3"
contains "qpage -h prints usage" "$out" "Usage:"

out="$WORK/noargs.out"; timeout 20 "$QPAGE" </dev/null > "$out" 2>&1; rc=$?
check_eq "qpage without recipients fails" "$([ "$rc" -ne 0 ] && echo yes || echo no)" yes
contains "qpage without recipients complains" "$out" "No recipients!"

out="$WORK/nomsg.out"; timeout 20 "$QPAGE" -p foo </dev/null > "$out" 2>&1; rc=$?
check_eq "qpage without message fails" "$([ "$rc" -ne 0 ] && echo yes || echo no)" yes
contains "qpage without message complains" "$out" "No message!"

out="$WORK/badtime.out"; timeout 20 "$QPAGE" -a bogus -p foo hi > "$out" 2>&1; rc=$?
check_eq "qpage rejects an invalid time" "$([ "$rc" -ne 0 ] && echo yes || echo no)" yes
contains "qpage invalid-time diagnostic" "$out" "Invalid time: bogus"

out="$WORK/badlvl.out"; timeout 20 "$QPAGE" -l 99 -p foo hi > "$out" 2>&1; rc=$?
check_eq "qpage rejects an invalid level" "$([ "$rc" -ne 0 ] && echo yes || echo no)" yes
contains "qpage invalid-level diagnostic" "$out" "Level must be between 0 and 11"

out="$WORK/refused.out"; timeout 20 "$QPAGE" -s 127.0.0.1 -p foo hi > "$out" 2>&1; rc=$?
check_eq "qpage reports a connect failure" "$([ "$rc" -ne 0 ] && echo yes || echo no)" yes
contains "qpage connect-failure diagnostic" "$out" "Cannot connect to SNPP server"

# ---- live SNPP round trips against the mock server ----
PORT=$(( 20000 + ($$ % 20000) ))
MOCKLOG="$WORK/mock.log"

start_mock() {
	rm -f "$MOCKLOG"
	"$MOCK" "$PORT" "$MOCKLOG" &
	MPID=$!
	sleep 1
}

stop_mock() {
	if [ -n "$MPID" ]; then
		kill "$MPID" 2>/dev/null
		wait "$MPID" 2>/dev/null
	fi
	MPID=""
}

# 1. basic page
start_mock
LD_PRELOAD="$REDIR" QPAGE_SNPP_PORT="$PORT" timeout 20 \
	"$QPAGE" -s 127.0.0.1 -f tester -p 12345 "hello pager" > "$WORK/rt1.out" 2>&1
rc=$?
sleep 1
stop_mock
check_eq "SNPP basic page succeeds" "$rc" 0
contains "SNPP sends CALLerid" "$MOCKLOG" "CALLerid tester"
contains "SNPP sends PAGEr" "$MOCKLOG" "PAGEr 12345"
contains "SNPP sends DATA" "$MOCKLOG" "DATA"
contains "SNPP sends the message body" "$MOCKLOG" "hello pager"
contains "SNPP sends SEND" "$MOCKLOG" "SEND"
contains "SNPP sends QUIT" "$MOCKLOG" "QUIT"

# 2. service-level / coverage / hold modifiers
start_mock
LD_PRELOAD="$REDIR" QPAGE_SNPP_PORT="$PORT" timeout 20 \
	"$QPAGE" -s 127.0.0.1 -f bob -l 0 -c sky -a +5 -p 999 "urgent" > "$WORK/rt2.out" 2>&1
rc=$?
sleep 1
stop_mock
check_eq "SNPP page with modifiers succeeds" "$rc" 0
contains "SNPP sends LEVEl" "$MOCKLOG" "LEVEl 0"
contains "SNPP sends COVErage" "$MOCKLOG" "COVErage sky"
contains "SNPP sends HOLDuntil" "$MOCKLOG" "HOLDuntil"
contains "SNPP sends the modified PAGEr" "$MOCKLOG" "PAGEr 999"

# 3. e-mail message parsing (-m)
start_mock
{
	echo "From alice@example.com Mon Jan  1 00:00:00 2024"
	echo "From: Alice <alice@example.com>"
	echo "Subject: Test"
	echo "Content-Type: text/plain"
	echo ""
	echo "Body line one"
} | LD_PRELOAD="$REDIR" QPAGE_SNPP_PORT="$PORT" timeout 20 \
	"$QPAGE" -m -s 127.0.0.1 -p 777 > "$WORK/rt3.out" 2>&1
rc=$?
sleep 1
stop_mock
check_eq "SNPP e-mail page succeeds" "$rc" 0
contains "SNPP e-mail subject included" "$MOCKLOG" "(Subj: Test"
contains "SNPP e-mail body included" "$MOCKLOG" "Body line one"

echo "QPAGE_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
