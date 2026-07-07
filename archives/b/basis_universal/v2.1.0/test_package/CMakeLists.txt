cmake_minimum_required(VERSION 3.15)
project(test_basis_universal C)

# Find the package via Conan-generated CMakeDeps
find_package(basis_universal REQUIRED)

add_executable(test_basis_universal test.c)
target_link_libraries(test_basis_universal basis_universal::basis_universal)

enable_testing()
add_test(NAME test_basis_universal COMMAND test_basis_universal)
