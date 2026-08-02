# stk latest 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-02
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
- 产物: libstk.a (静态库) + include/stk/*.h (头文件)
- 依赖: 无外部依赖（纯 C++ 库，可选依赖 ALSA/JACK 用于实时音频，本归档未启用）

## Conan 配方说明

本归档采用 Conan 2.x CMAKE 配方：

- `conanfile.py`: CMAKE 构建配方
  - settings = "os", "compiler", "build_type", "arch"
  - OHOS 平台强制 `shared=False`（仅构建静态库）
  - `export_conandata_patches()` 导出 `patches/*`
- `conandata.yml`: 源码 URL + 已验证的 SHA-256 + 补丁清单
- `test_package/`: 消费者视角测试，链接已安装的 libstk 验证 DSP 与线程原语

## 编译步骤

1. Conan 下载源码：`get(self, **self.conan_data["sources"], strip_root=True)`
2. 应用补丁：`apply_conandata_patches(self)`
3. 生成工具链：`CMakeToolchain`
4. 配置：`cmake.configure(variables={...})`
5. 构建：`cmake.build()`
6. 安装：`cmake.install()`

## 遇到的问题与解决方案

| # | 问题 | 原因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 平台不支持实时音频后端 | 上游对未知平台 `message(FATAL_ERROR "Unknown system type for realtime support.")` | 禁用 `REALTIME` 与示例工程，仅构建静态核心库 |
| 2 | CMake 4 移除旧策略兼容 | 上游最低版本仍为 3.1 | 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | 源码完整性校验 | master 归档需要固定校验值 | 使用实测 SHA-256 `c5d1fa6ca903b5f0571a2ba036b35cac2aee552f45c7a273e0df793cfefbace7` |
| 4 | STK 选项未生效 | `tc.variables`（工具链文件）不被直接 `cmake` 调用采纳 | 所有 STK 选项改为 `build()` 中经命令行 `-D` 传入 |
| 5 | `TEST_BIG_ENDIAN` try_run 失败 | 受限环境无法运行探测程序 | 固定 `CMAKE_CXX_BYTE_ORDER=LITTLE_ENDIAN`，跳过 try_run |
| 6 | `MUTEX`/`THREAD_HANDLE`/`sockaddr_in` 缺失 | `REALTIME=OFF` 后无人定义 `__OS_LINUX__`，而 CMakeLists 仍 glob 全部 `src/*.cpp` | `tc.preprocessor_definitions["__OS_LINUX__"] = 1` |
| 7 | `use of undeclared identifier 'pthread_cancel'` / `'pthread_testcancel'` | `Thread.cpp` 假定「有 pthreads 就有线程取消」，而本平台 C 库未提供这两个函数 | 两个补丁：CMake 侧用 `check_symbol_exists()` 探测，源码侧按探测结果降级。详见下节 |
| 8 | 下游 include `Thread.h`/`Mutex.h` 编译失败 | 库以 `__OS_LINUX__` 编译，但该开关没有传给消费者，头文件里 `THREAD_HANDLE`/`MUTEX` 不会被声明 | `package_info()` 中 `self.cpp_info.defines = ["__OS_LINUX__"]` |

## 关于线程取消的可移植性处理

### 根因

线程取消是 POSIX 线程里的**可选设施**。POSIX 规定了 `pthread_cancel()` /
`pthread_testcancel()`，但 C 库可以不提供它们——强制取消离不开栈展开
（unwinder）支持，若干 C 库因此有意不实现。本平台就属于这一类，实测：

```
$ grep -rn "pthread_cancel" <sysroot>/usr/include/
(无任何结果)

$ clang -o probe probe.c        # probe.c: 取 &pthread_cancel 的地址
probe.c:7:19: error: use of undeclared identifier 'pthread_cancel';
              did you mean 'pthread_once'?
```

对照组 `pthread_join` 的同款探测可正常编译链接，说明并非头文件路径问题，
而是这两个符号确实不存在。`<pthread.h>` 里只保留了 `PTHREAD_CANCEL_ENABLE`
等常量宏，没有函数声明。

STK 的 `Thread.cpp` 把这两个调用直接放在 `__OS_LINUX__` 分支里，于是
问题 6 选中该分支后必然编译失败。

### 方案：特性探测，而非平台判断

不使用任何平台条件编译宏。改为在构建期探测符号是否存在，源码只认探测结果：

- `patches/0001-CMakeLists.txt.patch`
  ```cmake
  set(THREADS_PREFER_PTHREAD_FLAG TRUE)
  find_package(Threads QUIET)
  include(CheckSymbolExists)
  set(CMAKE_REQUIRED_LIBRARIES ${CMAKE_THREAD_LIBS_INIT})
  check_symbol_exists(pthread_cancel "pthread.h" STK_HAVE_PTHREAD_CANCEL)
  unset(CMAKE_REQUIRED_LIBRARIES)
  ```
  探测同时覆盖「未声明」与「声明了但链不上」两种情况，结果以
  `-DSTK_HAVE_PTHREAD_CANCEL=0/1` 传给编译。带上
  `CMAKE_THREAD_LIBS_INIT` 是为了避免在把 pthread 符号放在独立
  `libpthread` 的老 glibc 上误判为「不存在」。

- `patches/0002-src-Thread.cpp.patch`
  ```c
  #if !defined(STK_HAVE_PTHREAD_CANCEL)
    #define STK_HAVE_PTHREAD_CANCEL 1
  #endif
  ...
  #if (defined(__OS_IRIX__) || ... ) && STK_HAVE_PTHREAD_CANCEL
  ```
  只在 `cancel()` 与 `testCancel()` 两处追加条件；`start()` / `wait()`
  用的 `pthread_create()` / `pthread_join()` 是必备设施，原样不动。
  没有探测结果时（例如不经 CMake 构建）默认为 1，保持上游历史行为。

降级后的语义：`cancel()` 走原有的 fall-through 返回 `false`
（「无法取消」，调用方本就按此处理），`testCancel()` 成为空操作——既然
永远无法发起取消请求，也就不可能有待处理的取消点。

这两个补丁不含任何平台专属宏，且是可直接向上游提交的通用可移植性修复。

### 本机实测（HarmonyOS PC, aarch64, clang 15.0.4）

配置阶段探测输出：

```
-- Check if compiler accepts -pthread - yes
-- Looking for pthread_cancel - not found
-- pthread_cancel() unavailable: Thread::cancel() will report failure
```

编译结果：`[91/91] Linking CXX static library libstk.a`，全部 91 个翻译
单元零错误通过（打补丁前在 `src/Thread.cpp` 处失败）。
`Thread.cpp.obj` 中已无 cancel 相关未定义符号。

行为验证（链接 libstk.a 后实跑）：

| 断言 | 结果 |
|------|------|
| `t.start(&worker, NULL) == true`（`pthread_create` 仍可用） | ok |
| `t.cancel() == false`（无 `pthread_cancel`，报告失败而非崩溃） | ok |
| `t.testCancel()` 不崩溃 | ok |
| `t.wait() == true`（`pthread_join` 仍可用，线程正常回收） | ok |

### 顺带核实：RtAudio.cpp 的三处 `pthread_testcancel()`

`src/RtAudio.cpp:9090 / 9366 / 10849` 也调用了 `pthread_testcancel()`，但
逐行跟踪条件编译栈确认它们分别位于 `#if defined(__LINUX_ALSA__)` /
`__LINUX_PULSE__` / `__LINUX_OSS__` 内。本归档以 `REALTIME=OFF` 构建，
三个后端宏都不会被定义，这些代码不参与编译，无需处理。

## 关于向消费者传递 `__OS_LINUX__`

`__OS_LINUX__` 是 STK 自己的可移植性开关（含义是「POSIX 线程 + BSD
套接字」），不是本归档引入的平台宏，且对所有配置无条件设置，不做按平台
分支。

必须传给消费者的原因：安装出的头文件不是自包含的。`Thread.h` / `Mutex.h`
/ `Socket.h` 只有在某个 `__OS_*` 开关生效时才声明 `THREAD_HANDLE` /
`MUTEX` / `sockaddr_in`；而 `Stk.h` 是从音频后端宏推导这些开关的，
`REALTIME=OFF` 的构建永远不会定义它们。库的目标文件是带
`__OS_LINUX__` 编译的，消费者若看不到同一个开关，轻则编译报错，重则与
编译期不一致。因此 `package_info()` 中：

```python
self.cpp_info.defines = ["__OS_LINUX__"]
```

test_package 用到了 `Thread.h` 与 `Mutex.h`，因此它同时是这条传递逻辑的
回归测试——一旦漏掉，test_package 直接编译不过。

## 验证结果

test_package 链接已安装的 libstk，共 **20 条断言**，本机实跑
**20/20 通过，0 失败，退出码 0**：

| 分组 | 覆盖内容 | 断言数 |
|------|----------|--------|
| 全局采样率 | `setSampleRate()` / `sampleRate()` 往返 | 2 |
| SineWave | 输出有界、满幅扫过、整周期直流为零、`reset()` 归零 | 4 |
| Noise | 输出有界且非常量 | 2 |
| OnePole / OneZero | 直流增益收敛到 1；`setZero(-1)` 的冲激响应为 0.5/0.5 | 3 |
| Delay | 精确延后 7 个采样吐出冲激 | 3 |
| ADSR | 走完 attack 停在 sustain，`keyOff()` 后归零 | 2 |
| Thread / Mutex | start / cancel / testCancel / wait 全生命周期 + 互斥计数 | 4 |

上游没有可运行的测试套件（`Makefile.in` 只有 `distclean` 和 `install`
两个 target，无 `check`；无 test 目录；CMakeLists 中无 `enable_testing()`
或 `add_test()`），详见 `test_package/MANIFEST.yml`。

## 注意事项

- stk 为依赖项范畴
- 默认静态构建（shared=False），符合系统库规则
- 未启用实时音频（`REALTIME=OFF`），`__STK_REALTIME__` 始终未定义；
  需要实时后端的下游应另行评估 ALSA/JACK 依赖
