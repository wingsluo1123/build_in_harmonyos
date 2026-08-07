cmake_minimum_required(VERSION 3.15)
project(test_openimageio CXX)

find_package(OpenImageIO REQUIRED CONFIG)

add_executable(test_openimageio src/test.cpp)
target_link_libraries(test_openimageio PRIVATE OpenImageIO::OpenImageIO)
set_target_properties(test_openimageio PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_openimageio COMMAND test_openimageio)
