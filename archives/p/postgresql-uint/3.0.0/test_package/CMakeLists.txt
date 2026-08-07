cmake_minimum_required(VERSION 3.15)
project(test_postgresql_uint C)

# Find the package via Conan-generated CMakeDeps
find_package(postgresql-uint REQUIRED)

# Compile the test that verifies the .so binary
add_executable(test_postgresql_uint test.c)
target_link_libraries(test_postgresql_uint ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_postgresql_uint COMMAND test_postgresql_uint)
