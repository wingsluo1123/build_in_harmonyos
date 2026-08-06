#include <stdio.h>

#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

static void set_arg_table(lua_State *L, int argc, char **argv) {
    lua_createtable(L, argc, 1);
    for (int i = 0; i < argc; ++i) {
        lua_pushstring(L, argv[i]);
        lua_rawseti(L, -2, i);
    }
    lua_setglobal(L, "arg");
}

static int apply_tmpdir_tmpname(lua_State *L) {
    const char *script =
        "do\n"
        "  local tmpdir = os.getenv('TMPDIR')\n"
        "  if tmpdir and tmpdir ~= '' then\n"
        "    local counter = 0\n"
        "    local token = tostring({}):gsub('[^%w]', '')\n"
        "    os.tmpname = function()\n"
        "      counter = counter + 1\n"
        "      return tmpdir .. '/lua_' .. token .. '_' .. tostring(counter) .. '.tmp'\n"
        "    end\n"
        "  end\n"
        "end\n";
    return luaL_dostring(L, script);
}

int main(int argc, char **argv) {
    lua_State *L = luaL_newstate();
    if (L == NULL) {
        fputs("busted: failed to create Lua state\n", stderr);
        return 1;
    }

    luaL_openlibs(L);
    set_arg_table(L, argc, argv);

    if (apply_tmpdir_tmpname(L) != LUA_OK) {
        const char *message = lua_tostring(L, -1);
        fprintf(stderr, "busted: %s\n", message != NULL ? message : "failed to initialize tmpname override");
        lua_close(L);
        return 1;
    }

    if (luaL_dostring(L, "require('busted.runner')({ standalone = false })") != LUA_OK) {
        const char *message = lua_tostring(L, -1);
        fprintf(stderr, "busted: %s\n", message != NULL ? message : "unknown Lua error");
        lua_close(L);
        return 1;
    }

    lua_close(L);
    return 0;
}
