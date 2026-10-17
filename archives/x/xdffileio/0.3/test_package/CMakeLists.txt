cmake_minimum_required(VERSION 3.15)
project(test_xdffileio C)

find_package(xdffileio REQUIRED)

add_executable(test_xdffileio_api test_xdffileio_api.c)
target_link_libraries(test_xdffileio_api PRIVATE xdffileio::xdffileio)

add_executable(test_xdffileio_ohos test_xdffileio_ohos.c)
target_link_libraries(test_xdffileio_ohos PRIVATE xdffileio::xdffileio)

enable_testing()
add_test(NAME test_xdffileio_api COMMAND test_xdffileio_api)
add_test(NAME test_xdffileio_ohos COMMAND test_xdffileio_ohos)
