# DRAFT-expect-ohos-tcl-test-runtime.md — OHOS 上 Tcl/Expect testsuite 运行时适配方法

- **知识主题**：路径 B 候选，最终以官方审核为准
- **来源**：expect 5.45.4 PR !3194（OHOS 适配，依赖 tcl 8.6.14）
- **日期**：2026-08-08

## 问题范围

OHOS（HarmonyOS aarch64）上运行上游 Tcl/Expect testsuite 时，标准方法会因三类平台差异失败，且失败形态容易被误判为"测试没跑"或"测试全绿"：

1. **运行时入口选择**：静态 Tcl 构建下 `tclsh` 无法动态加载 Expect 扩展（`can't find package Expect`），标准 `make test` 入口（`$(TCLSH) tests/all.tcl`）**不是**实际可执行入口。
2. **只读 `/tmp`**：OHOS `/tmp` 为只读文件系统，测试直接写 `/tmp`（如 `/tmp/null.[pid]`）必然失败。
3. **PTY raw-mode 能力缺失**：OHOS PTY 不支持 raw mode（`/bin/stty` 缺失），依赖 `exp_stty raw` 的用例会失败。

## 最小复现条件

```sh
# 静态 tclsh 入口（不可用）
TCL_LIBRARY=<tcl_lib> tclsh tests/all.tcl   # → can't find package Expect

# 写 /tmp（只读失败）
# expect.test 中 set filename /tmp/null.[pid] → couldn't open "/tmp/null.[pid]": read-only file system

# PTY raw-mode 用例（失败）
# expect-1.10 gate-keeping → Result 0, expected 1（/bin/stty 缺失，raw mode 不生效）
```

## 实际入口与静态 tclsh 限制

- **实际执行入口**：构建后的 `./expect tests/all.tcl`（在 conan create 的 build 阶段以正式入口运行）。
- **静态 tclsh 限制**：`tclsh tests/all.tcl` 报 `can't find package Expect`（静态 Tcl 无法动态加载 Expect 扩展），如实单列，不作为实际入口，不得写"上游测试未执行"。
- 测试子进程环境需设置 `TMPDIR=$HOME/tmp`、`TCL_LIBRARY`、`LD_LIBRARY_PATH`（指向 tcl 包 libdir，expect 动态链接 libtcl8.6.so）。

## `env(TMPDIR)` 方案

- 配方（conanfile.py）在运行测试前：`export TMPDIR=$HOME/tmp; mkdir -p "$HOME/tmp"`，并校验目录存在且可写（`[ -d ] && [ -w ]`），失败则 exit 1。
- 测试源码写临时文件一律经 Tcl `env(TMPDIR)`：

  ```tcl
  set filename [file join $::env(TMPDIR) "null.[pid]"]
  ```

- **禁止**硬编码 `$HOME/tmp` 或其他固定用户路径；路径必须来自 `env(TMPDIR)`，由配方统一注入。

## PTY capability constraint 适用边界

- 用 tcltest 运行时 capability 探测，仅对**确实依赖** PTY raw-mode 的用例标 Unsupported/Skipped：

  ```tcl
  ::tcltest::testConstraint ohosPtyRaw [expr {[file executable /bin/stty]}]
  ```

- **不得扩大跳过范围**：`expect-1.10`（gate-keeping，依赖 raw）可标 Skipped；`expect-1.11/1.12/1.13` 保持原语义实际执行（实测通过）。
- 不得修改用例断言来伪造 PASS。
- spawn 子进程 shell 噪音（`sh: /bin/stty: inaccessible or not found` 混入 buffer）导致上游脆弱断言（`regexp $expect_out(buffer) "ab"`，pattern/string 颠倒）失效时，改尾部匹配（`regexp {ab$} $expect_out(buffer)`），修复须有修复前后证据。

## 真实统计

- `./expect tests/all.tcl`：**29 Total / 28 Passed / 1 Skipped / 0 Failed**（expect exit code 0）。
- Skipped 1 = `expect-1.10`（OHOS PTY raw-mode 运行时约束，ohosPtyRaw constraint）。
- test_package/test_expect.sh：**4/4 通过**（可执行 / `-c` puts / spawn echo / EXP_STTY）。
- `finish` 返回 exit 1：原因为 E213/E214 本地知识图谱基线条目与 `gen_summary` 框架工具错误，**不属于 Expect 配方、构建或测试失败**。

## 复用步骤

1. 以构建后的 `./expect tests/all.tcl` 作为真实测试入口，静态 tclsh 入口如实单列。
2. 配方注入 `TMPDIR=$HOME/tmp`（mkdir + 可写校验），测试写临时文件用 `env(TMPDIR)`。
3. 对 PTY raw-mode 依赖用例加 tcltest 运行时 constraint（探测 `/bin/stty`），仅跳过真正依赖 raw 的用例。
4. spawn 噪音场景改用尾部匹配断言。
5. 如实记录 `29 Total / 28 Passed / 1 Skipped / 0 Failed`，不得伪造 100% 或把 SKIPPED 写成 PASS。

## 失效边界

- 动态加载可用的常规构建（`tclsh` 可 `load` Expect）无需入口选择与 constraint。
- `/tmp` 可写的系统无需 TMPDIR 路由（但仍建议统一）。
- 支持 PTY raw-mode 的平台无需 ohosPtyRaw constraint。
- 本方法不适用于库专属配方细节（如具体 patch 内容），仅沉淀可复用的 testsuite 运行时方法。

## 到 Expect 配方/patch 的可定位引用

- `archives/e/expect/5.45.4/conanfile.py`（TMPDIR 注入、正式测试入口、runenv LD_LIBRARY_PATH/TCL_LIBRARY）
- `archives/e/expect/5.45.4/patches/0009-ohos-pty-raw-constraint.patch`（ohosPtyRaw constraint）
- `archives/e/expect/5.45.4/patches/0010-ohos-tests-compat.patch`（env(TMPDIR)、expect-1.3 平台期望、1.8b/1.9 尾部匹配）
- `archives/e/expect/5.45.4/notes.md`（测试口径记录）
