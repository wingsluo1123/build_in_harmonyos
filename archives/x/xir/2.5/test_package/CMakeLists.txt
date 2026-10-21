cmake_minimum_required(VERSION 3.15)
project(test_xir CXX)

# xir 经 CMakeDeps 生成的 config 提供 xir::xir target
# （unilog 由 cpp_info.requires 传播，消费者无需直接依赖）
find_package(xir REQUIRED CONFIG)

add_executable(test_xir test.cpp)
target_link_libraries(test_xir PRIVATE xir::xir)
target_compile_features(test_xir PRIVATE cxx_std_17)
# 二进制放固定位置，供 conanfile.py test() 运行
set_target_properties(test_xir PROPERTIES
                      RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")

enable_testing()
add_test(NAME test_xir COMMAND test_xir)
