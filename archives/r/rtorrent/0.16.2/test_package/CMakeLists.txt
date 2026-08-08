cmake_minimum_required(VERSION 3.15)
project(test_rtorrent C)

# Find the package via Conan-generated CMakeDeps
find_package(rtorrent REQUIRED)

add_executable(test_rtorrent test.c)
target_link_libraries(test_rtorrent rtorrent::rtorrent)

enable_testing()
add_test(NAME test_rtorrent COMMAND test_rtorrent)
