cmake_minimum_required(VERSION 3.15)

# Force CMake to treat this as a Linux cross-compile target (E092 fix)
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

project(test_libqalculate CXX)

# System dependencies (gmp, mpfr, libxml2, readline) are pre-installed
# in ~/usr/local — needed because libqalculate headers include <gmp.h> etc.
include_directories($ENV{HOME}/usr/local/include)
link_directories($ENV{HOME}/usr/local/lib)

# Find the package via Conan-generated CMakeDeps
find_package(libqalculate REQUIRED)

add_executable(test_libqalculate test.cpp)
target_link_libraries(test_libqalculate libqalculate::libqalculate)

enable_testing()
add_test(NAME test_libqalculate COMMAND test_libqalculate)
