cmake_minimum_required(VERSION 3.15)
project(test_CLI11 CXX)

find_package(CLI11 REQUIRED)

add_executable(test_CLI11 test.cpp)
target_link_libraries(test_CLI11 CLI11::CLI11)

enable_testing()
add_test(NAME test_CLI11 COMMAND test_CLI11 --name OpenHarmony)
