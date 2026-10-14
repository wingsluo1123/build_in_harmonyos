cmake_minimum_required(VERSION 3.15)

# 与 port/CMakeLists.txt 同一处修复：原生 HarmonyOS 构建（= CI worker）下 CMake 按
# `uname -s` 得出 CMAKE_SYSTEM_NAME=HarmonyOS，而 CMake 官方只提供 Platform/OHOS.cmake，
# 于是 "System is unknown to cmake, create: Platform/HarmonyOS"（CI #79867 日志实测，
# test_package 配置阶段同样出现）。必须在 project() 之前预置。
if(CMAKE_HOST_SYSTEM_NAME STREQUAL "HarmonyOS" AND NOT CMAKE_SYSTEM_NAME)
    set(CMAKE_SYSTEM_NAME OHOS)
endif()

project(test_lca_consumer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 消费者视角：qtbase 以 cmake_find_mode=none 发布（无 qtbase-config.cmake），
# 故 Qt6 由 CMAKE_PREFIX_PATH（生成器注入 qtbase 包目录）原生查找；
# libcontentaction 本体按包目录绝对路径链接（与本仓既有 Qt 配方 test_package 同款，
# 避免 CMakeDeps 为 qtbase 生成 find_dependency(qtbase) 而无法解析）。
if(DEFINED LCA_QT_PREFIX)
    list(PREPEND CMAKE_PREFIX_PATH "${LCA_QT_PREFIX}")
endif()
find_package(Qt6 REQUIRED COMPONENTS Core DBus Test Xml)

add_executable(test_lca_consumer lca_consumer_case.cpp)
target_include_directories(test_lca_consumer PRIVATE
    "${LCA_INCLUDEDIR}" "${LCA_INCLUDEDIR}/contentaction6")
target_link_libraries(test_lca_consumer PRIVATE
    "${LCA_LIBRARY}" Qt6::Core Qt6::DBus Qt6::Test Qt6::Xml)

# RUNPATH：消费者按**包目录绝对路径**链接 libcontentaction6.so（见上），链接期没问题，
# 但运行期加载器只按 RUNPATH/LD_LIBRARY_PATH 搜索，**不会**记住链接时的绝对路径，
# 于是：
#   Error loading shared library libcontentaction6.so.0: (needed by ./test_lca_consumer)
#   Error relocating ./test_lca_consumer: _ZN13ContentAction...: symbol not found
# → 消费者退出码 127（CI #79867 / #79942 实测，test() 第 67 行）。
#
# 注意（2026-10-10 修正）：先前写的 "${LCA_LIBDIR};\$ORIGIN" 在 CI 上**没有生效**。
# OHOS 的 lld 对 $ORIGIN 的支持与 glibc 工具链不同，混在 ';' 列表里可能导致整条
# RUNPATH 未被写入或不被解析。此处改为**只写绝对 lib 目录**（确定可解析），
# 并在 test_package/conanfile.py 里同时注入 LD_LIBRARY_PATH 作为第二道保险。
if(UNIX AND LCA_LIBDIR)
    set_target_properties(test_lca_consumer PROPERTIES
        BUILD_RPATH "${LCA_LIBDIR}"
        INSTALL_RPATH "${LCA_LIBDIR}"
        BUILD_WITH_INSTALL_RPATH OFF
        SKIP_BUILD_RPATH OFF)
endif()
