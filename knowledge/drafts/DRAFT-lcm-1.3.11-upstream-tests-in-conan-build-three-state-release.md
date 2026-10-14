# DRAFT-lcm-1.3.11-upstream-tests-in-conan-build-three-state-release

> OHOS 真机将上游 gtest/自测接入 conan build()，以 HMBS_UPSTREAM_TEST_RESULT 三态 + gaps 证据放行，仅真实失败阻断

## 问题特征（真实日志片段/标记）

lcm/1.3.11（autotools，依赖 glib/pcre2 等传递闭包）真机 compile 阶段，上游自带 gtest 无法用默认 `make check` 接入，需手工把它编入 conan `build()` 的 `_run_upstream_tests`。日志标记：


lcm/1.3.11: upstream gtest: discovered=12 executed=9 passed=9 failed=0 skipped=3
lcm/1.3.11: HMBS_UPSTREAM_TEST_RESULT={"status": "failed", "framework": "gtest", ...,
  "discovered": 12, "executed": 9, "passed": 9, "failed": 0, "skipped": 3,
  "gaps": [{"count": 3, "category": "ohos_feature", ...}]}


- `run_upstream_tests.sh: Segmentation fault (core dumped) .../test/c/eventlog_test (rc!=0)`：`eventlog_test` 三条用例经 `make_tmpnam()=tmpnam(NULL)` 写设备只读 `/tmp`(erofs)，`lcm_eventlog_create()` 的 `fopen` 失败返回 NULL，首用例对 NULL 调 `lcm_eventlog_destroy` 段错误（`fclose(NULL)→SIGSEGV`）。
- 阶段产物缺少机器证据：`test_package` 阶段不产出 `HMBS_TEST_PACKAGE_RESULT`（`test_package_result_absent`），discovered/passedCount 必填缺失。
- 早期 `status="passed"` 与 skipped=3/gaps 并存，被门禁判 `rule4「passed 状态与上游结果矛盾」` 拒绝。

## 根因

1. autotools 库在 OHOS 真机不能直接把上游测试当作默认回归环节：无 formal `make check`/ctest，或需原生工具链与设备能力；简单脚本不经统一计量会漏跑/漏报。
2. 测试运行 `_run_upstream_tests` 把 `eventlog_test` 整进程段错误简单累计为"未通过"，但段错误根因是设备只读 `/tmp`(erofs) 的 `ohos_feature` 环境缺口，并非测试逻辑真实失败；事件网（装有 segmented logs）把这些用例当未执行处理。
3. `status` 语义不清：只要没有真实 `[ FAILED ]` 就报 `passed`，忽略了 skipped>0 / gaps 意味着"未 100% 执行/通过"，与 skipped/gaps 并存自相矛盾被 rule4 否决。真实失败（`failed>0`）与只读 `/tmp` 环境缺口（`skipped=3`）必须分离判别。

## 修复方案（rec）

在 conan `build()` 引入 `_run_upstream_tests`，把上游 gtest 提升为通用回归套件并统一计量与上报：

1. **接入与单数据源计量**：`conanfile.py` `_run_upstream_tests` 对每个 gtest 二进制（memq_test、eventlog_test、udpm_test 及 cpp 版）独立分日志运行、记录各自退出码；仅以 `[ RUN ]/[ OK ]/[ FAILED ]` 行作单一计数来源，得 `discovered/executed/passed/failed/skipped`（lcm 实测 12/9/9/0/3）。
2. **三态 status**：`has_real_failure = failed > 0`：
   - `failed>0` → `status="failed"` 且末尾 `raise RuntimeError` 阻断 build()（仅真实 `[ FAILED ]` 阻断）；
   - 否则若 `skipped>0` 或 gaps 非空（存在未 100% 执行/环境缺口）→ `status="incomplete"`；
   - 仅当 `discovered==executed==passed`（无 skipped/failed/gaps）→ `status="passed"`。
   - `has_real_failure` 是末尾是否 `raise` 的唯一判据：`ohos_feature`/`environment` gap 不阻断。
3. **gaps 带证据放行**：对只读 `/tmp` 导致的 eventlog 3 用例段错误，如实记入 `gaps`（`category=ohos_feature`，`count=3`，`detail` 含 `tmpnam(NULL)/lcm_eventlog_destroy(NULL)/erofs` 根因，`evidence` 含真机日志 `Segmentation fault (core dumped)` + 源码 `lcm/eventlog.c`），用 `incomplete` 状态通过，不删除/跳过/伪造任何用例。恒等式校验 `sum(gaps)==discovered-passed` 保持成立。
4. **补 test_package 证据**：`test_package/` 补 `test_lcm.c`（C 消费者经 CMakeDeps 链 `lcm::lcm`→glib 闭包，`memq://` 提供者做 6 项生命周期校验）+ `CMakeLists.txt` + `conanfile.py`（确定性数 `CHECK-OK:` 得 passedCount，输出 `HMBS_TEST_PACKAGE_RESULT` 并从包内 `res/upstream_test_result.json` 复发 `HMBS_UPSTREAM_TEST_RESULT`）+ `MANIFEST.yml`（`upstream_test_total=12`、`upstream_test_count_method=gtest_macros`、`assertion_count=6`）。
5. 记录修复证据到 `notes.md`；工作树待 HMBS 真机预检复跑确认合法结果后提交。

## 禁止策略

- **禁止** `HMBS_UPSTREAM_TEST_RESULT` 中 `"status":"passed"` 与 `"skipped":N(N≥1)` 或非空 `"gaps"` 并存；未 100% 执行/存在环境缺口必须如实标 `incomplete`，否则被 rule4 "passed 与上游结果矛盾" 拒绝。
- **禁止**把 `ohos_feature` 环境缺口（只读 `/tmp` 段错误、HMDFS setgid、子进程目录不可见等）伪造成 passed 或从计数删除；只能带证据放行。
- **禁止**以 2>/dev/null || true + ignore_errors 等方式吞掉 lcm-gen/测试工具的任何失败，掩盖真实缺失。
- **禁止** `discovered=0` 且 `status=passed` 的零证据放行。

## 与相近条目的边界（查重）

- **E672（libstdc++ 头缺失）**：根因是 SDK 头文件缺失，属 headers 环节，与本条"上游测试接入 + 证据门禁"不同根因不同环节。
- **buildtorrent/darts/boost（/tmp 只读、config.status、mktemp 权限）**：均为解包/configure/mktemp 环节的编译或权限问题，与本条"上游测试统一计量、gaps 证据放行、三态 status 语义"不重叠。
- **ccrtp/1.0.0（DRAFT-ccrtp-...）**：主题是"上游无 formal make check 时将 demo 改造为新增回归测试，保留独立上游盘点口径"；本条目是"把已存在的上游 gtest 编入 conan build() 并统一计量与三态证据放行"。两者互补：本文处理"测试已存在但需接入+放行"，ccrtp 处理"无测试时新增"，均遵守独立盘点、不伪造成通过的口径。

## 适用判断

适用于在 OHOS 真机可运行的、自带 gtest/自测（JSON 行级 `[ RUN ]/[ OK ]/[ FAILED ]` 输出）的 autotools/CMake C/C++ 库，需把上游测试接入 conan `build()` 作通用回归套件、并对事件网真机能力缺口（只读 /tmp、HMDFS setgid、子进程目录可见性、mktemp 权限）带证据放行的场景。触发特征：`upstream gtest: discovered=... executed=...` 与 `HMBS_UPSTREAM_TEST_RESULT="status":"...","gaps":[...]`、`Segmentation fault (core dumped) ...eventlog_test`、`test_package_result_absent`、`rule4 passed 状态与上游结果矛盾`。当上游测试在上游即无（discovered=0）或需新增断言时，改用 ccrtp 蓝本的"新增回归套件"法；当测试依赖量过大无法真机编译时，走 api-equivalent-substitute-test 替代。
