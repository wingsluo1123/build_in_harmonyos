#!/bin/sh
# test_zarith.sh — Verify ZArith library is installed and functional
# Called by test_package/conanfile.py test() method
set -e

# 1. Verify zarith is findable via ocamlfind
echo "Checking ocamlfind can locate zarith..."
ocamlfind query zarith -format "%v"

# 2. Verify big integer arithmetic: 42 + 1 = 43
echo "Running big integer addition test (42 + 1 = 43)..."
ocamlfind ocaml -package zarith -linkpkg -e \
    'let () = let n = Z.add (Z.of_int 42) (Z.of_int 1) in assert (Z.to_int n = 43)'

echo "All tests passed."
