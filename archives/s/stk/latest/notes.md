# stk latest 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang / clang++
- 状态: built
- 平台: HarmonyOS PC (aarch64)
- 源码来源: https://github.com/thestk/stk/archive/refs/heads/master.tar.gz

## 软件信息
- 名称: stk
- 版本: latest
- 上游仓库: thestk/stk
- 许可证: MIT
- 描述: The Synthesis ToolKit in C++ - audio synthesis library
- 产物: libstk.a (静态库) + Stk.h (头文件)
- 依赖: 无外部依赖（纯 C++ 库，可选依赖 ALSA/JACK 用于实时音频）

## Conan 配方说明

本归档采用 Conan 2.x CMAKE 配方：

- `conanfile.py`: CMAKE 构建配方
  - settings = "os", "compiler", "build_type", "arch"
  - OHOS 平台强制 `shared=False`（HarmonyOS 仅构建静态库）
  - exports_sources = "patches/*"
- `conandata.yml`: 源码 URL + 已验证的 SHA-256
- `test_package/`: 测试包，编译链接测试程序验证库核心功能

## 编译步骤

1. Conan 下载源码：`get(self, **self.conan_data["sources"], strip_root=True)`
2. 生成工具链：`CMakeToolchain`
3. 配置：`cmake.configure()`
4. 构建：`cmake.build()`
5. 安装：`cmake.install()`

## 遇到的问题与解决方案

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 平台不支持实时音频后端 | 上游对未知平台会中止配置 | 禁用 `REALTIME` 和示例工程，仅构建静态核心库 |
| 2 | CMake 4 移除旧策略兼容 | 上游最低版本仍为 3.1 | 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | 源码完整性校验 | master 归档需要固定校验值 | 使用实测 SHA-256 `c5d1fa6ca903b5f0571a2ba036b35cac2aee552f45c7a273e0df793cfefbace7` |
| 4 | STK 选项未生效 | `tc.variables`（工具链文件）不被直接 `cmake` 调用采纳 | 所有 STK 选项改为 `build()` 中经命令行 `-D` 传入 |
| 5 | `TEST_BIG_ENDIAN` try_run 失败 | 交叉/受限环境无法运行探测程序 | 固定 `CMAKE_CXX_BYTE_ORDER`，跳过 try_run |
| 6 | `MUTEX`/`THREAD_HANDLE`/`sockaddr_in` 缺失 | `REALTIME=OFF` 后无人定义 `__OS_LINUX__`，而 CMakeLists 仍 glob 全部 `src/*.cpp` | `tc.preprocessor_definitions["__OS_LINUX__"] = 1` |
| 7 | `use of undeclared identifier 'pthread_cancel'` / `'pthread_testcancel'` | 选中 `__OS_LINUX__` 分支后 `Thread.cpp` 会调用这两个函数，而 OHOS 的 musl 系 libc 未实现 | `patches/0001-src-Thread.cpp.patch` 守卫调用点，并在 `generate()` 中显式定义 `__OHOS__` 使守卫生效 |

## 关于 pthread_cancel 与 R8 的说明

`Thread.cpp` 的两处调用在 OHOS 上必然编译失败（CI 实测：
`src/Thread.cpp:62:8: error: use of undeclared identifier 'pthread_cancel'`）。

采用的方案与 `archives/a/axel/2.17.14`（同样是 musl/OHOS 缺 `pthread_cancel`）
一致：在调用点加 `#if defined(__OHOS__)` 守卫，退化为「不支持取消」的语义
（`cancel()` 返回 `false`，`testCancel()` 为空操作），调用方本就把 `false`
当作「无法取消」处理，行为安全。

守卫依赖的 `__OHOS__` **不假定工具链隐式注入**，而是在 `generate()` 中显式
定义：

```python
if self.settings.os == "OHOS":
    tc.preprocessor_definitions["__OHOS__"] = 1
```

这与 `archives/a/audit/4.1.2/conanfile.py` 的
`tc.extra_defines.append("__OHOS__")  # R8: Define __OHOS__ so #ifdef __OHOS__
guards in patches are active` 属同一做法；全仓库共 548 个补丁使用 `__OHOS__`
守卫，为既有约定。

## 验证结果

test_package 验证 stk 核心功能，编译链接测试程序验证库核心功能。

## 注意事项

- stk 为依赖项范畴
- 默认静态构建（shared=False），符合系统库规则
