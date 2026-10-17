# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_a3068845.md`

---

## 背景

- **软件名称**: totem-pl-parser
- **版本**: 3.26.7
- **构建日期**: 2026-10-16
- **构建系统**: meson
- **上游仓库**: https://download.gnome.org/sources/totem-pl-parser/3.26/totem-pl-parser-3.26.7.tar.xz
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
  - glib/2.84.0.1（HARD，构建期工具 glib-mkenums/glib-genmarshal 亦取自该包）
  - libxml2/2.15.3（HARD）
  - uchardet/0.0.7（HARD，可选特性 -Denable-uchardet 默认开）
- **最终状态**: 适配完成（`conan create` 全绿 + 上游测试实跑 + 消费者测试通过；PR #16249 已创建，CI/AI 闭环待 follow-up「submit --resume」——R42 口径：PR 创建 ≠ 成功）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: meson |
| conan-verify | 配方验证 | PASS | Verdict=PASS（G1/G2/G3/G4 + L2/L4/L5 全绿；G0 预扫命中 E490，场景不符未触发） |
| finish | 归档收尾 | 完成 | W2 结构 + R36 依赖 + W3 本地 CI（`.ci-result.json` exit_code=0） |
| submit | PR提交+AI检视+CI | 部分 | PR #16249 创建成功（手工 create-pr：框架 PF0 对 `ns:branch` 解析缺陷）；--no-wait 退出，AI Review/CI 未监控 |

### 失败与问题

本次流程未遇到阻塞性问题

### 知识图谱使用情况

- **引用知识条目**: E490（G0 预扫命中；该条为 autotools helper 脚本场景，本包为 meson，未触发）
- **新增知识草稿**: 无（本次 7 类问题均属平台通用陷阱，见下方「知识图谱覆盖」建议）
- **引擎命中情况**: 草稿目录 3775 条
- **测试统计**: 上游注册 3 项（实跑 1 通过 / 2 项因环境缺 MIME 数据库跳过）+ 消费者测试 1 项通过
- **未覆盖的错误模式**:
  1. 构建期 GLib 工具（glib-mkenums/glib-genmarshal）不可用——CI worker SDK lld 缺 libxml2.so.16，自建 GLib 走不通；处方=零编译 sh wrapper 转发注册表 glib 包内已构建工具
  2. 依赖 `.pc` 缺 Cflags 与 `-lc++`（uchardet 静态归档为 C++ 实现）→ meson `--no-undefined` 链接期 undefined reference
  3. OHOS libc `posix_spawn` 不做 PATH 查找 → meson/autotools 调外部工具须写绝对路径
  4. `meson install` 生成的 SONAME 别名是软链接 → 签名流程跳过软链接 → 运行期加载失败；处方=删软链接、按实体复制、逐个签名
  5. 设备无 freedesktop MIME 数据库 → GLib 类型判定退化为 text/plain → 上游 parser/podcast 假失败
  6. 沙箱无 /etc/passwd → GLib `getpwuid_r` 失败触发 GLib-FATAL-WARNING → 测试进程 SIGTRAP（易误判为签名问题）
  7. 框架侧（非编译知识）：preflight PF0 把 `namespace:branch` 当 git `rev:path` 解析 → 跨 fork 提交必然误拦；`gitcode_pr.api_request` 30s 硬编码读超时且裸 TimeoutError 逃逸（假超时被当失败），`_find_existing_pr` 用带命名空间 source 比对 `head.ref` 使复核失效

### AI 检视结果

- **检视阶段到达**: 未进入（`--no-wait` 退出，PR 创建后工具不再监控 AI Review）
- **变更摘要评估**: 未评估（同上；需 follow-up `submit --resume` 触发检视闭环）
- **检视意见数量**: 0（尚未产生）
- **检视意见处理**: 待 follow-up 闭环（R42：成功 = 检视意见闭环 + CI 绿，二者缺一不可）

### CI 结果

- **本地 CI 模拟 (W3)**: 未知
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 6（`self_check_failed` ×1、`pr_body_incomplete` ×1、`pr_creation_failed` ×4）
- **重试次数**: PR 创建 4 次失败 + 1 次放宽读超时的驱动重试；PR 正文完整性 1 次修复（均属框架/流程侧，非配方问题）
- **关键瓶颈**: PR 创建链路——token 401（旧 token 失效，改用 `GITCODE_TOKEN`）→ preflight PF0 把 `weijiapan:feat/...` 当 `rev:path` 解析误拦 → `api_request` 30s 读超时（实为假超时，PR 已在服务端建成 !16249）。合计约 20 分钟，全部耗在框架缺陷上
- **耗时较长的步骤**: `conan create`（构建 + GLib 工具 wrapper + 上游测试 + MIME 能力探测）与 PR 创建链路排查
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 11 个事件（含 6 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-16T12:58:17 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-10-16T13:02:33 | skeleton_created | result_partial |
| 2026-10-16T17:13:33 | handoff:self_check_failed | 自检未通过: ['packaging_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit totem-pl-parser 3.26.7 |
| 2026-10-16T17:16:23 | handoff:pr_body_incomplete | PR body 缺“上游仓库地址”字段（模板占位符形态）\| 依 conandata.yml 补全后重跑；同轮修复：正文按积分赛模板补「补全测试用例说明」「补充说明」章节 |
| 2026-10-16T17:17:56 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/totem-pl-parser-3.26.7 --target main --title 'feat(totem-pl-parser): 3.26.7 适配完成' |
| 2026-10-16T17:18:51 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/totem-pl-parser-3.26.7 --target main --title 'feat(totem-pl-parser): 3.26.7 适配完成' |
| 2026-10-16T17:20:33 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/totem-pl-parser-3.26.7 --target main --title 'feat(totem-pl-parser): 3.26.7 适配完成' |
| 2026-10-16T17:21:53 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/totem-pl-parser-3.26.7 --target main --title 'feat(totem-pl-parser): 3.26.7 适配完成' |
| 2026-10-16T17:29:40 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-10-16T17:29:41 | skeleton_exists | resume_pr_exists |
| 2026-10-16T17:29:41 | loop_pending | no-wait 退出，CI/AI 闭环未启动；follow-up: submit --resume (PR #16249) |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **preflight PF0 必须归一化 `namespace:branch`**（跨 fork 提交的硬阻断）：现状把 `weijiapan:feat/xxx` 整串交给 `git diff main...<head>`，git 按 `rev:path` 语法解析 → 必然误报 PF0 环境闸，逼出 `--no-preflight`（自担风险逃离全部 PF 闸）。建议：head 若含 `:` 前缀则剥离后用于本地 git 校验；本次以「手工运行 `run_preflight(repo, 'main', 'feat/totem-pl-parser-3.26.7')` 全绿」等价兜底，但该兜底不应是常态。
2. **`api_request` 读超时应可配且捕获裸 `TimeoutError`**：现状硬编码 `timeout=30`，且 `except` 只兜 `HTTPError/URLError` → 裸 `TimeoutError` 直接 traceback 逃逸，`cmd_create_pr` 的"假超时 15s 后 list 复核"分支（本就为 GitCode 偶发超时设计）根本没机会执行。本次 PR 实际建成却报失败，属该缺陷直接产物。建议：默认抬到 60-120s，并把 `TimeoutError/socket.timeout` 一并纳入假超时复核分支。
3. **`_find_existing_pr` 比对口径修正**：复核用 `pr["head"]["ref"] == source`，而 `source` 带命名空间（`weijiapan:feat/...`）、API 返回的 `head.ref` 不带 → 永远不相等，复核 100% 失效（本次 409 已明示 `!16249` 存在，复核仍判"创建失败"）。建议比对前剥离命名空间前缀。
4. **`submit` 应支持跨 fork 的 source 命名空间**（或自动识别分支归属 fork）：现状 submit 传裸分支名被平台拒、手工 create-pr 又绕过 submit，导致 `.submit-state.json` 不落盘、`--resume` 报 `resume_no_state`，需人工补状态文件才能续环。建议 submit 增加 `--source-namespace` 并在创建成功后无条件回写 `pr_number/pr_url/branch_name/commit_hash`。
5. `_writeback_submit_state` 只更新「已存在」的仓库根 `.submit-state.json`，而 `submission.py` 读写的是**版本目录**下的同名字文件——两处路径不一致，手工路径下回写形同虚设，建议统一为版本目录。

### 模板改进

1. **积分赛事PR模板「补全测试用例说明」语义待补**：二选一复选框在「上游已有测试 + 按 R34/L0c 另加消费者测试」场景下无落点（勾"是"与事实矛盾，勾"否"又没处写消费者用例）。建议在模板中补一行固定说明位（如「另增鸿蒙特有测试」小节），本次系手工补写。
2. **`conanfile-meson.py.tmpl` 建议内置三类共性后处理**（本次全部手写，且均为 GLib 系/OHOS 通用）：①GLib 工具零编译 wrapper（转发注册表 glib 包内 glib-mkenums/glib-genmarshal）；②native 文件写工具绝对路径（posix_spawn 无 PATH 查找）；③SONAME 别名的软链接→实体复制 + 逐个签名。已在建议中列为知识条目候选，模板内置可一次性消掉绝大多数 meson 适配的重复劳动。
3. **`test_package` 模板应默认带 `VirtualRunEnv`**：初版消费者用例因缺 `conanrun` 环境导致二进制加载失败（找不到 Conan 依赖链内的 .so），属模板默认值缺失而非个案。
4. `manifest.yaml` / `notes.md` 模板建议显式给出 R51 上游测试台账字段（注册数/实跑数/跳过原因），本次为手工补，避免"漏写即审计 P1"。

### 自动化补全

1. **打包步骤接线**：`scripts/ohc/package_builder.py`（`PackageBuilder`）未接入 CLI/finish，而 `packaging_present` 自检与 CI 均要求 `packaging/<name>-<version>-ohos-aarch64.tar.gz` → 本次需人工用 `conan cache path` 取包目录再手工调用 `package_cli` 才过闸。建议 finish step [10/10] 直接调用，或在 submit 前置自检里给出可执行的补生成命令。
2. **PR 创建后无条件回写状态文件**（版本目录），使 `submit --resume` 在手工 create-pr 路径下也能续环；否则跨 fork 场景永远是"手工建 PR + 人工补 `.submit-state.json`"。
3. **CI 触发自动化**：CI 是评论触发型（`/rebuild`），`--no-wait` 退出后无人评论则 CI 永不启动；`loop_pending` 草稿已带 follow-up 命令（好），建议平台侧按 `draft:true + milestone=loop_pending` 自动派发 `submit --resume`。
4. **`api_request` 的重试与超时可配**（见设计改进 #2），并把 GitCode 的 409「同源分支已有 MR」直接归一化为"PR 已存在"成功态，而非失败回执——本次正是该 409 暴露了前一次"假超时"其实成功。

### 知识图谱覆盖

本次遇到的 6 类编译/测试问题均为平台通用陷阱（非本包专属），建议补为知识条目或并入既有条目：

1. **GLib 工具链在 OHOS 构建环境的零编译 wrapper 方案**（glib-mkenums / glib-genmarshal / glib-compile-schemas 等）：CI worker 的 SDK lld 缺 `libxml2.so.16` → 自建 GLib 走不通；处方=生成 sh wrapper 转发注册表 glib 包内已构建工具，并把 wrapper 目录并入 build 环境 PATH。适用范围覆盖所有 GLib 系下游（gnome-desktop、grilo、tracker 等本批后续包）。
2. **OHOS 下外部工具必须绝对路径**（libc `posix_spawn` 不做 PATH 查找）——meson native 文件 / autotools 均适用，建议与既有同类条目互链。
3. **SONAME 别名软链接导致签名遗漏**：`meson install`/libtool 产生的 `.so.N`、`.so` 别名是软链接，签名流程按 `islink` 跳过 → 运行期加载失败；处方=删软链接 + 实体复制 + 逐个签名。跨 meson/libtool 通用。
4. **测试期 `getpwuid` LD_PRELOAD shim**：沙箱无 `/etc/passwd` → GLib `getpwuid_r` 失败 → GLib-FATAL-WARNING → 测试进程 SIGTRAP。cracklib2 已有先例，建议升格为通用条目并与本次互链（避免下次再被误判成"签名问题"排查半天）。
5. **依赖 `.pc` 最小改写处方**：下游包 `.pc` 缺 `Cflags` include 路径、C++ 实现却只在 `Libs.private` 写 `-lstdc++` → meson `--no-undefined` 链接失败；处方=`generate()` 内改写为 `Cflags` + `-lc++`（不改依赖包本体）。
6. **环境能力差导致的"上游测试假失败"判定法**：先判环境缺件（如 freedesktop MIME 数据库）再判包缺陷，配方按能力选择注册/跳过测试并在 PR 中如实申报（R51 台账），不要改上游测试源码迁就环境。

框架缺陷（preflight 命名空间解析、`api_request` 超时/复核、submit 跨 fork）不属编译知识，建议进 SKILL backlog（已在「SKILL 设计改进」列明），不立 E-entry。

---

## 作者

- **姓名**: weijiapan
- **邮箱**: weijiapan@noreply.gitcode.com
- **Agent ID**: 105C
- **生成时间**: 2026-10-16 13:02:33
- **PR 编号**: #16249（https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/16249，title「【积分赛】feat(totem-pl-parser): 3.26.7 适配完成」）
- **Git Commit**: 4226965ced（本地 HEAD；base = e3aaad7dbb main）
