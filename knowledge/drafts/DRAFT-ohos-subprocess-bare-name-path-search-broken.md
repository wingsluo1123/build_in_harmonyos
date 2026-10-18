# DRAFT — 本机 Python `subprocess` 无法按 PATH 解析裸命令名

> Status: DRAFT | Source: lru-dict/1.5.0 adaptation（preflight PF9 / `changed_files` 失败）
> Environment: HarmonyOS PC aarch64，CPython 3.12.9，Conan 2.29.1（OHOS 适配版）

## 1. 问题现象

跑 `create-pr` / `submit` 前置硬闸时，PF9 与 PF0 报错：

```
PF9 分支/路径闸 -> ERROR FileNotFoundError: [Errno 2] No such file or directory: 'git'
PF0 环境闸: 无法计算变更文件（git diff 失败: ...）—— fail-closed 拦截
```

但同一 shell 下 `git` 工作正常：

```bash
$ which git
/data/service/hnp/bin/git
$ git --version
git version 2.45.2
```

## 2. 根因实测

不是 git 的问题，也不是 PATH 缺项——是**本设备 CPython 的 `posix_spawn`
不做（或做不通）PATH 搜索**：

| 调用 | 结果 |
|---|---|
| `subprocess.run(["ls", "/"])` | ❌ `FileNotFoundError: ...: 'ls'` |
| `subprocess.run(["sh", "-c", "echo ok"])` | ❌ `FileNotFoundError: ...: 'sh'` |
| `subprocess.run(["git", "--version"])` | ❌ `FileNotFoundError: ...: 'git'` |
| `subprocess.run(["python3", "--version"])` | ❌ `FileNotFoundError: ...: 'python3'` |
| `subprocess.run(["/data/service/hnp/bin/git", "--version"])` | ✅ 正常 |
| `shutil.which("git")` | ✅ `/data/service/hnp/bin/git` |
| 自建 shim 目录（**普通文件** `git`，置于 PATH 首位） + 裸名调用 | ❌ 同样失败 |

结论要点：

1. **与命令无关**：`ls`/`sh`/`git`/`python3` 全部失败，故不是某个二进制的问题。
2. **与是否传 `env=` 无关**：`env=None` 与 `env=os.environ` 都失败。
3. **与符号链接无关**：自建 shim 是普通文件且位于 PATH 首位，仍然失败；
   说明不是「解析不了 hnp 符号链接」，而是 PATH 搜索本身失效。
4. **只有绝对路径可用**；`shutil.which()`（纯 Python 实现）反而能正确解析。

## 3. 影响面

任何 shell out **裸命令名**的 Python 代码。

具体到本仓 `scripts/ohc/preflight.py`：

- `changed_files()` → `subprocess.run(["git", "diff", ...])`
- `check_branch_and_paths()`（PF9）→ `subprocess.run(["git", "rev-parse", ...])`

因此 `run_preflight()` 在本机取不到变更文件 → 走 PF0 **fail-closed** →
本机无法 `create-pr` / `submit`。（`bash` 脚本自身不受影响，
`ci/scripts/*.sh` 里的 `git` 调用正常——bash 的 PATH 搜索是好的。）

## 4. 处置

**推荐（根治）**：调用前解析为绝对路径，或把解析封装到统一的
`run_git()` 辅助函数：

```python
import shutil, subprocess
exe = shutil.which("git") or "git"
subprocess.run([exe, *args], ...)
```

**验证用（不改工具源码）**：在验证脚本里 monkeypatch `subprocess.run`，
把裸名替换为 `shutil.which()` 的绝对路径。门禁逻辑本身原样运行，
结论仍然可信——lru-dict 适配即用此法跑通 PF1–PF9（0 findings）。

**CI 侧**：若 CI worker 的 PATH 搜索正常，则无影响；上述修复对两边都安全。

## 5. 适用边界与反例

- **适用**：本设备及同类 HarmonyOS PC 环境的 Python 调用层。
- **反例**：CI worker 上若 `subprocess.run(["git",...])` 正常，则不要为了
  「统一」而引入不必要的抽象；修复以 `shutil.which()` 兜底即可。
- **禁止**：把 `FileNotFoundError: 'git'` 判读为「仓库不存在 / 无变更文件」
  之类的 git 语义结论。那是平台的 PATH 搜索失效，按前者解读会让 PF0/PF9
  结论失真（把「有变更」当成「无变更」）。

## 6. 查重差异

正式知识 / 图谱 / 草稿四范围检索 `posix_spawn` / `subprocess` /
`FileNotFoundError` / PATH 搜索：无既有条目覆盖该平台行为，故非重复。
