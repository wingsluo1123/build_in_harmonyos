cmake_minimum_required(VERSION 3.15)
project(test_mnxdom LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 经 CMakeDeps 生成的配置查找被测包；mnxdom 的公共头依赖 nlohmann/json.hpp，
# 消费端需显式 find_package 该 header-only 依赖（见 test_package/conanfile.py）。
find_package(mnxdom CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)

add_executable(test_mnxdom test_mnxdom.cpp)
target_link_libraries(test_mnxdom PRIVATE mnxdom::mnxdom nlohmann_json::nlohmann_json)
