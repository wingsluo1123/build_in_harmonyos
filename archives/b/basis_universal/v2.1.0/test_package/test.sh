#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for basis_universal executable
set -eu

echo "[test] basis_universal --version"
basis_universal --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    basis_universal --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: basis_universal failed both --version and --help"
        exit 1
    }
}
