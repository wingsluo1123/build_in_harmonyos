cmake_minimum_required(VERSION 3.15)
project(test_lua_term C)

set(LUA_DIR "" CACHE PATH "Path to lua source directory")

add_executable(test_lua_term test.c)
target_include_directories(test_lua_term PRIVATE ${LUA_DIR})
target_link_libraries(test_lua_term ${LUA_DIR}/liblua.a dl m)
# Export all symbols so dlopen() in lua can resolve them in core.so
target_link_options(test_lua_term PRIVATE -Wl,-E)

enable_testing()
add_test(NAME test_lua_term COMMAND test_lua_term)
