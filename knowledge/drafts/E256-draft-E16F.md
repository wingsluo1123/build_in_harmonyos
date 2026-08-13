# E256 — OpenHarmony 挂载层 UID 映射导致 Git dubious ownership 与 pytest 临时目录所有权失败（测试驱动合规恢复）

> 状态：**路径 B 候选草稿（困难/阻塞分析型，尚未写入 knowledge/）** — probe_only_no_upload，未经用户审核不得正式写入。
> 来源：Issue #2006 · 平台库名 aider · 版本 0.86.2 · 分支 feat/aider-0.86.2
> 生成：2026-08-12（编号纠偏迁移，原 E217 draft 内容；E217 已被 conan-recipe 正式条目占用）· 证据来自鸿蒙真机（aarch64, HongMeng Kernel 1.12.0, Python 3.12.9, git 2.45.2）实测

---

## 1. symptom

- 运行上游 Python 测试套件（pytest 生成临时 Git 仓库）时大量用例失败：
  - `git.exc.GitCommandError: Cmd('git') failed due to: exit code(128)，stderr: fatal: detected dubious ownership in repository at '<tmp>'`；
  - `ValueError: Reference at 'refs/heads/master' does not exist` / `SHA is empty, possible dubious ownership`；
  - `OSError: The temporary directory .../pytest-of-<uid> is not owned by the current user`（pytest 临时目录 fixture 阶段 ERROR）。
- 触发条件：任何在 `tempfile.gettempdir()`（本真机为 `/storage/Users/currentUser`）下创建临时 Git 仓库的测试；任何使用 pytest `tmp_path`/`tmpdir` fixture 的测试。
- 受影响规模（aider 0.86.2 上游 489 项）：Git 相关失败 43 个 + pytest 临时目录错误 6 个。

## 2. root cause

- **挂载层 UID 映射**：本真机所有 tmpfs 挂载点（`/storage`、`/data` 等）创建目录/文件后 `st_uid=20001006`，而测试进程 `euid/egid=20020084`（`groups=[1006,1007,1097,3009,3099]`）。两者不一致是环境级事实（`os.stat` 与 `os.geteuid` 直接对比确认）。
- **Git 2.45.2 安全检查**：`git` 校验仓库目录 owner 是否等于当前用户，UID 不一致时拒绝执行（dubious ownership）。git 仅接受**精确路径**或 `*` 作为 `safe.directory`：
  - `safe.directory=<根>/*` **无效**（git 2.45.2 实测不支持 glob/前缀）；
  - `safe.directory=<根>/`（尾斜杠前缀）**无效**；
  - 仅 `safe.directory=<精确绝对路径>` 或 `safe.directory=*` 有效（`*` 被安全边界禁止）。
- **pytest 临时目录所有权检查**：pytest tmpdir 工厂创建 basetemp 后校验 `st_uid != euid` 即报 "not owned by the current user"；TMPDIR 无法在用户侧修复（挂载层 st_uid 固定映射）。

## 3. verified solution（测试驱动层合规恢复）

仅允许在**仓库外、仅测试进程生效**的驱动层解决；不修改上游测试、不修改 aider 包运行时代码、不写系统目录、不修改全局 Git 配置。

### 3.1 精确 safe.directory Git wrapper

```bash
# 仓库外临时目录：$HOME/final-driver-r10/bin/git
#!/bin/sh
REAL_GIT=/data/service/hnp/bin/git
# 解析 cwd / -C / --git-dir 得到实际仓库绝对路径 repo
# 仅注入精确路径：
exec "$REAL_GIT" -c "safe.directory=$repo" "$@"
```

- wrapper 解析三种调用形式：默认 cwd（`rev-parse --show-toplevel`）、`-C <dir>`、`--git-dir`；
- **只注入精确绝对路径**，不使用 `safe.directory=*`、不信任整个文件系统、不写全局配置（`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_CONFIG_NOSYSTEM=1` 隔离验证）；
- 仅对当前 pytest 命令的 `PATH` 生效（`PATH=$WDIR/bin:$PATH`），测试结束后清理。

### 3.2 固定受控 --basetemp

```bash
pytest <targets> --basetemp=$HOME/<受控固定目录> -p no:cacheprovider
```

- 显式 `--basetemp` 规避 pytest 的 tmpdir 所有权检查（实测默认 basetemp 2 errors → 显式 basetemp 2 passed）；
- 固定受控目录，不修改 TMPDIR、不改变测试 cwd 语义。

### 3.3 隔离 HOME/XDG（必要设置）

```bash
HOME=$HOME/<隔离HOME> XDG_CONFIG_HOME=.../.config XDG_CACHE_HOME=.../.cache
```

- 保留隔离 HOME/XDG 必要设置；不全局修改 TMPDIR 或测试 cwd，避免改变上游路径语义。

### 3.4 OHOS posix_spawn 边界（附加修复）

- OHOS Python 3.12 的 `os.posix_spawn` 对相对路径命令（`subprocess.run(["git",...])`）不执行 PATH 查找 → `FileNotFoundError: [Errno 2] 'git'`；
- 受控修复：测试 venv2 的 `site-packages/sitecustomize.py` 设置 `subprocess._USE_POSIX_SPAWN = False`（回退 fork+execvp，按 PATH 查找）。实测该单一 node 修复前 ENOENT → 修复后 `1 passed`。

## 4. verification（修复前后）

| 项 | 修复前 | 修复后（wrapper + --basetemp + 隔离 HOME/XDG + sitecustomize） |
|---|---|---|
| Git dubious ownership（43 个） | 43 failed | **test_repo.py 16 failed/5 passed → 21 passed；test_repomap 2 failed → 45 passed；test_commands git 用例 3 passed**（wrapper 对 cwd/-C/--git-dir 全部生效） |
| 原 6 个 errors（pytest/Git） | 6 errors | **6 passed**（--basetemp + wrapper） |
| test_main_with_empty_git_dir_new_subdir_file | FileNotFoundError 'git' | **1 passed**（sitecustomize 修复 posix_spawn） |
| 最终上游统计（489） | 476 passed/10 failed/1 skipped/0 errors/2 timeout（第 10 轮） | **482 passed/4 failed/1 skipped/0 errors/2 timeout = 489 ✓**（第 16 轮最终统一统计；test_main 修复后 6→5 failed→0，test_voice 8/8 通过后 failed 降为 scrape 4） |

实际命令（最终统一驱动）：
```bash
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_CONFIG_NOSYSTEM=1 \
PATH=$HOME/final-driver-r10/bin:$PATH \
HOME=$HOME/final-home-r10 XDG_CONFIG_HOME=.../.config XDG_CACHE_HOME=.../.cache \
pytest <targets> --basetemp=$HOME/final-basetemp-r10 -p no:cacheprovider
```

## 5. security boundary

- wrapper 仅对当前测试进程的 PATH 生效（临时目录，仓库外）；
- 只注入精确 safe.directory，不使用 `*`、不信任整个文件系统；
- 不修改全局 Git 配置（验证时以 GIT_CONFIG_GLOBAL/SYSTEM=/dev/null 隔离）；
- sitecustomize 仅写入测试 venv 的 site-packages（仓库外）；
- wrapper、basetemp、隔离 HOME、sitecustomize 均不提交；测试结束后清理。

## 6. applicable scope

- OpenHarmony 真机存在 UID 映射的挂载目录（HMDFS/tmpfs）；
- Python/pytest 测试套件中生成临时 Git 仓库的项目（git.exc.GitCommandError dubious ownership）；
- 使用 pytest tmp_path/tmpdir fixture 且遭遇 "not owned by current user" 的测试套件；
- 其他存在相同 UID 映射问题的 CI/真机测试环境（执行机需配置同类 wrapper+--basetemp 驱动）。

## 7. failure boundary（aider 当前适配边界，不属于本条目已解决内容）

以下为 aider 0.86.2 适配的外部依赖边界，仅记录，不伪装为本条目已解决：

- **音频**：test_voice 5 个 node 依赖 portaudio/19.7.0（status=built 未 published）与 libsndfile/1.2.2（published 但 remote 不可见），`conan install` 均 `Unable to find in remotes`；恢复条件 = 制品仓发布 portaudio binary + libsndfile 可匿名下载。
- **Playwright**：scrape 4 failed + 1 timeout（社区源 `from versions: none`，venv2 无包、无浏览器运行时）；恢复条件 = 社区源/Conan 补充 playwright 包与浏览器运行时。
- **help extra**：`requirements-help.in` 的 `numpy<2` 与重基 `numpy==2.5.1`/`scipy==1.18.0`（官方约束 `numpy<2.8,>=2.0.0`）直接冲突 → help 1 timeout（install_help_extra 挂起）；恢复条件 = 解决 numpy 冲突 + llama-index 链可得。
- **冷 Conan 下载**：独立 CONAN_HOME 连续三次卡在同一 source() 下载阶段（67.5MB tarball），属环境待 CI 验证。

## 8. 知识库查重

- `dubious ownership` / `safe.directory`：命中 `knowledge/graph/E101.kv`（HMDFS UID 映射 + 系统级 `safe.directory=*` 方案）。**本条目不重复**：E101 面向系统级全局配置；本条目面向**测试作用域精确 wrapper（禁止 `*`）+ --basetemp + HOME/XDG 隔离**，并补充 pytest 临时目录所有权维度，二者方案与适用边界不同。
- `basetemp` / `uid mapping` / `挂载层`：无既有条目覆盖。
- 结论：本条目（E256 draft）为新增独立主题，不与现有条目重复；E217 正式条目为 conan-recipe 主题，与本条目无关。
