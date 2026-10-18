# E429 草稿：多进程锁测试的阶段屏障与受控延迟反证

状态：路径 B 候选，尚未纳入正式知识库。工具生成的暂定 E429 不占用正式编号；主编可定号、合并或拒绝。来源为 locket/1.0.0 PR !15473；独立实测案例数为 1，同库重跑不算多个案例。

## 错误特征与适用条件

多进程竞争测试先启动辅助进程，休眠固定 100ms，再断言它已经持锁。高负载真机中，`test_lock_is_released_if_holding_process_is_brutally_killed` 在杀进程**之前**的 `assert locker_1.has_lock()` 失败，上游全量为 15/16；清理还可能因没有取得辅助进程 PID 出错。这不能据此判定系统 flock 或杀进程后的释放行为错误。

适用于有真实子进程、可观测事件和竞争资源的测试：锁、队列工作者、IPC 服务等。推广场景尚未逐库验证。若真实操作本身失败、网络文件系统语义不同、辅助程序不输出事件，需另行定位，不套用本方案。

## 根因与知识增量

父进程的固定 sleep 只说明时间过去；它不能建立“子进程已初始化 → 首进程已持锁 → 竞争者开始请求”的先后关系。仅等启动 READY 仍可能让竞争者先拿到锁；仅发送 release 也不能证明锁已释放。

新增的是**多阶段竞争测试协议 + 保持原判定语义的反证闭环**，不主张初始化握手本身首次提出：

1. 启动辅助进程后等真实 READY。
2. 命令首进程 acquire，等成功操作之后发出的 Acquired，再发竞争请求。
3. 正向持锁断言等实际 Acquired；release 后等实际 Released。
4. 辅助响应等待设上限，产品锁 timeout 保持原值。
5. 同一受控启动延迟下比较原套件失败与修复套件成功，并比较全部原测试名及 Assert AST；最后跑未注入延迟的全量上游和安装包消费者。

不把“最长等多久”当作“锁请求允许多久”，不改变负向断言、锁 timeout 或生产实现。

## 输入、输出与实施步骤

输入：准确版本的官方源码、未修改的辅助进程、真实执行平台、完整失败日志、全部上游测试清单、带流式 stdout 的进程执行器。

输出：测试专用同步补丁、原套件与补丁套件延迟对照、测试名/Assert AST 对比、完整回归结果与日志哈希；不能输出假 PASS、自动跳过或替代生产锁。

本例补丁为 `archives/l/locket/1.0.0/patches/0001-tests-locket_tests.py.patch`，仅修改 `tests/locket_tests.py`。原版 `tests/locker.py` 的 READY、Acquired、Released 事件保留。逻辑顺序为：

```text
spawn first + second → 各自 READY
first.acquire → first Acquired
second.acquire → 原阻塞/timeout 判定
first.release → first Released
second Acquired → 原持锁判定
```

`_wait_for_output` 匹配完整输出行，检查进程异常终止并限制等待 10 秒。上游锁 timeout 的 0、0.5、2 秒保留。本例为兼容上游 Python 2 风格使用 `time.time()`，并未实现单调时钟。每个辅助进程仅进行一次取得/释放事务，因此本例累计输出不会跨事务重用。

推广到循环使用的辅助进程时须用输出游标、事务序号或新流区分事件世代；否则旧 Acquired 会误判第二次 acquire。新实现宜用单调时钟，但这属于推广约束，未在本例验证。原负向检查附近保留的 0.1 秒 sleep 不作为 READY/持锁的证明；本补丁不声称消除了所有调度时序问题。

禁止：只加长 sleep、失败后重试到绿、删 Assert、skip/xfail 原用例、放宽锁 timeout、mock 掉真实子进程、把诊断延迟装入包。

## 验证与复现

实测：2026-10-12，HarmonyOS PC / HongMeng Kernel 1.12.0 / AArch64 / Python 3.12.9 / OHOS Conan 2.29.1。

1. 官方标签 `32248e25d9a92c76d14e7eb86098c2fdb6995f03`，归档 SHA256 `1017278428998ac23c0716660587eeb39f069493d39922b7f5ae6c39c62f86c6`。分别解包到 original、patched，在 patched 应用本 PR 测试补丁。两份源码使用官方 spur.local/0.3.7 私有测试工具和实际 pytest 工具环境。
2. 在两份**诊断副本**的 `tests/locker.py` 中，仅在 `import locket` 后加入 `import time; time.sleep(0.4)`。设置 PYTHONPATH 为对应源码、spur.local 源码及 pytest 工具路径，`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`。
3. 对两份执行 `python3 -m pytest -v tests/locket_tests.py -k brutally_killed`。原版退出非零，补丁版退出 0；每份只选择 1 项，15 项 deselected，这是诊断实验，不是全量跳过。
4. 使用 try/finally 恢复辅助源码；在 patched 执行 `python3 -m pytest -v tests`，16/16，无失败、skip 或 xfail。
5. AST 比较全部 `test_*` 名称及每个 `ast.Assert` 的 `ast.dump(..., include_attributes=False)`，16 个测试名及 47 个原 Assert 均相同；锁 timeout 数值不变。再用官方 URL `conan create` 执行上游 16/16 与消费者 10/10，均 100%。
6. 原版 W3 setup.sh/build_and_test.sh 退出 0；L2 因没有 CLI 不适用，其余要求门禁通过。移走专用安装包 lib/ 后消费者真实导入失败，finally 恢复后 10/10。

生产模块始终等于官方字节，SHA256 `e421665e59bcb956253551053fee25fb2cd4b2f52b0cefa6e9a8559961cb36fc`；补丁前后 PREV 同为 `bfb3001a17d9ae157415e76aeebd827c`。

原始日志及诊断脚本保留于 `D:/codex/harmonypc/_work/locket-1.0.0-artifacts/`。提交的 `archives/l/locket/1.0.0/reports/evidence-sha256.json` 绑定原失败、延迟对照、完整 Conan、W3 和负向日志，`validation-summary.md` 记载执行结果。没有虚构历史远端 CI 失败编号；当前 PR HEAD 的远端 CI、审核、发布仍需平台证据。

## 查重与覆盖边界

基线：2026-10-13 的 `origin/main`，提交 `ca72b8c6f689926d7ccc7425a08b140b9adcd26a`。检索正式 graph/doc、operations 与 drafts，关键词为 ready、Acquired/Released、readiness handshake、fixed sleep、startup sleep、固定休眠、测试时序，并通过 `ohc-run.py draft-review E429-draft-LK13 --json` 预审。

| 相近条目 | 已有覆盖 | 本草稿实际增量 |
|---|---|---|
| E361 | MPICH 脱离后代进程在清理后通过 token gate 检查 canary | 竞争资源的 READY/首持锁/释放多阶段协议；原 Assert AST 与延迟反证，不是清理逃逸检测 |
| E605-draft-1146 | 原生 Meson harness、本地 HTTP fixture 通过成功 listen 握手、loader 闭包 | 初始化握手之后的首持锁与竞争请求排序、释放确认 |
| DRAFT-easylogger-2.2.0-async-output-consumer-wait | 异步输出消费时固定等 1 秒、核查输出捕获 | 用实际操作事件和受控延迟对照代替仅凭固定时间推断阶段 |
| E055 / E226 | fork/posix_spawn 语义 / bytes 与文本捕获 | 不覆盖多阶段竞争测试与语义保持对照 |

预审评分及原样建议见 `reports/knowledge-dedup.json`；工具不是入库批准。是否独立成条目、并入相近知识、正式编号与创新积分均由官方审核决定。

## 限制与申请

已实测一个库和上述单一环境；未验证其他 Python 版本、fork 后继承、网络文件系统、路径别名、跨事务事件复用。AST 相同是未删改原断言的证据，不等于形式证明所有运行语义。

作为路径 A+B 申报材料，申请贡献创新 10 分候选；不重复申报测试框架工具链加分，不申报路径 C。Python 库的参赛资格、通用性和新增知识是否获认可，均需官方确认。本地知识同步不等于正式图谱入库。
