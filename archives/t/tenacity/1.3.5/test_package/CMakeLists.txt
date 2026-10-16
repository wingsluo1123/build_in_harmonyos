cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C CXX)

# tenacity 各核心库的公开头文件按 C++17 编写（MemoryX.h 等使用 C++14/17 特性），
# 消费者必须显式对齐标准；上游以 cxx_std_17 目标特性下发，此处直接钉死。
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 真实链接 tenacity 静态核心库并调用其公开 API（R34 非空壳）
find_package(tenacity REQUIRED)

add_executable(test_tenacity test_tenacity.cpp)
target_link_libraries(test_tenacity PRIVATE tenacity::tenacity)

# 产物验证：校验打包的静态库为合法 ar 归档、成员为 AArch64 ELF（R34 补充）
add_executable(elf_check elf_check.c)
