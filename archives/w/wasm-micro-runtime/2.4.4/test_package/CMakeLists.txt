cmake_minimum_required(VERSION 3.15)
project(test_wasm C)

find_package(wasm-micro-runtime REQUIRED)

add_executable(test_wasm test.c)
target_link_libraries(test_wasm wasm-micro-runtime::wasm-micro-runtime)

enable_testing()
add_test(NAME test_wasm COMMAND test_wasm)
