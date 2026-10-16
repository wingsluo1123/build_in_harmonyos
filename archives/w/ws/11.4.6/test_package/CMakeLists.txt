cmake_minimum_required(VERSION 3.15)
project(test_ws CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The ws package exports the ws::ws CMake target (conan CMakeDeps).
find_package(ws REQUIRED CONFIG)

add_executable(test_ws test_ws.cpp)
target_link_libraries(test_ws PRIVATE ws::ws)

enable_testing()
add_test(NAME test_ws COMMAND test_ws)
