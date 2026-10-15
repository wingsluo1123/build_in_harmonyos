cmake_minimum_required(VERSION 3.15)
project(spot_consumer CXX)

# spot 2.15 以 C++20 构建（HEADERS 亦要求 C++20）。
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(spot REQUIRED)

add_executable(spot_probe spot_probe.cpp)
target_link_libraries(spot_probe PRIVATE spot::spot)
target_compile_features(spot_probe PRIVATE cxx_std_20)
