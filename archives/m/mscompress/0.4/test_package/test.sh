#!/bin/sh
# test.sh — mscompress 0.4 round-trip verification (HarmonyOS aarch64)
set -e

TMP="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMP"
WORKDIR="$TMP/mscompress-test.$$"
mkdir -p "$WORKDIR"
trap 'rm -rf "$WORKDIR"' EXIT

# Sample payload: text containing runs of identical bytes (LZ77-friendly)
cat > "$WORKDIR/test.txt" <<'EOF'
HarmonyOS PC mscompress round-trip test payload.
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
0123456789 0123456789 0123456789 0123456789 0123456789
EOF

cd "$WORKDIR"

# 1) compress
mscompress test.txt
[ -f test.txt_ ] || { echo "FAIL: mscompress did not produce test.txt_"; exit 1; }

# 2) expand back
msexpand < test.txt_ > test.new

# 3) round-trip must be byte-identical
cmp test.txt test.new || { echo "FAIL: round-trip mismatch"; exit 1; }

# 4) sanity: expanded file size matches input
sz_orig=$(wc -c < test.txt)
sz_new=$(wc -c < test.new)
[ "$sz_orig" = "$sz_new" ] || { echo "FAIL: size mismatch $sz_orig != $sz_new"; exit 1; }

echo "PASS: mscompress round-trip identical (${sz_orig} bytes)"
