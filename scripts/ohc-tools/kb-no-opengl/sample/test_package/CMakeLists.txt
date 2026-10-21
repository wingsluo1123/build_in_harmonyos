cmake_minimum_required(VERSION 3.20)
project(noopengl_demo_test_package LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Qt6 config 由 qtbase 包提供（_DIR 由 test_package/conanfile.py 注入）
find_package(Qt6 REQUIRED COMPONENTS Core Gui)

# 被测样例包按显式路径链接：qtbase 不提供 <name>-config.cmake，
# CMakeDeps 生成的 config 会带一条无法满足的 find_dependency(qtbase)。
find_library(NOOPENGLDEMO_LIB NAMES noopengldemo
    PATHS "${NOOPENGLDEMO_LIB_DIR}" NO_DEFAULT_PATH REQUIRED)

add_executable(noopengl_demo_test src/main.cpp)
target_include_directories(noopengl_demo_test PRIVATE "${NOOPENGLDEMO_INCLUDE_DIR}")
target_link_libraries(noopengl_demo_test PRIVATE ${NOOPENGLDEMO_LIB} Qt6::Core Qt6::Gui)
