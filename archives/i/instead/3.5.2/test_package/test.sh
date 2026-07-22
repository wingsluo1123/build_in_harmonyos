#!/data/service/hnp/bin/bash
# test_package/test.sh — R34 smoke test for INSTEAD Engine 3.5.2 binary
# Runs in conanrun env (PATH includes installed bin/)
set -eu

NAME=instead
BIN_DIR="${CONAN_BINDIR:-/storage/Users/currentUser/usr/local/bin}"
BIN="${BIN_DIR}/sdl-instead"

echo "[test] locate ${BIN}"
if [ ! -x "${BIN}" ]; then
    echo "❌ ${BIN} not found or not executable"
    exit 1
fi

echo "[test] ${NAME} --version"
if "${BIN}" --version > /dev/null 2>&1; then
    VERSION=$("${BIN}" --version 2>&1 | head -1 | tr -d '\r')
    echo "✅ ${NAME} --version OK: ${VERSION}"
else
    echo "[test] --version returned non-zero, falling back to --help"
    "${BIN}" --help > /dev/null 2>&1 && echo "✅ ${NAME} --help OK" || {
        echo "❌ ${NAME} failed both --version and --help"
        exit 1
    }
fi

echo "[test] ${NAME} executed successfully on OpenHarmony PC"
