#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for man-db executable
set -eu

echo "[test] man --version"
man --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    man --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ man failed both --version and --help"
        exit 1
    }
}

echo "[test] mandb --version"
mandb --version && echo "✅ mandb OK" || echo "⚠️ mandb --version failed (non-fatal)"

echo "[test] whatis --version"
whatis --version && echo "✅ whatis OK" || echo "⚠️ whatis --version failed (non-fatal)"

echo "[test] lexgrog --version"
lexgrog --version && echo "✅ lexgrog OK" || echo "⚠️ lexgrog --version failed (non-fatal)"
