#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gnupg executables
set -eu

echo "[test] gpg --version"
gpg --version && echo "OK gpg --version OK" || {
    echo "[test] gpg --version failed, trying gpg --help..."
    gpg --help > /dev/null 2>&1 && echo "OK gpg --help OK" || {
        echo "FAIL gpg failed both --version and --help"
        exit 1
    }
}

echo "[test] gpgv --version"
gpgv --version && echo "OK gpgv --version OK" || {
    echo "[test] gpgv --version failed, trying gpgv --help..."
    gpgv --help > /dev/null 2>&1 && echo "OK gpgv --help OK"
}

echo "[test] gpgsm --version"
gpgsm --version && echo "OK gpgsm --version OK" || {
    echo "[test] gpgsm --version failed, trying gpgsm --help..."
    gpgsm --help > /dev/null 2>&1 && echo "OK gpgsm --help OK"
}
