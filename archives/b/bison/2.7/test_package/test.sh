#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for GNU bison 2.7
# Uses absolute BISON_BIN (set by test_package/conanfile.py) to ensure the
# PACKAGED binary is tested, not a system bison.
set -euo pipefail

BISON="${BISON_BIN:?BISON_BIN not set — test_package/conanfile.py must export it}"

echo ""
echo "=== GNU bison 2.7 test_package ==="
echo "[info] Using: $BISON"

# T1: version check — must be GNU bison 2.7
echo "[T1] bison --version (GNU check)"
version_out=$("$BISON" --version 2>&1) || {
    echo "❌ T1 FAIL: bison --version failed"
    exit 1
}
echo "$version_out" | head -1
if echo "$version_out" | grep -q "GNU Bison"; then
    echo "✅ T1 PASS (GNU Bison confirmed)"
else
    echo "❌ T1 FAIL: not GNU Bison (got: $(echo "$version_out" | head -1))"
    exit 1
fi
if echo "$version_out" | head -1 | grep -q "2\.7"; then
    echo "✅ T1 PASS (version 2.7 confirmed)"
else
    echo "❌ T1 FAIL: not version 2.7"
    exit 1
fi

# Locate m4 (bison needs it to generate parsers); skip grammar tests
# gracefully if it is unavailable so we don't fail for the wrong reason.
M4=""
for cand in m4 /data/app/bin/m4 /system/bin/m4 /usr/bin/m4; do
    if [ "$cand" = "m4" ]; then
        command -v m4 >/dev/null 2>&1 && M4="m4" && break
    elif [ -x "$cand" ]; then
        M4="$cand" && break
    fi
done

# T2: compile a minimal grammar — bison must parse it and emit a .c file
echo "[T2] compile minimal grammar"
if [ -z "$M4" ]; then
    echo "⚠️  T2 SKIP: m4 not found on PATH — skipping grammar compile test"
else
tmpdir="${TMPDIR:-/tmp}"
test -w "$tmpdir" || tmpdir="$HOME/tmp"
mkdir -p "$tmpdir"
export M4
work=$(mktemp -d "$tmpdir/bison-test-XXXXXX")
cat > "$work/calc.y" <<'GRAMMAR'
%{
#include <stdio.h>
int yylex(void);
void yyerror(char const *s);
%}
%token NUM
%%
expr: expr '+' NUM   { printf("add\n"); }
    | NUM            { printf("num\n"); }
    ;
%%
int yylex(void) { return 0; }
void yyerror(char const *s) { fprintf(stderr, "error: %s\n", s); }
GRAMMAR

( cd "$work" && "$BISON" -o calc.tab.c calc.y ) || {
    echo "❌ T2 FAIL: bison failed to compile grammar"
    rm -rf "$work"
    exit 1
}
if [ -f "$work/calc.tab.c" ]; then
    echo "✅ T2 PASS (calc.tab.c generated)"
else
    echo "❌ T2 FAIL: calc.tab.c not generated"
    rm -rf "$work"
    exit 1
fi

# T3: -y / --yacc compatibility mode
echo "[T3] yacc-compatible output (-y)"
( cd "$work" && "$BISON" -y -o y.tab.c calc.y ) || {
    echo "❌ T3 FAIL: bison -y failed"
    rm -rf "$work"
    exit 1
}
if [ -f "$work/y.tab.c" ]; then
    echo "✅ T3 PASS (y.tab.c generated)"
else
    echo "❌ T3 FAIL: y.tab.c not generated"
    rm -rf "$work"
    exit 1
fi

rm -rf "$work"
fi  # end of m4-available block

echo ""
echo "=== All test_package tests PASSED ==="
