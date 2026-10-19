cmake_minimum_required(VERSION 3.15)
project(test_libespeak-ng C)

find_package(libespeak-ng REQUIRED)

# 测试源 1：基础初始化/终止（espeak_Initialize + espeak_Terminate）
add_executable(test_basic test.c)
target_link_libraries(test_basic libespeak-ng::libespeak-ng)

# 测试源 2：完整 TTS 合成（espeak_SetSynthCallback 收集 PCM → WAV 校验）
add_executable(test_libespeak-ng test_libespeak_ng.c)
target_link_libraries(test_libespeak-ng libespeak-ng::libespeak-ng)

enable_testing()
add_test(NAME test_basic COMMAND test_basic)
add_test(NAME test_libespeak-ng COMMAND test_libespeak-ng)