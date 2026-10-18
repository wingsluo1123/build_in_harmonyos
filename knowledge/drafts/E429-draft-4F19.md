# E429 — 终端/子进程类包在受限环境上的三个通用坑

本轮适配 piep（流编辑）与 vit（Taskwarrior 终端界面）时，三个坑都表现为"上游测试整批挂掉"，
但根因都不在被测业务代码。

## 坑 1：`Popen(['echo'])` 直接 FileNotFoundError

Python 3.12 的 `subprocess` 在本平台走 `os.posix_spawn`，而 posix_spawn（非 posix_spawnp）
**不做 PATH 检索**。实测对照：

```
Popen(['echo','hi'])                 # FileNotFoundError ✗
Popen(['/system/bin/echo','hi'])     # OK ✓
Popen('echo hi', shell=True)         # OK ✓
os.spawnvp(os.P_WAIT,'echo',[...])   # OK ✓
```

改 `PATH` 没用（检索这步没发生）。解法：spawn 前 `shutil.which` 解析成绝对路径，
打成 `patch_type: portability` 的小补丁 —— 同时修好运行时 `sh()`/`spawn()`。

## 坑 2：pytest 的 `tmp_path` 校验属主

```
OSError: The temporary directory ... is not owned by the current user
```

HMDFS 上构建目录属主是映射后的另一 uid，而 `tmp_path` 校验"属主 == 当前用户"。
解法：按属主挑选可写 TMPDIR（专用临时挂载点优先，如 `/data/storage/el2/base/cache`），
不要用构建目录下的临时路径。

## 坑 3：导入期 `curses.setupterm()` 在无 terminfo 环境必抛

```
_curses.error: setupterm: could not find terminfo database
```

`vit/util.py` 在模块级直接 `curses.setupterm()`，于是无终端/无 terminfo 的环境里连 `import vit` 都失败
（urwid 这类 TUI 库的导入链同样受影响）。解法：把 setupterm 包进 `try/except curses.error`，
失败时把清屏序列降级为空 —— 只有真正清屏退化为无操作，其余功能不受影响。

```python
try:
    curses.setupterm()
    e3_seq = curses.tigetstr('E3') or b''
    clear_screen_seq = curses.tigetstr('clear') or b''
except curses.error:
    e3_seq = b''
    clear_screen_seq = b''
```

> 注意：这类补丁要**同时当作运行时修复**看待 —— 只在测试侧设环境变量，用户拿到的包在无终端环境仍会崩。

## 禁止做法

- ❌ 假设 `Popen` 一定按 PATH 找命令、假设 `setupterm` 一定有数据库（`forbid_1`）。
