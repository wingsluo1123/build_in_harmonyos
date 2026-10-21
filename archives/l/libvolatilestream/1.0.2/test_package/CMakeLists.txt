cmake_minimum_required(VERSION 3.15)
project(test_libvolatilestream C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Conan CMakeDeps 生成的 config 文件
find_package(libvolatilestream CONFIG REQUIRED)

add_executable(test_libvolatilestream test.c)
target_link_libraries(test_libvolatilestream PRIVATE libvolatilestream::libvolatilestream)
