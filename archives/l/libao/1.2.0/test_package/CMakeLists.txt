cmake_minimum_required(VERSION 3.15)
project(test_libao C)

# Find the package via Conan-generated CMakeDeps
find_package(libao REQUIRED)

add_executable(test_libao test.c)
target_link_libraries(test_libao libao::libao m)

enable_testing()
add_test(NAME test_libao COMMAND test_libao "${CMAKE_CURRENT_BINARY_DIR}/ctest-out.wav")
