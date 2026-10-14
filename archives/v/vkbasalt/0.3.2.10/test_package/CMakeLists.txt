cmake_minimum_required(VERSION 3.15)
project(test_vkbasalt CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(vkbasalt REQUIRED CONFIG)

add_executable(test_vkbasalt test_vkbasalt.cpp)
target_link_libraries(test_vkbasalt PRIVATE vkbasalt::vkbasalt ${CMAKE_DL_LIBS})

# 包根目录（含 share/vulkan/implicit_layer.d/vkBasalt.json）由 conan 的
# runenv 注入；测试进程用 TEST_PACKAGE_ROOT 指向包根以定位层配置。
