cmake_minimum_required(VERSION 3.15)
project(test_samarium CXX)

# 消费者视角：只用交付的包（CMakeDeps 生成的 samarium CMake 包配置）。
find_package(samarium CONFIG REQUIRED)

add_executable(test_samarium test_package.cpp)
# 只链接交付的目标；fmt / range-v3 由包的 cpp_info.requires 传递（公共头需要它们）
target_link_libraries(test_samarium PRIVATE samarium::samarium)

# 公共头使用 C++20（concepts / std::span / std::numbers）：包同时通过
# cpp_info.cxxflags 把 -std=c++20 传给消费者，这里显式要求以固定编译口径。
set_target_properties(test_samarium PROPERTIES CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_samarium COMMAND test_samarium)
