#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bib-tool
set -eu

echo "[test] bib-tool --version"
bib-tool --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bib-tool --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bib-tool failed"
        exit 1
    }
}
