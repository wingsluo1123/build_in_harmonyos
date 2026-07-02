cmake_minimum_required(VERSION 3.15)

# E092 fix: Force CMake to treat this as a Linux target
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

project(test_qalculate_gtk CXX)

# System dependencies (gmp, mpfr, libxml2, etc.) are pre-installed
# in ~/usr/local — needed because libqalculate headers include <gmp.h> etc.
include_directories($ENV{HOME}/usr/local/include)
link_directories($ENV{HOME}/usr/local/lib)

# Find qalculate-gtk package (brings libqalculate transitively)
find_package(qalculate-gtk REQUIRED)
# Also find libqalculate directly for header include and linking
find_package(libqalculate REQUIRED)

add_executable(test_qalculate_gtk test.cpp)
# Link against libqalculate which is brought in as a transitive dependency
target_link_libraries(test_qalculate_gtk libqalculate::libqalculate)

enable_testing()
add_test(NAME test_qalculate_gtk COMMAND test_qalculate_gtk)
