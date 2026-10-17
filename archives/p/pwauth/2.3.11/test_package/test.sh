#!/data/service/hnp/bin/bash
# test_package consumer test for pwauth 2.3.11 (PAM backend).
#
# The core case is a complete end-to-end consumer scenario, not a bare
# assertion: test_consumer.c is compiled and then does what Apache
# mod_authnz_external does - it spawns the installed pwauth binary, feeds
# "<login>\n<password>\n" on stdin and takes the exit status as the
# authentication result.
#
#   1. success flow  : private PAM service using the linux-pam package's
#                      pam_permit.so  -> authentication + account management
#                      succeed -> pwauth exits 0
#   2. failure flow  : service whose module cannot be loaded -> non-zero
#   3. default flow  : without the private service directory the system PAM
#                      configuration is used (no /etc/pam.d/pwauth on OHOS)
#                      -> non-zero, i.e. the test hook does not change the
#                      default behaviour
#
# The remaining checks keep the documented failure paths and the libpam
# linkage covered (see pwauth.h for the status codes).
set -euo pipefail

BIN_NAME="pwauth"
UNKNOWN_LOGIN="pwauth-no-such-user-2.3.11"
WRONG_PASS="pwauth-wrong-password-2.3.11"
STATUS_SET="0 1 2 3 4 5 6 7 50 51 52 53"
checks=0
skipped=0

command -v "$BIN_NAME" >/dev/null 2>&1 || {
    echo "FAIL: $BIN_NAME not found on PATH — package bin/ missing?"
    exit 1
}
BIN_PATH="$(command -v "$BIN_NAME")"
echo "[info] pwauth: $BIN_PATH"

# --- scratch space (OHOS /tmp may be read-only) ------------------------------
BASE_DIR="${TMPDIR:-.}"
mkdir -p "$BASE_DIR" 2>/dev/null || BASE_DIR=.
WORK_DIR="$(mktemp -d "$BASE_DIR/pwauth-e2e.XXXXXX" 2>/dev/null || true)"
if [ -z "$WORK_DIR" ]; then
    WORK_DIR="$BASE_DIR/pwauth-e2e.$$"
fi
mkdir -p "$WORK_DIR"
export TMPDIR="$WORK_DIR"
cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT
echo "[info] work dir: $WORK_DIR"

is_known_status() {
    local code="$1" status
    for status in $STATUS_SET; do
        [ "$status" = "$code" ] && return 0
    done
    return 1
}

# --- build the consumer ------------------------------------------------------
CC_BIN="${CC:-clang}"
command -v "$CC_BIN" >/dev/null 2>&1 || {
    echo "FAIL: no C compiler ($CC_BIN) available to build the consumer test"
    exit 1
}
echo "[info] consumer compiler: $(command -v "$CC_BIN")"
"$CC_BIN" -O2 -o "$WORK_DIR/test_consumer" test_consumer.c || {
    echo "FAIL: cannot build test_consumer.c"
    exit 1
}
CONSUMER="$WORK_DIR/test_consumer"

# --- locate the PAM module shipped by the linux-pam package ------------------
PAM_MODULE="${PWAUTH_TEST_PAM_MODULE:-}"
if [ -z "$PAM_MODULE" ] && [ -n "${LINUX_PAM_MODULE_DIR:-}" ]; then
    PAM_MODULE="$LINUX_PAM_MODULE_DIR/pam_permit.so"
fi
[ -f "$PAM_MODULE" ] || {
    echo "FAIL: pam_permit.so not found (PWAUTH_TEST_PAM_MODULE='${PWAUTH_TEST_PAM_MODULE:-}', LINUX_PAM_MODULE_DIR='${LINUX_PAM_MODULE_DIR:-}')"
    exit 1
}
echo "[info] pam module: $PAM_MODULE"

# --- a login that is not filtered by MIN_UNIX_UID ---------------------------
pick_nonroot_login() {
    [ -r /etc/passwd ] || return 1
    while IFS=: read -r name _pass uid _rest; do
        [ -n "$name" ] || continue
        [ "$name" = "root" ] && continue
        case "$uid" in
            ''|*[!0-9]*) continue ;;
        esac
        [ "$uid" -ge 100 ] || continue
        printf '%s' "$name"
        return 0
    done < /etc/passwd
    return 1
}
PAM_LOGIN="$(pick_nonroot_login || true)"
[ -n "$PAM_LOGIN" ] || {
    echo "FAIL: no non-root login with uid >= 100 in /etc/passwd for the end-to-end case"
    exit 1
}
echo "[info] end-to-end login: $PAM_LOGIN"

# --- private PAM service directories ----------------------------------------
OK_CONFDIR="$WORK_DIR/pam-ok"
BAD_CONFDIR="$WORK_DIR/pam-bad"
mkdir -p "$OK_CONFDIR" "$BAD_CONFDIR"
printf 'auth sufficient %s\naccount sufficient %s\n' "$PAM_MODULE" "$PAM_MODULE" > "$OK_CONFDIR/pwauth"
printf 'auth required %s/does-not-exist.so\n' "$WORK_DIR" > "$BAD_CONFDIR/pwauth"

echo "--- pwauth service (success flow) ---"
cat "$OK_CONFDIR/pwauth"

# --- 1. end-to-end success flow ---------------------------------------------
rc=0
PWAUTH_PAM_CONFDIR="$OK_CONFDIR" "$CONSUMER" "$BIN_PATH" "$PAM_LOGIN" "$WRONG_PASS" || rc=$?
if [ "$rc" -ne 0 ]; then
    echo "FAIL 1: end-to-end authentication through PAM did not succeed (exit=$rc)"
    exit 1
fi
checks=$((checks + 1))
echo "PASS 1: end-to-end consumer flow: PAM authentication succeeded -> exit 0"

# --- 2. end-to-end failure flow (module cannot be loaded) -------------------
rc=0
PWAUTH_PAM_CONFDIR="$BAD_CONFDIR" "$CONSUMER" "$BIN_PATH" "$PAM_LOGIN" "$WRONG_PASS" || rc=$?
if [ "$rc" -eq 0 ]; then
    echo "FAIL 2: broken PAM service was reported as a successful login"
    exit 1
fi
if ! is_known_status "$rc"; then
    echo "FAIL 2: broken PAM service exit=$rc (not a pwauth status)"
    exit 1
fi
checks=$((checks + 1))
echo "PASS 2: end-to-end consumer flow: broken PAM service -> exit $rc (documented non-zero status)"

# --- 3. default flow must still use the system PAM configuration ------------
rc=0
"$CONSUMER" "$BIN_PATH" "$PAM_LOGIN" "$WRONG_PASS" || rc=$?
if [ "$rc" -eq 0 ]; then
    echo "FAIL 3: login without a private service directory was reported as OK"
    exit 1
fi
if ! is_known_status "$rc"; then
    echo "FAIL 3: default PAM configuration exit=$rc (not a pwauth status)"
    exit 1
fi
checks=$((checks + 1))
echo "PASS 3: default PAM configuration (no private service dir) -> exit $rc"

# --- 4. no input at all => STATUS_INT_ARGS (51) -----------------------------
rc=0
printf '' | "$BIN_NAME" || rc=$?
if [ "$rc" -ne 51 ]; then
    echo "FAIL 4: empty stdin exit=$rc (expected 51 STATUS_INT_ARGS)"
    exit 1
fi
checks=$((checks + 1))
echo "PASS 4: empty stdin -> exit 51 (STATUS_INT_ARGS)"

# --- 5. unknown login => getpwnam() fails before PAM => 1 -------------------
rc=0
printf '%s\n%s\n' "$UNKNOWN_LOGIN" "$WRONG_PASS" | "$BIN_NAME" || rc=$?
if [ "$rc" -ne 1 ]; then
    echo "FAIL 5: unknown login exit=$rc (expected 1 STATUS_UNKNOWN)"
    exit 1
fi
checks=$((checks + 1))
echo "PASS 5: unknown login -> exit 1 (STATUS_UNKNOWN)"

# --- 6. the caller's own login with a wrong password ------------------------
#     (may stop at the MIN_UNIX_UID gate instead of reaching PAM)
login="$(id -un 2>/dev/null || echo root)"
rc=0
printf '%s\n%s\n' "$login" "$WRONG_PASS" | "$BIN_NAME" || rc=$?
if [ "$rc" -eq 0 ]; then
    echo "FAIL 6: wrong password for '$login' was reported as OK"
    exit 1
fi
if ! is_known_status "$rc"; then
    echo "FAIL 6: wrong password for '$login' exit=$rc (not a pwauth status)"
    exit 1
fi
checks=$((checks + 1))
echo "PASS 6: existing login '$login' + wrong password -> exit $rc (documented non-zero status)"

# --- 7. the binary must really be linked against libpam ---------------------
if command -v llvm-readobj >/dev/null 2>&1; then
    dynamic_table="$(llvm-readobj --dynamic-table "$BIN_PATH" 2>&1 || true)"
elif command -v readelf >/dev/null 2>&1; then
    dynamic_table="$(readelf -d "$BIN_PATH" 2>&1 || true)"
else
    dynamic_table=""
fi
if [ -n "$dynamic_table" ]; then
    echo "$dynamic_table" | grep -q "libpam" || {
        echo "FAIL 7: $BIN_PATH declares no libpam dependency"
        exit 1
    }
    checks=$((checks + 1))
    echo "PASS 7: binary declares a libpam shared-library dependency"
else
    skipped=$((skipped + 1))
    echo "SKIP 7: neither llvm-readobj nor readelf is available"
fi

if [ "$skipped" -eq 0 ]; then
    echo "test pwauth 2.3.11: $checks/7 checks PASS"
else
    echo "test pwauth 2.3.11: $checks/7 checks PASS ($skipped skipped)"
fi
exit 0
