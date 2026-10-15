#!/bin/bash
# test_package/test.sh -- sexplib0 0.17.0 consumer test (L0c test source)
set -eu

LIB_DIR="${1:?usage: test.sh <lib_dir> <ocaml_lib> <ocaml_bin>}"
OCAML_LIB="${2:?}"
OCAML_BIN="${3:?}"

export OCAMLLIB="$OCAML_LIB"
export CAML_LD_LIBRARY_PATH="$OCAML_LIB/stublibs"
export PATH="$OCAML_BIN:$PATH"
export OCAMLPATH="$(dirname "$(dirname "$LIB_DIR")")"

cd "$(dirname "$0")"

echo "=== artifact presence check ==="
for a in sexplib0.cma sexplib0.cmxa sexplib0.cmxs sexplib0.a \
         sexplib0.cmi sexplib0__Sexp.cmi sexplib0__Sexp_conv.cmi META; do
    if [ ! -f "$LIB_DIR/$a" ]; then
        echo "ERROR: package missing artifact: $LIB_DIR/$a" >&2
        exit 1
    fi
done
echo "artifacts: OK (8/8)"

echo "=== bytecode compile (compile-only, explicit cma linkage) ==="
ocamlc -I "$LIB_DIR" "$LIB_DIR/sexplib0.cma" -o /dev/null test_sexplib0.ml
echo "bytecode compile: OK"

echo "=== native compile + run (Sexp parse/print + Sexp_conv converters) ==="
ocamlopt -I "$LIB_DIR" "$LIB_DIR/sexplib0.cmxa" \
         -o test_sexplib0.exe test_sexplib0.ml
OUT="$(./test_sexplib0.exe)"
printf "%s\n" "$OUT"
case "$OUT" in
    *"ALL TESTS PASSED"*) ;;
    *) echo "ERROR: expected \"ALL TESTS PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== HarmonyOS e2e consumer case (file I/O -> parse -> query -> round-trip) ==="
ocamlopt -I "$LIB_DIR" "$LIB_DIR/sexplib0.cmxa" \
         -o test_ohos_e2e.exe test_ohos_e2e.ml
E2E_OUT="$(./test_ohos_e2e.exe)"
printf "%s\n" "$E2E_OUT"
case "$E2E_OUT" in
    *"ALL OHOS E2E PASSED"*) ;;
    *) echo "ERROR: expected \"ALL OHOS E2E PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== All tests passed ==="
