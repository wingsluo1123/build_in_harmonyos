cmake_minimum_required(VERSION 3.16)
# 必须启用 C 语言: juce_core 自带 zlib 源码 (juce_core_zlib.c) 是 C 编译单元,
# 仅启用 CXX 会导致该文件被忽略, 链接期 deflate/inflate/crc32 符号缺失
project(test_juce C CXX)

# juce 包通过 cpp_info.includedirs 暴露模块目录 (include/JUCE-9.0.3/modules)
find_package(juce REQUIRED)

add_executable(test_juce main.cpp)

# 链接 juce::juce 目标: 同时携带 include 目录与 cpp_info.defines
# (JUCE_USE_CURL=0 — OHOS sysroot 无 libcurl, 必须由包声明传播到消费者)
target_link_libraries(test_juce PRIVATE juce::juce)

# JUCE 消费者必须编译自己使用的模块源码 (官方使用模型)
# juce_core.cpp = 单编译单元; zlib 与编译时间戳为配套编译单元
target_sources(test_juce PRIVATE
    ${juce_INCLUDE_DIRS}/juce_core/juce_core.cpp
    ${juce_INCLUDE_DIRS}/juce_core/juce_core_zlib.c
    ${juce_INCLUDE_DIRS}/juce_core/juce_core_CompilationTime.cpp
)

# JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED 是 JUCE 对消费者的标准要求
target_compile_definitions(test_juce PRIVATE
    JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1
    JUCE_STANDALONE_APPLICATION=1
)