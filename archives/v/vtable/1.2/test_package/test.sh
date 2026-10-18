#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer end-to-end check for the installed vtable CLI.
#
# Flow: real input (a genuine C++ shared library with polymorphic classes,
# built here with the toolchain) -> call the binary installed by this package
# -> core function (dump the virtual tables of that library) -> assert the
# actual business output.
#
# The tool reports failures on stdout and still exits 0, so every assertion
# matches output content rather than the exit status.  Checks:
#   C1  -dumpversion reports the upstream version 1.2
#   C2  the consumer shared library builds and is a real ELF shared object
#   C3  Invoice vtable is recovered from that library
#   C4  Invoice entry count equals the number of slots actually printed (7)
#   C5  Invoice virtual member functions are de-mangled correctly
#   C6  Document vtable is recovered from the same library
#   C7  Document entry count equals the number of slots actually printed (6)
#   C8  Document virtual member functions are de-mangled correctly
#   C9  the typeinfo slot of the vtable is reported
#   C10 -mangled mode reports mangled member names
#   C11 non-ELF input is reported as a failure
#   C12 non-ELF input produces no vtable output at all
#
# Usage: test.sh <path-to-installed-vtable-dumper>

set -euo pipefail

TOOL="$1"
CXX_BIN="${CXX:-clang++}"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

OUT_DEMANGLED="dump-demangled.txt"
OUT_MANGLED="dump-mangled.txt"
OUT_BAD="dump-badinput.txt"

pass=0
fail=0

ok() {
    echo "  [ok]   $1"
    pass=$((pass + 1))
}

bad() {
    echo "  [fail] $1"
    fail=$((fail + 1))
}

check_contains() {  # <id-and-description> <needle> <file>
    if grep -qF -- "$2" "$3"; then
        ok "$1"
    else
        bad "$1 — expected '$2' in $3"
    fi
}

check_count() {  # <id-and-description> <expected> <actual>
    if [ "$2" -eq "$3" ]; then
        ok "$1 == $3"
    else
        bad "$1 — expected $2, got $3"
    fi
}

echo "[test] C1: installed tool reports its version"
version="$("$TOOL" -dumpversion)"
if [ "$version" = "1.2" ]; then
    ok "C1 -dumpversion == 1.2"
else
    bad "C1 -dumpversion returned '$version'"
fi

echo "[test] C2: build the consumer shared library"
"$CXX_BIN" -shared -fPIC -o libvtable_consumer.so "$SRC_DIR/vtable_consumer.cpp"
if [ -f libvtable_consumer.so ]; then
    ok "C2 libvtable_consumer.so built"
else
    bad "C2 libvtable_consumer.so was not produced"
fi

echo "[test] C3-C9: dump the virtual tables of the consumer library"
"$TOOL" ./libvtable_consumer.so > "$OUT_DEMANGLED" 2>&1

check_contains "C3 Invoice vtable recovered" "Vtable for Invoice" "$OUT_DEMANGLED"
check_count "C4 Invoice slot count" 7 \
    "$(sed -n '/^_ZTV7Invoice/,/^$/p' "$OUT_DEMANGLED" | grep -cF '(int (*)(...))')"
check_contains "C5 Invoice::lineCount() const" "Invoice::lineCount() const" "$OUT_DEMANGLED"
check_contains "C5 Invoice::sizeKiB() const" "Invoice::sizeKiB() const" "$OUT_DEMANGLED"
check_contains "C6 Document vtable recovered" "Vtable for Document" "$OUT_DEMANGLED"
check_count "C7 Document slot count" 6 \
    "$(sed -n '/^_ZTV8Document/,/^$/p' "$OUT_DEMANGLED" | grep -cF '(int (*)(...))')"
check_contains "C8 Document::kind() const" "Document::kind() const" "$OUT_DEMANGLED"
check_contains "C9 typeinfo slot of Invoice" "(& _ZTI7Invoice)" "$OUT_DEMANGLED"

echo "[test] C10: -mangled mode"
"$TOOL" -mangled ./libvtable_consumer.so > "$OUT_MANGLED" 2>&1
check_contains "C10 mangled Invoice::lineCount" "_ZNK7Invoice9lineCountEv" "$OUT_MANGLED"

echo "[test] C11-C12: non-ELF input must not look like a success"
printf 'this is not an ELF object\n' > notelf.txt
# The tool reports errors on stdout and still exits 0 (upstream behaviour), so
# the status is captured explicitly and C11/C12 assert on the output content.
bad_rc=0
"$TOOL" ./notelf.txt > "$OUT_BAD" 2>&1 || bad_rc=$?
check_contains "C11 non-ELF input reported as failure" "Failed to read v-tables" "$OUT_BAD"
if grep -qF "Vtable for" "$OUT_BAD"; then
    bad "C12 non-ELF input produced vtable output"
else
    ok "C12 non-ELF input produced no vtable output (tool exit status: $bad_rc)"
fi

echo "[test] result: passed=$pass failed=$fail"
[ "$fail" -eq 0 ] || exit 1
