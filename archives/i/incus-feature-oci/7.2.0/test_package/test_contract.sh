#!/bin/sh
# test_contract.sh — incus-feature-oci 7.2.0 test_package contract tests.
# Invoked by test_package/conanfile.py test() via `sh test_contract.sh ...`.
#
# Usage: sh test_contract.sh <wrapper> <incus_bin>
#   wrapper    — installed bin/incus-oci from the incus-feature-oci package
#   incus_bin  — bin/incus provided by the incus-feature-client dependency
#
# Cases (mirrors Alpine incus-feature APKBUILD oci() sub-package contract,
# upstream incus client/oci_images.go):
#   1. incus-oci --version executes the real installed wrapper;
#   2. without skopeo on PATH, the wrapper fails with the exact upstream
#      error message (exec.LookPath contract);
#   3. incus binary exists (dependency contract, checked by caller too);
#   4. with a skopeo stub on PATH, the wrapper really delegates: the incus
#      binary is executed (R34 substantive dependency exercise).
set -u

WRAPPER="$1"
INCUS_BIN="$2"
fail() { echo "FAIL: $*" >&2; exit 1; }
ok()   { echo "OK: $*"; }

[ -x "$WRAPPER" ] || fail "incus-oci wrapper not found/executable: $WRAPPER"

# Case 1: --version runs the real installed wrapper.
ver=$("$WRAPPER" --version) || fail "incus-oci --version exited non-zero"
case "$ver" in
    incus-feature-oci*) ok "case1 --version: $ver" ;;
    *) fail "unexpected --version output: $ver" ;;
esac

# Case 2: skopeo contract — exact upstream error when skopeo is missing.
# Ensure skopeo is not on PATH (conanrun env must not contain it).
if command -v skopeo >/dev/null 2>&1; then
    fail "skopeo unexpectedly present on PATH; contract case 2 is untestable"
fi
err=$("$WRAPPER" version 2>&1 >/dev/null)
rc=$?
[ "$rc" -ne 0 ] || fail "incus-oci must fail when skopeo is missing (upstream contract)"
expected='OCI container handling requires "skopeo" be present on the system'
[ "$err" = "$expected" ] || fail "unexpected skopeo contract message: $err"
ok "case2 skopeo contract: exact upstream message"

# Case 3: dependency contract — incus-feature-client provides the incus binary.
[ -e "$INCUS_BIN" ] || fail "incus binary not found (incus-feature-client dependency)"
ok "case3 dependency contract: incus binary present at $INCUS_BIN"

# Case 4: delegation — with a skopeo stub on PATH the wrapper really execs
# incus. Note `--version` is answered by the wrapper itself (never delegates),
# so use `version`: with the stub present the wrapper must reach
# `exec incus "$@"` and the real incus client answers with its own version
# line (NOT the meta-package banner).
TD=$(mktemp -d) || fail "mktemp failed"
trap 'rm -rf "$TD"' EXIT
cat > "$TD/skopeo" <<'EOF'
#!/bin/sh
exit 0
EOF
chmod 755 "$TD/skopeo"

out=$(PATH="$TD:$PATH" "$WRAPPER" version 2>&1)
rc=$?
[ "$rc" -eq 0 ] || fail "delegated incus version exited non-zero: $out"
case "$out" in
    *"incus-feature-oci"*) fail "wrapper answered itself instead of delegating to incus: $out" ;;
esac
case "$out" in
    *"Client version:"*) ok "case4 delegation: exec incus -> $(echo "$out" | head -1)" ;;
    *) fail "delegation output is not incus client version: $out" ;;
esac

echo "ALL CONTRACT TESTS PASSED"
