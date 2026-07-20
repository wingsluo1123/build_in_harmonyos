#!/bin/sh
# test_crypt_openssl_guess.sh — Shell wrapper for Perl test (satisfies CI L0c)
# Runs test_crypt_openssl_guess.pl with PERL5LIB from Conan runenv
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
perl "${SCRIPT_DIR}/test_crypt_openssl_guess.pl"
