#include <wx/init.h>
#include <wxlua/wxlua.h>
#include <cstdio>
int main() {
    wxInitializer init;
    if (!init.IsOk()) return 1;
    wxLuaState state;
    if (!state.Create() || !state.Ok()) return 2;
    if (state.RunString("value = 6 * 7") != 0) return 3;
    lua_State* lua = state.GetLuaState();
    lua_getglobal(lua, "value");
    if (lua_tointeger(lua, -1) != 42) return 4;
    lua_pop(lua, 1);
    if (state.RunString("this is invalid lua") == 0) return 5;
    std::puts("WXLUA_CPP_PASS 4");
    return 0;
}
