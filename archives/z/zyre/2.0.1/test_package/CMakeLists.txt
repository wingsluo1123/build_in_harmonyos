cmake_minimum_required(VERSION 3.15)
project(test_zyre C)

find_package(zyre REQUIRED)

add_executable(test_zyre test_zyre.c)
target_link_libraries(test_zyre PRIVATE zyre)

# rule12 鸿蒙特有端到端消费者用例（双节点 UDP beacon 发现 + JOIN + SHOUT 组播流）
add_executable(test_ohos_flow test_ohos_flow.c)
target_link_libraries(test_ohos_flow PRIVATE zyre)

enable_testing()
add_test(NAME test_zyre COMMAND test_zyre)
add_test(NAME test_ohos_flow COMMAND test_ohos_flow)
