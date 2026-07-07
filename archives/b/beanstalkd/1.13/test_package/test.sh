#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for beanstalkd executable
set -eu

echo "[test] beanstalkd --version"
beanstalkd --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    beanstalkd --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: beanstalkd failed both --version and --help"
        exit 1
    }
}
