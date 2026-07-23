#!/bin/sh
# test.sh — AFL++ test_package smoke test
# Runs afl-fuzz --version and afl-cc --version to verify installed binaries
set -e

AFL_FUZZ="${1:-afl-fuzz}"
AFL_CC="${2:-afl-cc}"

"$AFL_FUZZ" --version
"$AFL_CC" --version
