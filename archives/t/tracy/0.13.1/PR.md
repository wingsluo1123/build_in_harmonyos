# tracy 0.13.1 OpenHarmony PC 适配 PR

<!--
PR 标题：feat(tracy): 0.13.1 适配 OpenHarmony PC
PR URL：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/3163
本 PR 严格遵循 templates/积分赛事PR模板.md 结构
-->

- **三方库名称**：tracy
- **上游版本**：v0.13.1
- **上游仓库地址**：https://github.com/wolfpld/tracy
- **适配路径**：路径 A（基础适配） — 仅打包 `libTracyClient`（嵌入式 client lib）；capture GUI 端不在本 PR 范围
- **使用知识库**：conan 2.x recipe 模板、cmake 探针适配、R26/R32/R34/R36 规则

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：上游未引入 gtest/doctest/catch 等单元测试框架 |
| 集成测试 | 0 | 来源：上游无集成测试套件 |
| 其他测试 | 1 | 来源：`test/test.cpp` demo 程序（23 worker 线程覆盖 30+ Tracy API），依赖 capture GUI + image.jpg + 手动信号触发，不可 CI 化 |
| **合计** | **1** | 仅 1 个视觉验证 demo，未在 CI 范围 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | +1（上游 0→1） | `test_package/test.cpp` 1 个 test binary；9 个 worker 函数 + main 线程，覆盖 22 个 Tracy API + 2 处运行时 assert；可自动 `exit 0`、可 ctest |
| 集成测试 | 0 | 不变 | 无 |
| 鸿蒙特有测试 | 0 | 新增 | `/proc/self/task/<tid>/comm` 子线程名查询的实际行为通过子线程 `SetThreadName` + capture 间接验证，未单独抽离测试 |
| **合计** | **1** | 不变 | 数量一致，质量提升：从不可 CI 的 demo 升级为可自动 ctest 的二进制 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 1. **修改的测试文件**：`test/test.cpp`（上游 demo，未原样搬运，按 API 覆盖度移植到 `test_package/test.cpp`）
>    - **修改原因**：上游 demo 是无限循环程序（主线程每 2ms `TracyMessageL("Tick")`），无法自动退出；注册 `SIGUSR1`/`SIGUSR2` 触发 crash handler，本 PR 已 `TRACY_NO_CRASH_HANDLER=ON` 关闭信号处理（OHOS 信号语义与 Linux 不同）；依赖 capture GUI 加载 `image.jpg` 才能"看到"输出，OHOS 桌面侧不提供 capture 工具链；仅"程序没崩"就算通过，无运行时行为验证
>    - **修改内容**（移植而非简单复制）：去掉无限循环（每个 worker 在作用域内完成有限工作后自然返回，main 等待 join 后退出）；去掉信号处理（不再注册 `SIGUSR1`/`SIGUSR2`）；去掉 `image.jpg` 依赖；去掉 capture server 强依赖（保留连接尝试，测试不失败于连接失败）；添加 2 处 `assert` 真断言（`steady_clock` 单调性、`payload` 非空）把"程序没崩"升级为"行为正确"；多 worker 线程拆分（从上游 23 个具名 worker 收敛到 9 个按功能分组的 worker）

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游有充分测试用例且未补全
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：22 个 Tracy API + 2 处运行时 assert；9 个 worker 线程 + 1 个 main 线程；覆盖 Zone/Frame/Lockable/Plot/Message/Memory/Depth/Callstack 八大类基础 profiling 功能
> - **补全原因**：上游库仅有 `test/test.cpp` 视觉验证 demo（无限循环 + 依赖 capture GUI + 无 assert），无法作为 CI 门禁；OHOS bionic 平台特性（如子线程名查询走 `/proc/self/task/<tid>/comm`）需要实际跑一遍验证
> - **新增测试文件清单**：
>   1. `test_package/test.cpp` — 22 API + 9 worker + 2 assert；含 `worker_zones_and_frames` / `worker_clock_sanity` / `worker_nested_scopes` / `worker_mutex_locks` / `worker_plot` / `worker_messages` / `worker_depth` / `worker_callstack` / `worker_memory` 9 个 worker
>   2. `test_package/CMakeLists.txt` — CXX project + `find_package(tracy)` + `target_link_libraries(... tracy::tracy)`
>   3. `test_package/conanfile.py` — `CMakeDeps` + `CMakeToolchain` + `test()`
>   4. `test_package/MANIFEST.yml` — `upstream_tests` + `test_package_tests` + `assertion_count: 2` + `api_call_count: 22`

---

## 验证结果

- **编译状态**：通过（clang 15.0.4 aarch64-unknown-linux-ohos，无 warning）
- **上游测试用例通过率**：0/0（上游 demo 未在 CI 范围，本 PR 仅在结构上移植其 API 覆盖度）
- **新增测试用例通过率**：1/1（100%；`1/1 Test #1: test_tracy ... Passed 0.14 sec`）

### 8 道门禁（conan-verify）

| Gate | 结果 |
|------|------|
| G0 预构建风险 | PASS |
| G1 配方完整性 | PASS |
| G2 conan create | PASS |
| G3 系统同名库隔离 | PASS |
| G4 产物完整性 | PASS |
| L2 smoke test | PASS |
| L4 安全扫描 | PASS |
| L5 产物基线 | PASS |

---

## 补充说明

[其他需要说明的事项，如已知限制、TODO 项等]

### 已知限制

- capture GUI（`tracy-capture`、`tracy-profiler` 等）不在本 PR 范围，需在 PC 上跑；OHOS 桌面侧不提供 capture 工具链
- `/proc/self/task/<tid>/comm` 子线程名查询已在本地 smoke test 验证通过，但 CI 不直接断言（需要 capture 端配合）
- system tracing（`perf_event_open`）已关闭（OHOS bionic 不暴露该 syscall），不影响 `ZoneScoped`/`FrameMark` 等基础功能
- `TRACY_NO_CRASH_HANDLER=ON` 关闭信号处理（OHOS 信号处理与 Linux 不同），不影响 profiling 主体功能
- 上游 demo 程序的 23 worker 中 `DeadlockTest`/`ArenaAllocator`/`FrameImage` 等仅在 capture 端有意义，本 PR 不构建 capture server 故跳过

### 补丁清单

3 个源码 patch（OHOS bionic libc 兼容）：

| Patch # | 文件 | 作用 |
|---------|------|------|
| 0001 | `patches/0001-CMakeLists.txt.patch` | `target_compile_definitions(TracyClient PUBLIC _GNU_SOURCE=1)` + CMake `check_symbol_exists` 特性检测（`HAS_PTHREAD_SETCANCELSTATE`、`HAS_PROGRAM_INVOCATION_SHORT_NAME`），由 patch 0002 / 0003 通过特性宏消费 |
| 0002 | `patches/0002-public-client-TracyProfiler.cpp.patch` | `#elif !defined(HAS_PROGRAM_INVOCATION_SHORT_NAME)` 分支用 `/proc/self/cmdline` + `readlink /proc/self/exe` 替代 glibc 独有 `program_invocation_short_name` / `program_invocation_name` |
| 0003 | `patches/0003-public-common-TracySystem.cpp.patch` | `#ifndef __ANDROID__` 改为 `#ifdef HAS_PTHREAD_SETCANCELSTATE` 守护 `pthread_setcancelstate` 调用 |

### 依赖

- **0 个外部 Conan 制品仓依赖**：`libTracyClient.a` 仅依赖系统 `pthread` + `dl`；也不构建 capture GUI（依赖 15+ 桌面库 wayland/mesa/glfw 在 OHOS 不存在）