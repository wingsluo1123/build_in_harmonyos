cmake_minimum_required(VERSION 3.15)
project(test_lsp-r3d-glx-lib CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(lsp-r3d-glx-lib REQUIRED)

add_executable(test_lsp-r3d-glx-lib test.cpp)
target_link_libraries(test_lsp-r3d-glx-lib PRIVATE lsp-r3d-glx-lib::lsp-r3d-glx-lib)
