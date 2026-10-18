#!/bin/sh
# HarmonyOS-specific verification of the packaged GNU Mailutils 3.20.
# Usage: sh test_ohos_mailutils.sh <package_folder>
set -eu

PKG="$1"
checks=0
fail() { echo "OHOS TEST FAILED: $*" >&2; exit 1; }
pass() { checks=$((checks + 1)); echo "ok   - $*"; }

# 1. Platform identity
[ "$(uname -s)" = "HarmonyOS" ] || fail "uname -s is not HarmonyOS: $(uname -s)"
pass "platform is HarmonyOS"
[ "$(uname -m)" = "aarch64" ] || fail "uname -m is not aarch64: $(uname -m)"
pass "machine is aarch64"

# 2. Client utilities are installed and runnable
for tool in mailutils mail frm from messages readmsg sieve mimeview movemail \
            decodemail dotlock putmail mailutils-config; do
    [ -x "$PKG/bin/$tool" ] || fail "missing executable bin/$tool"
    "$PKG/bin/$tool" --version >/dev/null 2>&1 || fail "bin/$tool --version failed"
    pass "bin/$tool --version"
done

# 3. Servers are installed
for tool in imap4d pop3d comsatd mda lmtpd; do
    [ -x "$PKG/sbin/$tool" ] || fail "missing executable sbin/$tool"
    pass "sbin/$tool present"
done

# 4. Reported version
"$PKG/bin/mailutils" --version 2>&1 | grep -q "3.20" \
    || fail "mailutils --version does not report 3.20"
pass "mailutils reports version 3.20"

# 5. Installed library set
for lib in libmailutils.so.9 libmu_auth.so.9 libmu_sieve.so.9; do
    [ -e "$PKG/lib/$lib" ] || fail "missing lib/$lib"
    pass "lib/$lib present"
done

[ "$checks" -eq 24 ] || fail "expected 24 checks, ran $checks"
echo "OHOS-SPECIFIC TEST PASSED ($checks/$checks checks)"
