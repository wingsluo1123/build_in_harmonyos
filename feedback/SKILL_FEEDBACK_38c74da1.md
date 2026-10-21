# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_38c74da1.md`

---

## 背景

- **软件名称**: ifmail
- **版本**: 2.14tx8.10
- **构建日期**: 2026-10-16
- **构建系统**: makefile（顶层 Makefile + include CONFIG；上游无 configure/cmake/meson）
- **上游仓库**: https://deb.debian.org/debian/pool/main/i/ifmail/ifmail_2.14tx8.10.orig.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 15
- **编译依赖**:
- gdbm/1.23
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: makefile（顶层 Makefile + include CONFIG；上游无 configure/cmake/meson） |
| conan-verify | 配方验证 | 通过 | `--profile ohos-local`：G1/G2/G3/G4 + L2/L4/L5 全 PASS（reports/conan-verify-report.md）；finish Step 4 用硬编码 ci/conan/profiles/ohos-aarch64 在开发机必然失败（见下） |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | PR #16259 已创建 | 分支已 push；AI 检视：atomgit-bot 已出「变更摘要」，但代码审查被跳过（机器人判定「均为数据/生成/二进制文件」），已评论 `/ai review force` 重跑；远程 CI：已评论 `/rebuild`（note_id 194244912）触发，**结果尚未回流，不得记为通过** |

### 失败与问题

本次共 4 次 HANDOFF（见下方时间线）+ 远程 CI 三轮失败，其中绝大多数由框架侧缺陷或环境假设引起：

0. **（最高影响，当前阻塞所有 PR）`ci/conan/build_and_test.sh` 的 G0b/G0d 只认三位数条目号**：
   两处模式写死 `E[0-9][0-9][0-9]`，而知识库已跨过 E999。CI #96134 实测：
   `G0b: knowledge/graph/ 下有 36 个非标准命名的 .kv 文件`（就是 `E1000.kv`…`E1035.kv`）、
   `G0d: index.tsv 行数(1035) vs .kv 文件数(999) 不匹配` ⇒ `G0 fail` ⇒
   `L0/L1/L2/L4/L5` 全部 `skip: blocked_by_G0`，构建在编译前就终止。
   按 CI 原式与修正式对同一基线 `c3e27421` 复算：现行正则 999 vs 1035（MISMATCH，36 个非标准）；
   放宽为 `E[0-9]{3,4}` 后 1035 vs 1035（MATCH，0 个非标准）。当前 main tip `d11b9806`
   用修正正则同样是 1999 vs 1999 MATCH。**修法**：G0b 的 `grep -vE` 与 G0d 的 `ls` glob
   同步放宽（`E[0-9][0-9][0-9]*`／`E[0-9]\{3,\}`）。本 PR 未触碰 `knowledge/graph/`
   与 `index.tsv`（协作者禁止项），`ci/` 属只读基础设施 ⇒ 只能单独开框架 PR 修。
0b. **CI 失败诊断把"空 diff"误判成"网络问题"**：#96094/#96105 的真实原因是
   `pull/16259.diff` 返回 HTTP 200 + **0 字节**（PR head 被解析成官方仓的同名占位分支），
   CI 脚本自己的 `[ERROR] ... diff 下载为空文件——GitCode 可能返回了错误页` 才是实情，
   但机器人诊断输出的是「类别: 网络问题 / 源码下载超时 / Worker 网络受限」。
   建议 `classify_failure_log` 优先匹配脚本自己打出的 `[ERROR] PR ... diff 下载为空文件`
   与 `diff 无法应用`，把它们与真正的下载超时分开——否则适配者会去查网络/换源，
   而真实问题是 PR 的 head 分支指向错了仓库。
0c. **`create-pr` 的 `--source <branch>` 在同名分支同时存在于 fork 与官方仓时会解析到官方仓**：
   平台为本任务在官方仓预建了空的 `feat/ifmail-2.14tx8.10`（tip=当时的 main），
   `gitcode_pr.py create-pr --source feat/ifmail-2.14tx8.10` 建出的 PR head 是
   `OpenHarmonyPCDeveloper/build_in_harmonyos@b544378a`（零提交），而不是
   `songzhenyan/build_in_harmonyos@<我的提交>` ⇒ diff 恒空、CI 必红，且从 PR 页面看不出来。
   建议：① create-pr 后回读 `head.repo.full_name` + `head.sha` 并与本地 `git rev-parse HEAD`
   比对，不一致就报错而不是继续；② 支持 `--source <owner>:<branch>` 显式跨仓；
   ③ 若官方仓已存在同名空分支，提示"应推送到官方仓该分支或改用带 owner 前缀的 head"。
   本次靠 `git push --dry-run` 确认官方仓任务分支可写（fast-forward）后推送解决。

1. **`scripts/gitcode_pr.py:1066` NameError（阻塞级框架 bug）**：`cmd_monitor_review` 引用未定义变量
   `unreplied_opinions`（提示 "Did you mean: 'review_opinions'?"），导致 `monitor-review` **每次调用必崩**。
   连带后果：`submit` 的 AI Review 监控 Phase 1 只能反复打印「获取检视状态失败，重试...」，
   5 个阶段一个都推进不了，30 分钟超时后必然 HANDOFF。本次只能 kill 掉轮询、
   改用 `get-comments` / `api_request` 手工驱动。`scripts/` 属只读基础设施，未在本 PR 修改。
2. **`refresh-patch --auto` 生成的补丁 hunk 头行号偏 1**：`iflib/parsedate.y` 生成
   `@@ -659,22 +665,26 @@`，而首个上下文行实际在第 658 行；conan 的 patch-ng 直接判
   `hunk no.2 doesn't match source file at line 659` / `source file is different`，G2 失败。
   GNU `patch -p1` 能靠偏移搜索容忍，patch-ng 不能 ⇒ 只有 conan 路径会暴露。
   改用 `diff -u --label a/<f> --label b/<f>` 重生成 15 个补丁后全部通过。
3. **`refresh_patch.py` 的排除清单把手写 `Makefile` 当构建产物**（第 24 行 `"Makefile", "config.h", "libtool", ...`）：
   对 Makefile 驱动型项目会**静默丢掉 Makefile 改动**（本例补丁 0015 只能手工生成）。
   更麻烦的是 `finish` Step 1 每次都重跑该生成器，会把手工修正覆盖回错误版本；
   本次靠"移走 `.orig`/`.work` 临时树 → 生成器判无差异 → 保留现有补丁"规避。
4. **`templates/conanfile-makefile.py.tmpl` 的 conf 读法在 conan 2.29.1 上抛异常**：
   `self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)` →
   `ConanException: [conf] 'tools.build:compiler_executables:c' does not exist in configuration list`。
   正确写法是取整个 dict 再取键（`run-parts/5.23.2`、`rvvm/0.6`、`ren/1.0` 已是该形态）。
5. **开发机上的环境假设**（非阻塞但会误导）：`clean_verify.py:68` 与 finish Step 3 硬编码
   `/data/service/hnp/bin/bash`（可用 `CONFIG_SHELL` 覆盖，已覆盖）；G0 假设存在 `configure`
   （本包无 configure，报 `exit 127`）；finish Step 4 硬编码 `ci/conan/profiles/ohos-aarch64`
   （其 compiler 路径只在 worker 存在，`CONAN_PROFILE` 不被 Step 4 读取）；
   Step 10 的 submit 就绪清单仍要求 v3.0 已废弃的 `packaging/` 与 `.staging-verified`。
6. **JC/PF9 的 diff 基线取 `origin/main`**：协作者 fork 的 main 落后官方 main 377 个提交时，
   JC6 误报「本 PR 涉及 185 个软件包」、PF9 连带扫到 3456 个"配方变更"、
   JC1/JC5 还会把别人历史提交里的 `archives/k/kcachegrind/26.04.0/.staging-verified` 算到本 PR 头上。
   本次用 CI 同款的 `JUNK_PR_DIFF=<pr.diff>` 基线绕开；PF9 无同类逃生口（只有全局 `--no-preflight`）。
7. **PF9 对 ARCHIVE-SPEC v3.0 强制的软件级文件误报**：`len(path.split('/')) < 5` 会命中
   `archives/<l>/<pkg>/{README.md,commands.json,manifest.yaml}`。证据：已合入 main 的
   `6a5d628041`（rdate）与 `8f570e151f`（sortmerna）含完全相同的 4 段路径。
9. **真机 CI 第 4 轮的唯一硬失败是 HMDFS 无硬链接**（`ifgate/Makefile:92` 的 `ln ifmail ifnews`
   → `Operation not permitted` → `make all` Error 2 → `conan create` 在 build() 失败）。
   这类问题**本地与交叉构建都不可能发现**（macOS/APFS 支持硬链接），只能靠真机暴露；
   已按 E079 推荐方案加补丁 0016（两处 `ln` 改 `cp`）。同一轮日志也证明前 15 个补丁在真机全部生效
   （133 个 .c 零编译错误、`ifmail` 成功静态链接 `libgdbm_compat`+`libgdbm`）。
8. **Python CA 证书**：仓库工具用的 python3（python.org 3.10.11 构建）默认 verify 路径不可用，
   所有 gitcode API 调用报 `CERTIFICATE_VERIFY_FAILED`；须显式 `SSL_CERT_FILE=/etc/ssl/cert.pem`。
   `init-build` 的环境检查也试图往 `/storage/...` 装 CA 证书并失败（只读文件系统）。

### 知识图谱使用情况

- **引用知识条目**: E516（OHOS libc 无 `_res`/`__res_state` 对象——补丁 0002 的直接依据，本次独立定位后查重命中）、E525（force-j1：HMDFS 上 GNU make jobserver FIFO 不可用）、E011/E114（HMDFS 临时目录家族——三个测试脚本的工作目录一律不用 `/tmp`，改由参数传入）、E063（add-cflags-disable-werror——本次**明确排除**该修法：varargs/va_dcl 是硬错误而非警告升级）、E119（同一 TU 双头类型重定义的相似条目，作为草稿 1 的 `similar_to`）、E543（flex/bison 走 `tool_requires` 的既有约定）
- **新增知识草稿**: 2 对（4 个文件，`.kv`+`.md` 成对）——`DRAFT-ifmail-2.14tx8.10-gdbm-compat-ndbm-no-include-guard`、`DRAFT-ifmail-2.14tx8.10-kr-varargs-clang-error-stub-stdarg`；两份都做过与 ifmail 无关的最小复现，`draft-review` 质量预检 signature/root_cause/rec 全 ✅、相似度 TOP1 仅 0.20/0.23、判定 create。（骨架里的「6 条」是按文件数误计）
- **引擎命中情况**: 草稿目录 3777 条
- **测试统计**: 总计 62, 通过 60, 失败 0, 跳过 2
- **未覆盖的错误模式**: ① gdbm compat `<ndbm.h>` 无 include guard + 制品仓 gdbm/1.23 与 1.24 的 `--enable/--disable-libgdbm-compat` 开关相反（已成稿）；② clang `<varargs.h>` 为 `#error` 桩、K&R `va_dcl`/单参 `va_start` 必须转 C99 stdarg（已成稿）；③ musl 无 BSD `re_comp`/`re_exec`（修法即标准 POSIX 替换，常识级，未成稿）；④ flex 生成的 `extern int yywrap ( void );` 与项目内 `#define yywrap() 1` 相撞 → `YY_SKIP_YYWRAP`（有跨软件价值，本次未成稿，留候选）；⑤ `readconfig()` 式 `freopen(debugfile,"a",stderr)` 导致测试取证位置改变（单包行为，不申报）

### AI 检视结果

- **检视阶段到达**: Phase 1 的产物（变更摘要）已由 atomgit-bot 生成；Phase 2-5 因
  `gitcode_pr.py:1066` 的 NameError 无法通过工具推进，改由人工读评论驱动
- **变更摘要评估**: 摘要内容准确（正确识别 15 个自研补丁、Debian pool `.orig` 源与 sha256 核验、
  E516 对应关系、K&R→C99 变参转换、上游 `-DTESTING` 自测首次可链接可执行、62 项检查、
  `package_folder` 烤路径、`USE_NLS=no`、2 对知识草稿），无需更正
- **检视意见数量**: 代码审查 0 条——机器人判定「本次改动均为数据 / 生成 / 二进制文件（如测试用例、
  锁文件、媒体资源），没有可审查的代码逻辑，已跳过 AI 代码审查」（comment_id 194222517）。
  该分类对本 PR 不成立：变更含 `conanfile.py`（Python 配方）、15 个 `.patch`（源码 diff）、
  3 个 shell 测试驱动。已评论 `/ai review force` 重跑，机器人仍返回同一条「已跳过 AI 代码审查」
  ⇒ 建议跳过判定不要只看扩展名/文件类型：`.patch` 是源码 diff、`conanfile.py` 是 Python 配方，
  两者都该进入代码审查；否则 rule6（AI 检视 P0/P1 清零）在这类 PR 上永远是「空过」
- **检视意见处理**: 暂无 P0/P1 待处理项；`/ai review force` 的结果回流后逐条 `handle-review-opinion`

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（finish Step 5 阻塞门禁；`CONAN_PROFILE=ohos-local` +
  `JUNK_PR_DIFF` 的 CI 同款 prdiff 基线；`.ci-result.json` 由其写入 `exit_code=0` + log_sha256，未手工编辑）
- **远程 CI (PR 校验)**: **未通过，且三轮均未进入编译阶段**（骨架自动填的「通过」不成立，已更正）：
  #96094(CI-034)、#96105(CI-033) 卡在 `checkout-pr`——PR head 被解析成官方仓的空占位分支，
  `pull/16259.diff` 为 0 字节；把提交推到官方仓任务分支后 diff 恢复 188327 B / 39 文件，
  #96134(CI-027) 正确识别出变更包 `archives/i/ifmail/2.14tx8.10`，但卡在 **G0 知识图谱完整性**
  （见「失败与问题」第 0 条，属 CI 门禁正则缺陷 + main 侧状态，与本 PR 无关）
- **CI 失败原因**: G0b/G0d 的 `E[0-9][0-9][0-9]` 三位正则遇上 E1000+ 条目 ⇒
  `L0/L1/L2/L4/L5` 全部 `skip: blocked_by_G0`。按 §12.1 三轮止损，不再重跑；
  待框架侧放宽正则后 `/rebuild` 即可进入真实编译与真机测试
- **待真机定论的断言**: 本地已知 2 项在参考环境不可判定（`ifroute -h`、OHOS-1b 的
  `index.pag` 布局），以及 30 项上游自测 + 32 项 test_package 的真机执行结果

### 效率分析

- **HANDOFF 次数**: 4（w4_audit_not_done、self_check_failed、pr_creation_failed、
  finish 的 w3_local_ci_failed）
- **重试次数**: conan-verify 4 轮（补丁 hunk 行号 → conf 读法 → can_run 判据 → 规范修正后复跑）；
  finish 3 轮（JC 基线 → G0 shell/profile → 通过）；submit 2 轮（自检产物 → TLS/CA）
- **关键瓶颈**: ①「工具生成的补丁不可用」——refresh-patch 的 hunk 行号偏移 + Makefile 排除 +
  finish 每次覆盖，导致同一批补丁反复重做；② AI Review 监控因 NameError 完全不可用，
  只能人工读评论；③ 开发机与 worker 的环境假设不一致（shell 路径、profile、CA 证书、diff 基线）
- **耗时较长的步骤**: 上游 133 个 .c 的交叉编译（-j1，约 3-4 分钟/轮 × 多轮）；
  参考构建（macOS 原生重编一遍以采集确定期望值）约 2 分钟；
  真机不可执行导致的"参考构建 + 逐条对照"取证方式，比直接跑真机多花约一倍时间
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 5 个事件（含 3 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-16T18:41:30 | handoff:w4_audit_not_done | W4 Pre-PR 审计未执行，请先完成审计 \| python3 scripts/pre_pr_audit.py generate --repo-dir /Users/metyierzhen/Desktop/build_in_harmonyos/.worktrees/ifmail --package ifmail --version 2.14tx8.10 \| 审计子任务完成后将结果保存为 reports/audit-result.json |
| 2026-10-16T19:00:56 | handoff:self_check_failed | 自检未通过: ['packaging_present', 'test_report_present'] \| 修复后重新 submit \| python3 scripts/ohc-run.py submit ifmail 2.14tx8.10 |
| 2026-10-16T19:08:14 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/ifmail-2.14tx8.10 --target main --title 'feat(ifmail): 2.14tx8.10 适配完成' |
| 2026-10-16T19:17:29 | skeleton_created | pr_created |
| 2026-10-16T19:17:29 | pr_created | PR #16259 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/16259 |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. **`gitcode_pr.py:1066` 的 `unreplied_opinions` NameError 必须先修**：它让 `submit` 的
   AI Review 五阶段监控整体失效（每次调用必崩 → Phase 1 空转 30 分钟 → HANDOFF）。
   建议同时给 `_call_monitor_review` 加"连续 N 次异常即区分『网络/认证失败』与『脚本崩溃』"，
   脚本崩溃应立刻 HANDOFF 并打印 stderr，而不是当作"状态未就绪"静默重试。
2. **JC/PF9 的 diff 基线不应硬绑 `origin/main`**：协作者 fork 的 main 落后官方 main 时，
   会把别人的历史提交算进本 PR（本次 JC6 误报 185 个软件包、JC1/JC5 命中他人遗留的
   `.staging-verified`）。建议基线优先级改为 `JUNK_PR_DIFF` > `upstream/main`∪`ohpcd/main`
   的 merge-base > `origin/main`，并在报告里打印实际使用的基线 commit。
3. **PF9 需要软件级文件白名单**：`archives/<l>/<pkg>/{README.md,commands.json,manifest.yaml}`
   是 ARCHIVE-SPEC v3.0 §2.1 的强制项，却被"路径段数 < 5"判为缺版本目录层。
   建议按文件名白名单放行，或改成"PR 内**完全没有**版本级文件才报错"（那才是
   "No packages to build" 的真实成因）。
4. **`finish` Step 1 无条件重跑补丁生成器，会覆盖手工修正**：建议加"生成器产出的补丁若与
   现有补丁不同，先备份并要求确认"，或支持 `_SKIP_PATCH_GENERATION=true` 同时作用于 Step 1
   （目前只作用于 Step 2 的 close_archive）。
5. **Step 10 的就绪清单与 ARCHIVE-SPEC v3.0 脱节**：仍要求已废弃的 `packaging/*.tar.gz`、
   `.staging-verified`（且 `submit` 自检把它们当硬失败）。建议按 spec v3.0 改为
   `conanfile.py + conandata.yml + manifest.yaml + notes.md + test_package/`，
   `reports/test-report.md` 保留为可选。
6. **Step 4 应尊重 `CONAN_PROFILE`**：目前 `ConanVerifier` 在 finish 里被硬编码成
   `ohos-aarch64`，开发机上必然失败且不阻塞，容易让人误以为"配方有问题"。
7. **`finalize_archive.py:146` 的补丁计数通配只认 `000*.patch`**：`len(list((ver_dir/"patches").glob("000*.patch")))`
   只能匹配 0001-0009，任何补丁数 ≥10 的包都会被误报
   `⚠️ 补丁数不一致: manifest=16 vs disk=9`（本包实测：磁盘 16 个、conandata 16 条、manifest 16 条）。
   建议改成 `[0-9][0-9][0-9][0-9]-*.patch`，并把 manifest 侧的计数换成真正的 YAML 解析
   （现在按逗号切分字符串，条目描述里含逗号时会数错）。
8. **`ci/conan/build_and_test.sh` 的 G0b/G0d 三位条目号正则**（见「失败与问题」第 0 条）已在
   `#96134` 上实证会阻塞所有 PR；本包第 4 轮真机构建放行后才暴露出真正的平台问题
   （HMDFS 无硬链接，E079），说明 G0 挡在编译之前会让"平台真问题"晚一整轮才浮现。
   建议把 G0 的知识图谱完整性检查降级为 warn（或只对改动 `knowledge/graph/` 的 PR 生效），
   让配方 PR 至少能跑到 L1。
9. **CI 失败诊断的分类需要补 HMDFS 硬链接特征**：第 4 轮 `ln: cannot create hard link ...
   Operation not permitted` 被归为「类别: 未知 / 未能自动识别失败原因」，
   而知识库里 E079 的 error_signature 恰好就是这条正则。建议 `classify_failure_log`
   直接接知识图谱引擎做匹配（本例可自动给出 E079 + `ln`→`cp` 的推荐方案），
   而不是留给适配者自己翻日志。
7. **agent_id 不稳定**：`get_agent_id('.')` 在 worktree 里返回 `6E98`，
   而 feedback 骨架写的是 `EBCC`。草稿归属需要稳定标识，建议落到 `.ohc/` 下的持久文件。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. **`templates/conanfile-makefile.py.tmpl` 的 conf 读法是错的**（conan 2.29.1 实测抛
   `ConanException: [conf] 'tools.build:compiler_executables:c' does not exist in configuration list`）。
   建议改成仓内已在用的 dict 形态并给注释：
   `compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)`
   → `cc = compilers.get("c", "clang")`。
2. **makefile 模板缺"无 configure 项目"的路径烤入范式**：本次 8 个编译期路径常量
   （`BINDIR/CONFIGFILE/MAPTABDIR/DEBUGFILE/LOGFILE/LOCKDIR/PUBDIR/NEWSSPOOL/FAKEDIR`）
   只能靠 make 变量覆盖指到 `package_folder`（`rgb/1.1.1` 同法）。建议模板补一段
   "编译期路径常量 → package_folder"的示例与 `package()` 里创建运行期空目录（`.keep`）的做法，
   否则 `freopen(debugfile)` 一类逻辑在新装环境上会静默失败。
3. **模板应提示 `can_run()` 而不是 `cross_building()`**：`conan-verify`/CI 用
   `-pr:h=-pr:b=` 同一个 OHOS profile 时，`cross_building()` 在开发机也返回 False，
   导致"执行目标二进制"的步骤在 macOS 上真的去 exec OHOS ELF。本次即踩中
   （30 项上游自测全 0/30），改成 `can_run()` 后才正确跳过。建议模板与
   `test_package` 模板统一用 `can_run()`，并说明 `tools.build.cross_building:can_run` 的语义。
4. **PR 模板的"上游用例数"缺计数口径栏**：上游若无测试框架（本例只有 4 个 `-DTESTING` 目标、
   自身不含断言），"用例数"到底填程序数还是检查项数没有位置说明，只能在表格「说明」列里塞。
   建议给两张表各加一行"计数口径"或在模板注释里固定口径写法，避免不同 PR 口径不可比。
5. **`submit` 生成的 PR body 与 `templates/积分赛事PR模板.md` 不同构**（章节顺序、
   复选框形态都不一样）。本次靠"预先写好 `reports/pr-body.md`（不含任何待填写占位符）→ 工具判定 Already filled in 并保留"绕过。
   建议 `_generate_pr_body` 直接以赛事模板为骨架填充。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. **补丁生成器改用 `diff -u`（或生成后自校验）**：per-file difflib 产出的 hunk 头行号会偏 1，
   GNU patch 容忍、conan 的 patch-ng 不容忍。最低成本修法：生成后对每个补丁跑一次
   `patch -p1 --dry-run`（或直接 `git apply --check`）自校验，不通过就回退到 `diff -u` 重生成。
   本次 15 个补丁全部经 `patch -p1` 实测 rc=0 后才提交。
2. **`refresh_patch.py` 的排除清单应看构建系统类型**：Makefile 驱动型项目（无 configure/cmake）
   的 `Makefile` 是**源码**不是产物。建议按 `manifest.build.system == makefile` 或
   "该文件在原始 tarball 中就存在"来判定，而不是一律排除。
3. **`pre_pr_audit.py generate` 的输出目录**：默认写 `~/tmp/`，在受限沙箱里
   `PermissionError: /Users/<u>/tmp/audit-input-*.json`。建议默认落到 `$TMPDIR` 或 `reports/`。
   另外 `--base-branch` 只接受分支名并硬拼 `origin/<name>`，无法直接指定
   `ohpcd/main` 这类远端 ref（本次靠"origin/ohpcd/main 不存在→回退裸 ref"侥幸生效）。
4. **CA 证书自动兜底**：gitcode API 调用前若 `ssl.get_default_verify_paths()` 的 cafile 不存在，
   自动回退 `certifi.where()` / `/etc/ssl/cert.pem`，省掉每次手工 `SSL_CERT_FILE=`。
   `init-build` 往 `/storage/...` 装证书在开发机上必然失败，建议只在 worker 上尝试。
5. **`gitcode_pr.py` 增加一个 plain `add-comment` 子命令**：目前发 `/ai review force`
   这类顶层评论只能自己 import 模块调 `api_request`（`reply-comment` 需要 discussion-id，
   `trigger-ci` 只发 `/rebuild`）。
6. **`get-pr` 的 `--json` 未生效**：`--json get-pr` 仍输出人类可读文本（描述被截断到 ~1 KB），
   导致 PR 正文回读门禁只能自己调 API。建议修 `--json` 或加 `--raw-body`。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

本次已按【知识库扩展】交付 2 对草稿，另有 3 类模式建议后续补条目：

1. **已成稿**：`DRAFT-ifmail-2.14tx8.10-gdbm-compat-ndbm-no-include-guard`
   （OHOS 无系统 ndbm → 只能用 gdbm compat；其 `<ndbm.h>` 无 include guard，
   同 TU 二次包含即 `typedef redefinition ('struct DBM' vs 'struct DBM')`；
   且 `gdbm/1.23` 是 `--enable-libgdbm-compat`、`gdbm/1.24` 是 `--disable-`，
   `conan list` 看不出来，必须下载配方/包体实测）。engine 查重只命中 E119（0.20）。
2. **已成稿**：`DRAFT-ifmail-2.14tx8.10-kr-varargs-clang-error-stub-stdarg`
   （clang 的 `<varargs.h>` 是只含 `#error` 的桩头；`va_dcl` + 单参 `va_start(ap)` 一次炸三条硬错误；
   转换必须同步 ANSI 原型/static 前置声明/包含顺序；`-Wno-*` 完全无效，E063 不适用）。
   index.tsv 全文 grep `varargs|stdarg|va_dcl` 零命中。
3. **建议新增 E-entry：flex 生成的 `extern int yywrap ( void );` 与项目内 `#define yywrap() 1` 相撞**
   → 按 flex 约定 `#define YY_SKIP_YYWRAP 1`。报错形态很有辨识度
   （`too many arguments provided to function-like macro invocation`，指向生成文件而非 .l），
   任何 1990s lex 项目都可能踩；index.tsv 无 `yywrap` 相关条目，E543 只讲 flex/bison 的
   `tool_requires` 与 cross 分支，不覆盖此点。
4. **建议新增 E-entry：musl 无 BSD `re_comp`/`re_exec`**（glibc 需 `_REGEX_RE_COMP` 才暴露），
   修法是用 POSIX `regcomp`/`regexec` 包一层并保持调用点原样。链接期报
   `undefined symbol: re_comp`（ld.lld 会提示 `did you mean: regcomp`）。
   与 E093（musl 无 `getpass`）同族，可考虑合并成"musl 缺失的 BSD/GNU 便利函数清单"条目。
5. **建议扩充 E516**：其 `error_signature` 目前是链接期形态
   （`undefined symbol: _res|cannot find -lresolv`），本次遇到的是**编译期**形态
   `error: use of undeclared identifier '_res'`，外加 libresolv 私有的
   `_getshort`/`_getlong`（DNS 应答的大端读取）同样缺失。建议把这两个特征并进 E516，
   否则手工解析 DNS 的老代码（inn/trn/leafnode 家族）查重时命中不了。
6. **建议新增 E-entry：上游"自测目标链接不上"的通用形态**——`-DTESTING`/`make check` 的目标
   引用了前端程序才提供的符号（本例 `version`/`reldate`/`copyright`/`usage()`），
   在任何平台都链接失败；修法是补一个只用于测试构建的 glue 对象并把它接进测试规则。
   R51 要求"可运行的上游测试必须真跑"，这类阻塞会很常见。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: songzhenyan
- **邮箱**: apVBMI1DvwCqWTll.songzhenyan@noreply.gitcode.com
- **Agent ID**: EBCC
- **生成时间**: 2026-10-16 19:17:29
- **PR 编号**: 16259
- **Git Commit**: da09fa7d8e
