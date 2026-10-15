# CMakeLists.txt for megadepth 1.2.0 on HarmonyOS PC (OHOS aarch64)
#
# 上游仓库不含规范名 CMakeLists.txt：源码只提供 CMakeLists.txt.ci /
# .static / .statlib / .windows，构建脚本以 `ln -fs CMakeLists.txt.ci
# CMakeLists.txt` 取别名，并硬编码 `-L${CMAKE_SOURCE_DIR}/htslib` 等
# vendored 目录（依赖子模块 htslib/libBigWig/libdeflate/zlib）。
#
# 本平台改由 Conan 管理依赖链，故本文件以 CMakeDeps 生成的目标消费
# htslib / libBigWig / zlib，不引入任何 vendored 目录或绝对路径（R49）。
# 编译/链接语义与 CMakeLists.txt.ci 的 megadepth_dynamic 目标一致。
cmake_minimum_required(VERSION 3.15)

project(megadepth LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)

# 上游以 `-DMEGADEPTH_VERSION="\"`cat ../VERSION`\""` 注入版本号（见
# CMakeLists.txt.ci），megadepth.cpp 以 std::string(MEGADEPTH_VERSION) 使用。
if(NOT DEFINED MEGADEPTH_VERSION)
    file(READ "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" _megadepth_version_raw)
    string(STRIP "${_megadepth_version_raw}" MEGADEPTH_VERSION)
endif()

find_package(htslib REQUIRED)
find_package(libbigwig REQUIRED)
# zlib 由 Conan 提供（CMakeDeps 生成 zlib-config.cmake，目标 zlib::zlib），
# 不是 CMake 内置的 FindZLIB/ZLIB::ZLIB；megadepth.cpp 直接 include <zlib.h>。
find_package(zlib REQUIRED)
find_package(Threads REQUIRED)

add_executable(megadepth megadepth.cpp)
target_compile_definitions(megadepth PRIVATE MEGADEPTH_VERSION="${MEGADEPTH_VERSION}")
target_link_libraries(megadepth PRIVATE
    htslib::htslib
    libbigwig::libbigwig
    zlib::zlib
    Threads::Threads
)

install(TARGETS megadepth RUNTIME DESTINATION bin)
