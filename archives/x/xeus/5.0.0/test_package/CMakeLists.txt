cmake_minimum_required(VERSION 3.15)
project(test_xeus CXX)

# Find the package via Conan-generated CMakeDeps
find_package(xeus REQUIRED)
find_package(nlohmann_json REQUIRED)

# xeus 目标名兼容：conan CMakeDeps 生成 xeus::xeus（命名空间）；
# 源码安装的 xeusConfig 导出 xeus（共享）/xeus-static（静态），无命名空间
if (TARGET xeus::xeus)
    set(XEUS_LINK_TARGET xeus::xeus)
elseif (TARGET xeus)
    set(XEUS_LINK_TARGET xeus)
elseif (TARGET xeus-static)
    set(XEUS_LINK_TARGET xeus-static)
endif ()

# 1) 消费者验证（R34：调用被测包真实 API，断言可观察结果）
add_executable(test_xeus test_consumer.cpp)
target_compile_features(test_xeus PRIVATE cxx_std_17)
target_link_libraries(test_xeus PRIVATE ${XEUS_LINK_TARGET})

# 2) HarmonyOS 专项测试（R40：验证 OHOS 平台适配完整性）
add_executable(test_ohos_special test_ohos_special.cpp)
target_compile_features(test_ohos_special PRIVATE cxx_std_17)
target_link_libraries(test_ohos_special PRIVATE ${XEUS_LINK_TARGET})

enable_testing()
add_test(NAME test_xeus_consumer COMMAND test_xeus)
add_test(NAME test_ohos_special COMMAND test_ohos_special)