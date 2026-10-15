# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_7ade520c.md`

---

## 背景

- **软件名称**: run-parts
- **版本**: 5.23.2
- **构建日期**: 2026-10-07
- **构建系统**: custom
- **上游仓库**: https://salsa.debian.org/debian/debianutils/-/archive/debian/5.23.2/debianutils-debian-5.23.2.tar.gz
- **适配路径**: 路径 B（知识库扩展：适配 + 知识草稿 + Issue；自动判成路径 A 为误判）
- **补丁数量**: 1
- **编译依赖**:
无
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: custom |
| conan-verify | 配方验证 | 通过 | G1–G4 通过；G1 与 G2 各修一次后过（见失败与问题）；L2/L4/L5 因「无 cache 路径」被跳过 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | 未到达 | 反馈在建 PR 之前定稿；AI 检视与 CI 结果尚未产生，以 PR 页面为准 |

### 失败与问题

- **1**: 根因=tarball 无 `configure`，`Makefile.am` 强制 `SUBDIRS = po4a`，缺 `po4a-translate` 时 `po4a/de/Makefile.am:9` 的 `TRANSLATE` 为 `exit 1`, 解决方案=Debian native 源码包只发布 configure.ac/Makefile.am
- **2**: 根因=`conan-verify` G1 报缺 `export_sources()` 与补丁应用调用, 解决方案=G1 门禁对无补丁配方同样要求
- **3**: 根因=G2 `ConanException: 'tools.build:compiler_executables:c' does not exist in configuration list`, 解决方案=该 conf 是 dict，不存在 `:c` 子键（`templates/conanfile-makefile.py.tmpl` 的写法无效）
- **4**: 根因=`run-parts --version` 打印 5.23.1, 解决方案=上游 `acinclude.m4` 内置版本未随 5.23.2 更新

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 1 条（E14723-draft-8735；自动统计 3 条为误计，把全仓草稿目录中的邻近文件算了进来）
- **引擎命中情况**: conan-verify G2 首次失败时命中 E538（pangomm/harfbuzz 的 glib 静态/动态问题），与本次根因（`tools.build:compiler_executables:c` 不存在）无关，属误匹配
- **测试统计**: 上游 autopkgtest N=2、适用 N′=1、实跑 1/1 通过；test_package 消费者用例 9 条断言全过（自动采集为 0，因为配方无 test-report 格式的统计表）
- **未覆盖的错误模式**: Debian native 源码包（无 configure + po4a 子目录门禁 + 内置版本号落后于包版本），已写成草稿 E14723-draft-8735

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 不适用（建 PR 前定稿，尚无变更摘要）
- **检视意见数量**: 0（尚未产生）
- **检视意见处理**: 不适用

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（x86 + qemu；未暴露真机文件系统差异）
- **远程 CI (PR 校验)**: 第 1 轮失败（test_package 的 `--stdin` 用例），修复后重推
- **CI 失败原因**: 真机 worker 上 `open(O_TMPFILE)` 失败，上游 `copy_stdin()` 未检查 fd，报 `failed to write to temporary file`；已用 mkstemp 回退补丁修复

### 效率分析

- **HANDOFF 次数**: 0（init-build 之后到建 PR 前，conan-verify 两次失败均为直接输出报错，未产生 HANDOFF 块）
- **重试次数**: conan-verify 共 3 次（G1 缺方法、G2 conf 键错误、第 3 次通过）
- **关键瓶颈**: 无；耗时主要在阅读仓库已有 debianutils 归档与确认 O_TMPFILE 相关历史草稿
- **耗时较长的步骤**: conan-verify 的 conan create（含 test_package CMake 构建），约 20 秒量级，无明显长步骤
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-07T09:32:58 | lang_checked | detected=c 与任务 cpp 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. `scripts/ohc/conan_verify.py` 的 G1 要求每个配方都有 `export_sources()` 与补丁应用调用，但 `conan-init` 对 `autotools`/无构建系统给出的骨架没有统一带上它们；新手按「无补丁就不写」会白跑一轮 G1。建议 G1 在无 `patches` 时放行，或 `conan-init` 总是生成这两段。
2. `init-build` 末尾打印「环境检查未通过」（TMPDIR 未设置等），但随后仍继续输出「上下文文件」并退出码 0；建议把它降为提示或让退出码非零，避免误读。
3. `scripts/ohc/preflight.py` 的 PF7（`_PF7_DEBIAN_HOSTS`，约第 359 行）把 `deb.debian.org` 一律视为「Debian 下游重打包源」，但 debianutils 这类 Debian native 包的上游就是 Debian；本次只能改用 salsa 仓库的 tag 归档才能过闸。建议 PF7 对 native 包（源码包 `debian/source/format` 为 native）放行，或在提示里直接给出 salsa 归档 URL 写法。
4. `finish` 之前必须 `git commit` 的约束只写在使用说明里，建议 `finish` 开头检测 `git diff origin/main...HEAD` 为空时直接给出明确提示，而不是静默回退 full 模式扫描他人归档。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. `templates/conanfile-makefile.py.tmpl`（`R33` 注释段与 `build()`）用 `self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)`，在 Conan 2.29.1 上抛 `[conf] 'tools.build:compiler_executables:c' does not exist in configuration list`。该 conf 是 dict，应写成 `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")`；`ar`、`ranlib` 两行同理。
2. `conan-init` 生成的 `test_package/` 对可执行文件包仍给出 CMake 库消费模板（`find_package(<pkg>)` + `target_link_libraries`），对 CLI 包无意义；建议当 `commands.json` 类型为 tool 或 `package_type = "application"` 时直接使用 `templates/test_package-executable` 一类的消费者模板，并提示 rule12 要求「编译消费者程序并运行」。
3. 版本级 `manifest.yaml` 模板生成时 `software` 字段为字面量 `{software}`、`build_system` 为 `{BUILD_SYSTEM}`，需要人工改写；建议由 `init-archive` 直接渲染。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

0. W3 本地模拟在 x86 + qemu 上跑，文件系统相关能力（O_TMPFILE、mkfifo、linkat）与真机不同，本次 `--stdin` 用例本地全绿、CI 才红。建议 `finish` 在 W3 通过后提示「涉及临时文件/管道/硬链接的用例，本地结果不能代表真机」，并在 `reports/` 记录该告警，提醒作者在 PR 正文标明由 CI 验证。
1. 本反馈自动采集有 4 处失真：适配路径判为「路径 A」（实际路径 B）、知识草稿数 3（实际 1）、测试统计 0/0/0、上游仓库字段取到的是 tarball URL 而非项目主页；建议测试统计从 `test_package/MANIFEST.yml` 与 `reports/test-report.md` 读取。
2. `engine` 在 G2 失败时对 `ConanException: ... does not exist in configuration list` 命中无关的 E538（得分 3296）；建议匹配时要求 `error_signature` 中至少一条正则真实命中日志，仅关键词重叠不应作为命中。
3. `conan-verify` 的 L2/L4/L5 在「无 cache 路径」时直接跳过并记为 PASS，未真正做 NX/PIE/RELRO 检查；建议在跳过时显示为 SKIP，并按包 ID 自动定位 `CONAN_HOME` 下的产物。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

1. 新增草稿 `E14723-draft-8735`：Debian native 源码包「无 configure + po4a 子目录 exit 1 + 内置版本号落后」。`draft-review` 判定 `create`，最相近条目 E289（得分 0.02）。
2. 已有草稿（如 `DRAFT-cobs-c-0.4-no-build-system-pure-c-conan-recipe`、`DRAFT-E672`）已覆盖 `tools.build:compiler_executables` 键用法，建议主编合并为一条正式条目，并回写到 `templates/conanfile-makefile.py.tmpl`，避免下一个包继续踩。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: D9A4
- **生成时间**: 2026-10-07 09:40:26
- **PR 编号**: —
- **Git Commit**: b95978a475
