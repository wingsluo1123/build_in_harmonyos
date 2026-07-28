cmake_minimum_required(VERSION 3.15)
project(test_liquid-dsp C)

# Find the package via Conan-generated CMakeDeps
find_package(liquid-static REQUIRED)

add_executable(test_liquid-dsp test.c)
target_link_libraries(test_liquid-dsp liquid-dsp::liquid-dsp)

enable_testing()
add_test(NAME test_liquid-dsp COMMAND test_liquid-dsp)
