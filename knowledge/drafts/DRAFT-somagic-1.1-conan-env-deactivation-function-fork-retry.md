# DRAFT-somagic-1.1-conan-env-deactivation-function-fork-retry
> conan 反激活脚本切 function 形态消除共享 worker fork EAGAIN，并对 make 做 fork 指纹门控有界重试

## 问题特征（真实日志片段/标记）
- `Calling build()` 之后、make 尚未产生任何编译输出即失败：`ConanException: Error while running cmd` / `Error: [Errno 11] Resource temporarily unavailable`
- 同一构建日志中 CI 自身脚本（knowledge_check.sh、junk_check.sh）也反复报 `fork: retry: Resource temporarily unavailable`
- 真机 test_package：`[FAIL] somagic-init --skip-check rc=139 output=[Signal 11 (core dumped)]`，16 项检查 14 通过 2 失败
- 修复轮标记：`HMBS_REPAIR_METHOD`、`compile_error`、`hmbs_repair_method`、`no_tests`（同一轮上游测试原被误判为「存在测试」，与 MANIFEST 审计对齐为 `upstream_test_total: 0`、`count_method: none`）

## 根因
1. **env 反激活逐变量 fork 耗尽共享 worker 进程资源**：conan 默认（未设 `tools.env:deactivation_mode`）在 `conanbuildenv-<id>.sh` / `conanrunenv-<id>.sh` 顶部生成 source 时立即执行的反激活前导块，逐变量 fork `printenv`（每次 `self.run` 前十余次 fork），叠加共享 worker 的 fork/进程资源瞬时耗尽，报 `[Errno 11] Resource temporarily unavailable`，与源码、工具链、依赖均无关。
2. **libusb_init 返回值被忽略导致未初始化句柄解引用**：上游四个程序（`somagic-init.c:261`、`somagic-capture.c:720`、`somagic-both.c:817`、`somagic-audio-capture.c:157`）调用 `libusb_init(NULL)` 后不检查返回值，随后直接使用全局 `devh` 与 libusb 枚举接口。libusb 1.0.27 的 platform_notes 记录 OHOS/HongMeng 沙箱中 sysfs 与 netlink 不可用，`linux_netlink_start_event_monitor()` 失败使 `libusb_init` 返回错误（linux_usbfs.c:410 后直接返回错误码），原代码继续 `find_device()` → `libusb_open()`，用未初始化句柄触发 SIGSEGV（exit 139 = Signal 11）。

## 修复方案（rec）
1. **反激活切 function 形态**：主配方 `archives/s/somagic/1.1/conanfile.py` 新增 `generate()` 注入 conf `tools.env:deactivation_mode=function`，消除 source 期逐变量 fork `printenv`；`test_package/conanfile.py` 在 `configure()` 注入同一 conf（显式 VirtualRunEnv 早于 generate 运行）。
2. **make 指纹门控有界重试**：`build()` 的 make 改走 `_make_with_fork_retry()`，仅在命中 fork 指纹（`fork: retry: Resource temporarily unavailable`）时做有界退避重试，真实编译错误（compiler_error）立即抛出，不进重试。
3. **libusb_init 返回值守卫**：新增 `patches/0001-guard-libusb-init-failure.patch`，在四个 `libusb_init(NULL)` 调用点后插入返回值检查，失败打印 `Failed to initialize libusb` 并退出；配方经 `export_sources()` / `source()` 应用补丁。
4. **test_package 断言对齐**：`test.sh` 断言改为「exit 1 且非信号」（不再判 139/Signal 11 为通过）并强化临时目录探测；`no_tests` 标记与 MANIFEST 审计对齐（`upstream_test_total: 0`、`count_method: none`），测试用例与计数口径均未改动。
5. **验证闭环**：`py_compile` 通过 → HMBS 同步工作树 → 真机预检全部门禁通过（attempt 59401：`v2:evidence:compiler_error`；attempt 60977：`v2:compile:compiler_error`），再由 HMBS 提交推送。

## 禁止策略
- 禁止 libusb_init 守卫失效时仍以 `rc=139` / `Signal 11 (core dumped)` 崩溃通过测试；断言口径必须为「exit 1 且非信号」。
- 禁止在反激活 function 形态未生效时，以无指纹、无界重试吞掉 `ConanException: Error while running cmd` / `[Errno 11]`：fork 指纹未命中即为真实错误，必须立即抛出。
- 禁止改动上游测试计数口径或以其他方式替代 no_tests 审计（`upstream_test_total: 0`、`count_method: none` 不得被 demo/自造用例数污染）。

## 与相近条目的边界（查重）
- 现有知识库与修复轮命中条目仅与 `compile_error` / `hmbs_repair_method` 关键词同词相邻，主题分别为 GNU 扩展头、thin archive、编译器路径、winit 平台分支、configure triplet、shadow repo 等，均未覆盖「共享 worker fork 资源耗尽（fork EAGAIN）」与「libusb_init 返回值守卫」两类问题，增量明确。
- 与 `DRAFT-ccrtp-1.0.0-demo-as-upstream-regression` 的边界：ccrtp 蓝本主题是把 demo 提升为回归测试以补证据；本条目不涉及上游测试盘点替代，仅对齐 no_tests 审计口径，核心是两个构建/运行环境通类解法。

## 适用判断
- **fork EAGAIN / Errno 11**：适用于任意 conan 配方在共享或受限 worker 上的构建失败，凡「构建刚开始即 `Resource temporarily unavailable`」都应先查 env 反激活脚本是否逐变量 fork；解法为注入 `deactivation_mode=function`，make 级 fork 抖动用指纹门控有界重试（真实错误立即抛出）。
- **libusb_init 返回值守卫**：适用于 OHOS 下调用 libusb 系外设库、忽略初始化返回值后解引用全局句柄的 C 程序；netlink/sysfs 在 OHOS 沙箱不可用是该类 SIGSEGV 的典型诱因。
- 两项均属于构建环境/工具链生态通类（Q1 抽象可行性成立），可复用于其他 conan 配方与共享 worker 场景。
