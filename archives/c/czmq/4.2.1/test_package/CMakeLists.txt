cmake_minimum_required(VERSION 3.15)
project(test_czmq C)

find_package(czmq REQUIRED)

add_executable(test_czmq test_czmq.c)
target_link_libraries(test_czmq PRIVATE czmq)

# rule12 鸿蒙特有端到端消费者用例（config persistence + TCP req/rep + zmsg）
add_executable(test_ohos_flow test_ohos_flow.c)
target_link_libraries(test_ohos_flow PRIVATE czmq)

enable_testing()
add_test(NAME test_czmq COMMAND test_czmq)
add_test(NAME test_ohos_flow COMMAND test_ohos_flow)
