## PR 信息

- **三方库名称**：libcdr
- **上游版本**：0.1.9
- **上游仓库地址**：https://wiki.documentfoundation.org/DLP/Libraries/libcdr
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新）
- **使用知识库**：E545-draft-CD11；参考E317, DRAFT-eigen-3.4.1-r37-published-recipe-collision

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 2 | CppUnit官方testRead/testSeek，共2/2，零跳过。 |
| 集成测试 | 0 | 发布包无独立注册集成用例；不计LibreOffice应用级集成套件 |
| 其他测试 | 0 | 无其他注册程序，未删注册测试 |
| **合计** | **2** | 精确发布源码注册清单与原始日志绑定；无跳过 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 2 | 不变 | 未修改上游断言 |
| 集成测试 | 0 | 不变 | 消费者功能与平台检查合为一个程序 |
| 鸿蒙特有测试 | 1 | +1 | 独立1/1消费者程序，14个断言，不将断言冒充多个程序；实际文档识别、解析并导出1页SVG，以及HarmonyOS uname身份、TMPDIR写入/pread/unlink生命周期。 |
| **合计** | **3** | **+1** | 上游用例与独立新增程序分开；断言数不重复累计 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

未修改上游测试断言、数据或注册；仅平台识别与配方构建/链接适配。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

独立1/1消费者程序，14个断言，不将断言冒充多个程序；实际文档识别、解析并导出1页SVG，以及HarmonyOS uname身份、TMPDIR写入/pread/unlink生命周期。 新增test_package内conanfile.py、CMakeLists.txt、测试C++与MANIFEST.yml。未修改的 LibreOffice writerperfect 回归素材 fdo65220-2.cdr，10755字节，Git blob aff705ffa5eefa8f98d7fbfa49c4f6793d2c3732，SHA-256 88e62beb7a7ebe812f6ce06238017d07d215de9dbf76323dde93200f2d5dd348；来源及项目许可说明见test_package/FIXTURE-NOTICE.md。 消费者不替代上游注册测试。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：2/2（100%）
- 新增测试用例通过率：1/1（100%）

正式libcdr-finish-20261011-r1原生conan-verify及finish W3 PASS，事务已释放。原W3 SHA-256 9085fa15deb78850b7e8d1e0e5d431eb3d4777c9afbbd9695133c779639eb2cc，官方ci-result integrity 3c8fb0d9599e2874，保持生成器原始字节。整个finish RC1仅step5b/step8后置readiness/staging，不宣称全流程PASS；比赛worker CI尚未触发。CppUnit官方testRead/testSeek，共2/2，零跳过。

---

## 补充说明

- 关联 Issue：#3915
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/libcdr-0.1.9
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：主包版本子串替换会污染独立 provider 引用；recipe 构建成功不证明冻结依赖身份正确，必须分别绑定 resolved graph 与 ref/RREV/PID/PREV。 任务#15053依赖活动5火种；路径B候选以审核为准，HD1–HD4否定。合并后/release。素材源文件与原始失败日志不修改；源码补丁由官方流水线生成并干净源码dry-run。


### 2026-10-13 当前 CI 修复

A raw PR diff can omit a binary sample payload even when the Git source branch is mergeable. Carry the original fixture as bounded text, decode it only into the consumer build directory, and verify its original byte count/SHA256 separately from the text carrier hash.

当前真机事务 `libcdr-ci-repair-w3-20261013-r1`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `cd24f4b9b6ad2347b45bcaaa059142d44d1a8a8ab354827482473bca4d0db450`。上游 2 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。


### 2026-10-13 当前 CI 修复

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

当前真机事务 `libcdr-ci-repair-w3-20261013-r101`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `cb8b5ed11c5705ae2e9de2a3ee1e8ecaa7fea182ffebfe8a89e59ea8705cef65`。上游 2 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。


### 2026-10-14 当前 CI 修复

The producer shared=True/fPIC option cannot change an already published non-PIC static dependency. Pin the same-upstream static-PIC suffix artifact and force one consistent dependency version through both direct and transitive paths; keep system-name zlib static rather than adding a competing libz.so.

当前真机事务 `libcdr-ci-repair-w3-20261013-r301`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `69f097174198e763fb36bc86ffe2c53e063b992ef59aa84b2c6dd7e2b36e39a2`。上游 2 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
