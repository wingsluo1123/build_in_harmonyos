#!/system/bin/sh
# test_package/test.sh — Test wrapper for chezscheme
# R34: test substantively depends on the chezscheme package binary
# Called by conanfile.py test() method
#
# Usage: test.sh <scheme_binary_path>
# Exit: 0 = pass, non-0 = fail

SCHEME_BIN="${1:-scheme}"

# T1: Version check
"$SCHEME_BIN" --version || exit 1

# T2: Arithmetic test — verify scheme interpreter runs correctly
TMPSS="${TMPDIR:-$HOME/tmp}/chezscheme_test_$$.ss"
mkdir -p "$(dirname "$TMPSS")" 2>/dev/null
echo '(display (+ 1 2))(newline)' > "$TMPSS"
"$SCHEME_BIN" --script "$TMPSS" | grep -q "3" || { rm -f "$TMPSS"; exit 1; }
rm -f "$TMPSS"
