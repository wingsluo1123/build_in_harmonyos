cmake_minimum_required(VERSION 3.15)
project(test_savvy CXX)

# Package found through the Conan-generated CMakeDeps config.
# savvy 是 header-only INTERFACE 库；shrinkwrap（及其 xz/zlib/zstd）经
# savvy::savvy 的 cpp_info.requires 由 CMakeDeps 级联提供 include 与链接信息。
find_package(savvy REQUIRED)

add_executable(test_savvy test_savvy.cpp)
target_link_libraries(test_savvy PRIVATE savvy::savvy)
set_target_properties(test_savvy PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_savvy COMMAND test_savvy)
