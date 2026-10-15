cmake_minimum_required(VERSION 3.15)
project(test_vkroots CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 通过 Conan 生成的 CMakeDeps 查找被测包
find_package(vkroots REQUIRED)

# ── 消费者用例 1（集成）：用 vkroots 的 API 写一个最小 Vulkan layer，
#    编译成可被 loader 加载的模块（.so）—— header-only 库的典型消费形态
add_library(vkroots_consumer_layer MODULE test_layer.cpp)
target_link_libraries(vkroots_consumer_layer PRIVATE vkroots::vkroots)

# ── 消费者用例 2（端到端，可执行）：在进程内真实跑通 layer 协商流程
#    不需要 Vulkan loader / GPU / dlopen，因此在 CI worker 上也能实际执行
add_executable(vkroots_negotiate_e2e negotiate_main.cpp)
target_link_libraries(vkroots_negotiate_e2e PRIVATE vkroots::vkroots)
