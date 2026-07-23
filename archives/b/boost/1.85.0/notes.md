# Boost 1.85.0 OpenHarmony 适配笔记

## 概况

- 上游版本：1.85.0
- 上游源码：https://archives.boost.io/release/1.85.0/source/boost_1_85_0.tar.bz2
- 平台：OpenHarmony（aarch64-unknown-linux-ohos）
- 编译器：clang
- 构建系统：Boost.Build（b2）
- Conan 包类型：header-library；安装 `boost/` 头文件

## 适配补丁

### E035：b2 SHELL/vfork 兼容

在 `tools/build/src/engine/`：

- `jam.h`：OpenHarmony 下定义 `NO_VFORK`，避免 sandbox 环境中的 `vfork()` 不可靠行为。
- `execunix.cpp`：默认 shell 使用 `/bin/sh` → `$SHELL` → `sh` 的 fallback。

Boost 1.85.0 的 b2 引擎目录为 `tools/build/src/engine`，可通过：

```bash
cd tools/build/src/engine
./build.sh clang --cxx=clang++
./b2 --version
```

验证引擎可正常执行 SHELL 规则。

### E099：`pthread_setcancelstate` 缺失

补丁：`patches/0001-sp-thread-sleep-ohos.patch`

`boost/core/detail/sp_thread_sleep.hpp` 的三个 pthread 取消状态调用条件增加 `!defined(__OHOS__)`。OpenHarmony 使用 musl libc，不提供该 glibc 风格 API；鸿蒙下保留 `nanosleep` 路径。

### E100：ucontext API 缺失

OpenHarmony musl 不提供 `getcontext`/`swapcontext`/`makecontext`。在鸿蒙 clang 下跳过 native ucontext 测试，同时保留 fcontext 测试路径：

- `libs/fiber/test/Jamfile.v2`
- `libs/context/test/Jamfile.v2`
- `libs/coroutine2/test/Jamfile.v2`（补丁：`patches/0004-coroutine2-ohos-no-ucontext.patch`）

coroutine2 回归验证结果：`b2_exit=0`，通过 1，失败 0，且日志中无 `getcontext`/`ucontext` 错误。

## 测试结果

| 指标 | 结果 |
|------|------|
| 带测试目录的库 | 142/142 |
| 源码树测试 `.cpp` 文件 | 12201 |
| 实际执行 b2 测试目标 | 5754 |
| 通过 | 5439 |
| 失败 | 315 |
| 实际执行通过率 | 94.5% |
| 新增鸿蒙测试 | 0 |

12201 是 `libs/*/test/*.cpp` 源文件计数，包含 helper、fixture 及 compile-fail 辅助源码；5754 才是 b2 实际执行的独立测试目标，故通过率使用 `5439/5754`。

## 剩余失败

剩余 315 个失败主要不是 OpenHarmony 平台适配问题：

- b2 的 compile-fail/`failed updating` 分类问题；
- Boost 的编译期负例和 `static_assert` 断言测试；
- C++ 标准边界（mpl、filesystem、exception、rational）；
- mysql 测试缺少 OpenSSL 开发头文件；
- function_types 使用已废弃的 Boost header。

coroutine2 的 3 个 ucontext 残留已由 `0004-coroutine2-ohos-no-ucontext.patch` 修复。

## 配方验证

```bash
python3 scripts/ohc-run.py conan-verify boost 1.85.0
```

已验证 Conan 配方包含 OpenHarmony 补丁，并可从官方 1.85.0 源码应用补丁。
