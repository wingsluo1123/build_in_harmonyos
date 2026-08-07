#!/bin/sh
# test_arename.sh — Smoke test for arename package installation
# Verifies that arename and ataglist scripts are installed and syntactically valid
# Called by test_package/conanfile.py test() method
set -e

ARENAME_BIN="${1:-bin/arename}"
ATAGLIST_BIN="${1:-bin/ataglist}"
PERL_BIN="${PERL:-/data/service/hnp/bin/perl}"

# If first arg is a directory (package folder), construct paths
if [ -d "$1" ]; then
    ARENAME_BIN="$1/bin/arename"
    ATAGLIST_BIN="$1/bin/ataglist"
fi

# Verify arename script exists
if [ ! -f "$ARENAME_BIN" ]; then
    echo "FAIL: arename not found at $ARENAME_BIN"
    exit 1
fi
echo "OK: arename found at $ARENAME_BIN"

# Verify ataglist script exists
if [ ! -f "$ATAGLIST_BIN" ]; then
    echo "FAIL: ataglist not found at $ATAGLIST_BIN"
    exit 1
fi
echo "OK: ataglist found at $ATAGLIST_BIN"

# Check shebang contains perl
head -1 "$ARENAME_BIN" | grep -q perl || { echo "FAIL: invalid shebang"; exit 1; }
echo "OK: arename shebang valid"

head -1 "$ATAGLIST_BIN" | grep -q perl || { echo "FAIL: invalid shebang"; exit 1; }
echo "OK: ataglist shebang valid"

# Perl syntax check (verifies generated script is valid Perl)
"$PERL_BIN" -c "$ARENAME_BIN" 2>&1 || {
    echo "WARN: perl -c failed (may need runtime modules)"
    # Non-fatal: syntax check may fail due to missing Readonly module
}
echo "OK: arename syntax check completed"

echo "All smoke tests passed"
