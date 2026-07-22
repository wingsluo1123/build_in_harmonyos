cmake_minimum_required(VERSION 3.15)
project(test_sdl3_image C)

# Find the package via Conan-generated CMakeDeps
find_package(sdl3_image REQUIRED)

add_executable(test_sdl3_image test.c)
target_link_libraries(test_sdl3_image sdl3_image::sdl3_image)

enable_testing()
add_test(NAME test_sdl3_image COMMAND test_sdl3_image)
