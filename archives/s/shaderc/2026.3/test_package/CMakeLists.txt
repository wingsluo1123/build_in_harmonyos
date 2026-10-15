cmake_minimum_required(VERSION 3.15)
project(test_shaderc CXX)

# 通过 Conan 生成的 CMakeDeps 配置查找本包
find_package(shaderc REQUIRED)

add_executable(test_shaderc test.cpp)
target_link_libraries(test_shaderc shaderc::shaderc)

enable_testing()
add_test(NAME test_shaderc COMMAND test_shaderc)
