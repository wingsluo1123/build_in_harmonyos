cmake_minimum_required(VERSION 3.15)
project(test_nanojsonc C)

# Find the package via Conan-generated CMakeDeps
find_package(nanojsonc REQUIRED)

add_executable(test_nanojsonc test.c)
target_link_libraries(test_nanojsonc PRIVATE nanojsonc::nanojsonc)

enable_testing()

# L1 consumer test: drive the event-driven parser on a real JSON document
add_test(NAME test_nanojsonc COMMAND test_nanojsonc)