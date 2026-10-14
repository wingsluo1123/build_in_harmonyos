cmake_minimum_required(VERSION 3.18)
project(test_hpx CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Conan generated package config (cmake_file_name = HPX in the recipe)
find_package(HPX REQUIRED)

add_executable(test_hpx test_hpx.cpp)
target_link_libraries(test_hpx PRIVATE HPX::hpx)

enable_testing()
add_test(NAME test_hpx COMMAND test_hpx --hpx:threads=2)
