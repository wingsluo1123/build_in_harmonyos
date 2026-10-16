cmake_minimum_required(VERSION 3.15)
project(test_libskia CXX)

# Find the package via Conan-generated CMakeDeps (target libskia::libskia).
find_package(libskia REQUIRED CONFIG)

add_executable(test_libskia test_skia.cpp)
target_link_libraries(test_libskia PRIVATE libskia::libskia)

# Consumer use case 2: raster -> PNG encode (bundled libpng integration).
add_executable(test_libskia2 test_skia2.cpp)
target_link_libraries(test_libskia2 PRIVATE libskia::libskia)

enable_testing()
add_test(NAME test_libskia COMMAND test_libskia)
add_test(NAME test_libskia2 COMMAND test_libskia2)
