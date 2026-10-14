# libcontentaction 0.4.13 — 测试执行报告（实测口径）

- 库：libcontentaction 0.4.13（上游 https://github.com/sailfishos/libcontentaction tag 0.4.13）
- 口径：Conan profile `ohos-aarch64-run`（含 `CMAKE_CROSSCOMPILING_EMULATOR=/root/ohpc/bin/ohos-qemu-aarch64`），
  ctest 经 qemu-aarch64 执行；与 CI 使用同一套 OHOS 6.0 SDK / clang 15 交叉工具链。
- 生成时间：2026-10-02

## 1. 上游用例（ctest 注册名 = `tests/tests.xml.in` 的 case 名）

| # | ctest 名称 | 结果 | 耗时 |
|---|---|---|---|
| 1 | upstream-lca-cita-test-fail | Passed | 0.01s |
| 2 | upstream-test-defaults | Passed | 1.33s |
| 3 | upstream-test-regexps | Passed | 3.26s |
| 4 | upstream-test-highlight | Passed | 0.91s |
| 5 | upstream-generated-regex-testsuite | Passed | 13.28s |
| 6 | upstream-test-mimes | **Skipped (77)** | 0.02s |
| 7 | upstream-test-desktop-launching | Passed | 3.80s |
| 8 | upstream-test-fixedparams | **Skipped (77)** | 0.01s |
| 9 | upstream-test-special-chars | **Skipped (77)** | 0.01s |
| 10 | upstream-test-schemes | **Skipped (77)** | 0.01s |
| 11 | upstream-test-mimes-subset | Passed | 0.87s |
| 12 | upstream-test-info | Passed | 0.22s |
| 13 | upstream-test-action | Passed | 0.25s |
| 14 | upstream-test-mimedefaults | Passed | 1.24s |
| 15 | upstream-test-findhighlights | Passed | 0.26s |

**汇总：`100% tests passed, 0 tests failed out of 15`**（11 Passed + 4 Skipped，0 Failed）。
其中 **11 条真实执行且全部通过**（Passed），**4 条为 Skipped**（非 Passed 也非 Failed，
不计入通过率分母）。即：注册 15 条 = 执行并通过 11 条 + 跳过 4 条 + 失败 0 条。

### 消费者端到端断言计数（单一口径，回应检视 P1-1）

消费者用例分**两个独立进程**执行，各自打印一行 `RESULT:`，断言数**不可简单相加后固定**——
阶段 1 含条件断言，随构建机环境浮动：

| 阶段 | 本地 `ohos-aarch64-run`（有 mime 库） | DAYU200 真机（负载未含 mime 库） | 说明 |
|---|---|---|---|
| 阶段 1（主流程） | **26** checks, 0 failures | **23** checks, 0 failures | 源码含 31 处 `check(`（阶段 1 26 + 阶段 2 3 可静态计数；条件断言按环境取用），其中条件断言（mime 库描述项、span/match 分支、marker 分支）按环境取用 |
| 阶段 2（新进程回退） | **3** checks, 0 failures | **3** checks, 0 failures | 无分支，恒为 3 |
| 合计 | **29** | **26** | `test_package/MANIFEST.yml` 的 `assertion_count` 取本地口径 29 |

**结论**：`MANIFEST.yml` 记为 29（本地 profile 口径），真机口径为 26；
两处差异**已在上表逐项交代**，不随构建机环境漂移而无从复核。

### 执行口径（可复核性，回应检视 P2-2）

上表**全部 15 条**均在 **`ohos-aarch64-run`** profile 下执行 —— 该 profile 含
`tools.cmake.cmaketoolchain:extra_variables={"CMAKE_CROSSCOMPILING_EMULATOR":"/root/ohpc/bin/ohos-qemu-aarch64"}`，
即每条 aarch64 测试二进制都经 **qemu-user + OHOS musl 运行根**真实执行（运行器为 `port/run-guest.sh`）。

**必须区分两个 profile**（否则"Passed"不可复核）：

| profile | 是否含 emulator | 本表中用例能否真实执行 |
|---|---|---|
| `ohos-aarch64-run`（**本表所用**） | 是 | 能 —— 全部 Passed 均为 qemu 实跑 |
| `ohos-aarch64`（**CI 所用**） | **否** | 不能 —— 仅编译并注册用例，不执行 |

即：上表的 `Passed` 仅在本表声明的 `ohos-aarch64-run` 口径下成立。CI 使用
`ohos-aarch64`，其侧只验证"能编译 + 用例可注册"，**不产生执行结果**；CI 侧如需执行证据，
应改用带 emulator 的 profile 或在设备上运行（见 `device-e2e-evidence.md`）。

同时披露一项环境性限制：`upstream-test-desktop-launching` 依赖 `gio-launch-desktop`
（GIO ≥ 2.80 的 `.desktop` 启动助手）。该助手由 `port/CMakeLists.txt` 从 Conan 的 glib 包
`bin/` 目录解析并前置到测试 `PATH`（配置期输出 `libcontentaction tests: glib helper dir = ...`）；
若未定位到，配置期会打印 `WARNING ... trigger-based upstream cases may fail`。本表中该用例
`Passed`（3.80s），对应配置期已成功定位该助手。

> 说明：ctest 的 `SKIP_RETURN_CODE=77` 会把环境预检不满足的用例记为 **Skipped（不是 Passed、也不计为 Failed）**。
> 即 4 条 Skipped 明确**不计入通过数**，本报告不把它们算作通过。

## 2. 4 条 Skipped 的具体技术原因

均为 OHOS 侧缺少**运行时组件**，与配方正确性无关：

| 用例 | 原因 |
|---|---|
| upstream-test-mimes | `test-mimes.py` 的 2 个方法需要 dbus-python 假服务 `uberprogram.py`；OHOS 无 dbus-python 运行时 |
| upstream-test-fixedparams | 需要 dbus-python 夹具 `gallery.py`（DBus 服务） |
| upstream-test-special-chars | 同上（`gallery.py` 为 DBus 服务） |
| upstream-test-schemes | 同上（`gallery.py` 为 DBus 服务） |

为**不丢失**这部分覆盖，另加 `upstream-test-mimes-subset`：以上游**原始断言**逐方法执行
`test-mimes.py` 中不依赖 DBus 的 3 个方法（未放宽任何断言），实测 `Passed`。

## 3. 计数口径对照（上游 case 单元 vs 函数/断言级）

| 口径 | 数量 | 说明 |
|---|---|---|
| `tests.xml.in` `<case>` 数（**PR 声明的 N**） | 14 | 上游测试驱动自身声明的执行单元 |
| Python 用例内 `def test*` 函数 | 18 | defaults 3 / mimes 5 / regexps 4 / desktop-launching 3 / special-chars 2 / fixed-params 1 |
| QTest 二进制内真实测试函数 | 8 | test-info 3 / test-findhighlights 3 / test-action 1 / test-mimedefaults 1 |
| QTest 文件 `void *()` 声明（含 Qt 生命周期钩子） | 12 | findhighlights 7（4 钩子+3 测试）、mimedefaults 5（4 钩子+1 测试） |

## 4. 鸿蒙消费者端到端用例（rule12）

`test_package/lca_consumer_case.cpp` — 真实调用库完成完整消费流程：
配置 fixture 落盘 → `ContentInfo` → `Action` 查找 → mime 默认动作写读回环 → 方案动作 →
高亮检索 → `trigger()` 触发并校验执行痕迹（marker 文件内容）。

- qemu 本地口径（本报告同一 profile）：**29 项断言全部通过**（阶段 1 26 项 + 阶段 2 3 项，含新进程 `check-default` 回退路径）
- 真机 DAYU200 口径：见 `device-e2e-evidence.md`
