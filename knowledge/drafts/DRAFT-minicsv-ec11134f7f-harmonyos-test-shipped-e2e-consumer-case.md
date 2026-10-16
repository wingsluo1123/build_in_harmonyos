# 赛事规则的鸿蒙特有测试必须是随 PR 交付的端到端消费者用例（纯断言集合不构成）

- **草稿 ID**: DRAFT-minicsv-ec11134f7f-harmonyos-test-shipped-e2e-consumer-case
- **来源**: minicsv ec11134f7f R02（赛事 Review 规则 12「鸿蒙特有测试」FAIL 处置,
  PR #13611 update；OHOS aarch64）
- **分类**: contest / harmonyos-specific-test / end-to-end / consumer-case
- **状态**: 本地草稿（路径 B 知识库扩展，随 minicsv PR 提交）

## 问题 / 错误签名

- 赛事 Review 判定：**规则 12「鸿蒙特有测试」不通过**——
  「鸿蒙特有测试行只有断言（N=1），不算完整消费者用例——至少要有一个完整消费者用例
  （真正跑通功能/流程的端到端用例），纯断言不行」。
- 直接成因两条（分析端复核确认）：
  1. **形态不合格**：唯一支撑物是 `reports/harmonyos-test.c`（设备侧 12 项 `ok:` 断言的集合，
     经 clang 链接打包产物 `libminicsv.a` 后运行）——是断言集合，不是端到端消费者用例。
  2. **未随 PR 交付**：交付态 10 文件列表中没有任何鸿蒙特有测试源码或运行日志——
     `reports/` 按本仓规则属运行时产物、不随 PR 提交，远端评审无法复核该项。

## 根因

- 赛事口径（规则 12）与「本仓 conan-verify/本地门禁的断言测试」是两个不同的校验标准：
  本地门禁只要求真实运行的断言（R34/E472）；赛事 Review 额外要求「完整消费者用例」——
  真正跑通功能/流程的端到端用例（输入数据集 → 逐列解析 → 流转/聚合 → 汇总断言），
  且**测试源码必须随 PR 交付**，纯断言集合（尤其位于 gitignored `reports/` 下的）不被承认。
- `reports/` 被仓库 `.gitignore:96` 排除，故断言源码与运行日志天然不会进入 PR 文件列表。

## 方案

1. **源码位置**：端到端消费者用例源码放**白名单内、非 reports 路径**，例如
   `archives/m/minicsv/ec11134f7f/harmonyos-e2e/minicsv_consumer_e2e.c`
   （不在 test_package/ 内，避免与 Conan L1 测试混淆）。
2. **用例形态**：真实端到端流程（输入数据集 → `minicsv_parse_line` 逐行解析 →
   `minicsv_trim_cols` 清洗 → 分类/聚合流转 → 与独立计算的期望值汇总断言）；
   编译期 `-DEXPECTED_*` 宏可注入错误期望制造受控失败变体（failcap，非恒绿）。
3. **交付与证据**：源码 commit 进 PR（文件列表可见）；编译/运行/failcap 日志放
   `reports/`（gitignored，只作证据日志并给 SHA-256，不随 PR 提交）；
   PR 正文「鸿蒙特有测试」行取值 1 且说明支撑物为该 e2e 源文件。
4. **统计口径**：test_package 断言计为单元测试，不计入鸿蒙特有测试；三张表与实测台账一致。

## 验证

- `clang -O2 -I<conan_pkg>/include <src> <conan_pkg>/lib/libminicsv.a -o reports/<bin>` rc=0，
  OHOS 工具链 clang 15 aarch64-linux-ohos。
- 真机运行 rc=0：`minicsv_consumer_e2e: PASS (0 failures)`（5 行解析、bytes=10752、
  login=2/api=2/unique=4，5 项 ok；轮次日志 sha256 5a774b3e…）。
- failcap：`-DEXPECTED_BYTES_TOTAL=99999` 编译运行 rc=1（`FAIL: bytes 聚合 == 期望值`），
  变体未进入交付物/staged/commit/PR。
- PR #13611 回读文件列表包含 `archives/m/minicsv/ec11134f7f/harmonyos-e2e/minicsv_consumer_e2e.c`。

## 适用边界

- 适用：赛事（积分赛/知识库扩展/高难度挑战）要求「鸿蒙特有测试=完整消费者端到端用例」
  的所有库；凡 PR 正文鸿蒙特有测试行支撑物需要随 PR 可复核的场景。
- 不适用：非赛事场景（本地门禁/CI 只要求真实验证断言即可）；纯 CI 内部测试
  （test_package、ctest）不要求随 PR 交付二进制/日志。

## 反例 / 限制

- 反例：把 R01 的 12 项断言集合直接改名为端到端用例、把 test_package 断言计入鸿蒙特有测试、
  仅编译不运行（`compile_level_only`）却宣称规则 12 闭合、恒真开关或 printf-only 测试。
- 限制：本条目不覆盖 failcap 之外的测试质量规则（E472/ELf 签名等）；
  平台网络/基础设施故障不是本条目范畴，永远不走路径 B。

## 查重差异

- 与 E239（self.run consumer cases 聚合诊断）：E239 管 test_package 多用例失败聚合，
  不涉及「随 PR 交付」与「赛事口径端到端」。
- 与 E252（substantive pre-asset consumer tests）：E252 是资源型库外部资产前的实质性
  消费者流程，非赛事规则 12 判定口径。
- 与 E215（Path B consumer validation）：LuaRocks 消费者验证，场景不同。
- 与 E472（L0d self.run / SDL dummy）：本地门禁层真实执行要求，不覆盖「随 PR 交付」。