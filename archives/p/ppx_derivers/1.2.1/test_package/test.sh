#!/bin/bash
# test_package/test.sh -- ppx_derivers 1.2.1 consumer test (L0c test source)
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
for a in ppx_derivers.cma ppx_derivers.cmxa ppx_derivers.cmxs \
         ppx_derivers.a ppx_derivers.cmi META; do
    if [ ! -f "$LIB_DIR/$a" ]; then
        echo "ERROR: package missing artifact: $LIB_DIR/$a" >&2
        exit 1
    fi
done
echo "artifacts: OK (6/6)"

echo "=== bytecode compile (compile-only) ==="
ocamlc -I "$LIB_DIR" -c test_pd.ml
echo "bytecode compile: OK"

echo "=== native compile + run (register/lookup/derivers + negative controls) ==="
ocamlopt -I "$LIB_DIR" "$LIB_DIR/ppx_derivers.cmxa" -o test_pd.exe test_pd.ml
OUT="$(./test_pd.exe)"
printf "%s\n" "$OUT"
case "$OUT" in
    *"ALL TESTS PASSED"*) ;;
    *) echo "ERROR: expected \"ALL TESTS PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== HarmonyOS e2e consumer case (registry -> file -> read back) ==="
ocamlopt -I "$LIB_DIR" "$LIB_DIR/ppx_derivers.cmxa" -o test_ohos_e2e.exe test_ohos_e2e.ml
E2E_OUT="$(./test_ohos_e2e.exe)"
printf "%s\n" "$E2E_OUT"
case "$E2E_OUT" in
    *"ALL OHOS E2E PASSED"*) ;;
    *) echo "ERROR: expected \"ALL OHOS E2E PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== All tests passed ==="
