## PR 信息

- **三方库名称**：libqxp
- **上游版本**：0.0.3
- **上游仓库地址**：https://wiki.documentfoundation.org/DLP/Libraries/libqxp
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：E545-draft-QX11；参考E236、E480、E6403

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 11 | 官方CppUnit test程序9条、detection程序2条；按内部注册项计数，不以2程序少报 |
| 集成测试 | 0 | 发布包无其他注册集成测试 |
| 其他测试 | 0 | 未交付工具/docs；未删任一已注册测试 |
| **合计** | **11** | Makefile.am与CPPUNIT_TEST注册清单，实际OK(9)、OK(2)一致 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 11 | 不变 | 上游全量，零失败/跳过 |
| 集成测试 | 0 | 不变 | 消费者功能及平台检查整合为一个程序，不重复计数 |
| 鸿蒙特有测试 | 1 | +1 | test_qxp.cpp，真实QXP解析/SVG导出、OHOS uname与TMPDIR生命周期；15断言 |
| **合计** | **12** | **+1** | 15断言不冒充15测试程序 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

仅配方编译/链接环境和config.guess平台识别，测试断言与数据不变。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

另新增独立test_package与MANIFEST.yml，使用官方src/test/data/qxp31win.qxd，未修改3840字节样本，不替代上游测试。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：11/11（100%）
- 新增测试用例通过率：1/1（100%）

正式libqxp-finish-20261011-r1原生conan-verify与finish W3本地CI PASS，12阶段释放完整。原W3日志SHA-256 db21238f3fd19d54841e4a0527a28ae39911d9f4765c2dc3faec649c83516818，官方ci-result integrity f7bf5c880aa5d888。总finish RC1仅后置readiness/staging，不宣称整个流程PASS。比赛worker CI尚未触发。

---

## 补充说明

- 关联 Issue：#3911
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/libqxp-0.0.3
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：Automake 测试子目录独立 AM_CXXFLAGS 漏用 BOOST_CFLAGS/ICU_CFLAGS 时，纯编译侧 include 闭包与 Libtool scoped .la-free 链接闭包必须分离，避免补头同时重新引入 provider 全局 -L 和陈旧 .la。公共消费者 traits 是后续另一层契约，不代替测试私有头修复。 任务#15055本人已领取，依赖活动5火种；B候选以审核为准。HD1–HD4否定。源码/测试素材均为官方发布包MPL-2.0。合并后/release。


### 2026-10-13 当前 CI 修复

A checkout-pr message saying main conflict can actually originate from missing binary patch data and an unsupported patch fallback option. Identify the first low-level Git apply error; encode and hash-restore the unchanged consumer sample rather than rebasing or deleting its test.

当前真机事务 `libqxp-ci-repair-w3-20261013-r1`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `903166c1aa1c609b26b297f4ad11625925ab1d1e6869f56f9943a2d1dc339513`。上游 11 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。


### 2026-10-14 当前 CI 修复

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

当前真机事务 `libqxp-ci-repair-w3-20261013-r101`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `1cce135bf987be9821bfc280da8f1770c88ea7801d61a153a0bb87e55decaf3f`。上游 11 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
