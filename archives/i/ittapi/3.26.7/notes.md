# ittapi 3.26.7 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-26
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. **init-build**: 下载源码并解压到 .orig/.work 目录
   - 源码 URL: https://github.com/intel/ittapi/archive/refs/tags/v3.26.7.tar.gz
   - sha256: 29aa0dd50cdf0f0a0a21563eafc5b7ce79052c19594a64017a51f09304a4a39f

2. **cmake 配置**:
   ```bash
   cd $BUILD_SRC_DIR
   mkdir build && cd build
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF
   ```
   CMake 输出 "System is unknown to cmake" 警告（HarmonyOS 平台），但不影响编译。

3. **make 编译**:
   ```bash
   make -j1
   ```
   生成 libittnotify.a 和 libjitprofiling.a 两个静态库。

4. **make install DESTDIR (staging 隔离安装)**:
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```
   安装 libittnotify.a + 6 个头文件 + 4 个 CMake 配置文件。

5. **make test / ctest**:
   上游 CMakeLists.txt 未定义 enable_testing()，无测试目标。

6. **conan-init + conan-verify**: 生成 Conan 配方并验证 8 道门禁全部通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build copytree 失败 | 源码 `rust/ittapi-sys/c-library -> ../../` 符号链接循环 | 从 .orig 目录移除该符号链接 |
| 2 | conanfile.py 使用 Autotools 模板 | conan-init 误检测构建系统 | 手动重写为 CMake 工具链 (CMakeToolchain + CMake + cmake_layout) |
| 3 | conandata.yml sha256 占位符 | 自动生成时未计算实际值 | 计算并填入 29aa0dd50cdf0f0a0a21563eafc5b7ce79052c19594a64017a51f09304a4a39f |
| 4 | test.c 编译警告 | __itt_init_ittlib 是内部函数非公开 API | 移除函数调用，仅做头文件包含和链接测试 |
| 5 | 首次 finish 降级为 built | 知识草稿标记为空，缺少 .knowledge-done | .knowledge-done 在首次 finish 中自动创建，重新运行升级为 published |

## 源码修改

无补丁。仅移除了源码中的符号链接循环 `rust/ittapi-sys/c-library`（非源码文件修改，仅为解决文件系统层面问题）。

## 依赖版本

无外部依赖。ittapi 是自包含的静态库。

## 验证结果

```
$ file build/bin/libittnotify.a
ar archive

$ readelf -d build/bin/libittnotify.a
There is no dynamic section in this file.

$ make test
No rule to make target 'test'. (上游无测试套件)

Conan test_package: 1/1 Test #1: test_ittapi ... Passed (0.02 sec)
conan-verify: 8/8 门禁全部通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libittnotify.a | 主静态库 (包含 ittnotify_static.c + jitprofiling.c) |
| include/ittnotify.h | 主头文件 (公开 API) |
| include/jitprofiling.h | JIT 分析头文件 |
| include/libittnotify.h | 库头文件 |
| include/advisor-annotate.h | Advisor 注解头文件 |
| include/ittnotify-zca.h | ZCA 注解头文件 |
| lib/cmake/ittapi/ | CMake 配置文件 (ittapiConfig.cmake 等) |

## 注意事项

- 上游 CMakeLists.txt 仅安装 ittnotify 目标，libjitprofiling.a 虽然编译但不安装
- CMake 在 HarmonyOS 上输出平台未知警告，不影响功能
- 源码中的 rust/ 目录包含符号链接循环，init-build 时需移除

---

**编译结束**: 2026-06-26 03:11
**最终状态**: published
