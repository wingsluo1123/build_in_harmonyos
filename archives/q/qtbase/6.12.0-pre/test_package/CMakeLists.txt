cmake_minimum_required(VERSION 3.16)
project(test_qtbase CXX)

# R34: 实质调用 Qt6::Core API
find_package(Qt6 REQUIRED COMPONENTS Core CONFIG)

add_executable(test_qtbase src/test_qtbase.cpp)
target_link_libraries(test_qtbase PRIVATE Qt6::Core)

enable_testing()
add_test(NAME qtbase_core_link COMMAND test_qtbase)
