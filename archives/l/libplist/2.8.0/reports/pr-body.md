## PR 信息

- **三方库名称**：libplist
- **上游版本**：2.8.0
- **上游仓库地址**：https://github.com/libimobiledevice/libplist
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：本 PR 草稿 E553-draft-PL28，KV/MD 同 stem，draft: true

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 43 | 原始 test/Makefile.am 的完整 TESTS，包括格式、整数、时区、C++ 和 CLI stream 等 |
| 集成测试 | 0 | 未额外重复分类上游 TESTS |
| 其他测试 | 0 | 无额外注册入口 |
| **合计** | **43** | 原始身份逐项清单见 reports/upstream-inventory.txt |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 43 | 不变 | 原始测试代码、断言、清单均保留 |
| 集成测试 | 1 | +1 | 安装包 C API：UTF-8 键值、uint64 与 binary 编解码 |
| 鸿蒙特有测试 | 1 | +1 | 安装 plistutil 经中文/空格路径 JSON→binary→XML→JSON 语义一致和坏输入拒绝 |
| **合计** | **45** | **+2** | 上游 43 + 新增消费者 2；shared/static 不重复计数 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

结果收集按上游 TEST_EXTENSIONS=.test 的真实规则读取 stem.trs，保留原始完整 test_name 作为身份；一项一份 PASS 终态，交叉核对 TOTAL/PASS/SKIP/FAIL。没有靠汇总替代缺失记录、改断言、删测试或把 skip 计为通过。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增 test_package/test.c 和安装 CLI 工作流仅补充消费者覆盖，不替代上游 43 项测试。交付 C/C++ 库与 plistutil，不启用也不申报 Cython 绑定覆盖。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：43/43（100%）
- 新增测试用例通过率：2/2（100%）

OHOS ARM64、Clang 15、Conan 2.29.1：真实 shared/static 两种构建分别 43/43 + 2/2，0 FAIL、0 SKIP。完整双模式日志 SHA-256：1996d1cb59884369fd364210edb965afcd3dda29096bc681ea04ff600307f132。

官方 finish 的 conan-verify 和 W3 CI 子步骤实际通过；libplist-finish-w3-20261015-r4 的冻结 validator 接受十二阶段、退出与释放。完整日志 SHA-256：5fd99f884ec37332d476da6555c435c1a6cc3dcfaf16959bc72b2ebd70e03c08。原始 CI proof 未人工改写。聚合 finish 仍为 PARTIAL_POST_W3（共享既有图谱 step5b/step8 警告），本 PR 新知识对由 Pre-PR 独立阻塞验证。

---

## 补充说明

- 关联 Issue：#4081
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：2501_91199785:upgrade/libplist-2.8.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：依赖活动升级任务 #15225，沿用平台 upgrade 分支并保留旧版。libcnary 随原始源码内置，无新增未发布 Conan 库依赖。四范围知识查重及 HD1–HD4 复核见报告，四项均不匹配，申报路径 B 的 10 分候选，最终以官方审核为准。增量是 Automake 扩展名驱动的测试身份/结果 stem 映射及真实 43 项反例，区别于执行器路由类知识。旧失败保留；平台 Review/CI 与合并后的 release 另行执行，不声称已发布。
