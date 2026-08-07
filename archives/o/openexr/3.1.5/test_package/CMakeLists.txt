cmake_minimum_required(VERSION 3.15)
project(test_openexr LANGUAGES CXX)

find_package(OpenEXR CONFIG REQUIRED)

add_executable(test_openexr src/test.cpp)
target_link_libraries(test_openexr PRIVATE OpenEXR::OpenEXR)

enable_testing()
add_test(NAME test_openexr COMMAND test_openexr)
