# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_35c71377.md`

---

## 背景

- **软件名称**: semtag
- **版本**: 0.2.0
- **构建日期**: 2026-10-03
- **构建系统**: 无构建系统（单文件 Bash 脚本；自动采集写成 `custom`，实际无编译步骤）
- **上游仓库**: https://github.com/nico2sh/semtag （tag `v0.2.0`；自动采集误取成 tarball 下载地址）
- **适配路径**: 路径 B（知识库扩展）；自动采集写成「路径 A（基础适配）」，与实际不符
- **补丁数量**: 1（`patches/0001-semtag.patch`，仅 shebang 一行）
- **编译依赖**: 无 Conan 依赖（运行时 bash>=4.3 + git，均为 OS 工具）
- **最终状态**: built（本地 conan create 通过，PR 尚未创建时定稿）

---

## 情况

### 执行概要

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | `.orig`/`.work` 为硬链接，解包后立即 `cp --remove-destination` 断链再改 |
| lang-preflight | 语言预检 | 通过 | `detect_language`=other（纯 Shell），`--lang other` 如实申报，exit 0 |
| build | 编译构建 | 不适用 | 无编译；`build()` 只打补丁并校验 shebang |
| conan-verify | 配方验证 | 通过 | G1/G2/G3 通过；G2 的 `conan create` 内含 test_package，日志里 19+5 条断言全部 PASS |
| finish | 归档收尾 | 见提交记录 | W3 `conan create` 同上 |
| submit | PR提交+AI检视+CI | PR 创建前定稿 | 本报告须在建 PR 前入仓，AI 检视与 CI 结果产生于 PR 之后，不在本报告范围 |

### 失败与问题

- **上游缺陷被误读为平台差异的风险**：`semtag getcurrent` 在脏工作区静默 rc=1。根因是上游 `set -euo pipefail` 下的 `status=$(check_git_status)`，Debian bash 5.2 同样复现，故不打补丁，只让测试断言退出码与副作用（已沉淀草稿 E901-draft-A8C4）。
- **`--version` 输出 `v0.1.2`**：上游 0.2.0 tag 内嵌版本串不一致，不修改，测试用正则而非硬编码。
- **conanrun 的 PATH 不含 `/data/service/hnp/bin`**：沿用知识草稿 `DRAFT-ohos-test-package-bash-absolute-path` 的结论，`test()` 用 `sh` 调脚本、脚本内追加 PATH 并优先使用 hnp bash 绝对路径。
- **设备 hnp bash 在 HMDFS 目录可能产生 getcwd 诊断噪音**（见 `cvsgraph-1.7.0-hnp-bash-getcwd-shell-probe` 草稿）：test_package 的精确比较只取 stdout，不与 stderr 混合。

### 知识图谱使用情况

- **引用知识条目**: E037（shebang）、E002（/tmp 只读）、E165；草稿 `DRAFT-ohos-test-package-bash-absolute-path`、`cvsgraph-1.7.0-hnp-bash-getcwd-shell-probe`
- **新增知识草稿**: 1 条（`E901-draft-A8C4`；自动采集写成 4 条，是把 `knowledge/drafts` 目录里其他人的草稿数量算了进来）
- **引擎命中情况**: `engine` 对 shebang 症状命中 E037；对草稿本身 `draft-review` 判 `create`，最相近 E275（score 0.04，灰区披露：同属 errexit 误伤，但那是 `grep -v` 返回 1，本条是命令替换赋值语句）
- **测试统计**: 上游 0/0（源码包无任何测试，清点证据在 `test_package/MANIFEST.yml`）；test_package 24 断言（generic 19 + 鸿蒙特有 5）本地全通过；自动采集写成「总计 0」
- **未覆盖的错误模式**: 无新增失败模式；唯一新增知识点是 E901 草稿（上游 set -e 语义被误判为平台差异的识别与处置）

### AI 检视结果

- **检视阶段到达**: PR 创建前（未开始）
- **变更摘要评估**: 不适用（PR 创建前定稿）
- **检视意见数量**: 不适用
- **检视意见处理**: 不适用

### CI 结果

- **本地 CI 模拟 (W3)**: 以 `finish` 产出的 `.ci-result.json` 为准
- **远程 CI (PR 校验)**: PR 创建后由 `trigger-ci` 触发
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 0（`conan-verify` 一次通过）
- **重试次数**: 0
- **关键瓶颈**: 模板缺失——`init-build` 对该类项目报「conanfile.py 模板不可用（autotools）/ conandata.yml 模板不可用 / test_package 模板不可用」，且把构建系统默认成 autotools，配方、conandata、test_package、MANIFEST、软件级 commands.json/README/manifest 全部手写，参照近邻先例 `clitest` 完成
- **耗时较长的步骤**: 设计并验证 test_package（要手工在 x86 上先摸清 semtag 各子命令的真实行为：脏树、无新提交、无 Git 身份等分支）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-03T10:01:12 | lang_checked | detected=other 与任务 other 匹配 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. `lang-preflight` 对纯 Shell 项目只能靠 `--lang other` 绕过：检测器返回 `other` 且 `build_system=none`、源文件统计「无源文件可统计」。建议在 `scripts/ohc/lang_detect.py` 增加 shebang 统计（`#!/…/(ba|z|da)?sh`、`#!/usr/bin/env (ba)?sh`），判出 `bash`/`sh` 并在 `lang-preflight` 里直接放行，避免每个 Shell 包都靠人工记住 `--lang other`。
2. 终态回执被其他任务残留污染：`lang-preflight`/`conan-verify` 都打印 "R46: 终态 result.json 已上报（draft:false），跳过里程碑草稿"，原因是 `$HOME/ohpcd-ai-worker-result.json` 里留着别的任务的终态。建议 R46 草稿写入前先比对回执里的软件名/版本，不是当前任务就当作残留覆盖，而不是静默跳过。
3. rule12 在 `finish` 阶段没有任何本地提示：`finish`/`W3` 通过后才发现要手动核对 PR 正文表格里的「鸿蒙特有测试」行。建议 `finish` 的 submit 就绪预检读取 `test_package/MANIFEST.yml` 的 `harmonyos_test_count`，< 1 时直接 WARN。

### 模板改进

1. `templates/` 缺「纯脚本工具」模板：`init-build` 报 `test_package-conanfile-autotools.py` 等模板不可用后，什么也不生成。仓库里 `clitest`、`lynis` 等同形态先例已经很多，建议新增 `conanfile-shelltool.py.tmpl`（`no_copy_source`、`apply_conandata_patches`、`package_id` 去 arch/compiler/build_type、shebang 校验）+ `test_package` 的双脚本（generic + ohos）骨架 + `MANIFEST.yml` 骨架，并让 `init-build` 在构建系统判不出时不要默认写成 autotools。
2. `notes.md` 模板带 `{cmake|autotools|…}` 占位符且无门禁校验，建议 `finish` 的就绪预检对残留占位符给出 WARN。

### 自动化补全

1. `feedback` 骨架自动采集有四处失真：构建系统写成 `{BUILD_SYSTEM}`/`custom`、上游仓库误取 tarball 下载 URL、适配路径固定写「路径 A」、新增知识草稿数把 `knowledge/drafts` 里所有人的草稿都数进来（本次显示 4 条，实为 1 条；「引擎命中情况: 草稿目录 2870 条」同理），测试统计取到 0。建议草稿计数改为 `git status`/`git diff origin/main` 里本次新增的草稿文件；上游仓库取自 `manifest.yaml` 的 homepage。
2. `.work` 与 `.orig` 硬链接（E543）需要靠使用者记得断链：建议 `init-build` 解包后自动 `cp --remove-destination` 断链。

### 知识图谱覆盖

1. 新增 E901 草稿：上游 Bash 脚本 `set -e` + `x=$(fn)` 静默 rc=1，须先判定为上游行为而非平台差异；处置原则是不补丁、测试断言退出码与副作用。
2. 建议主编把 E037 的「禁止做法」与现行做法对齐：E037 的 `forbid_1` 写「硬编码 `#!/data/service/hnp/bin/perl` 换机后路径不同导致失效」，但仓库里有 21 个包的补丁、`lynis` 等配方都把 shebang 改成 `#!/data/service/hnp/bin/bash`，E037 的推荐方案（`#!/bin/bash`）与 E165（鸿蒙无 `/bin`）也彼此矛盾。需要一条明确的结论：脚本类 Conan 包的 shebang 到底用哪个路径。

---

## 作者

- **姓名**: nyaco3
- **邮箱**: aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **Agent ID**: 0D36
- **生成时间**: 2026-10-03 10:07:55
- **PR 编号**: —
- **Git Commit**: d66f94cc12
