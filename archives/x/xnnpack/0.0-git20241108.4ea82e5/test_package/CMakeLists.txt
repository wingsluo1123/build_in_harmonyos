cmake_minimum_required(VERSION 3.15)

# 消费者用例：以"库的使用者"身份链接 XNNPACK 的安装产物。
# XNNPACK 的公开 API 是 C 头（include/xnnpack.h），本用例用 C++ 写以便
# 使用 CHECK 宏累计失败数（不用 assert，Release 下 NDEBUG 会让 assert 消失）。
project(xnnpack_consumer_test CXX)

# CMakeDeps 按 recipe 的组件结构生成 xnnpack-config.cmake，其中
# xnnpack::xnnpack 组件已经 requires 了 microkernels-prod / pthreadpool /
# cpuinfo / fxdiv，静态链接顺序由 conan 的组件拓扑保证。
find_package(xnnpack CONFIG REQUIRED)

add_executable(test_xnnpack test_xnnpack.cpp)

target_link_libraries(test_xnnpack PRIVATE xnnpack::xnnpack)

set_target_properties(test_xnnpack PROPERTIES
    CXX_STANDARD 14
    CXX_STANDARD_REQUIRED ON)
