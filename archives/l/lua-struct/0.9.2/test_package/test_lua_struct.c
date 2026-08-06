#include <lua.h>
#include <lualib.h>
#include <lauxlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    lua_State *L = luaL_newstate();
    if (!L) {
        fprintf(stderr, "Failed to create lua state\n");
        return 1;
    }
    luaL_openlibs(L);

    /* LUA_PATH is set by the lua-struct package via runenv_info */
    const char *lua_path = getenv("LUA_PATH");
    if (!lua_path) {
        fprintf(stderr, "LUA_PATH not set\n");
        lua_close(L);
        return 1;
    }

    /* Apply LUA_PATH so require("struct") resolves to the package file */
    lua_getglobal(L, "package");
    lua_pushstring(L, lua_path);
    lua_setfield(L, -2, "path");
    lua_pop(L, 1);

    const char *script =
        "local struct = require('struct')\n"
        "assert(struct, 'require struct failed')\n"
        "\n"
        "local packed = struct.pack('<I', 12345)\n"
        "local unpacked = struct.unpack('<I', packed)\n"
        "assert(unpacked == 12345, 'pack/unpack <I failed: got ' .. tostring(unpacked))\n"
        "\n"
        "local s1, s2 = 'hello', 'world'\n"
        "local p = struct.pack('<ss', s1, s2)\n"
        "local u1, u2 = struct.unpack('<ss', p)\n"
        "assert(u1 == s1 and u2 == s2, 'pack/unpack <ss failed')\n"
        "\n"
        "local val = -3200\n"
        "p = struct.pack('<h', val)\n"
        "u1 = struct.unpack('<h', p)\n"
        "assert(u1 == val, 'pack/unpack <h failed')\n"
        "\n"
        "val = 255\n"
        "p = struct.pack('<B', val)\n"
        "u1 = struct.unpack('<B', p)\n"
        "assert(u1 == val, 'pack/unpack <B failed')\n"
        "\n"
        "val = -1\n"
        "p = struct.pack('<b', val)\n"
        "u1 = struct.unpack('<b', p)\n"
        "assert(u1 == val, 'pack/unpack <b failed')\n"
        "\n"
        "val = 123456789\n"
        "p = struct.pack('<I', val)\n"
        "u1 = struct.unpack('<I', p)\n"
        "assert(u1 == val, 'pack/unpack <I #2 failed')\n"
        "\n"
        "val = 1.56789\n"
        "p = struct.pack('<d', val)\n"
        "u1 = struct.unpack('<d', p)\n"
        "assert(u1 == val, 'pack/unpack <d failed')\n"
        "\n"
        "print('All lua-struct tests passed.')\n";

    if (luaL_dostring(L, script) != LUA_OK) {
        fprintf(stderr, "Test failed: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
    }

    lua_close(L);
    return 0;
}
