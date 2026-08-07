cmake_minimum_required(VERSION 3.15)
project(test_perl-moose C)

# Find the package via Conan-generated CMakeDeps
find_package(perl-moose REQUIRED)

add_executable(test_perl-moose test.c)
target_link_libraries(test_perl-moose perl-moose::perl-moose)

enable_testing()
add_test(NAME test_perl-moose COMMAND test_perl-moose)
