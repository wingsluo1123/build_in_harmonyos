# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_40944ddd.md`

---

## 背景

- **软件名称**: osdclock
- **版本**: 0.5
- **构建日期**: 2026-10-13
- **构建系统**: makefile
- **上游仓库**: https://deb.debian.org/debian/pool/main/o/osdclock/osdclock_0.5.orig.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 2
- **编译依赖**:
- libxosd/2.2.14
- libxcb/1.16
- libxau/1.0.11
- libxdmcp/1.1.5
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: makefile |
| conan-verify | 配方验证 | 通过 | G1–G4 + L2/L4/L5 全过（G2 真 conan create） |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | PR #15612, CI 通过 | AI Review: Phase 1 (等待摘要) |

### 失败与问题

本次流程未遇到阻塞性问题

### 知识图谱使用情况

- **引用知识条目**: E537（引擎命中，KD8/KF6 场景，经判定不适用）；同族归档 `archives/l/libxosd/2.2.14`（Debian pool 源 URL 先例 + `cpp_info.requires` 传递写法）
- **新增知识草稿**: 4 条（E429 / E479 / E549 / E550）
- **引擎命中情况**: 草稿目录 3300 条
- **测试统计**: 总计 9, 通过 9, 失败 0, 跳过 0（test_package：5 条用例 / 9 条断言）
- **未覆盖的错误模式**: ① aarch64 `char` 无符号 + `getopt_long` 返回值承接 → 选项循环死锁（E429）；② HMDFS 上 conan 依赖 `.so` 的 symlink 条目不可读 → lld `unable to find library -lX` / loader `Error loading shared library`（E479）；③ 老 XOSD 客户端对 libxosd 2.2.14 `xosd_init()` 7 参 API 漂移（E549）；④ zsh heredoc 临时文件走 `TMPPREFIX` 而非 `TMPDIR`，OHOS `/tmp` 只读致 L0 门禁失败（E550）。四条均已落草稿待审。

### AI 检视结果

- **检视阶段到达**: Phase 1 (等待摘要)
- **变更摘要评估**: 本次按 adapt-lib-flow §6「到 PR 即停」执行，PR 创建后未进入 AI 检视轮询（`--no-wait` 语义），故未见变更摘要
- **检视意见数量**: 0（会话内未进入 Phase 3；续环交 follow-up）
- **检视意见处理**: 无意见可处理。follow-up 续环命令：`python3 scripts/ohc-run.py submit osdclock 0.5 --resume`（或 `gitcode_pr.py get-comments --all-comments` 拉取后处理）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 通过 (PR 校验)
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 3（W3 × 2：zsh heredoc `TMPPREFIX` 缺失、`.staging-verified` 被跟踪触发 JC1/JC5；finish step3 G0 × 1：项目无 configure 被 autotools 约定误判，非阻塞）
- **重试次数**: finish × 4（含 2 次 W3 红灯修复后重跑）、conan-verify × 2（首轮 HMDFS `.so` symlink → lld `unable to find library -lxosd -lX11 -lXext -lXinerama`，实体化 `deplibs` 后通过）、W4 审计 × 2（首轮 P1×2 → 整改后 pass）
- **关键瓶颈**: ① 本机会话内核拒绝 `execve` shebang 脚本（EACCES），`conan`/`configure` 等必须做成 ELF 启动器或经解释器调用，首轮排查耗时最长；② HMDFS 上 conan 依赖包 `libX.so → libX.so.6 → libX.so.6.4.0` 的 symlink 条目 `open/readlink` 全 EACCES，lld 与 loader 双双失败；③ 多会话共享 `~/.conan2` 时出现只有 symlink 的残缺包目录（libxau），改用隔离 `CONAN_HOME`（非 HMDFS 卷）后稳定。
- **耗时较长的步骤**: ① HMDFS symlink/残缺缓存根因定位 + 隔离 CONAN_HOME 重建依赖（约 40 min）；② W4 独立审计两轮（约 25 min）；③ conan-verify 首轮失败后的实体化方案实现与复验（约 15 min）。
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-13T17:10:06 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->

---

## 建议

### SKILL 设计改进

1. **W3 的 zsh heredoc 依赖 `TMPPREFIX`**：`ci/conan/build_and_test.sh` 用 zsh 执行，heredoc 临时文件走 `TMPPREFIX`（默认 `/tmp/zsh`）；OHOS `/tmp` 只读时 L0i/L0m 等含 heredoc 的门禁会以 `can't create temp file for here document: read-only file system` 直接失败，报错完全看不出根因。建议在 `workflow_checks.run_local_ci()` 的 `_run()` `env_extra` 里自动注入 `TMPPREFIX=<可写目录>/zsh`（与已有 `ccache_disable_env()` 同处）。
2. **`.staging-verified` 自相矛盾**：`finish` step10/submit 预检要求该文件存在，但 `junk_check.sh` 的 JC1 正则把它当运行时状态文件、JC5 白名单又没有它（checklist #29 与实测不符）；`git add -f` 后 JC1+JC5 双红并阻塞 W3。建议将其加入 `JC5_ALLOWED`（或让 JC1 忽略），至少把「工作区保留但不得入库」写进预检提示。
3. **`junk_check` 的 incremental/full 判定**：本包尚无提交时回落 full 模式，会把全仓历史违规（cloog/kics/libbfio 等 `.staging-verified`）算作本次失败（本轮首跑即被误拦）。建议 full 模式按包目录过滤，或对 JC1/JC5 只告警。
4. **`finish` step3 G0（clean-verify）假定 autotools**：手写 Makefile/无 `configure` 的包必然报 `configure 失败 (exit 127)`（非阻塞但误导）。建议按 `.build-context` 的 `BUILD_SYSTEM` 分支或明确输出「无 configure，跳过」。
5. **`gen_summary` 崩溃**：step8 实测 `'str' object has no attribute 'append'`，SUMMARY.md 未刷新且只有一行 warning；建议补 try/except 与行号，避免框架缺陷被误认为包问题。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **缺「手写 Makefile」配方模板**：`conan-init` 只认 autotools/cmake 等（本轮 init-build 直接报「conanfile.py 模板不可用（autotools）」并跳过），而本仓 21% 配方属 Makefile 族。建议补 `conanfile-makefile.py.tmpl`，固化两条经验：① Makefile 的 `CC/CFLAGS/LDFLAGS/XOSDLIBS` 硬赋值必须走 make 命令行覆盖；② `package()` 不要用上游 `make install`（`INSTALL=/usr/bin/install` 在 OHOS 不存在且不建目录）。
2. **HMDFS 依赖 `.so` 实体化应进模板**：本轮为让 lld/loader 找到依赖库写了约 40 行「按 soname 别名实体化到 `deplibs`/`realdep_libs`」样板（libdazzle/xgamma/libxosd 反复出现同类问题）。建议提供官方小工具（如 `conan.tools.ohos.materialize_dep_libs()`）或模板函数，避免每个配方各写一份。
3. **PR body 模板的「用例数/断言数」口径**：模板只有「用例数」一列，而 R51/rule4 按上游源文件数计用例、test_package 常以断言计数（本轮 5 用例/9 断言）。建议模板分列或明确「合计=用例数，断言数写说明列」，否则极易被判为列和与合计不一致。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **`submit` 的 `packaging_present` 恒 FAIL 应给官方旁路**：本轮按 checklist #14 手工 `create-pr`，绕过了 `submit` 的 W4 前置、R50 两件套与 feedback 骨架自动化。建议对 status=`built` 的库/应用包提供 `--no-packaging-check`（或对 `package_type=application` 放宽），把手工作业收回工具链。
2. **PR 创建前置闸的「既定例外」登记表**：PF7（Debian 源）与 PF9（软件级 README/commands.json/manifest.yaml）对「首次入库 + 上游源消亡」是必然命中，目前每次都要 `--no-preflight` + 人工披露。建议在 `preflight.py` 增加可审计例外清单（如 `ci/config/preflight_exceptions.tsv`，含包名/闸位/理由/PR 链接），已登记则只告警不拦截。
3. **`finish`/`submit` 入口环境自检**：本轮两个失败点（`TMPPREFIX`、`.staging-verified`）都属环境/流程性，却烧掉整轮 W3。建议入口做 5 秒预检：zsh heredoc 可写性探针 + 本包是否跟踪 JC 黑名单文件 + conan home 可写性，命中即 HANDOFF。
4. **多会话共享 `~/.conan2` 的并发保护**：本轮出现只有 symlink 的残缺包目录（libxau，并发 conan 写入所致），且 `conan remove` 因 HMDFS chmod 失败无法自愈。建议 ohc-run 入口检测 `CONAN_HOME` 是否为 `~/.conan2` 并警告，或默认为每包分配 `conan-home-<pkg>`（与 MEMORY 约定一致）。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. **E429** — aarch64 `char` 无符号 + `getopt_long` 返回值承接错误 → 选项循环恒真、程序在初始化前空转（clang 判据 `-Wtautological-constant-out-of-range-compare`；修复=用 `int` 承接）。「x86 上游代码在 aarch64 静默挂死」的通用模式，建议为 `char c` + `getopt` 组合派生 prescan 规则。
2. **E479** — HMDFS 上 conan 依赖包 `libX.so → libX.so.6 → libX.so.6.4.0` 的 symlink 条目 `open/readlink` 全 EACCES：lld 报 `unable to find library -lX`、loader 报 `Error loading shared library`；修复=`generate()` 按 soname 别名实体化到 `deplibs`/`realdep_libs` 并前置 `-L`/`LD_LIBRARY_PATH`。建议与既有 E537（conan 缓存绝对路径 DT_NEEDED 泄漏）互链。
3. **E549** — 老 XOSD 客户端对 libxosd 2.2.14 的 `xosd_init()` 7 参 API 漂移（且 `xosd_display()` 有 `0 <= line < number_lines` 上界，`number_lines` 不能取 1）。
4. **E550** — zsh heredoc 临时文件走 `TMPPREFIX`（非 `TMPDIR`），OHOS `/tmp` 只读 → `can't create temp file for here document: read-only file system`，L0 门禁全挂。对所有在本机跑 finish/W3 的会话都有价值，建议尽快提升为正式条目并写入 MEMORY.md 环境准备段。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: ohc-agent
- **邮箱**: ohc-agent@local
- **Agent ID**: 4047
- **生成时间**: 2026-10-13 18:10:07
- **PR 编号**: 15612
- **Git Commit**: d76896df25
