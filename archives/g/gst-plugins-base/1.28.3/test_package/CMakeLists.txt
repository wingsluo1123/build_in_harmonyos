cmake_minimum_required(VERSION 3.15)
project(test_gst_plugins_base C)

# Find the package via Conan-generated CMakeDeps
find_package(gst-plugins-base REQUIRED)

add_executable(test_gst_plugins_base test.c)
target_link_libraries(test_gst_plugins_base gst-plugins-base::gst-plugins-base)

enable_testing()
add_test(NAME test_gst_plugins_base COMMAND test_gst_plugins_base)
