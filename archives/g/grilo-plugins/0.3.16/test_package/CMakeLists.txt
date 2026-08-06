cmake_minimum_required(VERSION 3.15)
project(test_grilo_plugins C)

# Find the package via Conan-generated CMakeDeps
find_package(grilo-plugins REQUIRED)

add_executable(test_grilo_plugins test.c)
target_link_libraries(test_grilo_plugins ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_grilo_plugins COMMAND test_grilo_plugins)
