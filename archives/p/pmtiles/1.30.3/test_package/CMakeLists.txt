cmake_minimum_required(VERSION 3.15)
project(test_pmtiles C)

# Find the package via Conan-generated CMakeDeps
find_package(pmtiles REQUIRED)

add_executable(test_pmtiles test.c)
target_link_libraries(test_pmtiles pmtiles::pmtiles)

enable_testing()
add_test(NAME test_pmtiles COMMAND test_pmtiles)
