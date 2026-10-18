# locket 1.0.0 验证摘要

验证日期：2026-10-12（Asia/Shanghai）。HarmonyOS PC / HongMeng Kernel 1.12.0 / AArch64，Python 3.12.9，OHOS Conan 2.29.1。

## 输入与依赖

- 官方 `1.0.0` 标签提交：`32248e25d9a92c76d14e7eb86098c2fdb6995f03`。
- 标签源码 SHA256：`1017278428998ac23c0716660587eeb39f069493d39922b7f5ae6c39c62f86c6`。
- 无第三方运行依赖，依据 `setup.py` 和模块全部 imports 审计。
- pytest/9.1.1 及四个传递依赖从 ohpcd 实际下载成功，`--build=never`；日志见 w0-dependencies.log。
- 官方测试驱动器 spur.local/0.3.7 从 PyPI 下载并校验 SHA256，仅存 source/build 的私有 test-tools。原版全部测试及断言保留，测试辅助进程增加同步，不把该测试驱动器装入消费者包。

## 测试结果

| 测试组 | 上游数量 | 执行 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|---:|---:|
| tests/locket_tests.py | 16 | 16 | 16 | 0 | 0 |
| test_package/test_locket.py | 补充 | 10 | 10 | 0 | 0 |

上游命令 `python3 -m pytest -v tests`，无过滤、排除、跳过或 xfail。消费者有 15 个断言调用点，覆盖安装来源、锁生命周期、异常释放、非重入、不同路径、线程竞争、独立进程排斥和被杀进程恢复。上游进程测试使用其原版 `tests/locker.py`，消费者另用真正的 Python 子进程，不以 mock 模拟平台锁。

最终官方 URL `conan create` 退出码 0；原始日志见 conan-create-device.log。

## W3 本地 CI 门禁

真机专用验证副本运行原版 `setup.sh` + `build_and_test.sh`，由 `FinishPipeline.step35_local_ci()` 写回执。

- G0、KC、JC、L0、L1、L4、L5：通过，Success 1 / Failed 0。
- L2：跳过，纯 Python 库没有 bin/ 或 CLI。
- 首次失败原因是设备没有 bash/git，而 CI 工作者基线具备这些工具；通过专用 Conan 缓存下载 bash/5.3、git/2.45.2 和二进制依赖，在验证进程启用工具环境后重跑成功。不修改仓库 CI 或共享设备安装。
- W3 日志 SHA256：`cd5e68ac2faf2ad5b80d8cb8b43b7a143d7e2b5bb868c70d017289f1ade3ce87`，与工具生成的 `.ci-result.json` 完全一致；日志见 w3-local-ci.log。

## 产物与负向验证

- 移走专用缓存包的 lib/，运行真实 `conan test`。消费者因 `ModuleNotFoundError: No module named 'locket'` 失败；finally 恢复后消费者 10/10 全过。见 negative-device.log。
- 包中仅 `locket/__init__.py`、BSD-2-Clause LICENSE 和 Conan 管理元数据，无测试、spur、pytest、字节码或 ELF。
- 模块 SHA256：`e421665e59bcb956253551053fee25fb2cd4b2f52b0cefa6e9a8559961cb36fc`，等于官方标签中的原版模块。
- 官方配方 RREV：`2a7b0a44533ac7d85658e4005de35001`。
- 包 ID：`da39a3ee5e6b4b0d3255bfef95601890afd80709`；PREV：`bfb3001a17d9ae157415e76aeebd827c`。
- 最终官方 codeload 与 W3 构建均通过，RREV 分别为 `2a7b0a44533ac7d85658e4005de35001`、`33c81fe3afe624a4314c0d5bedc38e1b`；PREV 相同。

既有适配阶段知识图谱验证为 542 对节点、170 条存量警告；本次仅提交 knowledge/drafts/ 配对草稿，不修改正式图谱或索引。最新知识质量检查另行记录。

## 验证边界

上述为真机本地构建、运行及本地 CI 模拟。PR 已开放；当前 HEAD 的远端 CI 与人工审核尚无完成结论，合并与 upload 未完成；不使用本地成功推断远端已发布。未验证其他 Python 版本、fork 后行为、网络文件系统或锁路径别名。

## 提交前时序修复与证据归档

首次提交前重跑原版测试为 15/16，失败在杀进程前的持锁断言。独立诊断副本加入 400 ms 启动延迟稳定复现，增加 ready/Acquired 输出同步后同一诊断通过，最终完整上游 16/16、消费者 10/10、W3 和负向测试均重新通过。补丁仅改变 tests/locket_tests.py 的辅助同步，16 项名称和每条原断言经 AST 比较完全保留；真正 timeout 值未改，注入延迟不进入提交或配方。

原始日志保留在本地本目录及任务 artifacts 中，依文件政策不进入最终 PR 文件树；提交 Markdown 摘要及独立审计，远端 CI 将产生对应 HEAD 的独立原始日志。

最终下载入口为 GitHub 官方 codeload，显式 filename 保留 .tar.gz；设备实测 HTTP 200，归档 SHA256 与初始官方标签一致。同步补丁在启动竞争者之前确认首锁，在 release 后等待 Released；最后一轮完整 Conan、W3、负向验证和注入延迟诊断均通过。

## 2026-10-13 提交材料更新

本次同步 origin/main，加入经查重的路径 B 草稿及完整模板；配方、补丁、消费者实现未改变。引用的是 2026-10-12 对相同实现的真机日志，未声称新提交已经重新构建或远端 CI 通过。结构化证据哈希见 evidence-sha256.json，草稿预审原样结果见 knowledge-dedup.json。当前 HEAD 以 PR 平台为准。

当前原版 graph validate 退出 0（170 条存量警告），knowledge_check 的 KC1–KC5 全过（546 对正式条目、Errors 0）。草稿另行校验必填字段、受控分类、正则、配对文档及 draft 标记；完整日志哈希和未修改的 W3 回执一致。重新比较官方与补丁测试的 16 个名称和 47 个 Assert AST，结果相同；配方/补丁/消费者实现哈希与真机证据对应的既有审计一致。提交 Markdown 已核对官方模板章节顺序、两表、两组选项和单一 Issue。
