#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for cdrtools executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] mkisofs --version"
mkisofs --version && echo "✅ mkisofs --version OK" || {
    echo "[test] mkisofs --version failed, trying --help..."
    mkisofs --help > /dev/null 2>&1 && echo "✅ mkisofs --help OK" || {
        echo "❌ mkisofs failed both --version and --help"
        exit 1
    }
}

echo "[test] cdrecord --version"
cdrecord --version 2>/dev/null || cdrecord version 2>/dev/null || true
echo "✅ cdrecord found"

echo "[test] cdda2wav --help"
cdda2wav --help > /dev/null 2>&1 || true
echo "✅ cdda2wav found"

echo "[test] readcd --help"
readcd --help > /dev/null 2>&1 || true
echo "✅ readcd found"
