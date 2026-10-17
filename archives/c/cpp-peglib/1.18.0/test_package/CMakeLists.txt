cmake_minimum_required(VERSION 3.14)
project(cpp_peglib_test_package LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 交付的 CMake 契约（package_info 里 cmake_file_name = "cpp-peglib"）
find_package(cpp-peglib CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE cpp-peglib::cpp-peglib)

enable_testing()
add_test(NAME test_package COMMAND test_package)
