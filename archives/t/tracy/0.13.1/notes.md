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
| 5 | init-build 误识别 build_system=autotools | tracy 同时提供 CMakeLists.txt 和 meson.build，init-build heuristic 误判 | manifest.yaml 手动指定 `build_system: cmake` |
| 6 | conandata.yml 7 个 mirror 网络层全挂（403/超时/SSL/500/sha mismatch） | 国内 GitHub 镜像生态不稳定 + Python urllib3 拒弱 SSL 证书 | 手动下载 source tarball 到 conan cache（sha256 校验通过），并预填 conandata.yml 多个 mirror 兜底 |

## 本地编译验证

- `libTracyClient.a` 487KB（已生成）
- install 列表干净：lib + headers + cmake config，无危险路径
- **smoke test 通过**（exit 0）：
  - `ZoneScoped` + `ZoneName` 调用 OK
  - `FrameMark` 调用 OK
  - 子线程 `tracy::SetThreadName("ohos-smoke-worker")` 跑通（验证 patched thread name + /proc/self/task lookup）
  - 链接 libTracyClient.a + pthread + dl 干净

## test_package 验证（conan create 内嵌 ctest）

```
1/1 Test #1: test_tracy .......................   Passed    0.14 sec
100% tests passed, 0 tests failed out of 1
```

22 个 Tracy API + 3 处运行时 assert 通过（详见 `reports/test-report.md`）。

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

## 源码修改（3 个 patch 固化在 patches/）

- `patches/0001-CMakeLists.txt.patch` — 加 `target_compile_definitions(TracyClient PUBLIC _GNU_SOURCE=1)`
- `patches/0002-public-client-TracyProfiler.cpp.patch` — OHOS 分支用 `/proc/self/cmdline` + `readlink /proc/self/exe` 替代 glibc 独有 `program_invocation_*`
- `patches/0003-public-common-TracySystem.cpp.patch` — `#ifndef __ANDROID__` 扩成 `#if !defined(__ANDROID__) && !defined(__OHOS__)` 跳过 `pthread_setcancelstate`

## 依赖版本

- 工具链: clang 15.0.4（来自 ohos-aarch64 conan profile）
- C++ 标准: C++17（libc++）
- 系统依赖: pthread, dl
- Conan deps: 0

## 验证结果

```bash
$ conan create archives/t/tracy/0.13.1 --build=missing \
    -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64
...
1/1 Test #1: test_tracy ... Passed 0.14 sec
100% tests passed

$ python3 scripts/ohc-run.py conan-verify tracy 0.13.1
✅ 配方验证通过: tracy 0.13.1
   可标记 status: published
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libTracyClient.a | 487 KB | 静态库产物 |
| tracy/tracy/*.hpp | ~50 KB | 主公共头 |
| tracy/client/*.hpp | ~80 KB | client 公共头 |
| tracy/common/*.hpp | ~40 KB | 通用头 |
| TracyConfig.cmake | ~2 KB | find_package 配置 |

## 注意事项

- 本 PR **只构建 libTracyClient**；capture GUI（`tracy-capture`/`tracy-profiler` 等）**不在本 PR 范围**，需在桌面 Linux/Windows 上跑
- 鸿蒙平台不能做实际 capture（capture GUI 依赖 wayland/mesa/glfw，鸿蒙桌面侧不提供），仅作 client lib 集成
- `/proc/self/task/<tid>/comm` 的子线程名查询已在本地 smoke test 验证通过；OHOS bionic procfs 与 Linux 同源
- system tracing（perf_event_open）已关闭（OHOS bionic 不暴露该 syscall），不影响 ZoneScoped/FrameMark 等基础功能
- `TRACY_NO_CRASH_HANDLER=ON` 关闭信号处理（OHOS 信号处理与 Linux 不同），不影响 profiling 主体功能

---

**编译结束**: 2026-07-22 04:04
**最终状态**: built / verified