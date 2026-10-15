# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_c70d9213.md`

---

## 背景

- **软件名称**: xaric
- **版本**: 0.13.9
- **构建日期**: 2026-10-14
- **构建系统**: autotools
- **上游仓库**: https://xaric.org/software/xaric/releases/xaric-0.13.9.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 3
- **编译依赖**:
- openssl/3.5.6.1
- ncurses/6.6
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: autotools |
| conan-verify | 配方验证 | 通过 | G0-G4 全 PASS（`--profile ohos-local`）。仓库默认 profile `ci/conan/profiles/ohos-aarch64` 的编译器指向设备路径 `/data/service/hnp/bin/clang`，在 macOS 上必然失败并把 manifest status 翻成 failed，需另行以 ohos-local 取得真实 PASS 报告 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 部分（PR 改用 gitcode_pr.py 直建） | Gate0-3 与 6 项自检全 PASS、push 成功；create-pr 以裸分支名调用时报 `Can not find the branch ... in project: build_in_harmonyos`（跨 fork 需 `owner:branch` 写法），改直建成功 → PR #15751，CI 以 /rebuild 触发。AI Review: ✅ 未发现问题 |

### 失败与问题

- **1**: 根因=configure 报 `i can not find tgetent`, 解决方案=OHOS 无 libtermcap/libcurses；Conan ncurses 仅提供 libncursesw.a，而 xaric 的 tgetent 搜索链（termcap/termlib/curses/xtermcap）不试 -lncursesw
- **2**: 根因=configure 报 `failed to find OpenSSL`（若未注入）, 解决方案=AX_CHECK_OPENSSL 硬依赖：找不到 openssl/ssl.h 或链接失败即 AC_MSG_ERROR
- **3**: 根因=`./xaric -v` 报 `Woops I need a tty!`, 解决方案=main() 先 `isatty(0)` 检查（irc.c:798），非 TTY 直接 exit(1)
- **4**: 根因=macOS 本地 sys_siglist 重定义, 解决方案=macOS SDK 已声明 sys_siglist，但 xaric configure 的探测程序未通过（macOS 特有），走 sig.inc 生成路径
- **5**: 根因=本机交叉构建 `configure: error: cannot run C compiled programs`（真机原生不复现）, 解决方案=该 configure 无 AC_CANONICAL_HOST，tar 包也不带 config.sub/config.guess（build-aux 只有 compile/depcomp/install-sh/missing），AutotoolsToolchain 因此不注入三元组，configure 停在 native 模式去执行刚链接出的 a.out
- **6**: 根因=cross 模式 `configure: error: cannot run test program while cross compiling`（SA_CHECK_SOCKOPT）, 解决方案=sa.ac 的 `AC_RUN_IFELSE` 第 4 参数（action-if-cross）为空，autoconf 2.69 生成 `as_fn_error` 硬失败
- **7**: 根因=`make: *** [aclocal.m4] Error 127`、`aclocal-1.16: command not found`, 解决方案=0001/0002 改了 sa.ac 与 configure.ac，二者正是 `am__aclocal_m4_deps`，mtime 晚于 aclocal.m4 → automake maintainer 规则要求重生成，而构建机无 aclocal/automake
- **8**: 根因=`ld.lld: error: duplicate symbol: term_scroll / term_insert / term_delete / term_cursor_left`, 解决方案=ircterm.h 把 4 个函数指针写成暂定定义，ircterm.c 又重复定义其中 2 个；clang ≥ 10 默认 `-fno-common`，每个包含该头的 TU 都发出强符号
- **9**: 根因=`ld.lld: error: duplicate symbol: trace`（另一侧为 libncursesw.a 的 lib_trace.o）, 解决方案=ncurses 也导出 `trace`；Conan 的 ncurses 是**静态** libncursesw.a，该成员被整体拉入链接。动态系统 ncurses（如 macOS libncurses.dylib）时可执行文件定义优先，故原生验证不暴露
- **10**: 根因=本机 W3 的 L1e 破坏性反向测试会判 test_package 为空壳, 解决方案=test() 在 `can_run(self)` 为假时直接 return，CI 把 bin/ 移走后 `conan test` 仍退出 0

### 知识图谱使用情况

- **引用知识条目**: knowledge/drafts/DRAFT-xaric-0.13.9-autotools-tgetent-chain-ncursesw.kv, knowledge/graph/E248.kv, knowledge/drafts/DRAFT-14410-static-ncurses-beep-duplicate-symbol.kv, knowledge/drafts/DRAFT-fermi-lite-0.1-header-tentative-definition-duplicate-symbol.kv, knowledge/graph/E205.kv
- **新增知识草稿**: 7 条
- **引擎命中情况**: 草稿目录 3320 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**:
  1. autoconf 2.69 且**无 AC_CANONICAL_HOST**、tar 包**不带 config.sub/config.guess** 时，AutotoolsToolchain 不注入三元组，交叉构建下 configure 停在 native 模式去运行刚链接的 a.out，报 `cannot run C compiled programs`（E205 只覆盖“有 config.sub 但不认 ohos 三元组”，E007 只覆盖 config.guess 无法判定系统）
  2. `AC_RUN_IFELSE` 的 action-if-cross 为空 → cross 构建直接 `cannot run test program while cross compiling` 硬失败（E543 覆盖 AC_TRY_RUN 交叉中止，但未覆盖“第 4 参数缺失”这一 autoconf 生成物形态与补 cross 分支的修法）
  3. 静态 `libncursesw.a` 与程序自有同名符号冲突的 **trace** 实例（DRAFT-14410 记录的是 beep；本例语义不同，其首选 `--allow-multiple-definition` 不可用，必须走 fallback 改名）

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: atomgit-bot 已生成合并请求摘要；代码审查结论 `✅ 未发现问题`
- **检视意见数量**: 0 条（仅 1 条 Info 级汇总评论 comment_id=193755851，无 P0/P1/P2 意见）
- **检视意见处理**: 无需修改；无未闭环 review thread（rule6/rule11 满足）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: **构建成功** — PR #15751 / 构建 #91339 / worker OpenHarmonyPCDeveloper-CI-005 / SHA 269c04ca，7 个构建步骤全绿，Conan test_package ✅（真机 PTY 运行）、L0 ✅、L1 ✅（L1e ✅）、L2 ✅、L4 ✅、L5 ✅，包产物 1 ✅，已上传 xaric/0.13.9
- **CI 失败原因**: 无（首轮即绿）

### 效率分析

- **HANDOFF 次数**: 3（① 前序会话 W3 失败：conandata 版本嵌套与 `source()` 取键不一致导致 `get() got an unexpected keyword argument '0.13.9'`；② 本会话 W3 失败：交叉构建 `cannot run C compiled programs`；③ 本会话 submit 的 pr_creation_failed：跨 fork head 写法）
- **重试次数**: conan create 6 轮失败后第 7 轮通过（TypeError → 三元组 → sockopt cross 分支 → aclocal Error 127 → term_* duplicate → trace duplicate → 成功）；另有 2 次 create-pr 读超时（假超时，均经 list-prs 复核确认 PR 已建）
- **关键瓶颈**:
  1. `finish` Step4 的 conan-verify 硬编码仓库 profile（设备路径），本机交叉场景必失败并污染 manifest status，需人工用 `--profile ohos-local` 补跑并纠正状态
  2. 每轮本机交叉 conan create 约 3-4 分钟（-j1），6 轮试错合计约 25 分钟纯等待
  3. PF9 与 PF8/R38 对软件级 commands.json/README.md/manifest.yaml 的结构性互斥（本 PR 以 OHC_PREFLIGHT=0 + 正文声明处理）
  4. `conan_verify.py` gate2 用 f-string 拼接 conan 路径未加 `shlex.quote`：当 `which conan` 落在含空格路径时 RC=127，日志只剩一行 `/bin/sh: /Users/.../Library/Application: No such file or directory`，定位成本高
- **耗时较长的步骤**: W3 本地 CI 模拟（setup.sh + build_and_test.sh 全量 conan create + L1e 反向测试，约 6 分钟）；远程 CI #91339 从触发到出结果约 65 分钟（含排队）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 1 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-14T15:44:52 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/xaric-0.13.9 --target main --title 'feat(xaric): 0.13.9 适配完成' |
| 2026-10-14T15:54:47 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. `finish` 的 Step4 应支持 `CONAN_PROFILE`（或 `--profile`）透传给 ConanVerifier：本机交叉（ohos-local）时 Step5 的 W3 已经按 `CONAN_PROFILE` 走，Step4 却固定用仓库 profile，两者口径不一致，且 Step4 失败会把 `status` 从 built 翻成 failed，需要人工依据 R29 纠回。建议 Step4 读取同一 `CONAN_PROFILE`，或在 profile 不可用时降级为 warn 而不是改 status。
2. SKILL 应明确“本机交叉验证”的标准姿势：`CONAN_PROFILE=ohos-local finish ...` + `conan-verify <pkg> <ver> --profile ohos-local` 两步，并说明 L2 冒烟在本机必然 skip（OHOS ELF 不可执行）、rule12 以远程 CI 为权威。目前这些只能从 slrn/scws 等历史归档反推。
3. 建议在 SKILL 中固化“跨 fork 建 PR”的 head 写法（`owner:branch`）：`ohc-run.py submit` 内部调用 `create-pr --source <裸分支名>`，在 fork 协作模式下必然报 `Can not find the branch`，本次与 puzzles 修复 PR 都因此改走 `gitcode_pr.py create-pr` 直建。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. `templates/积分赛事PR模板.md` 的两张表行集合不一致：上游表有「其他测试」行，适配后表没有。当上游把某类用例归入「其他测试」（如 puzzles 的 fuzzpuzz harness）时，适配后表无法一一对应，只能改分类或改合计口径，容易触发 rule2/rule3 的“测试减少/口径不一致”质疑。建议两表行集合统一（都含「其他测试」）。
2. 模板缺少「远程 CI 构建编号」字段：§13 要求回填真实构建编号，但只能塞进「补充说明」自由文本，机器不可校验。建议在「验证结果」增加一行 `- 远程 CI 构建编号：`。
3. `submission.py` 的 `_generate_pr_body()` 生成的正文与赛事模板不同构（无复选框、鸿蒙特有测试恒为 0、章节名不一致）。既然 SKILL 规定必须以 `templates/积分赛事PR模板.md` 为准，建议该函数直接读模板填充，避免每次手写覆盖。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. `scripts/ohc/conan_verify.py` gate2：`cmd = f"{self._conan_path} create ..."` 未对 conan 路径做 `shlex.quote`。当 `shutil.which("conan")` 命中含空格路径（本机为 `~/Library/Application Support/.../bin/conan` 的符号链接）时，shell 词分割使 RC=127，`reports/conan-create.log` 只留下一行 `/bin/sh: /Users/.../Library/Application: No such file or directory`，且知识图谱会误命中 E424/E540。建议改为 `shlex.quote(self._conan_path)` 或走 `_conan([...])` 的 list 形式。
2. `scripts/gitcode_pr.py monitor-review`：`NameError: name 'unreplied_opinions' is not defined`（cmd_monitor_review 内变量未定义），命令完全不可用；slrn 归档的 notes 也记录过同一 bug，至今未修。
3. `scripts/gitcode_pr.py create-pr`：请求读超时后直接抛栈，但 PR 实际已创建（本次 xaric #15751、puzzles #15767 两例）。`ohc-run.py submit` 有“假超时 → list 复核”逻辑，直建路径没有；建议 create-pr 自身在超时后自动 list-prs 复核并返回已存在的 PR 号。
4. `pre_pr_audit.py report` 只打印不落盘：`reports/audit-result.json` 仍需人工放置，且旧文件不会被覆盖，容易出现“审计文件早于被审文件”的 R52 失真。建议 report 直接把结果写入唯一权威路径并记录被检文件 sha256。
5. `pre_pr_audit.py generate` 默认输出 `$HOME/tmp/audit-input-*.json`，该目录在受限沙箱下不可写（PermissionError）；建议默认落到 `$TMPDIR` 或仓库内 reports/。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. **E205 表述过强**：`rec_description` 写 “Never use --build/--host flags as workaround”，但对**既无 config.sub/config.guess、又无 AC_CANONICAL_HOST** 的老 autoconf 包（xaric 0.13.9 实测），没有可补的 guess/sub 文件，显式三元组是唯一可行解，仓内 slrn/1.0.3、scws/1.2.3 亦如此。建议在 E205 增补适用边界，或新建条目区分“有 config.sub（补平台识别）”与“无 config.sub（显式三元组 + cross 模式探测钉值）”两种形态。
2. **E248 覆盖面偏窄**：现有 root_cause/affected_scope 只讲 `Makefile.am` 与 `Makefile.in` 的 mtime 倒挂。本包实例是补丁触及 `sa.ac`/`configure.ac`（即 `am__aclocal_m4_deps`），倒挂发生在 `aclocal.m4` 这一层，报错是 `aclocal-1.16: command not found`（而非 automake）。建议扩展 affected_scope 到“任何被 am__aclocal_m4_deps 引用的输入（configure.ac、sinclude 的 .ac/.m4）”，并把处方从“对齐单个 Makefile.in”推广为“按 aclocal.m4 → configure → config.h.in → Makefile.in 依赖序整体重打”。
3. **DRAFT-14410 的处方顺序**：其 rec 首选 `-Wl,--allow-multiple-definition`，仅在括注里提到“语义不同应改名”。本包 `trace()` 正是语义不同（varargs 日志 vs `char *trace(unsigned)`），若照首选做会让 ncurses 内部调用落到 xaric 的日志函数上。建议把“先判语义、语义不同即改名”提升为主判据，`--allow-multiple-definition` 降为语义等价时的选项。
4. **建议新增条目**：`AC_RUN_IFELSE` 缺 action-if-cross 时 cross 构建 hard fail（本包 0002 补丁），以及“交叉构建下 test() 必须保留产物断言，否则 CI 的 L1e 破坏性反向测试判空壳”（本包 test_package/conanfile.py），二者当前均无对应 E 条目。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: songzhenyan
- **邮箱**: apVBMI1DvwCqWTll.songzhenyan@noreply.gitcode.com
- **Agent ID**: DE5A
- **生成时间**: 2026-10-14 15:54:47
- **PR 编号**: —
- **Git Commit**: 269c04ca2b
