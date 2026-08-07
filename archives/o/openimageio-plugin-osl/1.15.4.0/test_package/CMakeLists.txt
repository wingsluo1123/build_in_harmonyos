cmake_minimum_required(VERSION 3.15)
project(test_openimageio_plugin_osl CXX)

# Find the package via Conan-generated CMakeDeps
find_package(openimageio-plugin-osl REQUIRED)

add_executable(test_openimageio_plugin_osl test.cpp)
target_link_libraries(test_openimageio_plugin_osl openimageio-plugin-osl::openimageio-plugin-osl)

enable_testing()
add_test(NAME test_openimageio_plugin_osl COMMAND test_openimageio_plugin_osl)
