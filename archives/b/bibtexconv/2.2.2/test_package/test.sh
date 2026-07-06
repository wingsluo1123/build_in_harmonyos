#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bibtexconv
set -eu

echo "[test] bibtexconv --version"
bibtexconv --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bibtexconv --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bibtexconv failed"
        exit 1
    }
}
