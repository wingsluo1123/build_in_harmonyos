## PR 信息

- **三方库名称**：quorum
- **上游版本**：1.1.2
- **上游仓库地址**：https://github.com/gmarcais/Quorum
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：E221（混合 CLI/library 建模）；E9945-draft-2501（本 PR 新增配对草稿：已发布依赖的下游显式 traits 修复边界）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 4 | unit_tests/test_mer_database.cc 的一个 TEST_P，Values(1,10,20,40) 展开为四个实例；保留原始十线程、序列长度和全部断言 |
| 集成测试 | 0 | 官方归档未另注册集成测试；不把新增消费者计入原上游 |
| 其他测试 | 0 | 无其他注册入口，不重复计算单个 GTest runner |
| **合计** | **4** | 原源码清单及实际 --gtest_list_tests 四实例均已保存，无跳过 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 4 | 不变 | 四个参数实例与原始断言完整执行 |
| 集成测试 | 8 | +8 | 已安装包的版本、merge、split、quality db、correct reads、gzip roundtrip、Perl frontend、adapter 数据 |
| 鸿蒙特有测试 | 0 | 不变 | 平台兼容场景已包含在原生构建及安装消费者中，不重复计数 |
| **合计** | **12** | **+8** | 上游 4/4 与新增消费者 8/8 分开统计 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. `unit_tests/test_mer_database.cc`：将已移除的 `INSTANTIATE_TEST_CASE_P` 改为现代 GTest 的 `INSTANTIATE_TEST_SUITE_P`。保留全部原始 Values(1,10,20,40)、十线程执行、100000 序列长度及原始断言，不删减或放宽期望。
2. `CMakeLists.txt`：通过已发布的 GTest imported target 构建原始测试源，不引入上游旧版 amalgamated GTest 的遮蔽 include 路径；实际运行 --gtest_list_tests 后执行全部四实例。CTest 包装器数量不是 GTest 实例分母。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游已有四项参数化实例。额外提供 `test_package/test.py` 的八组安装包消费者及 `test_package/MANIFEST.yml`，分别验证生产 CLI、真实数据库和纠错处理、gzip 输出、Perl 前端及 adapter 安装数据，不能代替上游测试。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：4/4（100%）
- 新增测试用例通过率：8/8（100%）

最新真机事务 `quorum-finish-r2-20261013`：HarmonyOS PC 6 / arm64 / Clang 15，当前主仓基线 ca72b8c6f689926d7ccc7425a08b140b9adcd26a 上的本次配方。完整官方 G1/G2、W3 本地 CI 子步骤通过，12 阶段冻结 validator 返回 W3_PASS；本任务进程已清零，logs/release 各执行一次。

总日志 SHA256：`5aad43fef4f6a2fa23e6bd60f958c878acfecb01c69cb6a701efed020e6af3ed`。

完整官方 finish 实际 RC1：step5b 为旧 staging 标记缺失，step8 为旧 knowledge 标记；step3、step35 等产品检查均通过。未修改框架、未伪造 `.ci-result.json`、未把完整 finish 写成 RC0，也未混用旧事务测试结果。知识草稿最终查重和提交合同独立完成。比赛 worker CI 与平台 AI Review 待本 PR 创建后验证；本地通过不代表已发布制品。

---

## 补充说明

- 关联 Issue：#3967
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：2501_91199785:feat/quorum-1.1.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：基础任务 #9945 归本人领取。历史他人 PR #14615 已关闭未合并，不改动其 fork/分支/Issue。HD1–HD4 逐项有当前否定证据，按 A+B，不申请 C。新增知识区分“上游完整建模”与“已发布且公开安装物完整时，下游 headers/libs traits 的窄修复”；不硬编码依赖缓存路径，不擅改发布依赖，不泛化到 CLI-only、缺头库或 ABI 不匹配场景。生产四个 CLI、Perl frontend 和 adapter 数据完整保留；GNU 私有 gzip streambuf 改为真实 zlib gzwrite stream，Perl 保留 -p/-P 区别，真实 export_sources 生命周期与补丁入口已验证。合并后由官方 release 发布，PR 阶段不上传。
