## PR 信息

- **三方库名称**：locket。
- **上游版本**：1.0.0，BSD-2-Clause。
- **上游仓库地址**：[mwilliamson/locket.py](https://github.com/mwilliamson/locket.py)，官方标签提交 `32248e25d9a92c76d14e7eb86098c2fdb6995f03`。
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新／知识库扩展）；不申报路径 C。
- **使用知识库**：openharmony-compile-agent；既有 Python Conan 路径传播、固定官方测试工具源码、E361 清理后屏障等知识。新增候选 `knowledge/drafts/E429-draft-LK13.kv` 与 `.md`：多进程锁测试阶段屏障与受控延迟反证。
- **关联申请**：[路径 B Issue #3962](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3962)，一个 PR 仅关联此申请。
- **分支**：`feat/locket-1.0.0 → main`；当前完整 HEAD 以平台 PR 为准，关联 Issue 绑定最终提交。

Conan 将官方 Python 模块安装到 `lib/python/site-packages/locket` 并传播 PYTHONPATH。生产模块使用原版 fcntl.flock，字节与官方标签相同。官方 codeload 源码归档 SHA256 `1017278428998ac23c0716660587eeb39f069493d39922b7f5ae6c39c62f86c6`；无第三方运行依赖。pytest/9.1.1 及四个传递依赖已在真机按 `--build=never` 下载核验；spur.local/0.3.7 为固定 SHA256 的官方 PyPI 测试驱动器，仅放私有 test-tools，不装入消费者包。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 11 | 官方 1.0.0 标签 `tests/locket_tests.py`，同进程锁生命周期、释放及非重入 |
| 集成测试 | 5 | 同文件，使用原版 `tests/locker.py` 的真实独立进程，验证阻塞、timeout、终止释放 |
| 其他测试 | 0 | 官方标签清点未发现额外正式测试 |
| **合计** | **16** | 统计 test_* 函数；47 个 Assert 不作为用例数 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------|------|
| 单元测试 | 19 | +8 | 保留上游 11，新增 Conan 消费者 8：导入来源、生命周期、异常释放、非重入、不同路径、线程竞争等 |
| 集成测试 | 7 | +2 | 保留上游 5，新增消费者真实子进程排斥和被杀进程恢复 2 |
| 其他测试 | 0 | 不变 | 无额外正式套件 |
| 鸿蒙特有测试 | 0 | 无新增 | 全部在鸿蒙真机运行，不将运行平台计作独立新增用例 |
| **合计** | **26** | **+10** | 上游全量 16 + 安装包消费者 10；无删减、skip 或 xfail |

上游入口 `python3 -m pytest -v tests`，消费者入口由 `test_package/conanfile.py` 执行 `test_locket.py`。延迟注入诊断每份选 1 项（15 deselected）及包移走负向实验单独统计，不混入正式 26 项或重复累计。

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例。
- [x] **是**，存在对上游测试用例的修改。

1. **修改的测试文件**：`tests/locket_tests.py`，补丁 `archives/l/locket/1.0.0/patches/0001-tests-locket_tests.py.patch`。
   - **修改原因**：提交前高负载重跑出现 15/16，杀进程前首持锁断言失败；固定 sleep(0.1) 无法证明子进程已启动并取得锁。诊断副本加入 400ms 启动延迟可复现同类失败，不能据此判定 flock 错误。
   - **修改内容**：启动后等待 READY；5 个进程测试均在发出竞争请求前确认首 Acquired；正向持锁断言等 Acquired，release 后等 Released。辅助响应等待上限 10 秒，与真实锁 timeout 0/0.5/2 秒分别处理；原有负向断言附近短 sleep 保留。
   - **语义核对**：16 个测试名、47 个原 Assert AST 和真实锁 timeout 均保留，未削弱断言；生产模块 SHA256 不变。补丁由仓库 `refresh-patch --auto` 生成；诊断延迟不进入配方、补丁或安装包。
   - **对照结果**：同一 400ms 延迟下原版失败、补丁版通过；恢复诊断副本后全量 16/16 通过。该诊断仅选 1 项，不冒充全量回归。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖。
- [ ] **是**，上游无测试用例，适配后补全了测试。

官方同版本标签已包含上述 16 项。本次另增 `test_package/test_locket.py` 10 项安装包消费者测试，覆盖真实模块导入来源、线程/进程锁和异常释放，作为补充验证。不是“上游无测试后补全”，也不是用消费者替代上游套件。

---

## 验证结果

- **编译状态**：纯 Python，无 C/C++ 编译；真机官方 URL `conan create` 打包及测试退出码 0。
- **上游测试用例通过率**：**16/16（100%）**，失败 0、跳过 0、xfail 0。
- **新增测试用例通过率**：**10/10（100%）**，失败 0、跳过 0。
- **验证环境与日期**：2026-10-12，HarmonyOS PC / HongMeng Kernel 1.12.0 / AArch64 / Python 3.12.9 / OHOS Conan 2.29.1，通过 SSH 在设备原生运行。
- **Conan 产物**：仅模块与 BSD-2-Clause LICENSE/Conan 元数据，无测试工具、字节码或 ELF；模块 SHA256 `e421665e59bcb956253551053fee25fb2cd4b2f52b0cefa6e9a8559961cb36fc` 与官方一致。测试补丁前后 PREV 同为 `bfb3001a17d9ae157415e76aeebd827c`。
- **本地 W3**：仓库原版 setup.sh + build_and_test.sh 和工具自动回执退出 0，G0/KC/JC/L0/L1/L4/L5 通过。L2 无 CLI，跳过该不适用门禁；不是跳过测试用例。日志 SHA256 `cd5e68ac2faf2ad5b80d8cb8b43b7a143d7e2b5bb868c70d017289f1ade3ce87` 与自动回执一致。
- **失败与修复记录**：原版上游 15/16 及受控延迟失败已保留；W3 首次缺 bash/git，使用本任务专用 Conan 工具环境补齐后成功，未修改共享 CI 或全局安装。
- **负向实验**：移走专用 Conan 包 lib/ 后真实 `conan test` 因 `ModuleNotFoundError` 失败，finally 恢复后 10/10；证实消费者没有误用宿主已装模块。
- **证据位置**：提交 `reports/validation-summary.md`、`reports/evidence-sha256.json`、`reports/audit-result.json`；原始日志和自动回执按文件规则保留在 D 盘任务 artifacts，不进入最终提交树。
- **本次更新范围**：2026-10-13 同步 main、补充知识草稿及提交材料，配方/补丁/消费者代码未改；上述真机证据对应相同实现，不宣称文档更新后已重新构建。
- **远端 CI**：当前 PR HEAD 尚未取得完成结论；旧 `/rebuild` 调度确认不能当作 CI 通过，更新后按规则请求新 HEAD 验证。远端审核、合并和发布分别待确认。

---

## 补充说明

**知识扩展与查重**：对 origin/main `ca72b8c6f689926d7ccc7425a08b140b9adcd26a` 的 graph/doc/operations/drafts 检索 ready、Acquired/Released、readiness handshake、fixed sleep、startup sleep、固定休眠、测试时序。E361 已覆盖清理后 canary gate；E605-draft-1146 已覆盖成功 listen 后的初始化握手；easylogger 草稿为异步输出固定等待。本次增量为初始化之后的“首持锁 → 竞争请求 → 释放确认”多阶段协议，加受控延迟反证、原 Assert AST 保留及安装包闭环。完整覆盖差异写入配对草稿。

当前 `draft-review` 建议 **create**，最高相似得分 E259 0.12（assert 副作用问题）；原样结果见 `reports/knowledge-dedup.json`。工具无法替代人工语义查重，邻近草稿由手工检索补充。E429 为暂定编号，仅交 `knowledge/drafts/`，不修改正式图谱/索引；最终独立入库或合并由主编决定。

申请路径 B **贡献创新 10 分候选**；测试框架/工具链验证作为证明，不重复申报额外分值，不申报路径 C。对应申请 Issue 请官方确认新增知识通用性、验证证据、最终编号及**纯 Python 库资格**，不将申报表述为获批/获分。

**审计与路径限制**：本次增量经独立 W4 检查，报告随 PR 提交。PF9 对归档规范必需的软件级 README.md/manifest.yaml 误报路径不足五层；版本目录、分支、原子性及其他静态检查已核验，仅使用 SKILL 明示的精确进程级例外，未修改共享框架，不宣称原版预检全过。报告自身不纳入递归哈希。

**适用边界**：实测仅上述设备/Python 环境；未验证其他 Python 版本、fork 后行为、网络文件系统及锁路径别名。单次辅助进程事务有效；推广到多次事务需隔离输出游标/事件世代，避免旧 Acquired 误判。当前 helper 用 time.time()，单调时钟是推广建议，未在本例实施或验证。同期原负向断言附近仍有短 sleep，不能声称所有竞态已消除。
