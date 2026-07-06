cmake_minimum_required(VERSION 3.15)
project(test_bluez-alsa C)

# Find the package via Conan-generated CMakeDeps
find_package(bluez-alsa REQUIRED)

add_executable(test_bluez-alsa test.c)
target_link_libraries(test_bluez-alsa bluez-alsa::bluez-alsa)

enable_testing()
add_test(NAME test_bluez-alsa COMMAND test_bluez-alsa)
