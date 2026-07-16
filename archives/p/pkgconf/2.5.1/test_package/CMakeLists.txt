cmake_minimum_required(VERSION 3.15)
project(test_pkgconf C)

# Find the package via Conan-generated CMakeDeps
find_package(pkgconf REQUIRED)

add_executable(test_pkgconf test.c)
target_link_libraries(test_pkgconf pkgconf::pkgconf)

# Static linking to avoid OHOS dynamic linker permission issues
target_link_options(test_pkgconf PRIVATE -static)

enable_testing()
add_test(NAME test_pkgconf COMMAND test_pkgconf)
