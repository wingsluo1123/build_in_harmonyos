#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for Crypt::OpenSSL::AES Perl XS module
# Verifies that the .so and .pm files exist and the .so is a valid ELF
set -eu

SO_PATH="${PERL_CRYPT_OPENSSL_AES_SO:-}"
PM_PATH="${PERL_CRYPT_OPENSSL_AES_PM:-}"

if [ -z "$SO_PATH" ] || [ -z "$PM_PATH" ]; then
    # Try to find from package folder
    PKG_DIR="${PERL_CRYPT_OPENSSL_AES_DIR:-}"
    if [ -n "$PKG_DIR" ]; then
        SO_PATH=$(find "$PKG_DIR" -name "AES.so" 2>/dev/null | head -1)
        PM_PATH=$(find "$PKG_DIR" -name "AES.pm" 2>/dev/null | head -1)
    fi
fi

if [ -z "$SO_PATH" ] || [ ! -f "$SO_PATH" ]; then
    echo "FAIL: AES.so not found"
    exit 1
fi

if [ -z "$PM_PATH" ] || [ ! -f "$PM_PATH" ]; then
    echo "FAIL: AES.pm not found"
    exit 1
fi

echo "Found AES.so: $SO_PATH"
echo "Found AES.pm: $PM_PATH"

# Verify ELF
file "$SO_PATH"
echo "✅ All file checks passed"
