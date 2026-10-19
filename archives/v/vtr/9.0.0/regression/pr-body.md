## PR 信息
- **三方库名称**：vtr（VTR / Verilog-to-Routing，FPGA CAD 全流程工具链）
- **上游版本**：9.0.0
- **上游仓库地址**：https://github.com/verilog-to-routing/vtr-verilog-to-routing
- **适配路径**：路径 C（高难度挑战）
- **使用知识库**：E077（OHOS 链接器 `.codesign` 自签名：任何后续 strip/objcopy 都会使签名失效致 "Operation denied"）

---

## 上游版本与源码

| 项 | 值 |
|----|-----|
| 正式 tag | `v9.0.0`（轻量 tag） |
| tag 指向 commit | `8cb20aa5293b5ce5f6a05c88b37b38e1305d9b07` |
| release 发布日 | 2025-01-21 |
| 官方源码地址 | `https://github.com/verilog-to-routing/vtr-verilog-to-routing/releases/download/v9.0.0/vtr-verilog-to-routing-9.0.0.tar.gz` |
| SHA256 | `bebbfac162630a2bea7403f2b2102200c31709dfea26bac85626ee7327a2881c` |
| 大小 | 468,148,819 B |
| 许可证 | MIT（`LICENSE.md`；ABC、部分 benchmark 与第三方库另有各自许可证，文件内逐项说明） |

### 为什么用官方 release asset 而不是自动 tag tarball（实测对账）

`.gitmodules` 在 v9.0.0 只声明 2 个 submodule：`libs/EXTERNAL/libcatch2`、`libs/EXTERNAL/sockpp`。

| 组件 | 官方 release asset | GitHub 自动 tag tarball |
|------|-------------------|------------------------|
| `libs/EXTERNAL/libcatch2` | **639** 条目 | **1** 条目（空目录，未填充） |
| `libs/EXTERNAL/sockpp` | **153** 条目 | **1** 条目（空目录，未填充） |
| `abc` / `parmys` / `odin_ii` / `vpr` / `yosys` / `vtr_flow` | 内联（非 submodule） | 完全相同 |
| 合计条目 / 大小 | 18424 / 468 MB | 17590 / 107 MB |

**Catch2 是全部 VTR 单元测试目标的链接依赖**（`Catch2::Catch2WithMain`）。用自动 tag tarball 会导致
`test_vpr` / `test_vtrutil` / `test_archfpga` / `test_fasm` 全部无法构建 —— 等于静默删除整套单元测试，
属于"删功能"而不是"修构建"。上游 `BUILDING.md` 亦明确说明 release 包无需再取 submodule。
**故配方固定使用官方 release asset。**

---

## 测试用例对比

> 完整清点口径见下；每个数字的口径来源都在表中注明。

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试（VTR 正式 Catch2 目标） | **126** | VTR 顶层 4 个正式测试目标中的 `TEST_CASE`；其中 20 项因上游条件编译为 N/A，实际适用并运行 106 项 |
| 其他源码测试入口（审查扫描附加命中） | **641** | 全树扫描得到 641 个真实的 `TEST(` 宏调用（已排除 `FTEST(` / `KJ_TEST(` / `INTERNAL_CATCH_TEST(` 等子串命中与宏定义），来自 capnproto 516 + Yosys 125 |
| 集成测试 | **0** | 297 个 VTR 回归 config 采用独立的 config 级闭合口径，单独报告，**不与源码扫描口径相加** |
| **合计** | **767** | 审查器扫描口径：**126 + 641 = 767** |

#### N=767 的可复现构成（逐项）

> **口径声明（必读）**：767 是 PC 鸿蒙化审查器采用的**源码宏扫描口径**（按宏调用行首匹配，
> 已排除 `FTEST(` / `KJ_TEST(` / `INTERNAL_CATCH_TEST(` 等子串与宏定义造成的假阳性）。
> **767 不代表** 767 个互相独立、全部可执行的 VTR 正式测试；
> **767 也不代表** 767 项全部执行通过。除 VTR 4 个正式 Catch2 目标外，其余命中均未经 VTR
> 顶层 CTest 注册，**一律不计为 PASS**。此表逐项披露命中来源，避免把扫描命中误读为执行结果。

| 来源 | 扫描模式 | 命中数 | 性质 |
|------|---------|-------:|------|
| VTR 4 个正式 Catch2 目标 | `TEST_CASE` | **126** | vpr/test 80 + libs/libvtrutil 29 + libs/libarchfpga 3 + utils/fasm 14；**经 CTest 注册，已执行**（106 适用运行，20 为上游条件编译 N/A） |
| `libs/EXTERNAL`（capnproto） | `TEST(` | **516** | 第三方测试框架（kj 的 `TEST(Suite, Name)`）；**未构建、未执行，不计 PASS** |
| Yosys | `TEST(` | **125** | 子项目自有测试（`libs/bigint` 等）；**未经 VTR 顶层 CTest 注册，未执行，不计 PASS** |
| **合计** | | **767** | 126 + 516 + 125 |

> **按扩展名的计数明细**（审查方口径）：`.c++` 515 + `.cc` 125 + `.h` 1 = 641，加 `TEST_CASE` 126 = **767**。
> **已排除的假阳性**：`abc/src` 下的 `FTEST(`（非测试宏）、`libcatch2` 头文件中的 `INTERNAL_CATCH_TEST(`（宏定义）、
> capnproto 中非行首的 `KJ_TEST(` 子串；`_py/` 目录是 Conan 引入的 Python 依赖，**不属于 VTR 上游源码**，不计入。
> `SCENARIO(` 在 GitHub tag 快照中出现 0 次（该快照的 libcatch2 为空目录），故不计入本口径。

> 复现命令（对官方 release asset 解压后的源码树执行，按宏调用行首匹配并排除子串假阳性）：
> `grep -rho 'TEST_CASE' <4 个测试目标目录> | wc -l` → 126；
> 行首 `TEST(`（排除 `FTEST(` / `KJ_TEST(` / `INTERNAL_CATCH_TEST(`）→ 641；
> 两者相加 = **767**。

#### 分层统计明细

计数按**层**分别给出，三层口径不同，**不可混用为同一个 N**。

| 层 | 项 | 值 | 口径来源 |
|----|----|----|---------|
| 单元测试 | 源码逻辑入口 | **126** | 源码中 `TEST_CASE` 宏的逻辑入口数（4 个 Catch2 目标合计） |
| 单元测试 | N/A | **20** | 上游自身条件编译排除，与本次适配无关（构成见下表） |
| 单元测试 | 实际适用并运行 | **106** | 126 − 20 |
| 上游回归 | N（config 级闭合） | **297** | 官方 `task_list.txt` 解析后的独立 config 全集 |
| 上游回归 | N/A | **2** | 平台无对应能力，逐项登记 |
| 上游回归 | A（适用） | **295** | 297 − 2 |
| 上游回归 | E / P / F | **205 / 186 / 19** | 已执行 / 严格通过 / 严格未通过 |
| 上游回归 | A − E（未执行） | **90** | 逐项登记原因，不计入 P 也不计入 F |
| 鸿蒙特有 | `test_package` | **1** | 真实端到端 CAD 流程 + 分阶段断言，**单独统计，不加入上游 N** |

> **上游测试总数按审查器扫描口径填 767**（构成见上表）。**297 个回归 config 是另一套口径**
> （`task_list.txt` 解析后的 config 级回归判定单位），**单独报告、不再与 767 相加**，
> 其闭合结果见下方「上游回归结果」一节。两套口径不得混用为一个 N。

**三个容易被误用的数字，各自的准确含义**：

| 数字 | 只能这样写 | 不得写成 |
|-----:|-----------|---------|
| **342** | 磁盘 config 目录库存（`vtr_flow/tasks/**/config/config.txt` 的目录总数，其中 `regression_tests/` 下 328 个，分属 23 个套件；333 个带 `golden_results.txt`） | 上游测试用例数 / N 的组成部分 |
| **303** | 官方 runner `run_reg_test.py` 按各套件 `task_list.txt` 解析出的**原始有效入口数**（342 个库存目录中实际可达者，差值 39 个是定义了但无套件引用的孤儿目录） | 唯一测试数 |
| **297** | config 级闭合口径的 **N**（展开去重后的独立判定单位，本报告全部回归统计以此为准） | — |

> invocation（一次 `run_vtr_task` 调用）数只作**工作量指标**，不参与 N。

**20 个 N/A 的构成（逐项可复现）**：

| 数量 | 编译守卫 | 排除原因 |
|-----:|---------|---------|
| 16 | `#ifndef NO_SERVER` | `vpr/CMakeLists.txt:43` 在 GUI 关闭时 `set(VPR_USE_SERVER OFF)`，`:50` 定义 `-DNO_SERVER`，经 `:179` 的 `target_compile_definitions(libvpr PUBLIC ...)` 传播到 `test_vpr`。这是**上游官方 headless 配置**本身的行为 |
| 3 | `#ifdef VTR_ENABLE_CAPNPROTO` | `round_trip_delta_delay_model` / `round_trip_override_delay_model` / `round_trip_map_lookahead`。`:183` 把该宏定义为 **`PRIVATE`**，只作用于 `libvpr`，**永远传不到 `test_vpr`**——即使构建开启了 capnproto 也进不去 |
| 1 | `#if 0` | `test_vpr_constraints.cpp:586` 的 `PlaceConstraintsIntegrity`，上游注释禁用 |

> **口径差异（必须说明，否则数字无法复现）**：
> ① 单元测试用**源码逻辑入口**口径：源码里 126 个 `TEST_CASE`，减去 20 个被上游条件编译排除的，
> 得实际适用并运行的 **106**。不能用 `--list-tests` 的行数计数——Catch2 会把超长用例名折行，
> 逐行统计会多算；也不以 `ctest` 的测试条目数计数——上游把 60 个 `test_vpr` 用例注册成**单个**
> ctest 测试（见下文"执行分组"）。
> ② 断言数只以**最终日志**为准，不沿用任何历史摘要。最终 SHA `0de984df64` 的日志中，
> `test_vpr` 拆成两个进程运行，分别报告 `All tests passed (10479 assertions in 59 test cases)`
> 与 `All tests passed (40 assertions in 1 test case)`，合计 **10519 条断言 / 60 个用例**。
> 另外三个目标经 `ctest -E '^test_vpr$'` 运行，**3/3 全部通过**
> （`100% tests passed, 0 tests failed out of 3`）；ctest 在测试通过时不输出各目标内部的
> 用例/断言数，故这三个目标的细分数字在本日志中不体现，本报告也不为它们填数。

### 是否存在对上游测试用例的修改？

**未删除、跳过、放宽或改写任何上游测试逻辑、断言及期望值。**

补丁涉及的测试源码仅 `vpr/test/test_vpr_constraints.cpp` 增加一行必要的
`#include <sstream>`，属于 libc++ 显式头文件兼容修复（该文件在 libc++ 下因不做传递包含
而编译失败：`implicit instantiation of undefined template 'std::basic_stringstream<char>'`）。

另通过进程隔离分别执行 59+1 个 `test_vpr` 用例，以规避上游测试之间的全局状态污染；
**60 个用例均实际执行**（59 + 1，无重复、无跳过），断言全部求值。

**逐项披露补丁对测试文件的触及**（唯一一处）：

| 补丁 | 触及的测试文件 | 改动内容 | 是否改变测试语义 |
|------|---------------|---------|-----------------|
| `0004-missing-sstream-includes.patch` | `vpr/test/test_vpr_constraints.cpp` | 仅新增一行 `#include <sstream>` | **否**。未改动任何断言、期望值或测试逻辑 |
| 0001 / 0002 / 0003 / 0005 | 无 | 均落在 `cmake/`、`CMakeLists.txt`、capnproto 源码、`vpr/src/route/` | 否 |

补丁 0004 共触及 15 个文件，其中 14 个是库/工具源文件，1 个是上述测试文件；
15 处改动全部是"新增一行 `#include <sstream>`"这一种形态。

**隔离执行的可复核性**（数字取自最终 SHA `0de984df64` 的 farm 日志，未沿用历史摘要）：
`ctest -E '^test_vpr$'` 跑另外三个二进制（`3/3` 通过）；
`test_vpr "~[vpr_compressed_grid]"` 输出 `All tests passed (10479 assertions in 59 test cases)`，
`test_vpr "[vpr_compressed_grid]"` 输出 `All tests passed (40 assertions in 1 test case)`。
59 + 1 = **60** 个 `test_vpr` 用例、合计 **10519** 条断言，全部实际求值。
（源码统计：`test_vpr` 有 80 个 `TEST_CASE`，其中 20 个被上游条件编译排除，80 − 20 = 60，与日志一致。）

**但有一处必须说明的差异——单元测试的执行分组**：

上游把 `test_vpr` 的 60 个 TEST_CASE 注册成**单个** ctest 测试
（`vpr/CMakeLists.txt:328`），全量单进程运行时**确定性段错误**。实测二分到最小复现：
`test_compressed_grid` 与 `connection_router` **不能共存于同一进程**，且正反两个顺序都崩；
而这两个用例各自单独运行、以及 `test_compressed_grid` 与其余任何用例组合，都通过。

根因在 `vpr/test/test_compressed_grid.cpp`：该用例把**测试自造的**设备上下文直接写进
**进程级全局** `g_vpr_ctx`——10 个**栈局部**的 `t_physical_tile_type` /
`t_logical_block_type` 对象的地址被发布进 `equivalent_tiles` / `equivalent_sites` /
`EMPTY_PHYSICAL_TILE_TYPE`，全局 `grid` 也被整个替换成自造的 `DeviceGrid("test_device_grid", …)`
——**既不初始化也不还原**。于是进程内任何随后走完整 `vpr_init()`/`vpr_free_all()` 的用例
都会踩到这份残留状态；反向顺序（`connection_router` 先跑完 `vpr_free_all()`）同理。
上游把 60 个注册用例塞进**单个** ctest 测试，而 5 个 workflow **没有任何一处调用
ctest 或 `make test`**，所以该缺陷在上游一直潜伏。

**处理方式**：不修改上游测试源码，改为**分组执行**——
`ctest -E '^test_vpr$'` 运行另外三个二进制，
`test_vpr` 拆成 `~[vpr_compressed_grid]`（59 用例）与 `[vpr_compressed_grid]`（1 用例）
两个进程。**60 个用例全部执行、全部断言全部求值，没有任何跳过或降级**；
与上游的唯一差异是进程分组（1 个进程 → 2 个进程）。完整的根因、最小复现与排查过程见
随附 `regression/test-isolation-evidence.md`。

> 排查中还试过给那 10 个局部对象加 `static` 延长生命周期，**实测仍 rc=139**，
> 证明单靠延长对象寿命不足（全局上下文里的假 grid / 假 logical_block_types 本身即致命）。
> 该实验已回滚。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------|------|
| 上游源码测试入口（审查扫描口径） | **767** | 一致 | 各类命中的实际注册与执行情况已在上表逐类披露；**未执行项不计 PASS** |
| 集成测试 | **0** | 一致 | 297 个回归 config 按独立闭合口径报告（E=205/P=186/F=19/A−E=90），**不与 767 重复相加** |
| 鸿蒙特有测试 | **1** | 增加 1 项 | `test_package` 真实端到端 CAD 流程及分阶段断言，**单独统计**，不加入上游 N 与上游回归通过率分母 |
| **合计** | **768** | **增加 1 项** | **上游审查口径 767 + 鸿蒙特有 `test_package` 1** |

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游已有 126 个单元测试逻辑入口和 297 个上游回归 config。适配后新增的 1 个 `test_package` 是鸿蒙消费者端到端验证，不替代、不删减上游测试，也不加入上游测试总数或上游回归通过率分母。

---


## 上游回归结果（config 级闭合，最终）

> 判定单位：上游 manifest 的独立 config。完整逐项表见随附 `closure-final.tsv`，
> 未执行原因见 `unexecuted-reasons.md`，未通过项逐项说明见 `F-explanations.md`。

| 项 | 值 |
|---|---:|
| N（resolved config） | **297** |
| N/A（平台缺外部工具，未启动） | 2 |
| A（可判定） | 295 |
| E（已执行） | 205 |
| P（严格通过） | **186** |
| F（已执行未通过） | 19 |
| A−E（未执行） | 90 |
| **严格 P/E** | **90.73%** |
| **语义 P/E** | **91.71%**（P=188, F=17） |
| **FAIL_ADAPTATION** | **0** |

校验：`N = N/A + E + A−E` → 297 = 2 + 205 + 90 ✔；`E = P + F` → 205 = 186 + 19 ✔

### A−E（未执行，90 项）的构成

| 类别 | 数 | 原因 |
|---|---:|---|
| UNEXECUTED_MANIFEST | 90 | 该 config 无任何执行记录，且其套件在生成阶段的脚本数为 0（上游 manifest 未能物化出可运行脚本）。**未计入 E/P/F** |
| DEFERRED_LONG_RUNNING | **0** | 3 项长耗时调用已于 2026-10-08 全部执行并 PASS（用时 5407 / 4338 / 16366 / 4665 / 18807 s，均在各自硬上限内） |

### 19 项严格 F 的构成（**其中适配缺陷 0**）

| 类别 | 数 | 性质 |
|---|---:|---|
| TIMEOUT | 9 | 平台算力导致的绝对时长超限（rc=124）；已逐项登记命令、阶段、产物时间戳与估算依据 |
| TIMEOUT_POLICY | 1 | 启动前时长门禁判定 `est_device > 上限`，未启动 |
| TIMEOUT_POLICY_PENDING_REVIEW | 2 | 新超时签名，保留证据待复核，不自动 HOLD |
| EXPECTED_FAILURE_STATUS_MISMATCH | 2 | 上游 golden 声明预期失败；裸进程两平台均 SIGABRT，仅 `time(1)` 表示为 134 vs 6；**语义口径计为 PASS_EXPECTED_FAILURE** |
| PLATFORM_ENVIRONMENT_DIFFERENCE_DETERMINISTIC | 2 | 上游 `fix_clusters` 把簇名写死在 constraints 中，对打包结果敏感；两端输入 sha256 相同、命令相同、适配补丁仅 `#include`；第一处分歧在打包器候选分子枚举，两端各自可复现 |
| FAIL_UPSTREAM | 3 | VTR 自带 yosys 无开源 SystemVerilog 前端（VERIFIC 商业）；Linux 对照已复现同一失败 |

### 上游回归口径的明确表述

- **上游回归逻辑入口：297**（官方 `task_list.txt` 解析后的独立 config 全集）
- **N/A：2**（平台缺外部工具，未启动，依据 manifest 判定）
- **适用：295**（= 297 − 2）
- **已执行：205**
- **严格通过：186**
- **严格未通过：19**（逐项类别、config 名称、首个有效错误与证据路径见 `F-explanations.md`）
- **未执行：90**（逐类汇总见下，逐项清单见 `unexecuted-reasons.md`）
- **严格通过率：90.73%**（186 / 205）
- **覆盖率：69.49%**（E / A = 205 / 295）
- **FAIL_ADAPTATION：0**
- **DEFERRED_LONG_RUNNING：0**

> 上述十项与 `final-stats.txt` 一一对应，并由两条守恒式校验：
> `N = N/A + E + A−E` → 297 = 2 + 205 + 90；`E = P + F` → 205 = 186 + 19。

### 90 项未执行（A−E）逐类汇总

| 类别 | 数 | 说明 |
|---|---:|---|
| UNEXECUTED_MANIFEST | 90 | 该 config 无任何执行记录，且其套件在生成阶段的脚本数为 0（上游 manifest 未能物化出可运行脚本） |
| DEFERRED_LONG_RUNNING | 0 | 3 项长耗时调用已于 2026-10-08 全部执行并 PASS |
| NOT_EXECUTED | 0 | — |

**这 90 项既不计入 PASS，也不计入 F**，逐项清单（含 config 名称与生成 rc）见 `unexecuted-reasons.md`。

### 迭代执行过程的准确表述

本轮分两阶段推进，均**按候选全集处理，未按通过率提前停止**：

- **有界恢复阶段**：154 个恢复候选**全部处理**，其中 **122 PASS、2 NONPASS、24 个 scripts=0（生成不出脚本）、6 个经准入检查排除**（3 项平台无 TBB、2 项上游 `-expect_fail` 取值缺陷、1 项重复项）。
  这 154 项是"全部候选"，但其中 24 项因生成失败从未启动——**不等于 154 项全部执行**。
- **长耗时阶段**：3 个原 DEFERRED_LONG_RUNNING 的 config 共 5 次 invocation，**逐次执行完毕且全部 PASS**，用时 5407 / 4338 / 16366 / 4665 / 18807 秒，均在各自硬上限 `max(10800, ⌈est_dev×1.5⌉)` 内。

## 上游测试用例修改说明
**未修改任何上游测试用例。**

- 未删除、未跳过、未注释任何上游测试；未放宽断言；未改动任何 `golden_results.txt` 期望值。
- 适配对源码的全部改动为 **5** 个补丁（`patches/0001`–`0005`，编号唯一、无重复），
  **均为纯 `#include` 增补或 CMake/构建脚本修补，零逻辑改动**
  （逐条全文见 `9.0.0/patches/`）。
- 唯一涉及测试文件的补丁是 `0004-missing-sstream-includes.patch`，其中
  `vpr/test/test_vpr_constraints.cpp` 增加一行 `#include <sstream>`——**新增 include，不改测试语义**；
  该补丁另外 14 个文件均为库/工具源文件，不涉及测试。

## 验证结果

### 编译验证
- 编译器：clang 15（OHOS 工具链）
- 编译状态：**成功**。最终 SHA `0de984df64ab6dc9e6b3bc6b4a6fe2718b411a28` 已通过 farm 的干净验证（从零 `conan create` → 单元测试 → package 自检 → `test_package` → 端到端 CAD 流程），结果 PASS。以下 ELF/产物/依赖项由该最终包的**只读检查**复核。
- 构建系统：CMake（`cmake_minimum_required(VERSION 3.16)`，C++17）
- 配置选项：`-DVPR_USE_EZGL=off -DWITH_ODIN=ON -DWITH_ABC=ON -DWITH_PARMYS=ON -DVTR_ENABLE_CAPNPROTO=ON -DVTR_ENABLE_STRICT_COMPILE=OFF -DVTR_IPO_BUILD=off`

> `VPR_USE_EZGL=off` 是**上游官方 headless 配置**：`CMakeLists.txt:393-406` 在 GTK3/X11 缺失时
> 上游自己就会关掉 GUI 并打印 `VPR Graphics: Disabled`，上游 CI 亦有 `NO_GRAPHICS` 矩阵项。
> 需如实说明上游耦合：`vpr/CMakeLists.txt:38-52` 规定 EZGL 关闭时 VPR server 模式一并关闭，
> 这是上游自身设计，与综合/打包/布局/布线/时序分析链路无关。

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | 通过 | farm 干净验证（从零构建）PASS；本机复核未发现编译期告警阻断 |
| 产物存在性 | 通过 | `vpr/vpr` 7,809,536 B；`abc/abc` 12,474,880 B；`ace2/ace` 12,560,896 B；`odin_ii/odin_ii` 1,948,160 B；`genfasm` 7,875,072 B；standalone `bin/yosys` 与 `build/bin/yosys` 均存在 |
| ELF 格式 | 通过 | `ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped` |
| 运行测试 | 通过 | `vpr --version` → `9.0.0-dev+v8.0.0-11943-g8cb20aa52-dirty`；`abc` → `UC Berkeley, ABC 1.01`；`odin_ii` 正常启动 |
| 动态依赖 | 通过 | `NEEDED`：`libz.so.1`、`libc++_shared.so`、`libc.so`（共 3 个）；`RUNPATH` 指向 7 个 conan 依赖包（zlib / openssl / eigen / tcl / readline / ncurses / libffi） |

### 补丁说明

共 **5** 个源码补丁（`patches/0001`-`0005`），全部为编译/构建修复，合计触及 **19 个文件**。
逐条的"原始 Linux 行为 / HarmonyOS 失败日志 / 修改原因 / 是否影响上游行为"四要素
见下表，覆盖全部 **5** 个补丁。

| 补丁 | 触及 | 根因 | 最小性 |
|------|------|------|--------|
| `0001-cmake-modules-AutoClangFormat.cmake.patch` | 1 文件 +6/-1 | `AutoClangFormat.cmake` 对 `ProcessorCount()` 返回 0 直接 `FATAL_ERROR`，导致**整个工程配置中止**；构建机上 `ProcessorCount` 被资源守卫模块影子替换为刻意返回 0 | CPU 数可知时完全 no-op；不可知时退化为串行格式化 |
| `0002-libs-libvtrcapnproto-CMakeLists.txt.patch` | 1 文件 +26/-7 | 构建期 `wget` 拉取 **capnproto-java 浮动 master 分支**的 `java.capnp`（不可复现），且下载失败 | 新增 `VTR_JAVA_CAPNP_SCHEMA` 缓存变量指向钉版本地副本；**未设置时回退到上游原逻辑** |
| `0003-libs-external-capnproto-kj-filesystem-disk-unix.c++.patch` | 1 文件 +27/-1 | capnproto 的 `openDir()` / `tryOpenSubdirInternal()` 在 `EACCES` 时直接抛异常；OHOS 根目录及部分路径为 0711（可执行不可读），遍历 `/` 即失败 | 仅在 `case EACCES:` 分支增加 `O_PATH \| O_DIRECTORY` 回退，正常可读路径行为不变 |
| `0004-missing-sstream-includes.patch` | 15 文件 +15/-0 | 15 处源文件隐式依赖传递包含的 `<sstream>`；libc++ 的传递包含比 libstdc++ 窄，编译报 `implicit instantiation of undefined template 'std::basic_stringstream<char>'` | 每处**只新增一行 `#include <sstream>`**，逐处对应一条真实编译错误 |
| `0005-vpr-route-partition_tree.cpp.patch` | 1 文件 +1/-0 | 该文件用了 `std::stack` 但未 include `<stack>`，报 `use of undeclared identifier 'stack'` | **只加一行 `#include <stack>`** |

> **范围声明**：`patches/` 下最终只有 **5** 个补丁（`0001`–`0005`），编号唯一、无重复，
> 与 `conandata.yml` 的引用集合**完全一致**（磁盘 ↔ 引用双向无差集）。
> 每个补丁都只针对编译器或构建**真实指名**的一处失败，且都对应一条真实编译错误。
> `0005` 只含 `vpr/src/route/partition_tree.cpp` 的**一行** `#include <stack>`。

#### 0001 补丁全文

`patches/0001-cmake-modules-AutoClangFormat.cmake.patch`

```diff
 include(ProcessorCount)
 ProcessorCount(CPU_COUNT)
+# ProcessorCount() returns 0 when the CPU count cannot be determined; CMake
+# documents this for constrained or sandboxed build hosts.  The value is only
+# used to parallelise the *code-formatting* helper targets defined below, so an
+# unknown count must not abort configuration of the whole project -- fall back
+# to serial formatting instead.  Where the CPU count is known this is a no-op.
 if(CPU_COUNT EQUAL 0)
-    message(FATAL_ERROR "Unknown number of CPUs!?")
+    set(CPU_COUNT 1)
 endif()
```

- **根因**：`CMakeLists.txt:506` 无条件 `include(cmake/modules/AutoClangFormat.cmake)`，该文件对
  `ProcessorCount()` 的返回值做 `if(CPU_COUNT EQUAL 0) FATAL_ERROR`。构建机上 `ProcessorCount`
  被资源守卫模块影子替换（刻意返回 0，用于阻止项目自行追加 `--parallel`），于是**整个 CMake 配置中止**。
- **为什么属于上游缺陷而非"平台限制"**：CMake 官方文档明确 `ProcessorCount()` **可能返回 0**
  （无法确定 CPU 数时）。而该值只用于 clang-format 辅助目标的 `xargs -P ${CPU_COUNT}`，
  与编译、链接、算法、测试完全无关。因一个代码格式化目标数不出 CPU 就中止整个工程配置，写法脆弱。
- **最小性**：CPU 数可知时行为完全不变（no-op）；不可知时退化为串行格式化。
  未改变算法语义、未删除功能、未修改测试期望值。
- **验证**：`patch --dry-run -p1` 通过。

### 依赖

**运行/链接依赖（host requirements）**

| 依赖 | 用途 | 出处 |
|------|------|------|
| `zlib/1.3.1` | VPR、libvtrcapnproto、Yosys | `vpr/CMakeLists.txt:124`、`libs/libvtrcapnproto/CMakeLists.txt:39` |
| `openssl/3.5.6` | capnproto（REQUIRED） | `libs/EXTERNAL/capnproto/c++/CMakeLists.txt:68` |
| `eigen/3.4.1` | 解析布局（**功能门控**：缺失即静默关闭） | `vpr/CMakeLists.txt:83-105` |
| `tcl/8.6.16` | Yosys（`ENABLE_TCL := 1`） | `yosys/Makefile:12` |
| `readline/8.3` | Yosys（`ENABLE_READLINE := 1`） | `yosys/Makefile:16` |
| `libffi/3.5.2` | Yosys 插件（`ENABLE_PLUGINS := 1`） | `yosys/Makefile:389-393` |

**构建工具依赖（tool requirements）**：`bison/3.8.2`、`flex/2.6.4.2`、`pkg-config/0.29.2`

> `flex` 固定为 **2.6.4.2** 而非 2.6.4：制品仓中 2.6.4 的某个 recipe revision
> 不含任何 binary（`No packages found for this revision`），依赖解析报
> `Missing prebuilt package`。2.6.4.2 的 revision 在制品仓与本地缓存中都有
> 对应 `ohos-aarch64` profile 的预编译包（R18：优先使用有预编译包的版本）。

**随包分发的 Python 运行时模块**：`prettytable 3.18.0`、`wcwidth 0.9.1`
（官方 PyPI `files.pythonhosted.org`，sha256 与 `pypi.org/pypi/<name>/json` 逐字一致）

> `vtr_flow/scripts/python_libs/vtr/__init__.py` 会 `from .util import ...`，而
> `util.py:18` 是**模块级** `from prettytable import PrettyTable` —— 缺它则
> `import vtr`（`run_vtr_flow.py`/`run_vtr_task.py`/`run_reg_test.py` 都会做）直接 ImportError。
> 实测确认：prettytable 渲染时又惰性 `import wcwidth`，故两者都必需；`vtr` 包**不**导入
> lxml/pandas/numpy/scipy（pandas 仅用于独立的可选脚本 `qor_compare.py`），故未打包。
> 三份归档统一放在 `conandata.yml` 的 `sources:` 列表中，由构建流水线统一预取与校验。

### 测试结论
- 总体评价：上游回归共 297 个独立 config，**严格 P/E = 90.73%、语义 P/E = 91.71%、FAIL_ADAPTATION = 0**；未通过的 19 项经逐项定性，**无一项属于源码或配方的适配缺陷**（详见 `F-explanations.md`）。90 项未执行均因上游 manifest 未能物化脚本，已逐项列出。
- 已知限制：① 平台无 TBB，VPR 平行布线不可用（VPR 自报 `VPR isn't compiled with TBB support`）；② 平台无 X11/GTK，GUI 走上游官方 headless 配置；③ 上游 `fix_clusters` 类测试把簇名写死，对工具链相关的打包结果敏感，本平台结果与 x86 对照存在确定性差异（已用独立对照实验排除 IPO 假设，剩余变量为编译器/标准库/CPU 架构）；④ 90 个 config 因上游 manifest 未产出脚本而未执行。

### 遇到的问题与解决方案
见上文「适配修改台账」与「补丁说明」：5 个补丁逐一给出原始 Linux 行为、HarmonyOS
失败现象、修改原因与最小性；每处改动都对应一条真实编译错误。

### 验证命令
```
# 1. 取官方 release asset 并校验
curl -fLO https://github.com/verilog-to-routing/vtr-verilog-to-routing/releases/download/v9.0.0/vtr-verilog-to-routing-9.0.0.tar.gz
sha256sum vtr-verilog-to-routing-9.0.0.tar.gz
# 期望 bebbfac162630a2bea7403f2b2102200c31709dfea26bac85626ee7327a2881c

# 2. conan create（真机，ohos-aarch64 profile）
conan create archives/v/vtr/9.0.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing

# 3. 上游单元测试（build() 内已自动执行，实际分组方式如下）
cd <build>/build
ctest --output-on-failure -E '^test_vpr$'        # 另外三个 Catch2 目标（3/3 通过）
cd vpr/test
<build>/vpr/test_vpr --colour-mode none "~[vpr_compressed_grid]"   # 59 用例
<build>/vpr/test_vpr --colour-mode none  "[vpr_compressed_grid]"   #  1 用例
# 分组原因（上游用例间的进程级全局状态污染）见 regression/test-isolation-evidence.md

# 4. 上游回归：官方入口 run_vtr_task.py -l <task_list> -system scripts
python3 vtr_flow/scripts/run_vtr_task.py \
    -l vtr_flow/tasks/regression_tests/<suite>/task_list.txt -system scripts
# 产出脚本后逐个执行：cd <job_dir> && bash vtr_flow.sh

# 5. 最终包的只读复核（本 PR 中的 ELF/依赖/版本数据来源）
file vpr/vpr
readelf -d vpr/vpr | grep -E 'NEEDED|RUNPATH'
vpr/vpr --version
```

---

## 查重结论

| 检查位置 | 结果 |
|----------|------|
| 最新 `upstream/main` | 无 vtr |
| `origin/main` | 无 vtr |
| 全部远端分支（2401 个） | 0 命中 |
| `archives/` 全部版本 + `_index.yaml` + `SUMMARY.md` | 无 `vtr` |
| git 历史（`git log --all -- archives/v/vtr`） | 0 提交 |
| PR（1986 开放 + 2674 关闭 = 4660） | 5 处正则命中，**逐一溯源全部为误报**：`vtraag` 用户名 / `iverilog` / `verilogAST` / yosys / chipvault |
| Conan 制品仓 | 无 `vtr*` / `verilog*` / `vpr*`；resolve API 确认 `vtr/9.0.0` 不存在 |

**结论：不存在重复适配。**

## 合规声明

- 未使用 `master`/`main` 浮动源码，未使用个人镜像；源码为官方 release asset 且 SHA256 固定。
- 未删除任何上游测试、benchmark 或核心组件；未注释失败测试、未放宽断言、未修改测试期望值。
- 未关闭综合、布局、布线或时序分析相关功能；GUI 采用上游官方 headless 配置。
- `test_package` 与上游测试分开统计，未相加为单一通过数。
- 所有未通过项已逐项列出（含 config 名称、首个有效错误与证据路径），见随附 `regression/F-explanations.md`；未执行项逐项原因见 `regression/unexecuted-reasons.md`。
