#!/data/service/hnp/bin/bash
# test_package/test.sh — swirc executable tests
# Runs under conanrun env (PATH/ld path include the installed package).
# R34: genuinely exercises the tested package's binary; judged by exit code.
set -eu

echo "[test] L1 smoke: swirc --version"
printf 'N\n' | swirc --version
echo "OK: --version exits 0"

echo "[test] OHOS rule12 consumer e2e: swirc --help"
swirc --help
echo "OK: --help exits 0"
