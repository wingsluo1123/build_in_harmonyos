cmake_minimum_required(VERSION 3.15)
project(test_fcitx5 CXX)

# fcitx5 头文件（log.h 等）使用 std::span 等 C++20 设施，须显式设置标准
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 消费者通过 Conan 生成的 CMakeDeps 找到本库顶层包（fcitx5 聚合
# Fcitx5::Core/Fcitx5::Config/Fcitx5::Utils 三个组件目标）
find_package(fcitx5 REQUIRED)

# 消费者验证：真实业务上层组件视角，仅用公开 API
add_executable(test_fcitx5 test_fcitx5.cpp)
target_link_libraries(test_fcitx5 fcitx5::fcitx5)

# 鸿蒙专项测试：验证 OHOS 平台行为（StandardPaths 路径、libuv 事件循环）
add_executable(test_fcitx5_ohos test_fcitx5_ohos.cpp)
target_link_libraries(test_fcitx5_ohos fcitx5::fcitx5)

enable_testing()
add_test(NAME test_fcitx5 COMMAND test_fcitx5)
add_test(NAME test_fcitx5_ohos COMMAND test_fcitx5_ohos)
