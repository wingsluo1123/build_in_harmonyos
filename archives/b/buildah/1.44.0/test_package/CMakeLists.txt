cmake_minimum_required(VERSION 3.15)
project(test_buildah C)

# Find the package via Conan-generated CMakeDeps
find_package(buildah REQUIRED)

add_executable(test_buildah test.c)
target_link_libraries(test_buildah buildah::buildah)

enable_testing()
add_test(NAME test_buildah COMMAND test_buildah)
