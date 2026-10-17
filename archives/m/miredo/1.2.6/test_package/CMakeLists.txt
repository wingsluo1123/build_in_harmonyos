cmake_minimum_required(VERSION 3.15)
project(test_miredo C)

# 通过 Conan 生成的 CMakeDeps 配置文件消费被测包
find_package(miredo REQUIRED)

add_executable(test_miredo_consumer test_consumer.c)
target_link_libraries(test_miredo_consumer miredo::miredo)

enable_testing()
add_test(NAME test_miredo_consumer COMMAND test_miredo_consumer)
