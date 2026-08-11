cmake_minimum_required(VERSION 3.15)
project(test_avahi C)

# Find the package via Conan-generated CMakeDeps
find_package(avahi REQUIRED)

add_executable(test_avahi test.c)
target_link_libraries(test_avahi avahi::avahi)

enable_testing()
add_test(NAME test_avahi COMMAND test_avahi)
