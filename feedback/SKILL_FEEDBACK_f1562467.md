# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_f1562467.md`
> 自动采集有 6 处失真（见「自动化补全」第 1 条），本文已按实修正。

---

## 背景

- **软件名称**: levee
- **版本**: 4.0
- **构建日期**: 2026-09-27
- **构建系统**: makefile（`configure.sh` + `configure.inc`，作者自写的 shell 版 autoconf 模拟器；init-build 误判为 autotools）
- **上游仓库**: https://github.com/Orc/levee（conandata 使用其 v4.0 tag 归档；自动采集填成了归档 URL）
- **适配路径**: 路径 A（基础适配）+ 路径 B（知识草稿 E587/E588/E590）；自动采集只判出路径 A
- **补丁数量**: 3
- **编译依赖**:
- ncurses/6.6
- **最终状态**: 成功（本地 conan-verify + W3 通过，built；远程 CI 待 PR 触发）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | Debian orig 与官方 tag 内容逐字节一致，conandata 改用官方 tag（PF7） |
| build | 编译构建 | 成功 | 构建系统: makefile；CC=`clang -static-pie` |
| conan-verify | 配方验证 | 通过（G1/G2/G3 实跑；G4/L2/L4/L5 被工具跳过但显示 PASS） | 见「SKILL 设计改进」第 1 条 |
| finish | 归档收尾 | 完成（W3 通过；step5b/step8 报失败均为框架侧问题） | W3: L0/L1(含 L1e)/L2/L5 pass，L4 warn |
| submit | PR提交+AI检视+CI | 本报告写于建 PR 之前，随 PR 首次提交 | fork 贡献者手动建 PR 后 trigger-ci；AI Review: 未开始 |

### 失败与问题

- **1**: 现象=链接报 `duplicate symbol: refresh / scroll / LINES / COLS / UP`（另一处定义在静态 `libncursesw.a` 的 lib_gen.o/lib_setup.o/lib_termcap.o）；根因=levee 自定义了与 curses 同名的全局，动态链接时被可执行文件符号抢占而静默通过，R26 下 ncurses 是静态单体归档；解决=补丁 0001 在 `levee.h` 用宏改名（草稿 E587）
- **2**: 现象=`unixcall.c:314 too many arguments provided to function-like macro invocation`；根因=musl `glob()` 不支持 `GLOB_NOMAGIC`，走 levee 内置 glob，其中一处 `logit()` 漏写双括号；解决=补丁 0003 顺带修正
- **3**: 现象=普通 CC 下 configure.sh 返回 0 但 Makefile 残留 12 个 `@CC@` 等占位符，make 报 `CC@: No such file or directory` Error 127；根因=configure.inc 在构建机执行 config.sed/mkversio，x86 上动态 OHOS 产物缺 ld-musl；解决=CC 驱动为 `clang -static-pie`（草稿 E588）
- **4**: 现象=撤销溢出、大块 yank、`!` 过滤临时文件写死 `/tmp/`；根因=`os_mktemp()` 硬编码且无视 TMPDIR，HarmonyOS PC `/tmp` 只读；解决=补丁 0003 跟随 `$TMPDIR`
- **5**: 现象=conan-verify L2 的 `--version/--help` 会进入编辑器阻塞；根因=上游只有短选项；解决=补丁 0002（E503 先例）
- **6**: 现象=本机 test_package 中 `TERMINFO` 指向 ncurses 包仍 `tgetent=-1`，levee 读 EOF 空转超时；根因=ncurses 在 uid 0 下忽略 TERMINFO，本机 conan 以 root 运行，且包内 terminfo 为 CI 用户属主、权限 640；解决=test.sh 在 root 下经 `unshare --user` + root 自有条目副本运行（草稿 E590）
- **7**: 现象=任务给定的 Debian 源会被 PF7 拦截；解决=改用内容一致的作者官方 tag

### 知识图谱使用情况

- **引用知识条目**: E002（/tmp 只读，构建期）、E503（CLI 长选项）；engine 对 duplicate symbol 日志误命中 E163
- **新增知识草稿**: 3 条（E587-draft-A841、E588-draft-B898、E590-draft-BC71；自动采集误报 5 条）
- **引擎命中情况**: 3 次查询：/tmp 硬编码命中 E002（只覆盖构建期）；静态 ncurses 重复符号误命中 E163；W3/G2 无失败未触发
- **测试统计**: 总计 9, 通过 9, 失败 0, 跳过 0（上游 N=0；自动采集误报「总计 0」）
- **未覆盖的错误模式**: ①静态 curses 与程序全局同名导致 duplicate symbol（E587）；②Orc configure.inc 构建期执行辅助程序、x86 上 AC_SUB 静默失败（E588）；③ncurses 在 uid 0 下忽略 TERMINFO 使 root runner 上 terminfo 类 test_package 失效（E590）

### AI 检视结果

- **检视阶段到达**: 未开始（本报告在建 PR 前完成并随首个提交入仓）
- **变更摘要评估**: 尚未生成；PR 建立后由机器人异步产出
- **检视意见数量**: 0（尚未开始）
- **检视意见处理**: 待 PR 检视完成后按 RV-27 逐条闭环；不因非必要意见追加提交

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（L0 pass / L1 pass 含 L1e 破坏性反向验证 / L2 pass / L4 warn / L5 pass）
- **远程 CI (PR 校验)**: 未知（建 PR 后评论 /rebuild 触发）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 2（① finish Step 3 G0 clean-verify HANDOFF，非阻断，原因是 G0 假设存在 `./configure`；② feedback 生成后的 14 处待填项 HANDOFF）。另有 finish 收尾的 KNOWLEDGE CONSOLIDATION 块（EXIT_REASON=finish_success，非失败）。下方自动时间线只记录了 1 个 lang_checked 事件——finish/feedback 发出的 HANDOFF 没有进入时间线（见「自动化补全」第 4 条）
- **重试次数**: test.sh 本地演练 4 轮（2 轮 60s 超时：root 下 terminfo 不可见、`:s` 的 `[more]` 提示吞键）；conan-verify 1 次、finish 1 次即通过
- **关键瓶颈**: 定位 root runner 上 ncurses 忽略 TERMINFO（需对比 root/nobody 探针与 `qemu-aarch64 -strace`）；设计能在 x86 与设备两端都运行的 test_package
- **耗时较长的步骤**: test_package 设计与演练（levee 读 EOF 时空转，脚本化按键需逐条实测 levee 与 vi 的差异，如 `:r` 在光标行之前插入、`p` 不支持计数）；每次演练受 60s 超时约束
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-09-27T05:31:52 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **conan-verify 的 G4/L2/L4/L5 对带点版本号全部静默跳过却报 PASS**：`scripts/ohc/conan_verify.py:601` 的
   `re.search(r'(\w+/\w+@\w+/\w+):(\w+)', output)` 中 `\w` 不含 `.`，`levee/4.0@ohpcd/stable` 取不到 package_id；
   G4（`conan_verify.py:729-741`）又按 `listing["Local Cache"][self.software][self.ref]` 解析
   `conan list --format=json`，而 Conan 2.29 的结构是 `{"Local Cache": {"levee/4.0@ohpcd/stable": {"revisions": ...}}}`
   （没有软件名这一层）→ KeyError →「无法找到程序包 ID」→ `_cache_path` 未设置 → L2/L4/L5 全部
   「⏭️ 跳过（无 cache 路径）」但报告仍是 `✅ PASS`。建议：G4 改为 `listing["Local Cache"][self.ref]`，
   G2 正则改为 `([\w.+-]+/[\w.+-]+@\w+/\w+):([0-9a-f]{40})`，被跳过的门禁在报告与判定里显示 SKIP 而非 PASS。
2. **W3 结束后 conandata.yml 还原到的是镜像改写版**：`ci/conan/build_and_test.sh:1028-1029` 先把
   conandata.yml 复制为 `conandata.yml.orig` 再改写成 gh-proxy 镜像 URL 列表；预下载段 `:1177` 备份的是
   **已改写**的文件，`:1181-1185` 的 trap 还原到它，并打印「已还原为官方 URL」。结果工作区里的已跟踪文件
   留着镜像 URL 列表（下次 commit 会被 PF7 拦）以及归档目录下的 `conandata.yml.orig`（JC1 备份残留模式）。
   建议：预下载备份改为优先取已有的 `conandata.yml.orig`，还原后删除 `.orig`。
3. **finish Step 1 refresh-patch 覆写人工填写的 manifest**：`scripts/ohc/refresh_patch.py:547` 用
   `re.sub(r'\npatch_classification:.*', '', content, flags=re.DOTALL)` 删除 `patch_classification:` **之后的全部内容**
   （包括其后的 `knowledge_gained:` 整节），再追加 `type: auto / guard: pending`；即使补丁逐字节未变，也会把
   旧补丁移进 `patches/.patch-backup-<ts>/`（`:490`）。本次需手工 `git checkout` 恢复。建议：补丁内容不变时
   直接跳过；只替换 `patch_classification` 块本身（匹配到下一个顶层键为止）。
4. **finish Step 3 G0 clean-verify 假设 `./configure`**：`scripts/ohc/clean_verify.py:69` 固定执行
   `{config_shell} ./configure`，对 configure.sh / 纯 Makefile 项目必然 exit 127 并发 HANDOFF。已有 conanfile.py
   的包 G2/W3 本身就是干净构建，建议此时跳过 G0，或按 manifest 的 build_system 选择入口。
5. **finish Step 8 gen_summary 崩溃**：`'str' object has no attribute 'append'`（`scripts/ohc/summary.py:437`
   `generate_summary` 调用链），导致 finish 以 rc=1 结束并把 step8 记为失败，容易被误读为 W3 失败。
6. **conan-verify 每次都留下 `conandata.yml.ghfast-bak`**：`scripts/ohc/conan_verify.py:565` 注入镜像前写备份，
   G2 的 `finally` 只把原文写回 conandata.yml、不删除备份，要到下一次运行开头（`:69`「已清理陈旧」）才清掉。
   该文件虽被 `archives/.gitignore` 忽略，但正是 JC1 的备份残留模式，建议在 `finally` 里一并 `unlink`。

### 模板改进

1. **缺少 CLI 包的「鸿蒙特有消费者流程」骨架**：rule12 要求「工具产出参与消费者构建并运行」，但
   `templates/test_package-executable/` 只有直接运行二进制的模板，submit 生成的 PR 正文又把鸿蒙特有测试写死为 0。
   建议新增 `consumer.c.in + test.sh` 骨架：工具处理（编辑/生成/解码）一份 C 源 → profile 编译器编成
   static PIE → 运行校验，并在 x86 runner 上按 `uname -m` 选择 qemu-aarch64。
2. **conan-init 的 makefile 模板对 CLI 包生成库包骨架**：`package_type = "library"`、`cpp_info.libs = ["levee"]`、
   `get(self, **self.conan_data["sources"], ...)`（与版本键的 conandata 写法不符）。建议按 manifest 或源码里的
   `bin/`/`install` 目标判断 application，并统一生成 `self.conan_data["sources"][self.version]`。
3. **notes.md 模板占位符无门禁**：`{cmake|autotools|makefile|meson|custom}`、`{published|built|failed}` 等占位符
   没有任何检查。建议 finish Step 6 增加 `grep -nE '\{[a-z]+\|[a-z|]+\}' notes.md` 校验。
4. **commands.json 模板的 `binary` 字段语义未说明**：全仓 1974 个 `false`、1278 个 `true`，模板与 review-memory
   均未解释。建议在 `templates/commands.json.template` 注释或 ADAPTATION_GUIDE 中写明取值规则。

### 自动化补全

1. **feedback 自动采集失真 6 处（本文已手工修正）**：上游仓库填成 conandata 的归档 URL；新增知识草稿计为 5 条
   （实际 3 条）；测试统计「总计 0、通过 9」自相矛盾；「失败与问题」把 notes 表格的「问题」列当根因、「根因」列
   当解决方案（错位一列）；引擎命中情况填成「草稿目录 2097 条」；适配路径只判出路径 A。建议按表头名而不是列序
   解析 notes 表格，草稿数只统计本分支新增的 `knowledge/drafts/E*-draft-*.kv`。
2. **init-build 构建系统误判**：`scripts/ohc/init_build.py:78-86` 的 `_guess_build_system` 只看 URL，
   默认 autotools；解包后可按 `configure.sh`/`configure.inc`、`Makefile` 等文件存在性二次判定，避免 conan-init
   选错模板、G0 走 `./configure`。
3. **x86 root runner 运行 OHOS 产物的辅助脚本**：本次 test_package 需要同时处理 qemu-aarch64（非 AArch64 主机）
   与 root 下 ncurses 忽略 TERMINFO（用户命名空间 + 条目副本）。建议在 `ci/` 或 `scripts/` 提供一个可复用的
   `run-target.sh`（自动选择 native/qemu，uid 0 时可选 userns），避免每个 CLI 包各写一遍。
4. **过程事件时间线漏记 HANDOFF**：R45 的事件累积只经 submit 的 `_emit_submit_handoff` 单一咽喉写入，finish
   （G0 HANDOFF）与 feedback（待填项 HANDOFF）发出的 HANDOFF 都没有进入 `.ohc/feedback-state/` 时间线，报告里
   「HANDOFF 次数」只能靠人工回忆。建议 finish/feedback/conan-verify 的 HANDOFF 出口也调用同一个事件记录函数。

### 知识图谱覆盖

1. **E587-draft-A841（建议 promote）**：termcap 时代程序的 `LINES/COLS/UP/refresh/scroll` 等与静态 libncursesw.a
   重复定义；draft-review 最相似条目 E163 仅 0.22。建议补 `prescan_pattern`：C 文件中
   `^\s*(int|char\s*\*)[^;(]*\b(LINES|COLS|UP|BC|PC|ospeed)\b` 且源码调用 `tgetent`，预扫即可提示。
2. **E588-draft-B898（建议 promote）**：Orc configure.inc 构建期执行 config.sed/mkversio，x86 上 AC_SUB 静默失败，
   CC 驱动为 `<cc> -static-pie` 解决；最相似 E064（autotools conftest 无法运行，0.26）机制与症状均不同。建议
   `prescan_pattern` 匹配 `configure.inc` 中的 `__ac_config_sed`。本仓 discount 2.2.7 同用该机制（未实测）。
3. **E590-draft-BC71（建议 promote）**：本仓 ncurses/6.6 在 uid 0 下忽略 TERMINFO（`_nc_env_access`），root runner
   上的 terminfo 类 test_package 需用户命名空间 + root 自有条目副本；最相似 E225 仅 0.05。与已有两条 terminfo
   数据库草稿（DRAFT-E5xx-terminfo-database-bundle、DRAFT-E568-mdp-ohos-musl-terminfo-path）互补。
4. **E002 扩面建议**：E002 只讲构建期 `/tmp` 只读（设 TMPDIR 即可）；运行期源码硬编码 `"/tmp/"` 且无视 TMPDIR 的
   情形（levee、openvi 7.9.33、googletest CapturedStream 等）已有多份草稿，建议主编合并为一条「运行期临时文件
   跟随 $TMPDIR」正式条目，PSCAN-FS-001 命中时直接引用。

---

## 作者

- **姓名**: lkjing2021345
- **邮箱**: 1908499668@qq.com
- **Agent ID**: 420E
- **生成时间**: 2026-09-27 07:26:06
- **PR 编号**: —（本报告随 PR 首次提交入仓，PR 编号建立后可在 PR 页查看）
- **Git Commit**: db76dbb422
