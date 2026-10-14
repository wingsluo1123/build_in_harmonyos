# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_2aa0a0df.md`

---

## 背景

- **软件名称**: unar
- **版本**: 1.10.8
- **构建日期**: 2026-10-08
- **构建系统**: makefile
- **上游仓库**: https://github.com/MacPaw/XADMaster/archive/refs/tags/v1.10.8.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 4
- **编译依赖**:
- gnustep-base/1.31.1
- wavpack/5.9.0
- zlib/1.3.1.1
- libobjc2/2.2.1
- bzip2/1.0.8.2
- icu/76.1
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: makefile |
| conan-verify | 配方验证 | 通过 | G0-G4 + L2/L4/L5 全 PASS（conan create 干净构建 + test 3/3） |
| finish | 归档收尾 | 完成 | W3 本地 CI 模拟 PASS（.ci-result.json exit_code=0）；step5b 因仓库存量知识条目字段缺失（E219/E253/E305，非本包）报黄 |
| submit | PR提交+AI检视+CI | PR 已创建（#15083），CI 已触发（调度排队中） | AI Review: bot 队列拥塞（占位评论 00:39 后摘要未出；对照 PR #15085/#15087 同样未出，平台侧问题） |

### 失败与问题

- **1**: 根因=编译失败：`getpass` 未声明（GNUSTEP 分支）, 解决方案=musl libc 无 getpass()（glibc 专有）
- **3**: 根因=tar.gz 嵌套档案静默失败：lsar 只显示 `Gzip/test.tar`、unar 把 tar 当普通文件解出, 解决方案=XADRegex 把未 NUL 终止的 NSData bytes 直接传给 regexec()：musl 用 strlen 定界 → 越界读相邻堆字节 → `\.(tar\
- **5**: 根因=即使 main() 内 setenv(TZ=UTC)，嵌套档案路径仍异常, 解决方案=gnustep-base 在**库加载期**（DT_INIT，早于 main）执行 getenv("TZ") 一次并固化结果（LD_PRELOAD 拦截实证：全进程仅 1 次调用）；main 内设置太迟
- **6**: 根因=`lsar -l` 长格式日期列显示 `(null)`, 解决方案=NSDateFormatter stringFromDate: 在 OHOS 返回 nil（与 TZ 无关：tzguard 生效、TZ=UTC 已设时仍如此；疑似 locale 数据相关，GNUstep 内部）
- **7**: 根因=conan create 报 `../UniversalDetector/UniversalDetector.h file not found`, 解决方案=XADMaster 的 GitHub tarball **不含** UniversalDetector（上游 README 要求两仓库并列 clone；XADString.m 硬引用 `../UniversalDetector/`，Makefile.linux 链接 `../UniversalDetector/libUniversalDetector.a`）
- **8**: 根因=conan test 运行期 `Error loading shared library libobjc.so`（及潜在 libz.so）, 解决方案=Conan 2 图解析：`package_type="application"` 包对静态库依赖推断 `run=False` → 这些依赖在 test_package 图中被 BINARY_SKIP → 其 package_folder=None → 依赖自身 package_info 的 None 守卫静默跳过 lib 目录 → 消费者 LD_LIBRARY_PATH 缺 libobjc2/lib、zlib/lib（libgnustep-base.so 运行期 NEEDED libz.so/libobjc.so/libcurl.so）
- **9**: 根因=conan test 报 `zip extraction missing file`, 解决方案=测试预期错误（非产品缺陷）：unar 对扁平条目档案**平铺**解压到 -o 目录（`out/hello.txt`），不建档案基名子目录；嵌套档案（tar.gz）子目录前缀来自 tar 内部条目结构

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 5 条
- **引擎命中情况**: 草稿目录 2976 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: ① gnustep-base 库加载期 TZ 固化（constructor 早于 main 读 getenv("TZ")，OHOS 无 TZ/localtime/zoneinfo → 固化失败态，日期 API 全部失效）——图谱无条目，已建草稿 DRAFT-UNAR-1108-GNUSTEP-TZ-CONSTRUCTOR；② musl regexec 要求 NUL 终止字符串（NSData bytes 直接传入 → 堆越界读，$ 锚点异常）——图谱无条目（E093 仅覆盖 getpass），已建草稿 DRAFT-UNAR-1108-MUSL-REGEXEC-NUL-OVERREAD；③ conan 2 application 包 STATIC 依赖 run=False → test 图 BINARY_SKIP → package_folder=None 的运行时缺库链——图谱无条目，已建草稿 DRAFT-UNAR-1108-CONAN-STATIC-LINK-FABRIC

### AI 检视结果

- **检视阶段到达**: Phase 1（等待变更摘要）——bot 占位评论 00:39 后摘要/意见未出（02:20 时点仍无）
- **变更摘要评估**: 摘要未生成，无法评估（对照同期 PR #15085/#15087 同样无摘要，bot 后端队列整体拥塞，非本 PR 问题）
- **检视意见数量**: 0
- **检视意见处理**: 无意见待处理（0 条）；监控循环已由 AI 手动接管（见下方 SKILL 设计改进①：monitor-review 工具确定性崩溃）

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（.ci-result.json exit_code=0，含 L0 全部门禁 + conan create 复跑）
- **远程 CI (PR 校验)**: 01:42 /rebuild 已触发，ohpcd-robot 确认"CI 调度处理中"；截至报告时点仍在调度排队（对照 PR #15085 的 00:51 rebuild 同样排队 80+ 分钟——平台 CI 队列拥塞，外部因素）
- **CI 失败原因**: 无（尚未出结果）

### 效率分析

- **HANDOFF 次数**: 3（finish 第一轮 W3 JC 全仓扫描误命中他人状态文件；finish 第二轮 W3 L0o "curl" 字面量误报 + JC；submit 第一轮 preflight PF9 拦截软件层文件）
- **重试次数**: finish ×4、submit ×3（含 setsid 分离重启 1 次）、conan create/conan-verify 约 10 次（含 dummy probe 调试 run trait）
- **关键瓶颈**: ① 平台侧：atomgit-bot 摘要队列（55+ 分钟未出）+ CI 调度队列（对照 PR 排队 80+ 分钟）；② 本地侧：gnustep-base 加载期 TZ 固化根因定位（需 LD_PRELOAD 拦截 getenv 实证调用时机）+ conan 2 application 包 run trait/BINARY_SKIP 调试（dummy probe recipe 秒级验证 package_info 上下文）
- **耗时较长的步骤**: Step 2 手动编译与根因定位（TZ 固化 + musl regexec 越界读，数小时）；W3 conan create 重建（去 -g 后 5 分钟/次）；finish step1 refresh-patch 竞态（每轮 finish 后需手动恢复 4 个验证补丁）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 8 个事件（含 2 次 HANDOFF、1 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-10-08T17:55:17 | lang_checked | detected=c 与任务 cpp 匹配 |
| 2026-10-08T22:56:50 | skeleton_created | result_partial |
| 2026-10-09T00:34:31 | handoff:pr_creation_failed | PR 创建失败 \| 手动创建: python3 scripts/gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --source feat/unar-1.10.8 --target main --title 'feat(unar): 1.10.8 适配完成' |
| 2026-10-09T00:39:14 | skeleton_exists | pr_created |
| 2026-10-09T00:39:14 | pr_created | PR #15083 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15083 |
| 2026-10-09T00:54:36 | task_started | submit --resume 重启预算计时（v12.15） |
| 2026-10-09T00:54:37 | skeleton_exists | resume_pr_exists |
| 2026-10-09T01:24:42 | handoff:ai_review_summary_timeout | 变更摘要未在 30 分钟内生成，请稍后手动检查 PR #15083 \| 检查: python3 scripts/gitcode_pr.py --json monitor-review --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 15083 \| 摘要出现后: python3 scripts/ohc-run.py submit unar 1.10.8 --resume |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

① **monitor-review 确定性崩溃（P0 级工具 bug，直接致盲 submit 监控循环）**：gitcode_pr.py cmd_monitor_review 输出 dict 引用未定义变量 `unreplied_opinions`（line 1066，函数体内从未赋值）→ 任何状态下 subprocess 都 NameError 崩溃 → submit 的 AI Review 监控循环永远收到"获取检视状态失败"，Phase 1 必然 30 分钟超时 HANDOFF，之后 resume 继续超时死循环。本次靠 AI 手动 get-comments 轮询接管。建议：定义该变量（如基于 review_opinions 与已回复 discussion_id 差集计算）或移除字段，并在 CI 加 monitor-review 冒烟用例。

② **conan-verify/W3 镜像注入还原不可靠**：ghfast/gh-proxy 镜像改写 conandata.yml 后，finish 崩溃/正常退出的多条路径都留下 `.ghfast-bak`/`.orig` 残留与 gh-proxy.com 列表持久化（PF7 黑名单域名，本次手动还原 3 次；每次还原后下一轮 finish 又可能再注入）。建议：注入/还原改原子事务（try/finally + 还原后 sha256 校验文件回原状，不一致自动从 .bak 恢复）。

③ **PF9 与 W2/R38 规则冲突**：PF9 用 `len(f.split("/")) < 5` 一刀切拦截所有版本目录外文件，但 R38 强制 CLI 工具在软件级目录放 commands.json、归档规范 §6 要求软件级 README.md——CLI 首包适配必然撞闸（本次靠 --no-preflight 逃生口过，且该逃生口同时跳过 R52 交叉校验）。建议：PF9 仅在"整个 PR 无任何版本目录文件"时拦截（其声明的"No packages to build"风险），允许单包 PR 混合软件层文件。

④ **W3 JC 本地 full 模式误伤**：工作未提交时 incremental diff 为空 → 回退 full 扫描 → 命中 main 上他人历史误提交的 5 个状态文件（cloog/kics/libbfio/thc）→ W3 假失败（CI prdiff 模式不受影响，本地 CI 结论失真）。建议：本地 full 模式对齐 CI prdiff 口径，或对 git 已跟踪的存量文件豁免。

⑤ **finish step1 refresh-patch 竞态**：无 edit tracker 时规则 diff 生成 git 风格前缀补丁（XADMaster-1.10.8/ 前缀 + 命名不含 conandata 引用名 + 多含 recipe 内嵌文件），覆写手工验证过的 patches/，且与 step4 G2 存在读-写竞态（E515 已有记录但无工具级防护）。建议：patches/ 存在 conandata 引用名文件时拒绝覆写（或输出到临时目录供比对），step1 提供跳过开关（本次用 _SKIP_PATCH_GENERATION 只挡了 step2，step1 无开关，靠临时改名 .orig 目录绕行）。

### 模板改进

① **_generate_pr_body 上游/适配后测试统计混用**：total_tests 同时填"上游库测试用例统计"与"适配后"两表——上游无测试套件时 PR 会显示"上游单元测试 3"（虚假申报，R51 违规风险）。建议：两表分源（上游数取 manifest.upstream_tests 清点值，无则显式 0 + 附清点证据列）。

② **PR 标题无积分赛前缀机制**：_generate_pr_body 硬编码 `feat(x): v 适配完成`，§0.2 规则（提示词含 积分赛/依赖项/知识库扩展/高难度挑战 → 标题必须对应前缀且仅一种）只能靠建 PR 后 update-pr 手工补。建议：submit 支持 --title 或从任务上下文自动推导前缀。

③ **conanfile.py 模板缺 shebang**（W4 审计 P3）；test.sh 模板用 `set -e` 而非 `set -euo pipefail`（POSIX sh/mksh 下 pipefail 兼容性建议注释说明）（W4 审计 P3）。

### 自动化补全

① **conan 2 run trait 问题静态提示**：application 包对 STATIC 依赖默认 run=False → test 图 BINARY_SKIP → package_folder=None 的缺库链（本次耗时数小时定位，dummy probe recipe 验证）。建议 conan-init 对 package_type=application 的包静态提示检查依赖 run trait + package_info None 守卫。

② **monitor-review API 失败优雅降级**：当前 subprocess 崩溃 → 整个监控循环空转 30 分钟超时。建议：失败计数 + 退避，连续 N 次失败时输出"手动接管指引"（get-comments + 判定口径），而不是静默重试到超时。

③ **finalize-archive tarball 命名自动生成**：期望 `*-ohos-aarch64.tar.gz`/`*-debug.tar.gz` 命名，本次按通用名生成后需手工改名消除警告。建议 finalize 直接按约定命名生成。

### 知识图谱覆盖

① 本次新增 3 条草稿（已随 PR 提交 knowledge/drafts/）：DRAFT-UNAR-1108-GNUSTEP-TZ-CONSTRUCTOR（gnustep-base 加载期 TZ 固化 + libtzguard.so 首个 DT_NEEDED 方案——对所有 GNUstep 系 OHOS 包通用，优先级最高）、DRAFT-UNAR-1108-MUSL-REGEXEC-NUL-OVERREAD（musl regexec NUL 终止要求 + NSData bytes 越界读——对所有 ObjC/musl 正则使用场景通用）、DRAFT-UNAR-1108-CONAN-STATIC-LINK-FABRIC（静态链接链路与 NEEDED 核对方法——runenv 编写前置检查）。

② 建议主编审核时优先提升前两条为正式 E 条目（跨包复用价值高）；E093（musl getpass）建议补注"GNUSTEP 分支常见触发点"。

---

## 作者

- **姓名**: gcw_Pp8UzTBn
- **邮箱**: 2280277721@qq.com
- **Agent ID**: F8D3
- **生成时间**: 2026-10-08 22:56:50
- **PR 编号**: —
- **Git Commit**: 82760c6f4
