#!/bin/bash
# test_package/test.sh -- cinaps 0.15.1 consumer test (L0c test source)
set -euo pipefail

BIN_DIR="${1:?usage: test.sh <bin_dir> <lib_dir> <ocaml_lib> <ocaml_bin>}"
LIB_DIR="${2:?}"
OCAML_LIB="${3:?}"
OCAML_BIN="${4:?}"

export OCAMLLIB="$OCAML_LIB"
export CAML_LD_LIBRARY_PATH="$OCAML_LIB/stublibs"
export PATH="$BIN_DIR:$OCAML_BIN:$PATH"

cd "$(dirname "$0")"
# best-effort cleanup of previous run leftovers (safe to fail)
rm -f ./*.corrected staged_*.ml staged_*.exe ./*.cmi ./*.cmx ./*.o 2>/dev/null || true

echo "=== artifact presence check ==="
for a in "$BIN_DIR/cinaps" "$LIB_DIR/META" \
         "$LIB_DIR/runtime/cinaps_runtime.cma" \
         "$LIB_DIR/runtime/cinaps_runtime.cmxa"; do
    if [ ! -f "$a" ]; then
        echo "ERROR: package missing artifact: $a" >&2
        exit 1
    fi
done
echo "artifacts: OK (4/4)"

echo "=== --help runs ==="
cinaps --help > help.out 2>&1
grep -q -- "-staged" help.out
echo "help: OK"

echo "=== staged generation + compile against packaged cinaps.runtime ==="
cinaps -staged staged_in.ml in_sync.ml
cinaps -staged staged_bad.ml out_of_sync.ml
ocamlopt -I "$LIB_DIR" -I "$LIB_DIR/runtime" "$OCAML_LIB/unix.cmxa" \
         "$LIB_DIR/runtime/cinaps_runtime.cmxa" staged_in.ml -o staged_in.exe
ocamlopt -I "$LIB_DIR" -I "$LIB_DIR/runtime" "$OCAML_LIB/unix.cmxa" \
         "$LIB_DIR/runtime/cinaps_runtime.cmxa" staged_bad.ml -o staged_bad.exe
echo "staged generation + compile: OK"

echo "=== in-sync file: evaluation driver must exit 0 ==="
./staged_in.exe > run_in.out 2>&1
echo "in-sync run: OK (exit 0)"

echo "=== negative control: corrupted expectation must be rejected ==="
if ./staged_bad.exe > run_bad.out 2>&1; then
    echo "ERROR: cinaps accepted an out-of-sync file" >&2
    exit 1
fi
if [ ! -f out_of_sync.ml.cinaps-corrected ]; then
    echo "ERROR: no out_of_sync.ml.cinaps-corrected produced" >&2
    exit 1
fi
grep -q "^toto$" out_of_sync.ml.cinaps-corrected
echo "negative control: OK (non-zero exit + corrected value regenerated)"

echo "=== All tests passed ==="
