#!/bin/sh
# test_package/test_ifenslave.sh - consumer test for packaged ifenslave 2.14 hooks.
# Static only: no /sys writes, no ip/ifquery calls, no root needed.
# Counting contract (HMBS hard gate): exactly 6 deterministic scenarios.
# PASS increments exactly once per scenario; sub-checks only fail it.
# POSIX sh only: must run under /bin/sh (HarmonyOS preflight has no bash).
set -eu
BIN_DIR="$1"
DOC_DIR="$(dirname "$BIN_DIR")/share/doc/ifenslave"
PRE_UP="$BIN_DIR/ifenslave.if-pre-up"
IF_UP="$BIN_DIR/ifenslave.if-up"
POST_DOWN="$BIN_DIR/ifenslave.if-post-down"
TOTAL=6
PASS=0

emit_markers() {
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$1,\"command\":\"sh test_ifenslave.sh\",\"discovered\":$TOTAL,\"passedCount\":$2}"
    echo "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"none\",\"command\":\"\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,\"reason\":\"upstream 2.14 ships only debian hooks, no tests dir nor test runner (audit: test_package/MANIFEST.yml)\"}"
}

fail() {
    echo "FAIL: $1"
    emit_markers false "$PASS"
    exit 1
}

check_contains() {
    case "$1" in
        *"$2"*) echo "ok: $3";;
        *) fail "$3 (missing '$2')";;
    esac
}

echo "[test 1/6] three hooks installed"
[ -f "$PRE_UP" ] || fail "$PRE_UP not found"
[ -f "$IF_UP" ] || fail "$IF_UP not found"
[ -f "$POST_DOWN" ] || fail "$POST_DOWN not found"
echo "PASS [1/6]: three hooks present"
PASS=$((PASS+1))

echo "[test 2/6] shebang is /bin/sh"
for f in "$PRE_UP" "$IF_UP" "$POST_DOWN"; do
    HEAD="$(head -n 1 "$f")"
    check_contains "$HEAD" "#!/bin/sh" "shebang of $(basename "$f")"
done
echo "PASS [2/6]: shebang"
PASS=$((PASS+1))

echo "[test 3/6] shell syntax check"
sh -n "$PRE_UP" || fail "sh -n failed for if-pre-up"
sh -n "$IF_UP" || fail "sh -n failed for if-up"
sh -n "$POST_DOWN" || fail "sh -n failed for if-post-down"
echo "PASS [3/6]: sh -n syntax"
PASS=$((PASS+1))

echo "[test 4/6] pre-up master setup contract"
PRE_TEXT="$(cat "$PRE_UP")"
check_contains "$PRE_TEXT" "add_master" "pre-up defines add_master"
check_contains "$PRE_TEXT" "enslave_slaves" "pre-up defines enslave_slaves"
check_contains "$PRE_TEXT" "ip link add" "pre-up creates bond via ip"
echo "PASS [4/6]: pre-up contract"
PASS=$((PASS+1))

echo "[test 5/6] post-down teardown contract"
POST_TEXT="$(cat "$POST_DOWN")"
check_contains "$POST_TEXT" "bonding/slaves" "post-down touches bonding slaves sysfs"
check_contains "$POST_TEXT" "ip link del" "post-down deletes bond via ip"
echo "PASS [5/6]: post-down contract"
PASS=$((PASS+1))

echo "[test 6/6] docs and examples staged"
[ -f "$DOC_DIR/README.Debian" ] || fail "README.Debian not staged"
[ -f "$DOC_DIR/examples/two_ethernet" ] || fail "two_ethernet example not staged"
EXAMPLE_TEXT="$(cat "$DOC_DIR/examples/two_ethernet")"
check_contains "$EXAMPLE_TEXT" "bond-slaves" "two_ethernet documents bond-slaves"
README_TEXT="$(cat "$DOC_DIR/README.Debian")"
check_contains "$README_TEXT" "bond-slaves" "README.Debian documents bond-slaves"
echo "PASS [6/6]: docs and examples"
PASS=$((PASS+1))

echo "SUMMARY: $PASS/$TOTAL behavior scenarios passed"
emit_markers true "$PASS"
