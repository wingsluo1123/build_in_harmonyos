#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for abuild-rootbld (noarch meta-package)
# Verifies the runtime dependency contract for `abuild rootbld`.
set -eu

echo "[test] rootbld --version"
rootbld --version | head -1 && echo "OK"
echo "[test] bwrap present"
command -v bwrap >/dev/null && echo "OK"
echo "[test] envsubst present"
command -v envsubst >/dev/null && echo "OK"
echo "[test] abuild present"
command -v abuild >/dev/null && echo "OK"
