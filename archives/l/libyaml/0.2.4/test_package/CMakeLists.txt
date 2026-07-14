cmake_minimum_required(VERSION 3.15)
project(test_libyaml C)

# Find the package via Conan-generated CMakeDeps
find_package(libyaml REQUIRED)

add_executable(test_libyaml test.c)
target_link_libraries(test_libyaml libyaml::libyaml)

enable_testing()
add_test(NAME test_libyaml COMMAND test_libyaml)
