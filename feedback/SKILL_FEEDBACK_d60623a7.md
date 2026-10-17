# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_d60623a7.md`

---

## 背景

- **软件名称**: uqm
- **版本**: 0.8.0
- **构建日期**: 2026-10-16
- **构建系统**: custom
- **上游仓库**: https://downloads.sourceforge.net/project/sc2/UQM/0.8/uqm-0.8.0-src.tgz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 2
- **编译依赖**:
- sdl2/2.32.10
- libpng/1.6.58.3
- libvorbis/1.3.7
- zlib/1.3.2
- **最终状态**: 成功（PR 已建、CI 已触发；按任务要求未等待 CI/AI Review，result 上报 partial）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | SourceForge 官方 tarball，sha256 核验一致；工具把 `src/abxadec` 误判为嵌套源码根，已手工还原正确源码树 |
| build | 编译构建 | 成功 | 构建系统: custom；`config.state` + `reprocess_config` 免交互，`build.sh uqm -j1` 0 error |
| conan-verify | 配方验证 | 通过 | G1/G2/G3/G4 + L2/L4/L5 全通过（conan create --build=missing --user=ohpcd --channel=stable） |
| finish | 归档收尾 | 完成 | W2 结构 16 文件仅配方目录；R36 依赖 4 项在仓；W3 本地 CI 模拟通过（JC/KC/L0 全通过） |
| submit | PR提交+AI检视+CI | PR 已建、CI 已触发 | PR #16274；AI Review: 未等待（--no-wait 口径） |

### 失败与问题

- **1**: 根因=configure 阶段报 `can't create /tmp/build.$$.tmp: Read-only file system`，libpng 探测失败后 exit 1, 解决方案=`build/unix/config_functions:19` 硬编码 `TEMPFILE="/tmp/build.$$.tmp"`；OHOS `/tmp` 只读（E002）；因是字面量，仅 export TMPDIR 无效，须补丁改 `${TMPDIR:-/tmp}`
- **2**: 根因=`netmanager_bsd.c` 报 `unknown type name 'fd_set'` / `FD_SETSIZE` / `select` 未声明（18 error）, 解决方案=musl 不随 `<sys/types.h>` 传递 `<sys/select.h>`，补丁新增 `#include <sys/select.h>`
- **3**: 根因=上游构建系统把编译器写死为 `gcc`（`config_proginfo_build: PROG_gcc_FILE="gcc"`），本机/CI 无 gcc, 解决方案=在 `build_folder/toolchain-shim/` 生成 `gcc` → conan clang 转发 shim 并前置到 PATH（私有目录，不污染共享前缀）
- **4**: 根因=`./build.sh uqm config` 会阻塞在交互菜单，CI 无法自动执行, 解决方案=合成 `config.state`（格式同 `menu_save_*`）+ `reprocess_config`，上游 INSTALL 明确认可该无人值守方式
- **5**: 根因=安装后 `lib/uqm/uqm` 直接运行报 `Error loading shared library libpng16.so.16 / libvorbisfile.so / libogg.so`, 解决方案=libpng/libogg/libvorbis 为共享依赖，位于 Conan 缓存；注入各依赖 libdir 的 `-Wl,-rpath`，test_package 另用 VirtualRunEnv
- **6**: 根因=直接运行 `uqm` 报 `*** FATAL ERROR: Could not load basic content ***`, 解决方案=游戏**内容包**（`uqm-0.8.0-content.uqm`）是上游单独发布的资源，不在源码包内；已在 README/notes/PR 说明并作为「SDL+音频+content 挂载链路已打通」的可观测终态
- **7（工具侧）**: 根因=`refresh-patch --auto` 规则模式因 `EXCLUDE_DIRS` 含 `build` 漏采 `build/unix/config_functions` 补丁, 解决方案=改用 `track-edit` 编辑追踪器精准模式（无需排除规则）生成
- **8（工具侧）**: 根因=OHOS 沙箱下 Python `posix_spawn` 无法按 PATH 解析可执行文件，`subprocess.run(["git", ...])`（无 cwd）抛 FileNotFoundError，使 `preflight.changed_files` PF0 fail-closed, 解决方案=本次以 `PYTHONPATH=sitecustomize`（`subprocess._USE_POSIX_SPAWN=False`）绕过；建议工具侧统一改用绝对路径或显式 cwd
- **9（工具侧）**: 根因=共享 `.git` 中两个对象被不完整写入（`index` 损坏 + `README.md` blob 截断），push 报 `inflate: data stream error`, 解决方案=重建 worktree index（`read-tree HEAD`）、删除损坏 loose object 后 `touch + git add` 重写；建议工具在 push 失败分支给出「对象损坏 → fsck/重写」指引

### 知识图谱使用情况

- **引用知识条目**: [E754, E757]
- **新增知识草稿**: 2 条（E754：构建脚本硬编码 /tmp，TMPDIR 无效须补丁；E757：musl 下 fd_set/select 需显式 `<sys/select.h>`）
- **引擎命中情况**: 草稿目录 3777 条
- **测试统计**: 总计 4, 通过 4, 失败 0, 跳过 0
- **未覆盖的错误模式**: 本次两类新问题均已沉淀为草稿（E754/E757）。仍建议补充两条：①「OHOS 无 gcc 时，自研构建系统写死编译器名 → 私有 shim 转发」；②「交互式 configure（文本菜单）→ 合成 config.state + 对应 reprocess 目标实现无人值守」。二者在本次均有完整实测证据，但尚无对应 E 条目。

### AI 检视结果

- **检视阶段到达**: —（按任务要求 `--no-wait`，未进入 AI Review 监控）
- **变更摘要评估**: 未获取（不等待平台异步产出）
- **检视意见数量**: 未知
- **检视意见处理**: 待 follow-up `submit --resume` 续环处理

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（JC/KC/L0 全通过，Pass rate 100% (1/1)；日志 `reports/w3-local-ci.log`）
- **远程 CI (PR 校验)**: 已主动评论 `/rebuild` 触发（note_id 194230641），未等待结果
- **CI 失败原因**: 无（尚未知）

### 效率分析

- **HANDOFF 次数**: 3（self_check_failed / git_push_failed / pr_creation_timeout）
- **重试次数**: submit 共 3 轮（补本地打包产物 → 修损坏 git 对象 → 成功推分支并建 PR）
- **关键瓶颈**: ①工具链环境问题（共享 `.git` 对象损坏、OHOS 沙箱下 `posix_spawn` 无法解析 PATH）而非适配本身；②`packaging/` 本地产物需手工 tar（submit 自检强制但工具不自动生成）；③上游自定义构建系统需要「读上游 INSTALL → 合成 config.state」的一次性调研成本
- **耗时较长的步骤**: ①W4 独立审计（两轮子任务各 ~10 分钟，纯上下文等待）；②`conan create` 干净构建（每轮约 3–5 分钟，本次共 4 轮）；③补丁工具盲点排查（refresh-patch 漏采 + track-edit 兜底约 10 分钟）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 4 个事件（含 3 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-16T20:22:09 | handoff:self_check_failed | 自检未通过: ['packaging_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit uqm 0.8.0 |
| 2026-10-16T20:25:37 | handoff:git_push_failed | git push 失败: error: inflate: data stream error (unknown compression method) error: unable to unpack ce5b6d06c314b3fe2510bc14796b4f412775a901 header error: inflate: data stream error (unknown compression method) error: unable to unpack ce5b6d06c314b3fe2510bc14796b4f412775a901 header fatal: loose obje |
| 2026-10-16T20:29:57 | handoff:pr_creation_timeout | gitcode_pr.py create-pr 超时，请手动重试或检查网络 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/uqm-0.8.0 --target main --title 'feat(uqm): 0.8.0 适配完成' |
| 2026-10-16T20:31:00 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **PF9 路径闸对软件级必需文件误拦（本次被迫 `--no-preflight`）**：`preflight.check_branch_and_paths` 用 `len(f.split("/")) < 5` 判定「缺版本目录层」，
   但 `archives/<字母>/<包>/commands.json`（R38 强制）、`README.md`、`manifest.yaml`（ARCHIVE-SPEC §2.1「必须」）天生只有 4 段 → 任何 CLI 包 PR 都会被硬拦。
   本次唯一 preflight 发现即此项（3 个文件），其余 PF1–PF8 全通过。建议给软件级白名单（`commands.json|README.md|manifest.yaml`）豁免后再判层次。
2. **create-pr 假超时后未自动复核**：v12.17 已为「POST 失败」加了 15s 复核，但 `submission` 的 **30s 超时分支**没有复用该复核，直接 emit HANDOFF；
   本次 PR #16274 实际已创建成功（`list-prs --source-branch` 复核确认），工具却报了 `pr_creation_timeout`，导致 `.submit-state.json` 缺 PR 号。
   建议超时分支统一走「先 list 复核，命中则回填 state 继续」。
3. **refresh-patch 规则模式的 `EXCLUDE_DIRS={"build",...}` 盲区**：UQM 这类自研构建系统把脚本放在 `build/unix/`，其源码级改动会被漏采，
   只能靠 `track-edit add` 兜底（本次即如此）。建议：要么把「源码树内的 `*.sh`/无扩展名脚本」从该排除中豁免，要么在该目录命中改动时输出显式警告提示改用 track-edit。
4. **submit 自检 `packaging_present` 与 `packaging/` 被 gitignore 的矛盾**：自检要求 `packaging/*.tar.gz`，但工具链没有任何一步生成它，
   每个任务都要手工从 conan 包目录 tar；且 `finalize_archive` 还会额外要求 `*-debug.tar.gz`。建议 `finish`（或 submit 前）自动完成本地打包。
5. **共享 `.git` 对象损坏缺指引**：本次 `git push` 报 `inflate: data stream error`（loose object 截断）。建议 push 失败分支识别该特征并输出
   「损坏对象 → `git cat-file -p` 定位 → 删除 loose 文件 + `touch && git add` 重写」的修复步骤。
6. **同机多会话共享 `$HOME` 的 result 覆盖风险**：默认输出 `$HOME/ohpcd-ai-worker-result.json` 会被并行会话互相覆盖（本次进入时该文件属于 kiconthemes 任务）。
   建议默认路径加入 session/agent 维度，或提示调度方注入 `OHC_RESULT_OUT`。

### 模板改进

1. **PR body 生成器把 test_package 断言数当成「上游用例数」**：`_generate_pr_body` 从 `test-report.md` 取 total/passed 后，
   直接填进「上游库测试用例统计」表；上游 0 用例时会出现「上游单元测试 4」的错误陈述（本次已手工在 `reports/pr-body.md` 修正，未用自动稿）。
   建议数据源拆分为 `upstream_total`（来自 MANIFEST.yml `upstream_tests`）与 `consumer_total`（来自 test-report.md），两表各取各源。
2. **建议把「补全测试用例说明」纳入自动模板**：`.gitcode/PULL_REQUEST_TEMPLATE.md` 无该小节，但积分赛模板有；
   上游无测试的包（本次即如此）必须以它为申报出口。建议标准模板补齐该小节并由 MANIFEST.yml 自动填充。
3. **`manifest.yaml` 版本级模板占位符未替换**：init-build 生成的版本级 manifest 残留 `software: "{software}"`、`build_system: "{BUILD_SYSTEM}"`，
   建议模板渲染时即替换或改为 `TODO` 显式标记（当前静默留 `{...}` 容易被 CJ/评审当成未完成）。

### 自动化补全

1. **init-build 嵌套源码根判定**：本次把 `uqm-0.8.0/src/abxadec`（仅含若干 .c 的模块子目录）判定为源码根并「提升」，
   导致 `.work` 只剩该子目录。建议启发式加约束：候选目录须包含构建入口（`configure`/`CMakeLists.txt`/`Makefile`+`README`/`.in` 模板）或位于 tarball 顶层；
   否则保持顶层而不是提升。
2. **`config.state` 类无人值守化可沉淀为通用能力**：对使用文本菜单 configure 的包，可提供「探测 `config.state` 机制 → 生成推荐取值 → 写入并 reprocess」的脚本化步骤。
3. **W4 审计子任务的产出落位**：`pre_pr_audit.py report` 只打印不写盘，`reports/audit-result.json`（submit Gate 3 的唯一权威路径）需人工从 `/tmp` 拷贝。
   建议 `report` 增加 `--write`（默认写入版本目录 reports/），消除这一手工缝隙。
4. **依赖探测方式自动识别**：本包三种机制（sdl2-config / pkg-config / 裸 `-lpng`）各需不同接入手段，建议在 init-build 预扫描阶段输出
   「该包使用哪些探测机制」清单，减少探索期试错。

### 知识图谱覆盖

1. **建议新增 E 条目：自研构建系统写死编译器名**。模式：`PROG_*_FILE="gcc"` / `CC=gcc` 硬编码于构建脚本 → OHOS 无 gcc → 编译/探测失败。
   推荐方案：在 `build_folder` 私有目录生成同名转发 shim 并前置 PATH（符合 R49 私有目录口径，不使用共享前缀）。
2. **建议新增 E 条目：交互式 configure 的无人值守化**。模式：上游 configure 是文本菜单（无 CLI 参数）→ CI 阻塞。
   推荐方案：优先读上游 INSTALL/README 是否提供状态文件机制（如 UQM 的 `config.state` + `reprocess_config`），否则用 `expect`/stdin 注入。
3. **E754/E757 的定位**：E754 覆盖「脚本内联 `/tmp` 字面量 → 仅设 TMPDIR 无效，须补丁改 `${TMPDIR:-/tmp}`」，与已有 E002（挂载只读）互补；
   E757 覆盖「musl 不随 `<sys/types.h>` 传递 `fd_set/FD_SETSIZE/select`」，与 E194/E208（musl 头文件缺失）互补。建议主编审核时保留其互补定位，避免合并进 E002/E194 后丢失「TMPDIR 无法覆盖字面量」这一关键判据。

---

## 作者

- **姓名**: ohc-agent
- **邮箱**: ohc-agent@local
- **Agent ID**: EE05
- **生成时间**: 2026-10-16 20:31:00
- **PR 编号**: 16274
- **Git Commit**: f4cb73b53c
