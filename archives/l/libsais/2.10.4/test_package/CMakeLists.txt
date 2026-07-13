cmake_minimum_required(VERSION 3.15)
project(test_libsais C)

# E092: HarmonyOS is unknown to CMake, project() resets library suffixes to empty
# Set them after project() so find_library can locate .a/.so files
if(NOT CMAKE_FIND_LIBRARY_SUFFIXES)
    set(CMAKE_FIND_LIBRARY_SUFFIXES ".a" ".so")
endif()

# libsais uses PREFIX "" so the library is libsais.a (no lib prefix)
# find_library defaults to looking for lib<name>.a, so we need to also search without prefix
list(APPEND CMAKE_FIND_LIBRARY_PREFIXES "")

# Find the package via Conan-generated CMakeDeps
find_package(libsais REQUIRED)

add_executable(test_libsais test.c)
target_link_libraries(test_libsais libsais::libsais)

enable_testing()
add_test(NAME test_libsais COMMAND test_libsais)
