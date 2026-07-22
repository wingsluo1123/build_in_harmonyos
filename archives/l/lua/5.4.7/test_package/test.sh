#!/data/service/hnp/bin/bash
# test_package/test.sh — R34 smoke + API smoke for Lua 5.4.7
# R34: real consumer exercise.
# Strategy:
#   - The conan-installed package location is passed in via
#     ${LUA_PACKAGE_FOLDER} (set by conanfile.py::test()).
#   - We exec lua/luac from <pkg>/bin and link test_lua.c against <pkg>/lib/liblua.a
#     to avoid relying on VirtualRunEnv PATH injection (which can be flaky
#     for library-typed packages on conan 2.29).
set -eu

: "${LUA_PACKAGE_FOLDER:?LUA_PACKAGE_FOLDER must be set by test_package conanfile.py}"
LUA_BIN="${LUA_PACKAGE_FOLDER}/bin/lua"
LUAC_BIN="${LUA_PACKAGE_FOLDER}/bin/luac"
LUA_LIB="${LUA_PACKAGE_FOLDER}/lib/liblua.a"
LUA_INC="${LUA_PACKAGE_FOLDER}/include"

echo "[test] package folder: ${LUA_PACKAGE_FOLDER}"

# ─── Assertion 1: lua binary present
if [ ! -x "${LUA_BIN}" ]; then
    echo "❌ lua binary missing at ${LUA_BIN}"; exit 1
fi
echo "✅ lua binary present at ${LUA_BIN}"

# ─── Assertion 2: luac binary present
if [ ! -x "${LUAC_BIN}" ]; then
    echo "❌ luac binary missing at ${LUAC_BIN}"; exit 1
fi
echo "✅ luac binary present at ${LUAC_BIN}"

# ─── Assertion 3: liblua.a present
if [ ! -f "${LUA_LIB}" ]; then
    echo "❌ liblua.a missing at ${LUA_LIB}"; exit 1
fi
echo "✅ liblua.a present at ${LUA_LIB}"

# ─── Assertion 4: lua -v reports Lua 5.4
V_OUTPUT=$("${LUA_BIN}" -v 2>&1)
echo "[lua -v] ${V_OUTPUT}"
case "${V_OUTPUT}" in
    *Lua\ 5.4*) echo "✅ lua -v reports Lua 5.4" ;;
    *) echo "❌ lua -v did not report Lua 5.4: ${V_OUTPUT}"; exit 1 ;;
esac

# ─── Assertion 5: luac -v reports Lua 5.4
LUAC_V=$("${LUAC_BIN}" -v 2>&1)
echo "[luac -v] ${LUAC_V}"
case "${LUAC_V}" in
    *Lua\ 5.4*) echo "✅ luac -v reports Lua 5.4" ;;
    *) echo "❌ luac -v did not report Lua 5.4: ${LUAC_V}"; exit 1 ;;
esac

# ─── Assertion 6: C API smoke
# /tmp is read-only on HMDFS — use the conan test_package build folder.
TMPDIR="$(pwd)/.lua-test-$$"
mkdir -p "${TMPDIR}"
trap 'rm -rf "${TMPDIR}"' EXIT

cat > "${TMPDIR}/test_lua.c" <<'EOF'
#include <stdio.h>
#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>
int main(void) {
    lua_State *L = luaL_newstate();
    if (!L) { fprintf(stderr, "luaL_newstate failed\n"); return 1; }
    luaL_openlibs(L);
    lua_pushinteger(L, 42);
    if (!lua_isinteger(L, -1)) { fprintf(stderr, "push 42 not int\n"); return 1; }
    if (lua_tointeger(L, -1) != 42) { fprintf(stderr, "value roundtrip fail\n"); return 1; }
    if (luaL_dostring(L, "return 6*7") != LUA_OK) {
        fprintf(stderr, "eval failed: %s\n", lua_tostring(L, -1));
        return 1;
    }
    if (!lua_isinteger(L, -1) || lua_tointeger(L, -1) != 42) {
        fprintf(stderr, "VM roundtrip fail\n");
        return 1;
    }
    lua_close(L);
    return 0;
}
EOF

echo "[test] compile test_lua.c against ${LUA_LIB}"
clang -std=c99 -O2 \
    -I"${LUA_INC}" \
    -o "${TMPDIR}/test_lua" \
    "${TMPDIR}/test_lua.c" \
    "${LUA_LIB}" \
    -lm -ldl

echo "[test] run test_lua binary"
"${TMPDIR}/test_lua"
echo "✅ Lua 5.4 API smoke test passed (state alloc, push integer, eval, close)"