cmake_minimum_required(VERSION 3.15)
project(test_bibutils C)

# Find the package via Conan-generated CMakeDeps
find_package(bibutils REQUIRED)

add_executable(test_bibutils test.c)
target_link_libraries(test_bibutils bibutils::bibutils)

enable_testing()
add_test(NAME test_bibutils COMMAND test_bibutils)
