cmake_minimum_required(VERSION 3.15)
project(test_allegro C)

# Find the package via Conan-generated CMakeDeps
find_package(allegro REQUIRED)

add_executable(test_allegro test.c)
target_link_libraries(test_allegro allegro::allegro)

enable_testing()
add_test(NAME test_allegro COMMAND test_allegro)
