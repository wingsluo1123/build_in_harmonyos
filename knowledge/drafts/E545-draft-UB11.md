# 自定义 check 和 Automake check-am 的临时依赖文件竞争

这是已经完成本次查重、待主编审核的知识草稿，不是已经发布的知识条目。

## 通用触发特征与根因

库编译成功，但平行 `make check` 在重命名 `.deps/*-tests.Tpo` 时报告不存在。先看完整命令日志：只有确实出现同一个测试对象重复编译，且自定义 `check` 和 Automake 的 `check-am` 都依赖相同 `check_PROGRAMS` 时，才按这类竞争处理。`.Tpo` 是编译临时依赖文件；重复编译不能安全共享它。

## 修复与边界

保留完整上游测试入口及源码，仅把测试目标明确限制为 `-j1`，库构建仍可有界并行。Conan 默认任务数可能不同于手工 `make`，因此限制应放在配方实际调用的 `make check` 参数中。不要删除 check_PROGRAMS、跳过失败或降低测试分母。长期上游方案是修复重叠依赖图。

此结论不适用于缺失源文件、错误目录、权限拒绝、依赖扫描器损坏，或没有重复编译证据的 `.Tpo` 报错；串行失败时应继续定位其真实根因。

## 本次实证

- 软件：libunibreak 8.0，官方发布源码 SHA-256 `9c4fad6e517338a098373acc9f35579ae2c325e6446666fb9ac2666ba15ceba4`。
- 失败：`libunibreak-conan-20261011T0600Z-r2`，保存于任务证据 `evidence/conan-r2.log`，正式 Conan create 非零；日志显示测试对象重复编译及 `.Tpo` 重命名失败。
- 修复后：`libunibreak-conan-20261011T0600Z-r4`，Conan create RC=0，上游 LineBreak 19338/19338、WordBreak 1944/1944、GraphemeBreak 766/766，消费者 10 个断言通过。
- 最终日志 SHA-256 `d9a52dad14fbbaf5e3baff9b12e42cda9210abaef6948a7947d526604c4b4777`；12 阶段回执完整，release/postrelease PASS。

正式补丁配方又通过 `libunibreak-finish-20261011-r3` 的 conan-verify 和官方 finish W3 本地 CI；原始 W3 日志 SHA-256 为 `ddb0071aa91181f256fa42b3bfcd0e260ae97fa4a74ae17a31b7749af0791335`，三组共 22048/22048，消费者 1/1 程序、10 个断言，12 阶段事务释放完整。finish 总返回值仍为 1（旧后置 readiness/staging），不宣称整个 finish 成功，也不冒充比赛 worker CI。

已检索 graph、drafts、doc、operations 的精确 .Tpo/check-am 与并行竞争语义。E007 的 GNU tuple、E2180 的 FIFO 警告、DRAFT-E728 的 bison 生成源竞争、并行 install 的 mkdir EEXIST，均不能覆盖本稿的重复对象构建与共享依赖临时文件机制。保留其相关知识，不重复登记相同根因；查重详情在本任务 submission/knowledge-dedup-result.json。

## 固定测试分母的检视增量：平台断言不能静默消失

PR #15318 的检视指出，平台身份断言被 `#ifdef __OHOS__` 包裹时，未预定义该宏的编译器会少执行一条断言却仍输出消费者通过。这与测试驱动的运行期 PASS/FAIL 不同：源文件中有断言并不能证明产物实际包含该断言。

修复采用无条件 POSIX `uname()`，由 Conan 的目标 `settings.os` 在测试环境中注入 `LIBUNIBREAK_EXPECTED_SYSNAME`（OHOS 为 HarmonyOS，Linux 为 Linux），精确比较真实系统名。预期值缺失或不相等均失败；不根据实际返回值自动选取“期望值”，也不过滤诊断。所有目标都固定执行 10 条断言，与上游 22048 项的分母独立。

验证方法是重新执行原完整上游与安装消费者，核对 22048/22048 和 `assertions=10`；另对同一消费者产物分别去掉预期变量和注入错误系统名，要求非零退出。本次后续验证结果以独立修复事务日志为准，不能复用 2026-10-11 的旧通过日志。


## 2026-10-14 CI 反例与修复增量

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

Current worker logs provide the independent second-failure boundary after the earlier checkout/fixture repair: successful source retrieval and dependency installation are not proof that configure generated usable config files. Use both-branch source reconciliation, timestamp-preserving production-helper tests and complete native recipe/tests; do not treat a missing-curl predownload warning as the cause when source() already succeeded. This extends the existing evidence/transport topic with a causal validation boundary, not a new generic umask claim.

验证：新事务 `libunibreak-ci-repair-w3-20261013-r101` 的12阶段及释放通过；当前官方本地CI子步骤 exit0，原始CI日志 SHA256 `d0a87427f041e339e92b9b369683ea87c75842311a5440387a2ffcb704765b06`。上游声明 22048 项及消费者 1 程序口径保持不变；原有整体finish失败/旧标记不改写为成功，比赛worker结果必须绑定新HEAD另查。
