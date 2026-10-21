#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>
#include <stdio.h>
int main(void) {
    lua_State* state = luaL_newstate();
    if (!state) return 1;
    luaL_openlibs(state);
    if (luaL_dostring(state, "local wx = require('wx'); assert(wx.wxString('module'):GetData() == 'module')")) {
        fprintf(stderr, "%s\n", lua_tostring(state, -1));
        return 2;
    }
    puts("WXLUA_MODULE_PASS");
    lua_close(state);
    return 0;
}
