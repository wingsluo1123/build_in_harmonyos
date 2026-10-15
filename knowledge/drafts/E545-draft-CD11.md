# E545 — Conan 版本子串替换与冻结依赖身份的独立一致性

## 错误特征
复制相近库的配方时，主包版本变更后出现 `Version conflict: Conflict between ... and ... in the graph`。另一种更隐蔽的症状是配方已经修正、构建 RC0，但冻结 identity 中的依赖完整引用仍为错误版本。

## 触发条件
- Conan 配方、测试配方和设备控制器由已有任务衍生。
- 主包旧版本字串是某个独立依赖版本的子串。
- recipe 与冻结依赖清单分别生成或修改，不能假定两者自动同步。

## 根因分析
整文件 `replace('0.0.3', '0.1.9')` 没有包名和字段边界。它不仅将主包版本迁移，还将 `boost/1.90.0.3` 污染为 `boost/1.90.1.9`。中间依赖仍要求正确 Boost，Conan 在计算图阶段就拒绝，不是编译器兼容性或缺二进制。

构建输入和证明输入是两个对象。只修 `requirements()` 后，旧控制器里的 `dependencies` 可以仍记录错误 ref。即使源配方完全相同、Conan 成功，也不证明证据声明的闭包正确。本例 r2/r3 的 recipe candidate 相同，而 dependency SHA-256 不同；这是需要独立比较的反例。

## 解决方案

### 推荐方案
1. 先定位图冲突的完整包引用与 originating 中间依赖，核对其真实已发布要求。
2. 主包名称/版本只能在确切字段、完整包引用或语法节点处变更；禁止整文件版本子串替换。Python AST 可以辅助盘点常量参数；动态引用以当前 Conan resolved graph 为权威。
3. 将 requirements、build requirements、测试配方的完整引用分别与解析图核对；不能靠只匹配版本数字校验。
4. 冻结前从同一解析图生成 ref/RREV/PID/PREV，并与 controller identity 独立比对。不把 `conan create RC0` 当作身份一致性证明。
5. 已消费的错误事务保持不可变；修正控制器/身份后新建事务，执行 fresh exact-byte transfer 与完整验证。不得在旧日志或 identity 上补改字段追认 PASS。

### 禁止做法
- 不用 dependency override 掩盖复制错误；这可能改变中间包 ABI 约束。
- 不改已发布 provider、缓存或已消费事务来让错误引用看起来成立。
- 不只修 recipe 后沿用旧冻结依赖 SHA，也不把部分构建成功拼成闭包正确。

## 验证
本次 libcdr 0.1.9 的真实链路（库名仅为证据示例）：

- r1：`evidence/libcdr-conan-r1.log` SHA-256 `70e59c2dbbe53e60764291a0dd563047038d2775bc6bf038c22e6fa26e7c04a2`，图冲突 Boost 1.90.0.3 / 1.90.1.9；没有进入编译。
- r2：recipe 已正确并构建成功，但 `w3-conan-libcdr-20261011T0638Z-r2/payload/identity.json` 仍声明 `boost/1.90.1.9`，dependency SHA-256 `da374ab1476a17751100072cd49dc39106e2a77987d3c3333b84dc2a391d62d5`。本轮不作为最终正确闭包证据。
- r3：独立冻结 identity 改为 `boost/1.90.0.3`，dependency SHA-256 `ccbd9222e9dd3d70425d9a15cfb7dc0ad107455727ec18931081ff41922931d5`；原生 `conan create` RC0、CppUnit 2/2、消费者 14 断言。日志 SHA-256 `37f31a315a0583facf5b88c40e5ec0bd2bb62019022ff8a722361558bcfc8931`。

上述是前轮原生验证，不代替正式补丁版 finish 或比赛 CI。该知识可用于所有独立 provider 版本含主包版本子串的 Conan 衍生配方及多文件冻结流程；不适用于真实且经论证的依赖升级。

## 关联条目
- 已在 knowledge/graph、drafts、doc、operations 查询 `version.*replace/collision`、版本全局替换、冻结依赖与精确子串/identity 场景。精确查询未命中同机制。
- E317 讨论 sed 误写运行时目录，并用首行范围限制修复。本条增量是完整包引用边界、Conan 中间依赖图冲突，以及 recipe 恢复成功后冻结身份仍独立错误；不是把 E317 换库名。


## 2026-10-13 CI 反例与修复增量

A raw PR diff can omit a binary sample payload even when the Git source branch is mergeable. Carry the original fixture as bounded text, decode it only into the consumer build directory, and verify its original byte count/SHA256 separately from the text carrier hash.

This is not a new base64 transport claim. The increment is preserving consumer test-data identity across a text-only CI diff application path, independently of package/recipe identity. The checksum-verified original parser sample and all assertions remain unchanged.

验证：新事务 `libcdr-ci-repair-w3-20261013-r1` 的12阶段及释放通过；当前官方本地CI子步骤 exit0，原始CI日志 SHA256 `cd24f4b9b6ad2347b45bcaaa059142d44d1a8a8ab354827482473bca4d0db450`。上游声明 2 项及消费者 1 程序口径保持不变；原有整体finish失败/旧标记不改写为成功，比赛worker结果必须绑定新HEAD另查。


## 2026-10-13 CI 反例与修复增量

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

Current worker logs provide the independent second-failure boundary after the earlier checkout/fixture repair: successful source retrieval and dependency installation are not proof that configure generated usable config files. Use both-branch source reconciliation, timestamp-preserving production-helper tests and complete native recipe/tests; do not treat a missing-curl predownload warning as the cause when source() already succeeded. This extends the existing evidence/transport topic with a causal validation boundary, not a new generic umask claim.

验证：新事务 `libcdr-ci-repair-w3-20261013-r101` 的12阶段及释放通过；当前官方本地CI子步骤 exit0，原始CI日志 SHA256 `cb8b5ed11c5705ae2e9de2a3ee1e8ecaa7fea182ffebfe8a89e59ea8705cef65`。上游声明 2 项及消费者 1 程序口径保持不变；原有整体finish失败/旧标记不改写为成功，比赛worker结果必须绑定新HEAD另查。


## 2026-10-14 CI 反例与修复增量

The producer shared=True/fPIC option cannot change an already published non-PIC static dependency. Pin the same-upstream static-PIC suffix artifact and force one consistent dependency version through both direct and transitive paths; keep system-name zlib static rather than adding a competing libz.so.

Current worker first advanced beyond the repaired config.status boundary and then rejected zlib/1.3.1 zutil.o while linking the real shared producer. Registry version suffix order is not proof of PIC: downloaded zlib/1.3.1.2 remains non-PIC, while 1.3.1.1 explicitly compiles the same upstream source with -fPIC. Bind the published recipe and binary revision before changing the graph, preserve every parser assertion, and validate a real DSO link rather than executable-only zlib smoke tests.

验证：新事务 `libcdr-ci-repair-w3-20261013-r301` 的12阶段及释放通过；当前官方本地CI子步骤 exit0，原始CI日志 SHA256 `69f097174198e763fb36bc86ffe2c53e063b992ef59aa84b2c6dd7e2b36e39a2`。上游声明 2 项及消费者 1 程序口径保持不变；原有整体finish失败/旧标记不改写为成功，比赛worker结果必须绑定新HEAD另查。
