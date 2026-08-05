#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for cargo-c executables
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] cargo-capi --version"
cargo-capi --version && echo "OK: cargo-capi --version" || {
    echo "[test] cargo-capi --version failed, trying --help..."
    cargo-capi --help > /dev/null 2>&1 && echo "OK: cargo-capi --help" || {
        echo "FAIL: cargo-capi failed both --version and --help"
        exit 1
    }
}

echo "[test] cargo-cbuild --version"
cargo-cbuild --version && echo "OK: cargo-cbuild --version" || {
    echo "[test] cargo-cbuild --version failed, trying --help..."
    cargo-cbuild --help > /dev/null 2>&1 && echo "OK: cargo-cbuild --help" || {
        echo "FAIL: cargo-cbuild failed both --version and --help"
        exit 1
    }
}

echo "[test] cargo-cinstall --version"
cargo-cinstall --version && echo "OK: cargo-cinstall --version" || {
    echo "[test] cargo-cinstall --version failed, trying --help..."
    cargo-cinstall --help > /dev/null 2>&1 && echo "OK: cargo-cinstall --help" || {
        echo "FAIL: cargo-cinstall failed both --version and --help"
        exit 1
    }
}

echo "[test] cargo-ctest --version"
cargo-ctest --version && echo "OK: cargo-ctest --version" || {
    echo "[test] cargo-ctest --version failed, trying --help..."
    cargo-ctest --help > /dev/null 2>&1 && echo "OK: cargo-ctest --help" || {
        echo "FAIL: cargo-ctest failed both --version and --help"
        exit 1
    }
}

echo "All cargo-c binary tests passed"
