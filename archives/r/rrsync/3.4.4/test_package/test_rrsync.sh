#!/bin/sh
# rrsync 3.4.4 test suite (complements the upstream rsync testsuite, which has
# no rrsync-specific tests).  POSIX sh; requires python3 and rsync in PATH.
# RRSYNC env var points to the rrsync script under test.
set -e

RRSYNC=${RRSYNC:?RRSYNC not set}
# Use TMPDIR (set by CI worker); ensure it exists before mktemp.
: "${TMPDIR:=$HOME/tmp}"
mkdir -p "$TMPDIR"
WORK=$(mktemp -d "$TMPDIR/rrsync-test-XXXXXX")
trap 'rm -rf "$WORK"' EXIT
SRC="$WORK/src"
OUT="$WORK/out"
mkdir -p "$SRC" "$OUT"
echo "hello rrsync on $(uname -m)" > "$SRC/hello.txt"
echo "second file" > "$SRC/second.txt"

pass=0
fail=0

check() { # name expected_rc actual_rc
    if [ "$2" = "$3" ]; then
        echo "PASS: $1"
        pass=$((pass + 1))
    else
        echo "FAIL: $1 (expected rc=$2, got rc=$3)"
        fail=$((fail + 1))
    fi
}

# ---- Test 1: --help exits 0 -------------------------------------------
python3 "$RRSYNC" -h > "$WORK/help.txt" 2>&1
check "rrsync -h exits 0" 0 $?

grep -q "restricted" "$WORK/help.txt"
check "help mentions restriction" 0 $?

# ---- Test 2: sshd guard (no SSH_ORIGINAL_COMMAND) ----------------------
set +e
python3 "$RRSYNC" "$SRC" > "$WORK/guard.txt" 2>&1
rc=$?
set -e
check "no SSH_ORIGINAL_COMMAND exits 1" 1 "$rc"
grep -q "Not invoked via sshd" "$WORK/guard.txt"
check "guard error message" 0 $?

# ---- Test 3: end-to-end restricted transfer via rrsync -ro -------------
cat > "$WORK/shim" <<SHIM
#!/bin/sh
# emulate sshd: everything after the host is the original command
shift
SSH_ORIGINAL_COMMAND="\$*" exec python3 "$RRSYNC" -ro "$SRC"
SHIM
chmod +x "$WORK/shim"

rsync -e "$WORK/shim" localhost:hello.txt "$OUT/"
check "e2e pull via rrsync -ro" 0 $?

cmp -s "$SRC/hello.txt" "$OUT/hello.txt"
check "e2e transferred content identical" 0 $?

# ---- Test 4: read-only enforcement (write must be rejected) ------------
# The client-side rsync exits 12 when the remote rrsync dies (remote exit 1);
# accept either the remote code (1) or the client-reported code (12).
set +e
rsync -e "$WORK/shim" "$OUT/hello.txt" localhost:hello.txt > "$WORK/wo.txt" 2>&1
rc=$?
set -e
case "$rc" in
    1|12) check "write to -ro server rejected" "$rc" "$rc" ;;
    *) check "write to -ro server rejected" 1-or-12 "$rc" ;;
esac
grep -q "sending to read-only server" "$WORK/wo.txt"
check "read-only error message" 0 $?

echo "----------------------------------------"
echo "rrsync test results: pass=$pass fail=$fail"
[ "$fail" = 0 ]
