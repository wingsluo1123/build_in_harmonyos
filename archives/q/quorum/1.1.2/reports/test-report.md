# 真机原生测试报告

## 当前权威结果 — 2026-10-13

新候选在最新 main 基线 ca72b8c6f689926d7ccc7425a08b140b9adcd26a 上补齐真实 export_sources 与 apply_conandata_patches 生命周期。
事务 quorum-finish-r2-20261013，boot 0a624b09-f722-42ec-8bf1-a2ce7720a040，UID 20020084，端点 10.62.201.39:2222。
官方 G1/G2、W3 本地 CI 实际通过；上游完整四个 GTest 参数实例 4/4，八组安装消费者 8/8，12 个不可变阶段全部验证 W3_PASS。
logs/release 各一次，本任务 runner 和子进程清零。总日志 SHA256 5aad43fef4f6a2fa23e6bd60f958c878acfecb01c69cb6a701efed020e6af3ed。
官方 full finish 的 RC1 仅为旧 step5b staging/step8 knowledge 标记，原始失败保留，不声称完整 finish RC0 或比赛 CI 已通过。知识查重与 PRE_CREATE/POST_CREATE 为独立提交门禁。

以下记录为历史，不挪用为当前候选的 PASS。

OHOS 6 arm64；Clang 15.0.4；目标端点 10.62.201.39:2222；UID 20020084。

| 类型 | 上游原始分母 | 本次结果 | 说明 |
| --- | --- | --- | --- |
| MerDatabaseWriteRead | 4 | 4/4 | 原始 Values(1,10,20,40)，完整原始断言 |
| 安装包消费者 | 不属于上游 | 8/8 | 版本、merge、split、quality db、correct、gzip roundtrip、Perl 前端、adapter 数据 |

run_id：quorum-w3-r6-20261011T223000Z（唯一身份标签，不据此推断时间）。
产品 tree：28cfed2a3fb2364f3c3a843331c223834b5b3320。
Conan create RC0，完整 12 receipts，release/postrelease PASS。
日志 SHA256：82322c35f10b6e1ca8cfbe14b970f88becec925443d99ec6977a3379875ef4cb。
terminal SHA256：ce41c24d5639d8e0486998a0ba5bb3783f5fc900b3f79752492156dec3e30150。
纠错生产 ELF SHA256：f70eba5a6a9fd8f92029f74c73fd3212bc0d1ec0b66faa855cb3d3cc9f7acda4。

这是目标机原生结果，不是比赛 worker CI。新增归档/知识文档不改变已冻结产品文件，但正式 finish 和 PR 合同必须绑定最终候选。

## 官方 finish 编译子步骤

run_id `quorum-w3-finish-20261011T083500Z`；tree `0a091cf313a48db0e65e67456b8678232cd5b366`；产品输入 SHA256 `ad8f0df59288a75b4c0531e4f1b4855ebf36379f9f1559c8a390ec213ab0c48e` 与 r6 相同。

未修改的官方 FinishPipeline.step35_local_ci() 实际运行 setup.sh 和 build_and_test.sh，主包原生构建、四项上游、八组消费者、L1e 破坏性反向验证全部通过；L0/L1/L2/L4/L5 均 PASS。12 项事务阶段及 release/postrelease PASS，已清理本任务运行资源。

总日志 SHA256 `bea89d235a807264f6e27d7d9c6e8ce35c0c789a844f21b9a01dbb1df75d6f3a`；原始子构建日志 `e067cb9b4f29b3a96373d3997bb33cecb604bd6901b655b016bae9ad57b2ec80`；终态 `875faa5ca155fc85edb887e10652faf6c6d3e4c8c89b35a8f97d0e853fa23d1a`。官方生成 CI result 原始回读 SHA256 `06a6b4d35e4b29cc4705e1447a49626513766cfd18d2dee3a4c79f9408aa6165`，没有人工补字段。

这只证明官方 finish 的 W3 子步骤，完整 finish 其他阶段与提交合同尚未完成，不能将本结果写成平台 CI 或已发布。
