# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_453e1a75.md`

---

## 背景

- **软件名称**: trimadap
- **版本**: 0.1-4
- **构建日期**: 2026-10-15
- **构建系统**: makefile
- **上游仓库**: https://github.com/lh3/trimadap/archive/ec5a764e1834363ae0c4b52f52bdb114ff7af265.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 2
- **编译依赖**:
- zlib/1.3.1
- **最终状态**: 成功（PR #15884，CI #92183 PASSED）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 首次因 `--project-dir` 未指向 worktree，归档被误建到技能 checkout（已清理并重跑） |
| build | 编译构建 | 成功 | 构建系统: makefile；`ksw.c` 需 SSE2→aarch64 标量回退补丁才能编译 |
| conan-verify | 配方验证 | 通过 | G1/G2/G3/G4/L2/L4/L5 全 PASS（G2 = conan create 干净构建，含 test_package 13/13） |
| finish | 归档收尾 | 完成 | W3 本地 CI `exit_code=0`（L0/L1/L2/L5=pass，L4=warn）；G0 非阻塞失败（本包无 `configure`） |
| submit | PR提交+AI检视+CI | 部分→改用 create-pr | submit 被 `packaging_present` 自检拦截（与 R19 冲突，见建议）；经用户授权改用 `gitcode_pr.py create-pr --no-preflight` 建 PR #15884。AI Review: ✅ 未发现问题 |

### 失败与问题

- **2**: 根因=标量内核必须复刻饱和算术, 解决方案=SSE2 用 `_mm_adds_epu8` 后 `_mm_subs_epu8` 两步饱和；写成单个 `clamp(h + S - shift)` 在 `h+S>255` 时结果不同
- **4**: 根因=`ksw.c` 注释里的 `KSW_ADDS_*/` 提前闭合块注释导致大量语法错误, 解决方案=C 注释中的 `*/` 序列

### 知识图谱使用情况

- **引用知识条目**: 无（无同型正式 E-entry，据 R11/R12 改为检索归档先例）
- **新增知识草稿**: 4 条（本次新增 `DRAFT-trimadap-0.1-4-ksw-sse2-scalar-fallback.kv/.md`）
- **引擎命中情况**: 草稿目录 3564 条；正式图谱无 SSE2/ksw 相关条目（`grep -i ksw knowledge/graph/index.tsv` 无命中）
- **测试统计**: 总计 0, 通过 13, 失败 0, 跳过 0（上游无测试套件；13 条为 test_package 补全断言）
- **未覆盖的错误模式**: ①SSE2-only SIMD 内核（`#include <emmintrin.h>` 为 x86 专属头、无 `__SSE2__` 守卫）在 aarch64 必编译失败；②glibc 经 `<pthread.h>` 间接暴露 `int64_t`，非 glibc libc 报 `unknown type name 'int64_t'`。二者均已写入草稿 `DRAFT-trimadap-0.1-4-ksw-sse2-scalar-fallback`，建议审核转正为正式 E-entry（L2 类别知识，含判定方法/逐步饱和修复/跨架构 oracle 验收判据）

### AI 检视结果

- **检视阶段到达**: Phase 5（完整 5 阶段：变更摘要 → 代码审查 → 无新意见 → 直入 CI 监控）
- **变更摘要评估**: 准确。摘要正确识别"`ksw.c` 仅 SSE2 且无条件 include x86 专属头"为核心难点，并如实复述了补丁策略（整块条件化 + 等价标量内核）、13 条断言与 `commands.json` 声明，无需修正
- **检视意见数量**: 1 条（`#### 代码审查 ✅ 未发现问题`）
- **检视意见处理**: 无需处理（无待回复/待解决意见，闭环校验通过）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`exit_code=0`，L0/L1/L2/L5=pass，L4=warn）
- **远程 CI (PR 校验)**: 通过（构建 #92183 / worker CI-012：`Conan test_package 通过`、`L0 门禁(结构完整性) 通过`、`L1 门禁(测试执行验证) 通过`）
- **CI 失败原因**: 首轮 #92162（worker CI-014）为 worker 侧网络故障——注入镜像 `https://gh-proxy.com/https://github.com/lh3/trimadap/...` 下载超时（诊断原文：「Worker 网络受限，无法访问外部源码仓库」），非配方缺陷；同 URL 本地 W3 可正常下载。评论 `/rebuild` 重试后一次通过

### 效率分析

- **HANDOFF 次数**: 4 处交接/拦截 —— ①`finish` Step3 G0（`./configure` 不存在，本包纯 Makefile，属非阻塞）②`finish` Step5 W3 被 JC6 拦截（**假阳性**：本地 ref 陈旧）③`submit` 自检 `packaging_present`（与 R19 冲突）④`create-pr` PF9 路径闸（**假阳性**：软件级三件套）。其中 2 处为基线/规则误报
- **重试次数**: CI 2 次（首轮 worker 网络失败 → `/rebuild` 后通过）；`conan create` 共 3 次（conan-verify G2 + finish Step4 + W3）；`create-pr` 3 次（404 目标项目无分支 → PF9 拦截 → `--no-preflight` 成功）
- **关键瓶颈**: ①**本地 git ref 陈旧**——`origin`(fork) 的 main 落后 HEAD 5602 个提交、本地 `main` 落后 1514 个提交，导致所有基于 `git diff` 的门禁（JC6 / finish Step9 W2 / `pre_pr_audit` / preflight）在 4266~41589 个无关文件上打转；preflight 逐文件 `git diff` 近 10 分钟无任何输出，实际不可完成 ②`packaging` 自检与 R19 冲突且无产出路径，`submit` 结构上无法完成 ③PF9 对 R38 规定的软件级文件误报
- **耗时较长的步骤**: preflight（陈旧基线下逐文件 diff）> W3/conan-verify 的 `conan create`（含 zlib 从源码构建）> 本地实验编译；CI 侧首轮 380s 超时 + 队列等待

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 1 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-15T01:32:07 | handoff:self_check_failed | 自检未通过: ['packaging_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit trimadap 0.1-4 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`submission.py::_check_packaging_present` 与 R19 直接冲突，建议删除或改造（本次最高优先级阻塞）**。该检查在 `manifest.status ∈ (published, built)` 时硬性要求 `packaging/` 存在至少一个 `*.tar.gz`，但 `references/iron-rules.md` R19 明确写「**`packaging/` 目录 — 不再生成**」并宣告 `package_builder.py` 废弃；实测 `package_builder.py` 已**零调用者**、`ohc-run.py` 无任何 packaging 产出命令、全仓无该产物。后果：**任何新包都无法通过 submit**（本次 4 个 Gate 全绿后卡在此处）。建议改为校验 Conan 侧证据（`.ci-result.json`/`conan-verify-report.md`），或提供显式 `--skip-packaging` 开关并登记为已知例外。
2. **PF9 路径闸对 R38 规定的软件级文件误报**。`preflight.py:570` 的 `bad = [f for f in arch if len(f.split("/")) < 5]` 会把 `archives/<字母>/<包>/commands.json`（4 段）判为"缺版本目录层——CI 将报 No packages to build"。但 R38/L0k 恰恰要求 CLI 包的 `commands.json` 位于**软件级**目录，`README.md`/`manifest.yaml` 同理。反例证据：上游 main 中已有 **4046 个**该形态 `commands.json`，且 2026-10-15 当天仍有 `sag`/`zathura`/`xsd`/`vcprompt`/`mps` 等以同形态合入（如 `808374411f` 新增 `archives/s/sag/commands.json`）——说明这些 PR 实际走的是 `--no-preflight`。建议对软件级三件套加白名单（与 `submission.py` 里 `f.count("/") <= 3` 的口径对齐）。
3. **`gitcode_pr.py monitor-review` 崩溃，5 阶段检视监控不可用**：`gitcode_pr.py:1066` 抛 `NameError: name 'unreplied_opinions' is not defined`（疑为变量重命名后漏改）。本次只能退回手工 `get-comments` 轮询，与 R42「禁止 agent 自己写 sleep 轮询」相悖。
4. **`create-pr` 的分支可见性与 `submit` 的推送目标不匹配**：`create-pr` 按"分支在目标项目"解析（`head: args.source`），而 `submit` 用 `git push origin` 推到 fork；本环境 `origin`=个人 fork、PR 目标=上游项目 → `404 Can not find the branch: feat/trimadap-0.1-4 in project: build_in_harmonyos`。建议 `create-pr` 支持 `head=owner:branch` 跨项目形态，或 `submit` 直接把分支推到目标项目（本次为手工 `git push upstream`）。
5. **worker 检出时应对齐 `main`/`origin/main`**。本次 `origin/main`（fork main）落后 HEAD **5602** 个提交、本地 `main` 落后 **1514** 个提交 / 12546 个文件，使 JC6、finish Step9(W2)、`pre_pr_audit`、preflight 全部在数千无关文件上打转（本次分别报出 191 个包 / 4266 文件 / 41589 文件）。手工把 `origin/main` 与 `main` 前进到权威 `upstream/main`（HEAD 是其祖先，`HEAD..main = 0`，无提交丢失）后，所有门禁立刻回到正确口径（15 个文件）。建议 harness 在 `worktree add` 后自动执行该对齐。

### 模板改进

1. **`conanfile-makefile.py.tmpl` 应补充"无 CPPFLAGS/LDFLAGS 钩子"的处置说明**。本包 Makefile 直接 `$(CC) $(CFLAGS) ... -lz`，既不认 `CPPFLAGS` 也不认 `LDFLAGS`，依赖的 include/lib 路径只能经 `CC`/`CFLAGS` 传入；同仓 `seqtk`、`bwa` 为同构形态，三例一致。建议写入模板注释与 `docs/ADAPTATION_GUIDE.md` §4.3（R33 段落），避免每个 Makefile 包重复试错。
2. **`templates/test-report.md` 的「可用功能清单」应区分"已由 test_package 断言覆盖"与"依赖上游、未单独验证"**。本次把 `-5 自定义接头` 与 gzip 输入标为 ✅ 但无对应断言，被 W4 审计如实记为 P3（一致性提示）。建议模板加一列"断言覆盖点"或分级标记，从模板层面消除这类不一致。

### 自动化补全

1. **W3 的镜像注入（E017 预防）应在 `finally` 中可靠还原 `conandata.yml`**：本次两轮 finish 结束后均残留 `https://gh-proxy.com/...` 行（甚至把单条 url 改写成镜像+官方的列表形态），若直接提交会被 PF7 源 URL 闸判为阻断项（我按归档内容手工改回官方单 URL）。同类问题在 v12.17 已修过一次（`.ghfast-bak`），建议覆盖 `conandata.yml` 本体可靠性。
2. **`finish` Step 8 `gen_summary` 崩溃**：`'str' object has no attribute 'append'`（两轮 finish 均出现），导致 `SUMMARY.md` 未重建（D3 索引同步失效）。建议修复或降级为不影响归档状态的告警。
3. **`preflight` 的逐文件 `_added_lines()` 在基线异常时无熔断**：5000+ 文件时每个文件起一个 `git diff` 子进程，近 10 分钟无输出也无超时保护。建议先做一次 `--name-only` 计数，超过阈值（如 50 个文件）直接报"基线异常"而不是硬跑。

### 知识图谱覆盖

1. **建议将 `DRAFT-trimadap-0.1-4-ksw-sse2-scalar-fallback` 审核转正为正式 E-entry**：这是 L2 类别知识（任何内嵌 lh3/SSW 系 SIMD 内核的项目，或更一般地"上游只保留 x86 SIMD 分支、无标量/NEON 回退"的源码都会命中），草稿内含①错误签名正则②条纹布局/lazy-F 为何不能简单删除 SIMD 的根因③**逐步饱和不可合并为单次 clamp** 的关键坑④判定命令⑤跨架构 oracle 验收判据（Homebrew 断言可复用）⑥先例互链（`archives/f/fermi-lite/0.1`）。
2. 建议把"非 glibc libc 缺 `int64_t`（`<stdint.h>` 未显式包含）"补入同类条目或独立登记——本次 `kthread.c` 命中该模式，属可复现的移植类问题。
3. `knowledge/graph/index.tsv` 当前无 `ksw`/`emmintrin` 相关条目（`grep -i` 无命中），说明该高发模式此前未沉淀；转正后可覆盖同类包。

---

## 作者

- **姓名**: Inception662
- **邮箱**: 3389004972@qq.com
- **Agent ID**: 037F
- **生成时间**: 2026-10-15 02:15:31
- **PR 编号**: 15884
- **Git Commit**: 99db1abd13
