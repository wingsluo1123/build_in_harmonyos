#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>

/*
 * Test program for lua-term.
 * Creates a Lua state, loads the term module, and tests isatty().
 * Requires LUA_CPATH and LUA_PATH to be set to include lua-term's
 * lib and res directories respectively.
 */

int main(void) {
    lua_State *L = luaL_newstate();
    if (!L) {
        fprintf(stderr, "FAIL: cannot create Lua state\n");
        return 1;
    }
    luaL_openlibs(L);

    /* Lua script: load 'term' module and call isatty() */
    const char *script =
        "local ok, err = pcall(require, 'term')\n"
        "if not ok then\n"
        "    print('FAIL: ' .. tostring(err))\n"
        "    os.exit(1)\n"
        "end\n"
        "local term = require 'term'\n"
        "if type(term.isatty) ~= 'function' then\n"
        "    print('FAIL: term.isatty is not a function')\n"
        "    os.exit(1)\n"
        "end\n"
        "local result = term.isatty(io.stdout)\n"
        "print('isatty: ' .. tostring(result))\n"
        "if type(result) ~= 'boolean' then\n"
        "    print('FAIL: isatty should return boolean')\n"
        "    os.exit(1)\n"
        "end\n"
        "print('PASS: lua-term module loaded and isatty() works')\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        fprintf(stderr, "FAIL: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    lua_close(L);
    return 0;
}
