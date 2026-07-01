#!/system/bin/sh
# test_package/test.sh — smoke test for mdfried executable
# Runs in conanrun env (PATH includes installed bin/)
# Uses /system/bin/sh (mksh) for OHOS compatibility
set -eu

echo "[test] mdfried --version"
mdfried --version && echo "OK --version passed" || {
    echo "[test] --version failed, trying --help..."
    mdfried --help > /dev/null 2>&1 && echo "OK --help passed" || {
        echo "[WARN] mdfried failed both --version and --help"
        echo "[INFO] This may be an OHOS security restriction on new binaries (R7)"
        exit 1
    }
}
