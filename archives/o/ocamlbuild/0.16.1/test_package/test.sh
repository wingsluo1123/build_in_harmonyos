#!/bin/sh
# test_package/test.sh — ocamlbuild 0.16.1 consumer test (L0c test source)
# POSIX sh on purpose: conan test() invokes it via `sh`. Failures are
# accumulated (no `set -e`) so every check is counted; the script exits
# non-zero at the end if any check failed.
# Usage: test.sh <pkg_dir> <ocaml_lib> <ocaml_bin> <find_lib> <find_bin> <shim> <cc>
set -u

PKG_DIR="${1:?}"; OCAML_LIB="${2:?}"; OCAML_BIN="${3:?}"
FIND_LIB="${4:?}"; FIND_BIN="${5:?}"; SHIM="${6:?}"; CC="${7:?}"

export OCAMLLIB="$OCAML_LIB"
export CAML_LD_LIBRARY_PATH="$OCAML_LIB/stublibs"
export OCAMLFIND_CONF="$SHIM/ocamlfind.conf"
export OCAMLPATH="$FIND_LIB:$OCAML_LIB"
export PATH="$SHIM:$OCAML_BIN:$FIND_BIN:$PATH"

cd "$(dirname "$0")"
ASSERT=0; FAIL=0
chk() {
    ASSERT=$((ASSERT + 1))
    if [ "$2" != "0" ]; then
        FAIL=$((FAIL + 1))
        echo "FAIL: $1"
    fi
}
run_last() {  # run_last <cmd...> -> OUT = last output line, RC = command rc
    OUT="$("$@" 2>&1)"; RC=$?
    OUT="$(printf '%s\n' "$OUT" | tail -1)"
}

echo "[step] artifact presence"
for a in bin/ocamlbuild bin/ocamlbuild.byte bin/ocamlbuild.native \
         lib/ocaml/ocamlbuild/META \
         lib/ocaml/ocamlbuild/ocamlbuildlib.cma \
         lib/ocaml/ocamlbuild/ocamlbuildlib.cmxa \
         lib/ocaml/ocamlbuild/ocamlbuildlib.a \
         lib/ocaml/ocamlbuild/signatures.cmi; do
    [ -f "$PKG_DIR/$a" ]; chk "artifact $a" $?
done

echo "[step] packaged ocamlbuild -version"
run_last "$PKG_DIR/bin/ocamlbuild" -version
V="$(printf '%s\n' "$OUT" | sed 's/.* //')"
[ "$V" = "0.16.1" ]; chk "version is 0.16.1 (got '$V')" $?

echo "[step] plain project (no findlib): native + bytecode"
rm -rf proj1; mkdir proj1; cd proj1
printf 'let () = print_endline "HELLO_OK"\n' > hello.ml
"$PKG_DIR/bin/ocamlbuild" -no-ocamlfind hello.native > build-native.log 2>&1; RC=$?
chk "ocamlbuild -no-ocamlfind hello.native" $RC
run_last ./hello.native
chk "run hello.native (signed ELF), rc=$RC" $RC
[ "$OUT" = "HELLO_OK" ]; chk "hello.native output" $?
"$PKG_DIR/bin/ocamlbuild" -no-ocamlfind hello.byte > build-byte.log 2>&1; RC=$?
chk "ocamlbuild -no-ocamlfind hello.byte" $RC
run_last ./hello.byte
chk "run hello.byte (fixed shebang), rc=$RC" $RC
[ "$OUT" = "HELLO_OK" ]; chk "hello.byte output" $?
cd ..

echo "[step] HarmonyOS e2e consumer case (findlib + device exec)"
rm -rf proj2; mkdir proj2; cd proj2
cat > strtest.ml <<'EOF'
let () =
  let re = Str.regexp "const\\.product\\.\\([a-z]+\\)" in
  let s = "const.product.name" in
  ignore (Str.search_forward re s 0);
  Printf.printf "FIND_E2E_OK %s\n" (Str.matched_group 1 s)
EOF
"$PKG_DIR/bin/ocamlbuild" -use-ocamlfind -package str strtest.native > build.log 2>&1; RC=$?
chk "ocamlbuild -use-ocamlfind -package str strtest.native" $RC
run_last ./strtest.native
chk "run findlib-built native on device, rc=$RC" $RC
[ "$OUT" = "FIND_E2E_OK name" ]; chk "findlib e2e output" $?
cd ..

echo "assertions=$ASSERT failures=$FAIL"
if [ "$FAIL" -ne 0 ]; then
    echo "test_package: ocamlbuild consumer tests FAILED" >&2
    exit 1
fi
echo "ALL TESTS PASSED"
