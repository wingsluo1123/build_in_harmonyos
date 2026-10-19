# E549 — Help 成功不能证明 getopt 参数循环能终止

## 错误特征
同一 CLI 的 `--version` / `--help` 正常退出，但带有效数据的子命令均在短小输入上超时，尚未进入算法输出。Clang 同时警告 `comparison of constant -1 with expression of type 'char' is always true`。

## 触发条件
- C/C++ 多子命令工具，使用 `getopt()` 或 `getopt_long()`，返回值先缩窄到 plain `char`。
- 编译目标的 plain char 为 unsigned；选项处理分支对 help/version 直接 exit，但循环没有使未知 255 立即退出的 default 分支。

## 根因分析
`getopt_long()` 返回 int，其中 -1 表示选项结束。赋给 unsigned plain char 后变成 255，再提升为 int 与 -1 比较永远不等。help 分支提前退出，普通数据命令则一直留在选项解析器；更换算法、缩小数据、延长超时均不能解决。

现有 E6401 已说明同样缩窄会使测试 harness 落入 default 并退出。本条增加的是另一分支边界和验证结论：**无 default 退出路径时表现为忙循环，help 可以假绿；必须覆盖同型参数解析器族及真正消耗 EOF 的数据命令**。它不是新增一种整数转换机制，也不是 E419 的全局 signed-char 编译模式方案。

## 解决方案

### 推荐方案
1. 从超时前最后阶段与 Clang 警告定位解析循环，确认实际函数返回类型和循环变量。
2. 将接收类型改为 `int`，审计同项目其他子命令的相同模式；不要全局修改 char 的 ABI，也不改输入与断言。
3. 用有界有效数据调用强制走到选项结束，要求真实产物以及逆变换后的内容和重复次数一致。
4. 在已安装包上再次执行相同数据路径，另测非法命令拒绝；保留失败事务及其原分母。

### 禁止做法
- 不能把索引、转换、压缩等数据路径换成 help/version 后声明功能适配完成。
- 不能仅通过换算法、增加超时或删除重复数据掩盖解析器缺陷。
- 如果实际失败在 IO、授权、锁等待或算法内部，本条不适用；需定位真实阶段。

## 验证
SGA 0.10.15 的 32 个解析器修复后，`sga-w3-20261014-r13` 保留原数据测试：SAIS 与 ropebwt 索引、逆 BWT、重复序列精确比较共 6/6 通过；安装包中文路径索引和精确回读 2/2 通过。ropebwt 从 90 秒超时降至约 0.03–0.04 秒。上游无注册 TESTS/check_PROGRAMS，仍如实单列 0/0，未把补充测试冒充上游测试。

证据：`w3-sga-r13/readback-conan-create.log` SHA-256 `3078c14b1ccc86f4b28a3e22dedcc8d770c044563f34c88878e45cb9889fff64`；candidate tree `575aba84650b96a67362c9800c9d28fb2374f69e`。早期 r8–r12 保留 FAIL；不拼接或重新解释旧事务。

## 关联条目
- E6401-draft-1687：同类 sentinel 缩窄，症状为 harness Invalid parameter，而非无 default 分支的忙循环。
- E419：plain-char 符号性改变 signed 8-bit API 值；本条只修复 int 返回值接收器，不对整个库强制 signed char。

## 验证边界增量：路径命中不等于测试注册或功能覆盖

诊断 help 假绿时，不能反过来把任意包含 `test` 的文件都当作原始回归
用例，再用这个分母判断是否少测。必须绑定精确上游版本和归档文件集合，
同时检查构建注册、入口、被测行为、输入及结果 oracle；业务类 `Tester`
以及文件名中的字母偶合都只是待分类候选。没有特定框架注册本身也不能
证明无测试，需要逐项审阅其他脚本或手写入口。

本次官方 SGA tag 与归档完整比对 403 个文件；tag/master 各四个 test 路径
均为 build-only Dockerfile、生产 VCFTester 类及 RapidJSON filewritestream
头。GraphDiff Makefile 明确将该类编入生产库，13 份 Makefile.am 和
configure.ac 无自动测试注册。因此原始 N=0，真实新增数据往返另列，不能
用文件名计数把它们变成“四个已存在测试”。精确树 SHA、路径角色和官方
链接见本 PR 的 `reports/upstream-test-inventory.md`。这一判定不适用于已
发现真实未注册测试脚本、外部框架入口或有 oracle 的原始用例的项目。
