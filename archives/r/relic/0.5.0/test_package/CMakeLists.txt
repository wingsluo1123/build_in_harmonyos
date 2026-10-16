cmake_minimum_required(VERSION 3.15)
project(test_relic_consumer C)

find_package(relic REQUIRED)

add_executable(test_relic_consumer src/main.c)
target_link_libraries(test_relic_consumer relic::relic)

enable_testing()
add_test(NAME test_relic_consumer COMMAND test_relic_consumer)
