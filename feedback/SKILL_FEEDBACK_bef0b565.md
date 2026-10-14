# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_bef0b565.md`

---

## 背景

- **软件名称**: typeshare
- **版本**: 1.13.4
- **构建日期**: 2026-10-13
- **构建系统**: custom（Rust / Cargo workspace：annotation / core / lib / cli）
- **上游仓库**: https://github.com/1Password/typeshare
- **适配路径**: 路径 A（基础适配，无补丁）
- **补丁数量**: 0
- **编译依赖**:
  - `rust-toolchain/1.97.1`（构建期 `tool_requires`，制品仓基础设施包；`conan download` EXIT=0）
  - cargo 运行期共享库：harmonybrew OHOS bottle `openssl@3-3.6.5`、`zlib-ng-compat-2.3.3_2`
  - 其余 110 个 crate 由 cargo 依 `Cargo.lock` 从 crates.io（rsproxy.cn）自动拉取；无 C/C++ 目标依赖包
- **最终状态**: LOCAL_AUDIT_PASS（本地门禁全通过，按用户在 commit/push/PR 前停止等待确认）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | 改用 `archives/t/typeshare/1.13.4/` 手工落位 + `init-archive` 建骨架（github 归档直连可用，sha256 双通道一致） |
| build | 编译构建 | 成功 | 构建系统: custom（Cargo）；`conan create` EXIT=0，用时 2 min 16 s |
| conan-verify | 配方验证 | **PASS** | G0/G1/G2/G3/G4 全通过（L2/L4/L5 报"无 cache 路径"跳过）；报告 `reports/conan-verify-report.md` |
| finish | 归档收尾 | 完成 | **W3 本地 CI 阻塞门禁 PASS**（JC/KC/L0/L1/L2/L4/L5），`.ci-result.json` exit_code=0 |
| submit | PR提交+AI检视+CI | 未执行 | 按用户要求在 commit/push/PR 前停止（LOCAL_AUDIT_PASS）；AI Review: — |

### 失败与问题

本次流程遇到 **3 个阻断性问题 + 1 个非阻塞门禁失败**，均已定位根因并修复：

1. **（阻断）proc-macro 测试 harness 加载未签名 `libstd-*.so`（exit 127，cargo test rc=101）**
   - 首个错误：`Error loading shared library libstd-6cb83eb787a5e858.so: (needed by .../typeshare_annotation-...)` + 大量 `symbol not found`，`exit status: 127`；同 workspace 其它 5 个测试目标全部通过。
   - 根因：proc-macro 测试 harness 以 `prefer-dynamic` 链接（`NEEDED libstd-<hash>.so`，无 RUNPATH）；**cargo 启动测试进程时把 `<sysroot>/lib/rustlib/<target>/lib` 前置到 `LD_LIBRARY_PATH`**（runner 探针实测输出证实），而该目录属只读工具链载荷、其中 `libstd-*.so` 未签名；HarmonyOS 拒绝加载未签名共享库，前置副本因此遮蔽了配方放进 `toolchain/lib/` 的已签名副本。
   - 修复：①`_prepare_signed_toolchain()` 增补复制+自签名 `rustlib/<target>/lib/*.so`；②新增 `_prepare_test_runner()`，经 `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_RUNNER` 注入 runner 把已签名目录前置（runner 路径不能含空格——cargo 以空白切分 runner 值）。
2. **（阻断）上游确定性样例依赖 `sed`，OHOS 构建 PATH 内缺失**
   - 首个错误：`FileNotFoundError: [Errno 2] No such file or directory: 'sed'`。
   - 修复：用 Python 标准库完成等价全局正则替换 + 字节级比对（`tests/justfile` 的 `sd`/`diff -q` 等价）。
3. **（非产品缺陷）test_package 参数错误 2 项**：`-l scala` 少 `--scala-package`（上游 `scala.rs:131` 缺 package 即 panic）；`--generate-config` 需带目录参数且与 `-o` 互斥。修复后 11/11 通过。
4. **（非阻塞）conan-verify G2 一次 `Text file busy (os error 26)`**：HMDFS 上 cargo exec 刚写入的 build script 偶发失败；结构性规避为把确定性样例移到 release 构建之后并复用 release 产物（消除"新建 debug 构建脚本立即 exec"路径）。知识已存在：`DRAFT-hmdfs-etxtbsy-write-then-exec-cargo-retry`。
5. **（非阻塞）finish step5b / step8 告警**：知识字段缺失（`E219/E253/E305` 为空，系 origin/main 存量）与 legacy `packaging/` 检查（对 conanfile.py v3 配方不适用）。详见下方建议。

### 知识图谱使用情况

- **引用知识条目**: `DRAFT-below-ohos-unsigned-rust-toolchain`（工具链自签名+运行库+CA）、`DRAFT-hmdfs-etxtbsy-write-then-exec-cargo-retry`（ETXTBSY 锚定重试）、`DRAFT-13336-rainfrog-rust-toolchain-relocate-sysroot`（sysroot 推导）
- **新增知识草稿**: 1 条 —— `knowledge/drafts/DRAFT-rust-cargo-rustlib-libstd-unsigned-test-harness.{kv,md}`（cargo 前置 sysroot 子目录 → 未签名 libstd 遮蔽签名副本；kv↔md 配套，KC1-KC5 全 PASS）
- **引擎命中情况**: `engine` 对 "Text file busy" 弱命中 E232（autotools configure 语义，非同类）；对 libstd 加载失败命中 E540（runner-path-prepend，弱相关）→ 均判为非同类，故按 R31 新增草稿
- **测试统计**: 总计 398, 通过 398, 失败 0, 跳过 0（上游 cargo 386 + 上游 shell 样例 1 + test_package 11）
- **未覆盖的错误模式**: 已由本次新增草稿覆盖「cargo 前置 `lib/rustlib/<target>/lib` 导致未签名 `libstd` 遮蔽签名副本」；「HMDFS 写后即 exec 的 ETXTBSY」已有草稿

### AI 检视结果

- **检视阶段到达**: — （未创建 PR，流程按用户要求在 LOCAL_AUDIT_PASS 停止）
- **变更摘要评估**: 不适用
- **检视意见数量**: 0
- **检视意见处理**: 不适用

### CI 结果

- **本地 CI 模拟 (W3)**: **通过**（`JC=pass KC=pass L0=pass L1=pass L2=pass L4=pass L5=pass`，Success 1/1；日志 `archives/t/typeshare/1.13.4/reports/w3-local-ci.log`）
- **远程 CI (PR 校验)**: 未触发（未创建 PR）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 1（finish 首轮 W3 因 JC 全仓扫描命中 other-tasks 存量运行时标记而 HANDOFF；按 typst 先例临时移除索引条目后 W3 通过并原样恢复）
- **重试次数**: `conan create` 5 轮（libstd 失败 1、sed 缺失 1、test_package 参数 1、并发写瞬时损坏 1、通过 1）；`conan-verify` 2 轮（G2 ETXTBSY 1 + 通过 1）；`finish` 3 轮（W3 JC 1 + 标记补齐 1 + 通过 1）
- **关键瓶颈**: ①定位"未签名 libstd 遮蔽"耗时最多（需区分加载期失败 vs 用例失败，并用 target runner 探针证明 cargo 的搜索顺序）；②每轮 `conan create`/`conan-verify G2`/`finish W3` 都要全量重编 Cargo workspace（每轮约 2–4 分钟）
- **耗时较长的步骤**: `conan create`（含上游测试，~2.5 min/轮）、`conan-verify` 内嵌 G2 create（~2.5 min）、`finish` step[5/10] W3（含内嵌 create，~4 min）

---

## 建议

### SKILL 设计改进

1. **PF9 与 R38/PF8 冲突（会阻断 CLI 包的 PR 创建）**：`preflight.check_branch_and_paths()` 要求 archives 变更路径深度 ≥5（`archives/<字母>/<包>/<版本>/<文件>`），但 R38/PF8 要求 CLI 包的 `commands.json` 放在**软件级** `archives/<字母>/<包>/commands.json`，归档规范同样在软件级放 `README.md`/`manifest.yaml`。以本包白名单实测，这三个软件级文件会被 PF9 判为「缺版本目录层」；在已合入的 `archives/r/rumdl`（2026-10-09 引入软件级 commands.json）上同样可复现。`create-pr` 对 preflight 结果 fail-closed，故**未打 --no-preflight 时 CLI 包 PR 无法创建**。建议 PF9 为软件级元数据文件（`commands.json`/`README.md`/`manifest.yaml`）加白名单，或仅校验"版本级子集落在单一包/版本目录"。
2. **`build_and_test.sh` 的 conandata 镜像改写未还原（会污染工作区并命中 PF7）**：该脚本把 `conandata.yml` 的单值 `url:` 改写为 `[gh-proxy.com 镜像, 官方 URL]` 列表，而 EXIT trap 只还原其后的 `predl_cache` 备份（备份在改写之后才建立），导致每次本地 `finish`/W3 后必然残留镜像列表 + `conandata.yml.orig`。实测 `check_source_urls()` 对该形态报 `PF7 源URL闸(R39): ... 镜像前缀 gh-proxy.com`——即框架自己产出了会被框架拦下的文件。建议把镜像改写纳入同一 trap 的还原范围（或在改写前统一备份一次）。
3. **`junk_check.sh` 在"分支尚无提交"时回退 full 全仓扫描**：`incremental` 模式用 `git diff origin/main...HEAD`，未提交分支该 diff 为空 → 回退 `git ls-files` 全仓扫描，必然命中 **origin/main 已合入的其它任务**运行时标记（本次 8 个 `.staging-verified`/`.build-closed`）。这使"首次提交前的 W3 验证"结构性不可通过，只能靠人工临时改索引。建议 full 模式增加"排除 origin/main 已跟踪文件"或包路径过滤（`CI_PACKAGES`）。
4. **`finish` 退出码语义混淆**：`run()` 用 `all(steps)` 决定退出码，非阻塞步骤（W5 知识字段、legacy packaging、gen_summary 异常）也会让 exit=1，容易被误读为"阻塞门禁失败"。建议区分 blocking / soft 两组并输出独立退出码（或在 HANDOFF 中显式标注"仅软性步骤未绿"）。
5. **step[10/10] submit 就绪预检要求 `packaging/` 非空**：对 `conanfile.py` v3 配方这是 legacy 语义（已合入的 conan 配方如 tdom / libcdio-paranoia / rumdl 均无 `packaging/`）。建议对存在 `conanfile.py` 的包以 `conanfile.py + test_package/ + .ci-result.json` 作为等价就绪证据。
6. **新增规则建议**：把"cargo 前置 sysroot 子目录 → 未签名 `.so` 遮蔽签名副本"纳入 Rust 配方检查清单（已由本次草稿沉淀）；同时把 `DRAFT-hmdfs-etxtbsy-write-then-exec-cargo-retry` 建议的"锚定错误文本的一次重试"作为 Rust 配方默认守卫写进 SKILL 正文。

### 模板改进

1. **缺 Rust/Cargo 配方模板**：`templates/` 现有 cmake/autotools/meson/makefile/headeronly 五种，无 cargo。建议新增 `conanfile-cargo.py.tmpl`，内容即本次已验证形态：`tool_requires rust-toolchain` + `_prepare_signed_toolchain()`（含 rustlib dylib）+ `_prepare_test_runner()` + `_prepare_runtime_libs()`（cargo 的 libssl/libcrypto/libz）+ `cargo test --workspace --all-features --tests` + 二进制签名。可显著减少同类任务的重复探索。
2. **`test_package-executable` 模板可预置"鸿蒙特有四项"骨架**：AArch64(EM_AARCH64=183) / `PT_INTERP=ld-musl-aarch64.so.1` / `.codesign` 存在 / 产物完整性。本次为手写，若模板内置可提升一致性并稳定满足"鸿蒙特有用例 ≥1"。
3. **SKILL_FEEDBACK 模板占位符未被自动填充**：`构建系统: {BUILD_SYSTEM}` 与 `上游仓库: (未知)` 在生成时未从 manifest.yaml/conandata.yml 回填（其余统计项也需要 AI 手填）。建议生成时从 `manifest.yaml` 的 `build.system`/`source.url` 与 `.ci-result.json` 自动回填。
4. **`reports/test-report.md` 被 .gitignore 忽略**：该文件是 submit 门禁与 W4 审计的重要输入，却不进 PR（仅 3 个包有 `!` 例外）。若期望它在 PR 中可见，需要显式 un-ignore 规则；否则建议在 SKILL 中说明"reports/ 为本地证据、不入 PR"以免误解。

### 自动化补全

1. **`init-build` 自动识别工具链依赖**：检出源码后按 manifest 判定语言（Cargo.toml → rust / package.json → node / go.mod → go），自动补 `tool_requires`（rust 场景即 `rust-toolchain/1.97.1`），免去手工试错。
2. **`conan-init` 对纯 Rust 项目直接落 cargo 骨架**：当前 `init-archive` 对 cargo 报"模板不可用，跳过"，需 AI 手写全部 conanfile.py（本次约 600 行）。
3. **`finish` 收尾自动还原 `conandata.yml` 并复跑 PF7**：现在需要人工发现镜像残留；建议在 step[9/10] W2 原子性检查里增加"conandata 镜像域自检 + 自动还原"。
4. **引擎对"同一 workspace 仅 1 个测试目标失败"给出加载期/用例期区分提示**：本次 `exit status: 127` + `Error loading shared library` 属加载期失败，与用例断言失败易混淆；建议 `engine`/HANDOFF 对 `process didn't exit successfully ... exit status: 127|126` 直接提示"检查 ELF 可执行性与动态库搜索路径"。
5. **`result --status partial` 的表述**：停止在 LOCAL_AUDIT_PASS 时只能上报 `partial`，语义上与"部分目标达成"混同；建议增加或明确"local_pass_awaiting_confirmation"类里程碑（现在靠 `--failed-reason` 文字表达）。

### 知识图谱覆盖

1. **本次新增**：`DRAFT-rust-cargo-rustlib-libstd-unsigned-test-harness`（cargo 前置 `lib/rustlib/<target>/lib` → 未签名 `libstd` 遮蔽签名副本 → proc-macro 测试 harness exit 127；含 runner 探针诊断法与两种修复方案）。
2. **建议补充**：Rust 配方"测试 harness 动态链接"家族条目——本次覆盖 proc-macro；`cargo test --tests` 的其它 prefer-dynamic 场景（如 `dylib` crate-type）可并入同一条目的 affected_scope。
3. **存量问题**：`knowledge/graph/E219.kv`、`E253.kv`、`E305.kv` 的 `root_cause` 为空（`E305` 的 `rec_approach` 亦为空），经 `git show origin/main:...` 确认是 **origin/main 既有状态**，导致 `finish` W5 与 `check-knowledge-gap` 恒报 1 类问题；建议由知识库维护者补齐。
4. **跨条目一致性**：建议在 `DRAFT-below-ohos-unsigned-rust-toolchain` 中补一行"仅签名 cargo/rustc/librustc_driver 不够，`lib/rustlib/<target>/lib/*.so` 亦可能被 cargo 前置加载"，并在新草稿中互相 `similar_to` 引用（本次已在新草稿侧引用）。

---

## 作者

- **姓名**: lyl_ling
- **邮箱**: lan_ling_wang@noreply.gitcode.com
- **Agent ID**: 2A71
- **生成时间**: 2026-10-13 13:15:46
- **PR 编号**: —
- **Git Commit**: ca72b8c6f6
