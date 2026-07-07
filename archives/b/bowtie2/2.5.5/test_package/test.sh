#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bowtie2 executable
set -eu

echo "[test] bowtie2 --version"
bowtie2 --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bowtie2 --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bowtie2 failed both --version and --help"
        exit 1
    }
}
