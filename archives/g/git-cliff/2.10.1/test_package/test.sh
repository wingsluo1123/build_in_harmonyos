#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for git-cliff executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

# Ensure system libraries are resolvable (OHOS lazy-loads some NEEDED libs)
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:/system/lib64:/system/lib:/lib:/data/service/hnp/lib"

echo "[step] git-cliff --version"
git-cliff --version 2>&1 && echo "        [ok] --version OK" || {
    echo "[step] --version failed (exit $?), trying --help..."
    git-cliff --help 2>&1 > /dev/null && echo "        [ok] --help OK" || {
        echo "        [fail] git-cliff failed both --version and --help"
        echo "[step] Binary location: $(which git-cliff 2>/dev/null || echo 'not in PATH')"
        echo "[step] File info: $(file "$(which git-cliff 2>/dev/null)" 2>/dev/null || echo 'N/A')"
        exit 1
    }
}
