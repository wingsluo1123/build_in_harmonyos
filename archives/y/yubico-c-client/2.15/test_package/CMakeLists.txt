cmake_minimum_required(VERSION 3.15)
project(test_yubico-c-client C)

# Find the package via Conan-generated CMakeDeps
find_package(yubico-c-client REQUIRED)

add_executable(test_yubico-c-client test.c)
target_link_libraries(test_yubico-c-client yubico-c-client::yubico-c-client)

enable_testing()
add_test(NAME test_yubico-c-client COMMAND test_yubico-c-client)
