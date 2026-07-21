# tracy 0.13.1 适配笔记

## 编译环境
- 构建系统: cmake（init-build 误识别为 autotools；最终走 cmake）
- 编译日期: 2026-07-22
- 编译器: clang 15.0.4 / clang++
- 状态: built（conan-verify 8 道门禁全部通过）
- 产物范围: libTracyClient.{a,so} + public headers（**不编译 capture GUI**；R36 阻断）

## 编译步骤

```bash
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DTRACY_STATIC=ON -DBUILD_SHARED_LIBS=OFF \
  -DTRACY_ENABLE=ON \
  -DTRACY_NO_BROADCAST=ON -DTRACY_ONLY_LOCALHOST=ON \
  -DTRACY_NO_SYSTEM_TRACING=ON -DTRACY_NO_CRASH_HANDLER=ON
make -j1 TracyClient
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pthread_setcancelstate` 未声明（TracySystem.cpp:278, 293） | bionic libc 不默认定义 `_GNU_SOURCE`，pthread 的 GNU 扩展（setcancelstate）需宏开启 | `target_compile_definitions(TracyClient PUBLIC _GNU_SOURCE=1)` 加到根 CMakeLists.txt（**但仍不够**，见 #4） |
| 2 | `program_invocation_short_name` / `program_invocation_name` 未声明（TracyProfiler.cpp:442, 461） | 这俩是 **glibc 独有的 `errno.h` GNU 扩展**，bionic **根本没有**这两个符号，加 `_GNU_SOURCE` 也无效 | **Patch #3**：在 OHOS 分支用 `/proc/self/cmdline` 读 argv[0] 替代 `program_invocation_short_name`；用 `readlink /proc/self/exe` 替代 `program_invocation_name` |
| 3 | `__NR_perf_event_open` 未声明（如果启用 TRACY_HAS_SYSTEM_TRACING） | bionic 不暴露 perf_event syscall 号 | 通过 `-DTRACY_NO_SYSTEM_TRACING=ON` 关闭 |
| 4 | #1 的 patch 不够：`pthread_setcancelstate` 即使 `_GNU_SOURCE` 也不存在 | bionic **根本没有**这个 GNU 扩展函数（Android bionic 也缺） | **Patch #2**：把 `#ifndef __ANDROID__` 扩成 `#if !defined(__ANDROID__) && !defined(__OHOS__)` |

## 本地编译验证

- `libTracyClient.a` 487KB（已生成）
- install 列表干净：lib + headers + cmake config，无危险路径
- **smoke test 通过**（exit 0）：
  - `ZoneScoped` + `ZoneName` 调用 OK
  - `FrameMark` 调用 OK
  - 子线程 `tracy::SetThreadName("ohos-smoke-worker")` 跑通（验证 patched thread name + /proc/self/task lookup）
  - 链接 libTracyClient.a + pthread + dl 干净

## 关键编译选项（CMake flags）

```
-DTRACY_STATIC=ON              # 静态库，CI 默认要 .a
-DBUILD_SHARED_LIBS=OFF
-DTRACY_ENABLE=ON              # 必须 ON，库才有功能
-DTRACY_NO_BROADCAST=ON        # 不广播（鸿蒙网络栈有限制）
-DTRACY_ONLY_LOCALHOST=ON      # 只听 localhost
-DTRACY_NO_SYSTEM_TRACING=ON   # 关键：bionic 没有 __NR_perf_event_open
-DTRACY_NO_CRASH_HANDLER=ON    # 关掉信号处理器（鸿蒙信号处理不同）
-D_GNU_SOURCE=1                # 即使没用，也无害
```

## 源码修改（探索阶段直接改）

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译结束**: 2026-07-22 02:35
**最终状态**: built
