#!/data/service/hnp/bin/bash
# test_package/test.sh - consumer smoke test for the swupdate application.
#
# Runs inside the conanrun environment: swupdate/swupdate-* are on PATH and
# LD_LIBRARY_PATH points at the conan dependency libraries.
#
# Every assertion below is an OHOS-side (test_package) assertion; it is
# counted separately from the upstream tests.
set -u

pass=0
fail=0

ok()  { echo "PASS  $1"; pass=$((pass + 1)); }
bad() { echo "FAIL  $1"; fail=$((fail + 1)); }

echo "== swupdate --version =="
version_out="$(swupdate --version 2>&1)"
version_rc=$?
printf '%s\n' "$version_out"

if [ "$version_rc" -ne 0 ]; then
    # Without a runnable binary every "must fail" expectation below would
    # pass for the wrong reason; stop here instead.
    echo "FAIL  swupdate is not runnable (rc=$version_rc) - aborting"
    exit 1
fi
ok "--version rc=0"

case "$version_out" in
    *2026.05.1*) ok "--version fingerprint 2026.05.1" ;;
    *)           bad "--version fingerprint 2026.05.1 (got: $version_out)" ;;
esac

echo "== swupdate -h =="
help_out="$(swupdate -h 2>&1)"
help_rc=$?
if [ "$help_rc" -eq 0 ]; then ok "-h rc=0"; else bad "-h rc=$help_rc"; fi

check_help() {
    # $1 = option text, $2 = description
    case "$help_out" in
        *"$1"*) ok "help lists $2" ;;
        *)      bad "help lists $2" ;;
    esac
}
check_help --check   "--check (image check path)"
check_help --key     "--key (CONFIG_SIGNED_IMAGES built in)"
check_help --key-aes "--key-aes (CONFIG_ENCRYPTED_IMAGES built in)"
check_help webserver "webserver face (CONFIG_WEBSERVER built in)"
check_help suricatta "hawkBit client face (CONFIG_SURICATTA built in)"

echo "== negative paths (binary proven runnable above) =="
swupdate -c -i /nonexistent-ohos-test.swu >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then ok "missing image rejected (rc=$rc)"; else bad "missing image rejected (rc=$rc)"; fi

swupdate -c >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then ok "check without image rejected (rc=$rc)"; else bad "check without image rejected (rc=$rc)"; fi

echo "== bundled CLI tools =="
if command -v swupdate-client >/dev/null 2>&1; then
    swupdate-client -h >/dev/null 2>&1
    rc=$?
    if [ "$rc" -eq 0 ]; then ok "swupdate-client -h rc=0"; else bad "swupdate-client -h rc=$rc"; fi
else
    bad "swupdate-client on PATH"
fi

if command -v swupdate-progress >/dev/null 2>&1; then ok "swupdate-progress on PATH"; else bad "swupdate-progress on PATH"; fi
if command -v swupdate-ipc >/dev/null 2>&1; then ok "swupdate-ipc on PATH"; else bad "swupdate-ipc on PATH"; fi

echo "== summary =="
echo "test_package assertions: PASS=$pass FAIL=$fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
