# E999 — OHOS sysroot 无 libcurl 头文件时 C++ 框架网络后端裁剪模式（JUCE_USE_CURL=0 配方级传播）

## 错误特征

OHOS/OpenHarmony PC (aarch64-linux-ohos) 上编译默认启用 libcurl 网络后端的 C/C++ 框架时：

```
# 编译期 (juce_core.cpp)
fatal error: 'curl/curl.h' file not found
   #include <curl/curl.h>

# 或链接期 (若误链接系统 curl)
ld.lld: error: undefined symbol: curl_easy_init / curl_easy_perform ...
```

## 触发条件

- 构建系统: cmake（conan create / 消费者编译模块源码）
- 阶段: compilation
- 环境: OHOS sysroot（`/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot`）不含 libcurl 头与库
- 框架侧默认宏: JUCE 的 `JUCE_USE_CURL` 默认 1（Linux/OHOS 路径）

## 根因分析

OHOS sysroot 不发布 libcurl（无 `curl/curl.h` 头、无 `libcurl.so`）。C/C++ 框架（如 JUCE
的 `juce_core`）在 `JUCE_LINUX` 分支默认启用 curl 网络后端（WebInputStream/URL 等），
导致编译期 `curl/curl.h not found`。核心功能（字符串/容器/文件/线程/DSP）不依赖 curl，
因此正确的 OHOS 适配是**裁剪网络后端**而非引入不可用的系统库。

## 解决方案

### 推荐方案（配方级传播，无需逐消费者配置）

1. 在 conan 配方 `conanfile.py::package_info()` 声明关闭宏并暴露给消费者：
   ```python
   def package_info(self):
       self.cpp_info.defines = ["JUCE_USE_CURL=0"]  # OHOS 无 libcurl
   ```
2. 消费者通过 CMakeDeps 目标链接自动继承该 define：
   ```cmake
   find_package(juce REQUIRED)
   add_executable(test_juce main.cpp)
   target_link_libraries(test_juce PRIVATE juce::juce)   # 携带 includes + JUCE_USE_CURL=0
   ```
   （仅 `target_include_directories(... ${juce_INCLUDE_DIRS})` 不会传播 defines ——
   必须链接 `juce::juce` 目标。）

### 禁止做法

- ❌ 在补丁中硬编码 `-DJUCE_USE_CURL=0` 到消费者构建（污染所有消费方，无法随包传播）
- ❌ 尝试为 OHOS 构建/引入 libcurl（sysroot 无此库，且裁剪后不影响核心 API）
- ❌ 仅改 test_package 本地编译参数而不在 cpp_info 声明（真实消费者仍会失败）

## 验证

```bash
# 1. sysroot 确实无 curl 头
find /data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot -name 'curl.h'   # 无输出
# 2. 消费者编译链接运行（JUCE_USE_CURL=0 经 juce::juce 目标传播）
clang++ --target=aarch64-linux-ohos -std=c++17 -I modules \
  -DJUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1 -DJUCE_STANDALONE_APPLICATION=1 \
  test_package/main.cpp modules/juce_core/juce_core.cpp \
  modules/juce_core/juce_core_zlib.c modules/juce_core/juce_core_CompilationTime.cpp \
  -o test_juce && ./test_juce   # HELLO, HARMONYOS JUCE! (rc=0)
# 3. conan-verify G2 conan create 全门禁 PASS（test_package 编译链接运行成功）
```

## 适用边界与反例

- 适用：上游框架默认启用 libcurl 网络后端、OHOS sysroot 无 libcurl、且网络后端可整体裁剪的场景（JUCE 9.0.3 juce_core 已验证）
- 反例：若库的**核心功能**强依赖 curl（如 libcurl 本身、curl 封装库），裁剪会让 API 缺失 → 应等待分析端发布 curl 依赖而非裁剪
- 不适用：消费者自身需要 curl 功能的场景（消费者可自行 require curl 并覆盖宏）

## 关联条目

- 相关: E127（OHOS 无 pthread_cancel，同类"OHOS sysroot 缺系统能力 → 源码级裁剪"模式）
- 相关: E321/E322（header-only/INTERFACE 库的 conan 打包与 CMakeDeps 传播）
