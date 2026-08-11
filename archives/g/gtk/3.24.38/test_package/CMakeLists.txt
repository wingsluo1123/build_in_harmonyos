cmake_minimum_required(VERSION 3.15)
project(test_gtk C)

# Find the package via Conan-generated CMakeDeps
find_package(gtk REQUIRED)

add_executable(test_gtk test.c)
target_link_libraries(test_gtk gtk::gtk)

enable_testing()
add_test(NAME test_gtk COMMAND test_gtk)
