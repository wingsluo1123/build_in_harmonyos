#!/bin/sh
# test_package/test.sh -- Menhir 20260209 consumer test
# Verifies menhir binary is functional and can generate parsers
set -e

MENHIR_BIN="${1:-menhir}"

echo "=== Menhir version check ==="
"$MENHIR_BIN" --version

echo "=== Parser generation test ==="
TMPDIR=$(mktemp -d)
cd "$TMPDIR"
cat > calc.mly << 'MENHIREOF'
%token <int> INT
%token PLUS EOF
%start <int> line
%%
line:
  | e = expr; EOF { e }
expr:
  | i = INT { i }
  | e1 = expr; PLUS; e2 = expr { e1 + e2 }
MENHIREOF
"$MENHIR_BIN" --explain calc.mly
echo "Parser generated successfully"

echo "=== All tests passed ==="
cd /
rm -rf "$TMPDIR"
