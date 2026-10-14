# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_4e1a998a.md`

---

## 背景

- **软件名称**: keydb
- **版本**: 6.3.4
- **构建日期**: 2026-10-04
- **构建系统**: makefile
- **上游仓库**: https://github.com/Snapchat/KeyDB
- **适配路径**: 路径 A（标准适配，系统自动计分）+ 路径 B（知识库扩展，人工审核，两者积分可叠加）
- **补丁数量**: 8
- **编译依赖**:
- uuid/2.40.1（OHOS sysroot 无 libuuid）
- openssl/1.1.1w（libcrypto，默认链接且无内嵌副本）
- tcl/8.6.16（仅原生构建时的测试工具依赖）
- **最终状态**: 成功（本地 `built`；未提交、未推送）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 上游 tarball sha256 `229190b251f921e05aff7b0d2f04b5676c198131e2abbec1e2cfb2e61215e2f3`，与 conandata.yml 一致（本机核对） |
| build | 编译构建 | 成功 | 构建系统: makefile；原生 aarch64/clang 15 构建 exit 0 |
| conan-verify | 配方验证 | 通过 | exit 0；G1/G2/G3/G4 全 PASS，L2/L4/L5 执行；报告 `reports/conan-verify-report.md` |
| finish | 归档收尾 | 完成 | 10 步管线走完；manifest→built、`.build-closed`/`.conan-verified` 已产出；step6/step10 留有 packaging/、`.staging-verified` 告警（R19：`built` 阶段本就属 published 就绪项，不伪造） |
| submit | PR提交+AI检视+CI | 未执行 | 按要求由用户的官方 agent 提交；本机不推送 |

上游 Tcl 套件（R51）：`tests/test_helper.tcl` 的 `set ::all_tests` 列表 **79 个单元**（55 `unit/*` + 24 `integration/*`），
harness 自报 `[N/79 done]`。最终补丁集（8 个）的一次完整运行：79/79 单元报完成、2123 用例、2121 通过 / 2 失败 = **99.91%**；
7 补丁集一次完整运行：78/79 单元、2105 用例、2102 通过 / 3 失败 = 99.86%；
更早一次完整运行：79/79 单元、2114 用例、2110 通过 / 4 失败 = 99.81%。失败项逐条归因见 notes.md。
新补丁 0008 把 `tests/unit/tls.tcl` 移入其同目录兄弟文件已在用的 `if {$::tls}` 守卫内，
消除了此前误归给 `unit/soft_shutdown` 的两例 `Can't start the Redis server`（该单元实测 14 ok / 0 err）。

### 失败与问题

真机阶段发现并修复了两个真实适配缺陷（Windows 交叉编译无法暴露）：

1. `keydb-server` 启动即 SIGSEGV（rc=139，无输出）：musl 不提供 glibc 的
   `program_invocation_name/short_name`，兼容层把它们定义为 `NULL`，而
   `spt_init()` 里 `strdup(NULL)` 崩溃（`server.cpp:7516` 在 `main()` 早期调用 `spt_init`）。
   证据：`keydb-cli` 正常而 server 崩；`REDIS_SERVER_OBJ` 含 `setproctitle.o` 而 `REDIS_CLI_OBJ` 不含。
   修复：`spt_init()` 先按 glibc 语义从 `argv[0]` 赋值再深拷贝。
2. arm64 fork-bug 探测在启动时 `serverAssert` 杀掉服务器（`server.cpp:6541`）：
   本机内核不支持 `MADV_FREE`（最小探针：`madvise(MADV_FREE)=-1 errno=22`，而 `MADV_DONTNEED=0`）。
   修复：探测失败时记警告并返回 0，而不是断言退出。

工具链侧另有两处阻塞（非配方问题）：沙箱 safe-bin 的 `rm` shebang 指向不存在的 `/bin/bash`
导致 `make clean` 报 126；`finish` 强制的 `refresh-patch` 在无编辑追踪器时会丢弃
`src/Makefile`/`src/config.h` 的改动（详见「建议」）。

### 知识图谱使用情况

- **引用知识条目**: []
- **新增知识草稿**: 无（本地已生成草稿但未纳入 PR，见「建议」）
- **引擎命中情况**: 草稿目录 2766 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: 本次遇到、但现有图谱未覆盖的模式有三类：
  ① musl 缺少 glibc 的 `program_invocation_name` → 兼容层以 NULL 定义 → `strdup(NULL)` 启动崩溃；
  ② 内核不支持 `madvise(MADV_FREE)`（EINVAL）导致上游断言型探测直接终止进程；
  ③ 工具链 `refresh-patch` 的 `_GENERATED_NAMES` 会把已修改的 `Makefile`/`config.h`
  当构建产物丢弃，且不回写 `conandata.yml`，使 `finish` 之后的 `conan create` 找不到补丁。

### AI 检视结果

- **检视阶段到达**: 未到达（本机未创建 PR；按要求由官方 agent 提交后再进入该阶段）
- **变更摘要评估**: 不适用——无 PR，故无平台侧变更摘要
- **检视意见数量**: 0（无 PR）
- **检视意见处理**: 不适用。替代手段：本机用一次独立的子代理评审（中性提示词）对配方做测试与审查，
  其结论为「无 P0，2 项 P1 + 若干 P2」，全部已修（软件级 README 缺失、版本级 README 补丁表与测试状态陈旧、
  manifest 漏 openssl、MANIFEST.yml `upstream_test_in_build` 与实际不符、notes 残留待办段）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知（未创建 PR）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 4（`finish` 前两次尝试各 1 次 `w3_local_ci_failed`；末次 `finish` 1 次
  `finish_success` 知识整理块；`feedback` 1 次 `feedback_placeholders_remain`）
- **重试次数**: `conan create` 共 7 次（2 次仅编译验证、5 次完整含套件），其中因真实缺陷重试 2 次、
  因补丁集与 conandata 失配重试 1 次、因包缓存命中而强制重建 2 次
- **关键瓶颈**: ① 上游套件本身耗时（含套件自带的每用例 1200s 超时，有一次 `integration/replication-3`
  卡住并靠该超时释放）；② 构建机到 github 不通，稳定复现 CI 行为需要显式提供 `pr.diff`
  （`junk_check` 无 PR diff 时回退整仓扫描，会被其它包的历史文件误判）；
  ③ `finish` 内部调裸 `conan`，而沙箱 PATH 无 conan，必须外层包装
- **耗时较长的步骤**: `make test`（上游套件，单次 20–35 分钟）、`conan-verify` 的 G2 `conan create`、
  `finish` 的 step4+step5（各自完整跑一次构建与套件）

---

## 建议

### SKILL 设计改进

1. **`refresh-patch` 的构建产物排除清单需要显式豁免通道**：`_GENERATED_NAMES` 目前对
   **已修改文件**同样生效，会把 `src/Makefile`、`src/config.h` 这类真实源码改动静默丢弃
   （`refresh_patch.py` 中该常量上方注释写「only used for NEW files」，与实际实现不一致），
   并且它**不回写 `conandata.yml` 的 `patch_file` 列表**。结果是 `finish` 的 step1 跑完后，
   补丁名与 conandata 失配，step5 的 `conan create` 报
   `Patch file does not exist` —— 对任何需要改这两个文件的配方都是必踩。
   建议：排除规则只作用于新增文件；或在替换补丁集时同步改写 conandata 的补丁清单；或至少
   在丢弃文件时打印显式警告而不是静默跳过。
2. **`finish` 的 W3 应默认以 PR 语义运行 `junk_check`**：`build_and_test.sh` 在无 PR diff 时
   回退整仓 `git ls-files`，会把**其它包**已跟踪的 `.staging-verified`/`.build-closed` 判为
   JC1/JC5 失败，本地必假失败；应默认走 prdiff 语义或在本地自动生成 diff。
3. **`finish`/`conan-verify` 应使用当前解释器可执行的 conan 路径**（例如通过
   `sys.executable` 同目录解析或读取 `tools.build:compiler_executables` 类似的配置），
   而不是依赖进程 PATH 中的裸 `conan`，否则在受限 shell 里整条流水线起不来。
4. **HANDOFF 的 `RESUME_CMD` 需与失败类型匹配**：`finish` 失败时给出的
   `RESUME_CMD: ... finish <pkg> <ver> failed` 把状态写成了 `failed`，而实际应带原目标状态
   （本任务为 `built`）续跑，照抄会把归档状态写错。

### 模板改进

1. **`SKILL_FEEDBACK` 报告的自动填充字段存在明显缺口**：本次自动生成后仍留有 14 处待填占位符，且若干自动填充项与实际不符 —— 上游仓库填成 `(未知)`（conandata.yml 里就有）、
   适配路径被固定写成「路径 A（基础适配）」（本任务申报 A+B 叠加，路径 B 无法表达）、构建日期为 `unknown`。
   建议：上游仓库从 `conandata.yml`/`conanfile.py` 读取；适配路径从平台任务
   `activity`/任务申报读取或留空由人填，而不是默认 A。
2. **`test_package/MANIFEST.yml` 的 `upstream_test_in_build` 语义建议明确**：本配方在原生构建时确实
   在 `build()` 内执行上游套件，但模板初值容易被写成 `false`（与行为不符会被评审挑出）。
   建议在模板注释里直接写明「原生构建会执行则填 true」。
3. **PR 模板缺少「补丁生成方式」字段**：当补丁由 `refresh-patch` 生成（且依赖编辑追踪器）时，
   评审需要知道这一前提，建议在模板里增加一行可选说明。

### 自动化补全

1. **编辑追踪器应在前置流程自动建立**：既然 `refresh-patch` 的精准模式依赖
   `edit_tracker`（基线指纹 + 精确模式无排除规则），而 `init-build` 已会调用
   `snapshot()`，建议把「修改后自动 `track-edit scan/add`」纳入 `finish`，或在
   `refresh-patch` 检测到无 tracker 时**拒绝运行并提示先建 tracker**，避免静默产出不完整补丁集。
2. **构建期可自动提供 PR 清单**：`JUNK_PR_DIFF`/`pr.diff` 目前需要人工准备；建议
   `finish` 在本地未提交场景下自动生成与最终 PR 等价的文件清单并传给 `junk_check`。
3. **套件卡死应可诊断**：本次有一次 `integration/replication-3` 长时间无进展、
   靠套件每用例超时释放。建议在本地 CI 增加「测试目录无活动 N 分钟」的检测并在日志中明确标注，
   否则容易被误读为构建失败或静默丢弃一个单元。

### 知识图谱覆盖

1. 新增 E-entry：**「musl 缺少 glibc `program_invocation_name` 系列符号，兼容层以 NULL 定义导致
   `strdup(NULL)` 启动崩溃」**，特征：程序无输出直接 SIGSEGV（rc=139），且同包内不链接
   `setproctitle.o` 的另一个可执行文件正常 —— 这是快速定位的关键判据。
2. 新增 E-entry：**「内核不支持 `madvise(MADV_FREE)`（EINVAL），上游断言型探测直接终止进程」**，
   附最小复现探针写法（`mmap`+`mprotect`+`madvise` 比较 `MADV_FREE` 与 `MADV_DONTNEED`）。
3. 新增 E-entry：**「`refresh-patch` 丢弃已修改的 `Makefile`/`config.h` 且不回写 conandata.yml，
   导致 finish 后 `Patch file does not exist`」**，并在条目里给出 `track-edit` 精准模式的解法。
4. 建议把「OHOS 上 `keydb-server --version` 需先签名才可执行」这类平台前置约定也纳入图谱，
   避免下一位适配者把签名缺失误判为配方缺陷。

---

## 作者

- **姓名**: Yunan0718
- **邮箱**: 2801558242@qq.com
- **Agent ID**: E548
- **生成时间**: 2026-10-04 20:38:06
- **PR 编号**: —
- **Git Commit**: 172d7d38e0
