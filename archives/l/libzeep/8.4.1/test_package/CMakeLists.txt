cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

find_package(zeep CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE zeep::zeep)
# libzeep 公开头文件使用 C++23 特性（std::unreachable 等），消费者必须以 C++23 编译
target_compile_features(test_package PRIVATE cxx_std_23)

# 鸿蒙专项测试：真实可执行的 OHOS 适配验证（URI/JSON 公开 API + 本机 HTTP daemon 往返）
add_executable(ohos_test ohos_test.cpp)
target_link_libraries(ohos_test PRIVATE zeep::zeep)
target_compile_features(ohos_test PRIVATE cxx_std_23)

# 消费者用例：第三方业务组件视角（仅公开 API：el JSON / http request / reply / uri）
add_executable(consumer_app consumer_app.cpp)
target_link_libraries(consumer_app PRIVATE zeep::zeep)
target_compile_features(consumer_app PRIVATE cxx_std_23)
