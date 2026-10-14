## PR 信息

- **三方库名称**：libunibreak
- **上游版本**：8.0
- **上游仓库地址**：https://github.com/adah1972/libunibreak
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：E007；本 PR 草稿 E545-draft-UB11

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 22048 | 官方 Unicode 数据行；LineBreak 19338、WordBreak 1944、GraphemeBreak 766 |
| 集成测试 | 0 | 发布版无独立注册集成测试 |
| 其他测试 | 0 | 三个驱动分组不另加到数据行分母 |
| **合计** | **22048** | 原 tests.c、test_skips.h 与三份官方数据未修改，完整逐行清单已保存 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 22048 | 不变 | 全量官方 make check -j1，无跳过 |
| 集成测试 | 0 | 不变 | 消费者与鸿蒙检查合在一个程序，不重复计数 |
| 鸿蒙特有测试 | 1 | +1 | test_unibreak.c：无条件 POSIX uname 校验，预期系统名由 Conan 目标设置注入；TMPDIR 临时文件读写后验证实际字素 API；含常规 API，所有目标固定10断言 |
| **合计** | **22049** | **+1** | 1 个消费者程序不按10断言重复计为10用例 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

仅修改 GNU 平台识别 config.guess/config.sub；对重叠 check/check-am 测试依赖竞争，在配方完整 check 调用中使用 -j1，库构建仍 -j2。测试源码、断言、预期数据、跳过列表均未改。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增 test_package/test_unibreak.c 与 MANIFEST.yml 验证安装包的实际 API 和鸿蒙平台行为；不替代上游完整测试。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：22048/22048（100%）
- 新增测试用例通过率：1/1（100%）

正式原生 conan-verify 与 finish W3 本地 CI PASS；run_id=libunibreak-finish-20261011-r3，目标 HarmonyOS PC arm64 / clang 15.0.4 / Conan 2.29.1，12 阶段释放完整。原始 W3 日志 SHA-256 ddb0071aa91181f256fa42b3bfcd0e260ae97fa4a74ae17a31b7749af0791335；官方 .ci-result.json integrity=eec0a634d263e3dc 已复核，未手改。三组终态由只读汇总转换为合计，原日志字节保留。

本地 finish 总 RC=1 为旧后置 readiness/staging，仅声明 W3 子步骤 PASS；由当前提交合同另外完成提交准备。比赛 worker CI 尚未触发，不将本地结果冒充其成功。

---

## 补充说明

- 关联 Issue：#3907
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/libunibreak-8.0
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：贡献任务 #15048 已领取，活动“开源鸿蒙PC专项积分赛-依赖”（显示5火种）；路径 B 候选以官方审核为准。HD1–HD4 全部为有证据否定；知识查重涵盖四个规定目录，新稿区别于 tuple、FIFO、bison生成源与安装目录竞争，仅针对重复对象/.Tpo 机制。PR 只含一个库及同 stem 草稿对；合并后 /release 发布 ohpcd，PR 不上传。


### 2026-10-14 当前 CI 修复

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

当前真机事务 `libunibreak-ci-repair-w3-20261013-r101`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `d0a87427f041e339e92b9b369683ea87c75842311a5440387a2ffcb704765b06`。上游 22048 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
