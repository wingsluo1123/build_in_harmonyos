# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成骨架，AI 按实际执行情况填写。
> 文件位置: `feedback/SKILL_FEEDBACK_ee224d1d.md`

---

## 背景

- **软件名称**: portio
- **版本**: 0.6.2
- **构建日期**: 2026-10-17
- **构建系统**: setuptools（上游 `setup.py build_ext`；PEP 517 后端同为 setuptools）
- **上游仓库**: https://github.com/fabriziop/portio（tag 0.6.2 = commit 6345900…）
- **适配路径**: CPython C 扩展 + x86 专有端口 I/O 的平台降级适配（1 个补丁）
- **补丁数量**: 1（`patches/0001-portio.c.patch`，+130/-2，portability）
- **编译依赖**: python/3.12.9（构建期另需 pinned setuptools-84.0.0 wheel，解包即用）
- **最终状态**: built（conan create / conan-verify / finish W2+W3 全绿；尚未 commit/push/PR）

---

## 情况

### 执行概要

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | GitHub tag tarball，sha256 与 manifest/conandata 一致 |
| lang-preflight | R47 语言预检 | **失败（分类器误判）** | 两次均判 `detected_language=python`（按文件数 python:3/c:1），实为 C 扩展包 |
| build | 编译构建 | 成功 | 0 告警 / 0 错误；产物 0 个 x86 未定义符号 |
| conan create | 完整构建 + test_package | 成功 | 10/10 用例，含 5 个鸿蒙特有用例 |
| conan-verify | 配方验证 | 通过（G1/G2/G3/G4；L2/L4/L5 工具侧 skip） | 报告 `reports/conan-verify-report.md` |
| finish | 归档收尾 | 完成（W2/W3 全绿） | step5b/step8 为工具侧告警：packaging tar.gz（与 JC3 冲突）与知识库既有空字段 |
| submit | PR提交+AI检视+CI | **未执行（用户要求在 commit/push/PR 前停止确认）** | — |

### 失败与问题

| # | 现象 | 根因 | 处置 |
|---|------|------|------|
| 1 | `lang-preflight` 两次 exit 2（cpp 与 c 都判 python） | `lang_detect.py` 以 manifest（pyproject.toml）优先 + 文件数统计，未识别 "setuptools + ext_modules + .c" 属 C/C++ 扩展（`build-systems.md §14` 明确该类属合法 cpp 任务） | 按 C 继续适配并在 notes.md 留痕；未伪造 result 字段 |
| 2 | W3 L0d `stub_test_method` | `test()` 用 `subprocess.run` 而非 Conan `self.run` | 改 `self.run`，结果 JSON 写临时目录回读 |
| 3 | W3 JC `full` 模式失败（9 个运行期标记文件） | 全部位于他人归档，且 `git cat-file -e origin/main:<path>` 证明 main 上即存在；W3 因无 commit 无法进入 incremental/prdiff 模式 | 以 CI 同源 `JUNK_PR_DIFF` 走 prdiff 模式复跑通过 |
| 4 | W3 每次运行后 `conandata.yml` 变成 `gh-proxy.com` 镜像列表，日志却打印"已还原为官方 URL" | Pre-download 的 `_restore_conandata` 把已被污染的内容当基线（备份取自运行前状态），trap 实际未能拉回官方 URL | 交付件人工恢复官方 URL，并作为框架缺陷上报 |
| 5 | `ci-metadata.json` L1 记为 "upstream tests + test_package executed" | 构建日志中 `reason` 文本含 `pytest/ctest` 字样，被 `build_and_test.sh:1449` 的 grep 命中 | 文案去掉该字样后 L1 = `test_package executed`（与"上游 0 用例"一致） |

### 知识图谱使用情况

- **引用知识条目**: E004（musl BIND_NOW 符号解析）、E077（OHOS .so 签名）、`knowledge/operations/build-systems.md §14`（Python C 扩展）、`archives/g/gpgmepy/2.0.0`（setuptools wheel 引导）
- **新增知识草稿**: E2141（`<sys/io.h>` 为空头文件 → 编译只告警/链接不报错/dlopen 才 symbol not found）
- **引擎命中情况**: 编译前 G0 预扫描未识别该构建族（构建系统 unknown），本次由人工诊断
- **测试统计**: 上游 0 用例（无入口）；上游样例 3/3 通过；test_package 10/10（鸿蒙特有 5）
- **未覆盖的错误模式**: "空头文件（header 存在但内容为空）导致的隐式声明 + 延迟链接失败" 此前无条目；"Python C 扩展" 缺 `lang_detect` 判定规则（不是知识条目问题而是分类器规则问题）

### AI 检视结果

- **检视阶段到达**: 未到达（尚未创建 PR）
- **变更摘要评估**: —
- **检视意见数量**: 0
- **检视意见处理**: 已用上下文隔离子任务做等价 Pre-PR 独立审计，发现 1×P0（conandata 镜像 URL）、3×P1（PyBuffer 泄漏 / patch_classification 占位符 / ci-metadata L1 虚假）、7×P2，全部整改并复验

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（`L0_RESULT=pass`、`L1_RESULT=pass`、`L4/L5=pass`、JC/KC pass，Pass rate 100% 1/1）
- **远程 CI (PR 校验)**: 未触发（未创建 PR）
- **CI 失败原因**: 无（此前失败均在本轮修复）

### 效率分析

- **HANDOFF 次数**: 3（W3 两次失败 HANDOFF + result 参数校验一次）
- **重试次数**: finish 共 6 次（L0d 修复 1 次、JC 模式 1 次、审计整改 + package_type 试错 2 次、其余为知识/摘要）
- **关键瓶颈**: 构建机 `/storage/Users` inode 几近枯竭（多次 `No space left on device`，`conan create` 与写日志均受影响），被迫改用稀疏检出并多次重试；其次是 W3 的 JC/全仓扫描与本包无关
- **耗时较长的步骤**: 稀疏 worktree 搭建与 inode 腾挪、finish 重复整跑（每次都重跑 conan-verify + conan create）

---

## 建议

### SKILL 设计改进

1. **`lang_detect` 需识别 Python C 扩展**：`pyproject.toml` + `setup.py` 含 `ext_modules`/`Extension(...)`、且存在 `.c/.pyx` 源时，应判 `cpp`（与 `build-systems.md §14` 口径一致），否则 R47 会把合法 C 扩展任务直接判 env_unsupported（本次两次 exit 2 均为误判）。
2. **Pre-download 的 conandata 还原不可信**：`_restore_conandata` 的备份是对"当前（可能已被上次运行污染）"文件做的，等价于把污染固化；建议改为：备份到 `.build-cache/predl_cache/<pkg>-<ver>-pristine.yml` 且只在文件是官方 URL 形态时才覆盖，还原后 `grep -q 'gh-proxy|ghfast'` 不通过即 fail，而不是打印"已还原"。
3. **`full` 模式的 JC 不应阻断本地 W3**：本地无 commit 时 JC 只能整仓扫描，命中历史遗留（9 个他人 `.staging-verified`/`.build-closed`）就把整包判负。建议 W3 在无 commit 时默认按 `git status` 变更集构造 prdiff（与 CI 同源），或把 full 模式的既有命中降级为 warning。
4. **`ci-metadata` 的 L1c 靠日志 grep 判定"上游测试已执行"**：任何包只要日志里出现 `pytest/ctest` 字样（哪怕只是"本包无 pytest 用例"的说明）就会被记成 "upstream tests executed"。建议改为读取结构化的 `HMBS_UPSTREAM_TEST_RESULT`（discovered/executed 字段），而非 grep 自由文本。
5. **稀疏 worktree 下 `SUMMARY.md` 会被重写**：finish 的 gen_summary 按本地检出统计，把全仓索引覆盖成"1 款软件"（-2603 行）。建议 gen_summary 在"检出文件数 << 索引条目数"时跳过或只做增量合并；PR 侧也应显式排除 SUMMARY.md。
6. **PF9 会把软件级文件误判为"缺版本目录层"**：`archives/p/portio/manifest.yaml`（4 段）必然命中 `len(f.split("/")) < 5`，而 ARCHIVE-SPEC 要求软件级 `manifest.yaml`/`README.md` 必填——新包 PR 会 100% 被拦。建议对 `{manifest.yaml, README.md, commands.json}` 白名单放行。

### 模板改进

1. **缺 Python C 扩展模板**：`templates/` 目前无 `conanfile-python-ext.py.tmpl`，`conan-init` 只能吐出 autotools/CMake 骨架（本次 4 个文件全部手写）。建议按 `lxml`/`gpgmepy`/本配方提炼：`requires python/3.12.9` + `setup.py build_ext` + `EXT_SUFFIX` 探测 + 签名 + `lib/python3.12/site-packages` 布局 + HMBS 上游结果上报。
2. **`test_package-conanfile-*.py` 模板只有 CMake 变体**：Python 扩展需要"用 conan python 跑 runner + 结果 JSON 回读"的变体（且 `self.run` 是 L0d 硬要求，模板应默认满足）。
3. `manifest-version.yaml` 的 `build.system` 枚举缺 `setuptools`/`python`（现只能填 `custom`），`conan-init` 也会因此把构建系统识别成 autotools。

### 自动化补全

1. **clean-verify（G0）硬编码 `./configure`**：对 setuptools/CMake/Meson 包必然 exit 127，建议按 `build.system` 选择 command，或提供 `hints` 字段；否则该步对非 autotools 包永远是"失败但非阻塞"的噪音。
2. **finish 的 packaging tar.gz 检查与 JC3 冲突**：既要求 `packaging/*.tar.gz`，又把归档内 tarball 判为 junk。建议对 conan 流程的 `built` 状态跳过该项（本次只能留 warning）。
3. **`result` 的 partial 草稿也必须给 `--failed-reason`**：语义上"等待用户确认"不是失败，建议允许 `--status partial` 使用 `--note/--summary` 代替 `--failed-reason`。
4. **inode 枯竭没有前置检查**：建议 `conan create`/`finish` 前检查可用 inode（`stat -f`），低于阈值直接提示"清理工作树"，而不是在构建中途报 `No space left on device`。

### 知识图谱覆盖

1. **已新增 E2141 草稿**：`<sys/io.h>` 在 OHOS aarch64 存在但 `bits/io.h` 为空 → 编译仅隐式声明告警、链接不报错（`.so` 允许未定义符号）、故障延后到 dlopen `symbol not found`；对策：架构宏 `#if` 分支 + 非 x86 显式失败（抛错/ENOSYS），禁止空 stub。
2. 建议追加一条：**"Python C 扩展在 OHOS 的构建公式"**（conan python + setuptools wheel 引导 + `-lpython3.12` + binary-sign-tool + `lib/python3.12/site-packages` 布局），可作为 `build-systems.md §14` 的落地示例而非新 E 条目。
3. 建议补一条：**"CI 日志里出现测试框架字样会被 L1c 判成上游测试已执行"** 的陷阱条目（本次 P1 根因）。

---

## 作者

- **姓名**: GaoPengqiang
- **邮箱**: GaoPengqiang@noreply.gitcode.com
- **Agent ID**: EA66
- **生成时间**: 2026-10-17 15:25:02
- **PR 编号**: —（未创建）
- **Git Commit**: a9a60dda65（分支 feat/portio-0.6.2 尚未提交）
