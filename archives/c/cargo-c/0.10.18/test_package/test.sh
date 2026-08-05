#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for cargo-c executables
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] cargo-capi --version"
cargo-capi --version && echo "        [ok] cargo-capi --version" || {
    echo "        [fail] cargo-capi --version failed, trying --help..."
    cargo-capi --help > /dev/null 2>&1 && echo "        [ok] cargo-capi --help" || {
        echo "        [fail] cargo-capi failed both --version and --help"
        exit 1
    }
}

echo "[step] cargo-cbuild --version"
cargo-cbuild --version && echo "        [ok] cargo-cbuild --version" || {
    echo "        [fail] cargo-cbuild --version failed, trying --help..."
    cargo-cbuild --help > /dev/null 2>&1 && echo "        [ok] cargo-cbuild --help" || {
        echo "        [fail] cargo-cbuild failed both --version and --help"
        exit 1
    }
}

echo "[step] cargo-cinstall --version"
cargo-cinstall --version && echo "        [ok] cargo-cinstall --version" || {
    echo "        [fail] cargo-cinstall --version failed, trying --help..."
    cargo-cinstall --help > /dev/null 2>&1 && echo "        [ok] cargo-cinstall --help" || {
        echo "        [fail] cargo-cinstall failed both --version and --help"
        exit 1
    }
}

echo "[step] cargo-ctest --version"
cargo-ctest --version && echo "        [ok] cargo-ctest --version" || {
    echo "        [fail] cargo-ctest --version failed, trying --help..."
    cargo-ctest --help > /dev/null 2>&1 && echo "        [ok] cargo-ctest --help" || {
        echo "        [fail] cargo-ctest failed both --version and --help"
        exit 1
    }
}

echo "[step] All cargo-c binary tests passed"
