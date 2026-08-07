#!/system/bin/sh
set -euo pipefail
# Test runner for MIME::Base32 Perl module
# Called by conanfile.py test() method
# Usage: sh test.sh <perl_lib_path>
perl_lib="$1"
perl -I"$perl_lib" "$(dirname "$0")/test.pl"
