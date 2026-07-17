cmake_minimum_required(VERSION 3.15)
project(test_onnx CXX)

find_package(ONNX REQUIRED)

add_executable(test_onnx test.cpp)
target_link_libraries(test_onnx ONNX::onnx)

set_target_properties(test_onnx PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_onnx COMMAND test_onnx)
