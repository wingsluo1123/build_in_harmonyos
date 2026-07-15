#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for pass-otp extension script
# Verifies the otp.bash extension script is installed and valid
set -euo pipefail

echo "[test] Checking otp.bash exists"
if [ -f "$PACKAGE_ROOT/usr/lib/password-store/extensions/otp.bash" ]; then
    echo "✅ otp.bash found"
else
    echo "❌ otp.bash not found"
    exit 1
fi

echo "[test] Syntax check otp.bash"
bash -n "$PACKAGE_ROOT/usr/lib/password-store/extensions/otp.bash" && echo "✅ Syntax OK" || {
    echo "❌ Syntax check failed"
    exit 1
}

echo "[test] Checking man page"
if [ -f "$PACKAGE_ROOT/usr/share/man/man1/pass-otp.1" ]; then
    echo "✅ Man page found"
else
    echo "❌ Man page not found"
    exit 1
fi

echo "[test] pass-otp smoke test: PASS"
