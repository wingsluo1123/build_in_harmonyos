cmake_minimum_required(VERSION 3.15)
project(test_libcsv C)

# Find the package via Conan-generated CMakeDeps
find_package(libcsv REQUIRED)

add_executable(test_libcsv test.c)
target_link_libraries(test_libcsv libcsv::libcsv)

enable_testing()
add_test(NAME test_libcsv COMMAND test_libcsv)
