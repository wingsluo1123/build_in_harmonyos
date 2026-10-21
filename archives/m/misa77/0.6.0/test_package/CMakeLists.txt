cmake_minimum_required(VERSION 3.15)
project(test_misa77 CXX)

# Find the package via Conan-generated CMakeDeps
find_package(misa77 REQUIRED)

add_executable(test_misa77 test.cpp)
target_link_libraries(test_misa77 misa77::misa77)

# HarmonyOS-specific test: verifies the NEON codec path and roundtrip
# integrity of the library as adapted for HarmonyOS PC (aarch64).
add_executable(test_misa77_harmonyos harmonyos_test.cpp)
target_link_libraries(test_misa77_harmonyos misa77::misa77)

enable_testing()
add_test(NAME test_misa77 COMMAND test_misa77)
add_test(NAME test_misa77_harmonyos COMMAND test_misa77_harmonyos)
