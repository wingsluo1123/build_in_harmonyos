#!/bin/bash
# test_package/test.sh -- ocaml-re 1.13.2 consumer test (L0c test source)
set -euo pipefail

LIB_DIR="${1:?usage: test.sh <lib_dir> <ocaml_lib> <ocaml_bin>}"
OCAML_LIB="${2:?}"
OCAML_BIN="${3:?}"

export OCAMLLIB="$OCAML_LIB"
export CAML_LD_LIBRARY_PATH="$OCAML_LIB/stublibs"
export PATH="$OCAML_BIN:$PATH"
export OCAMLPATH="$(dirname "$LIB_DIR")"

cd "$(dirname "$0")"

echo "=== artifact presence check ==="
for a in re.cma re.cmxa re.cmxs re.a re.cmi META \
         emacs/re_emacs.cmxa glob/re_glob.cmxa \
         pcre/re_pcre.cmxa str/re_str.cmxa; do
    if [ ! -f "$LIB_DIR/$a" ]; then
        echo "ERROR: package missing artifact: $LIB_DIR/$a" >&2
        exit 1
    fi
done
echo "artifacts: OK (10/10)"

echo "=== bytecode compile (compile-only, explicit cma linkage) ==="
ocamlc -I "$LIB_DIR" "$LIB_DIR/re.cma" -o /dev/null test_re.ml
echo "bytecode compile: OK"

echo "=== native compile + run (syntaxes, groups, split, replace, Str compat) ==="
ocamlopt -I "$LIB_DIR" "$LIB_DIR/re.cmxa" -o test_re.exe test_re.ml
OUT="$(./test_re.exe)"
printf "%s\n" "$OUT"
case "$OUT" in
    *"ALL TESTS PASSED"*) ;;
    *) echo "ERROR: expected \"ALL TESTS PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== HarmonyOS e2e consumer case (file I/O -> per-line regex -> aggregate) ==="
ocamlopt -I "$LIB_DIR" "$LIB_DIR/re.cmxa" \
         -o test_ohos_e2e.exe test_ohos_e2e.ml
E2E_OUT="$(./test_ohos_e2e.exe)"
printf "%s\n" "$E2E_OUT"
case "$E2E_OUT" in
    *"ALL OHOS E2E PASSED"*) ;;
    *) echo "ERROR: expected \"ALL OHOS E2E PASSED\" in output" >&2; exit 1 ;;
esac

echo "=== All tests passed ==="
