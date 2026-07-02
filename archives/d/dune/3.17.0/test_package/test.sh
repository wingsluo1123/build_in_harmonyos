#!/bin/sh
# test_package/test.sh -- Dune 3.17.0 consumer test
# Verifies dune binary is functional
set -e

DUNE_BIN="${1:-dune}"

echo "=== Dune version check ==="
"$DUNE_BIN" --version

echo "=== Dune build check ==="
TMPDIR=$(mktemp -d)
cd "$TMPDIR"
cat > dune-project << EOF
(lang dune 3.0)
(name test_project)
EOF
cat > test.ml << EOF
let () = print_endline "Hello from Dune!"
EOF
"$DUNE_BIN" build
echo "Build succeeded"

echo "=== All tests passed ==="
cd /
rm -rf "$TMPDIR"
