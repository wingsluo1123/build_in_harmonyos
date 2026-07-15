cmake_minimum_required(VERSION 3.15)
project(test_avro C)

# Find the package via Conan-generated CMakeDeps
find_package(avro-c REQUIRED)

add_executable(test_avro test.c)
target_link_libraries(test_avro avro-c::avro-c)

enable_testing()
add_test(NAME test_avro COMMAND test_avro)
