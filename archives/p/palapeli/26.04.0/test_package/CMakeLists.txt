cmake_minimum_required(VERSION 3.16)

# 真实消费者测试：像上层应用那样通过导出的 CMake 包找到 libpala 并链接
project(palapeli_consumer LANGUAGES CXX)

find_package(Pala REQUIRED)
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
# 切片器插件是 KPluginFactory 插件，实例化需要 KF6CoreAddons
find_package(KF6CoreAddons REQUIRED)

# 上游 libpala 的 install(EXPORT PalaTargets) 没有给 NAMESPACE，导出的导入目标
# 就叫 `Pala`（EXPORT_NAME Pala），不是 Pala::Pala。这里两种都兼容，避免受
# 上游将来加命名空间的影响。
if(TARGET Pala::Pala)
    set(PALA_TARGET Pala::Pala)
elseif(TARGET Pala)
    set(PALA_TARGET Pala)
else()
    message(FATAL_ERROR "Pala 包已找到但未提供 Pala / Pala::Pala 目标")
endif()
message(STATUS "palapeli_consumer: linking ${PALA_TARGET}")

add_executable(palapeli_consumer consumer.cpp)
target_link_libraries(palapeli_consumer PRIVATE ${PALA_TARGET} KF6::CoreAddons Qt6::Core Qt6::Gui)
