#!/bin/bash
# test_package/test.sh -- ocaml-compiler-libs 0.12.4 consumer test (L0c test source)
set -eu

LIB_DIR="${1:?usage: test.sh <lib_dir> <ocaml_lib> <ocaml_bin>}"
OCAML_LIB="${2:?}"
OCAML_BIN="${3:?}"

export OCAMLLIB="$OCAML_LIB"
export CAML_LD_LIBRARY_PATH="$OCAML_LIB/stublibs"
export PATH="$OCAML_BIN:$PATH"
export OCAMLPATH="$(dirname "$(dirname "$LIB_DIR")")"
CL_DIR="$OCAML_LIB/compiler-libs"

cd "$(dirname "$0")"

echo "=== artifact presence check ==="
for a in META common/ocaml_common.cma common/ocaml_common.cmxa \
         common/ocaml_common.cmxs common/ocaml_common.a \
         bytecomp/ocaml_bytecomp.cmxa shadow/ocaml_shadow.cma \
         toplevel/ocaml_toplevel.cmxa; do
    if [ ! -f "$LIB_DIR/$a" ]; then
        echo "ERROR: package missing artifact: $LIB_DIR/$a" >&2
        exit 1
    fi
done
echo "artifacts: OK (8/8)"

echo "=== bytecode compile (compile-only) ==="
ocamlc -I "$LIB_DIR/common" -I "$CL_DIR" -c test_ocl.ml
echo "bytecode compile: OK"

echo "=== native compile + run (Parsetree build/print/parse + Longident) ==="
ocamlopt -I "$LIB_DIR/common" -I "$CL_DIR" \
         "$LIB_DIR/common/ocaml_common.cmxa" "$CL_DIR/ocamlcommon.cmxa" \
         -o test_ocl.exe test_ocl.ml
OUT="$(./test_ocl.exe)"
printf "%s\n" "$OUT"
case "$OUT" in
    *"ALL TESTS PASSED"*) ;;
    *) echo "ERROR: expected \"ALL TESTS PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== HarmonyOS e2e consumer case (file I/O -> Parse -> Pprintast) ==="
ocamlopt -I "$LIB_DIR/common" -I "$CL_DIR" \
         "$LIB_DIR/common/ocaml_common.cmxa" "$CL_DIR/ocamlcommon.cmxa" \
         -o test_ohos_e2e.exe test_ohos_e2e.ml
E2E_OUT="$(./test_ohos_e2e.exe)"
printf "%s\n" "$E2E_OUT"
case "$E2E_OUT" in
    *"ALL OHOS E2E PASSED"*) ;;
    *) echo "ERROR: expected \"ALL OHOS E2E PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== All tests passed ==="
