cmake_minimum_required(VERSION 3.15)
project(test_bibtexconv C)

# Find the package via Conan-generated CMakeDeps
find_package(bibtexconv REQUIRED)

add_executable(test_bibtexconv test.c)
target_link_libraries(test_bibtexconv bibtexconv::bibtexconv)

enable_testing()
add_test(NAME test_bibtexconv COMMAND test_bibtexconv)
