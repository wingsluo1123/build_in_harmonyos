cmake_minimum_required(VERSION 3.15)
project(test_sg3_utils C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# 经 Conan 生成的 CMakeDeps 查找被测包
find_package(sg3_utils REQUIRED)

# 消费者用例：仅经公开头文件 <scsi/sg_lib.h> 使用 libsgutils2 公开 API
add_executable(test_sg3_utils test.c)
target_link_libraries(test_sg3_utils sg3_utils::sg3_utils)

# 鸿蒙专项测试：OHOS(musl) 下 sense 解码与类别映射语义一致性
add_executable(test_sg3_utils_ohos ohos_test.c)
target_link_libraries(test_sg3_utils_ohos sg3_utils::sg3_utils)

enable_testing()
add_test(NAME test_sg3_utils COMMAND test_sg3_utils)
add_test(NAME test_sg3_utils_ohos COMMAND test_sg3_utils_ohos)
