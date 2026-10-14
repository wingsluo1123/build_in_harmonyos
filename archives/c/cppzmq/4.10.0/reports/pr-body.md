- **三方库名称**：cppzmq
- **上游版本**：4.10.0（v4.10.0）
- **上游仓库地址**：https://github.com/zeromq/cppzmq
- **适配路径**：路径 A（基础适配，无补丁）
- **使用知识库**：无

> 说明：cppzmq/4.10.0 配方已存在于上游（2026-08-06 合入）。本次变更为在既有配方上**补充 HarmonyOS 专用消费者测试**并完善验证记录，
> 未修改 `conanfile.py` / `conandata.yml`（二者与制品仓中已有版本逐字节一致，故按 R37 无需递增版本后缀）。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 102 | 来源：上游 `tests/*.cpp`（Catch2 v2.13.9，CMake FetchContent） |
| 集成测试 | 0 | — |
| 其他测试 | 0 | — |
| **合计** | **102** | 上游套路以 `-DCPPZMQ_BUILD_TESTS=ON` 独立构建后由 `ctest` 运行 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 102 | 不变 | 上游 Catch2 套件在配方外独立构建执行，102/102 通过 |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test_cppzmq_ohos.cpp`：非断言，真实驱动 inproc REQ/REP 往返 + multipart 编解码 |
| **合计** | **103** | **+1** | 102 上游 + 1 鸿蒙特有消费者用例 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

> 上游 `tests/*.cpp` 与 Catch2 套件保持原样，未做任何改动。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无 HarmonyOS 专用测试，适配后补全了鸿蒙平台消费者测试

> 补全说明：
> - **补全的测试范围**：cppzmq 在 HarmonyOS (OHOS aarch64) 上的端到端消费者可用性 —— 上下文创建、inproc REQ/REP 往返、`zmq_addon` multipart 编解码。
> - **补全原因**：上游仅有 PC/Linux 上的 Catch2 单元测试，缺少鸿蒙平台消费者侧的真实链路验证；本次补齐 rule12 要求的鸿蒙特有非断言用例。
> - **新增测试文件清单**：
>   1. `archives/c/cppzmq/4.10.0/test_package/test_cppzmq_ohos.cpp` — 鸿蒙专用消费者用例（assertion-free，11 项显式校验，失败返回非零退出码）
>   - 接入点：`test_package/CMakeLists.txt`（`add_executable` + `add_test`）、`test_package/conanfile.py` 的 `test()`（`./test_cppzmq_ohos`）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：102/102（100%）
- 新增测试用例通过率：1/1（100%）
  （`test_cppzmq_ohos` 在 `conan create` 中真实执行，输出 11 行 `OK:` 并以 `OHOS consumer test PASSED` 结束）
- 附：随包消费者用例 `test_package/test_cppzmq.cpp`（断言式，5 个断言）亦通过：`cppzmq test passed! All assertions OK.`

### 证据与日志

| 项目 | 证据 |
|------|------|
| `conan create`（含 test_package） | `reports/conan-create.log` |
| W3 本地 CI 模拟（与远端 CI 同脚本/同 profile） | `reports/w3-local-ci.log` |
| 上游 Catch2 套件 102/102 | `reports/upstream-ctest.log` |
| 上游构建工具链（OHOS SDK LLVM） | `reports/upstream-build-cache.txt` |
| W4 Pre-PR 审计 | `reports/audit-result.json`（verdict=pass，P0=0，P1=0） |

## 补充说明

- cppzmq 为 **header-only** 库（`package_type=header-library`），无 `.so`/`.a` 二进制产物；头文件
  `zmq.hpp` / `zmq_addon.hpp` 安装到 `include/`（上游默认行为），另附 `licenses/LICENSE`。
- 运行期依赖 `zeromq/4.3.5`（libzmq），已随 `test_package` 链接并实际调用。
- 配方构建保持 `-DCPPZMQ_BUILD_TESTS=OFF`（header-only，无源码可编译）；上游 Catch2 套件在
  **配方之外的独立 CMake 构建**中执行，两者分开报告，避免把配方外执行误记为配方内执行。
- 本次未修改 `conanfile.py` / `conandata.yml`，故不涉及 R37 版本号递增。
- 已知限制：无。
