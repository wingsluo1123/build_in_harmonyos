# vit 2.3.4 适配说明（HarmonyOS PC / ohos-aarch64）

## 1) 身份与源

- 上游：`https://github.com/vit-project/vit`（版本 **2.3.4**，与平台清单一致；版本取自 `vit/version.py`）
- 源：PyPI sdist `vit-2.3.4.tar.gz`（平台 pip 镜像直链），sha256
  `346a210aa0de754cf7adaf73723bf7d2cc8ee754eeb785eb18370d33f74e5ce2`，73,363 字节，187 个文件
- 它做什么：Taskwarrior 的全屏终端界面 —— 任务列表浏览、按项目/标签/日期筛选、快捷键操作，
  支持自定义主题与列；数据由 Taskwarrior 提供。

## 2) 构建与安装

```
# ① 补丁 0001（见 §3）
pip install --target <包>/python "tasklib>=2.4.3" "urwid>=2.1.2"
pip install --no-deps --target <包>/python .
# 按 entry_points vit=vit.command_line:main 生成 <包>/bin/vit
```

产物：`bin/vit`、`python/vit/` + 随包依赖（tasklib、urwid）、`licenses/LICENSE`。

## 3) 补丁 0001：导入期 `curses.setupterm()` 要能降级

`vit/util.py` 在**模块级**直接调用：

```python
curses.setupterm()
e3_seq = curses.tigetstr('E3') or b''
clear_screen_seq = curses.tigetstr('clear') or b''
```

而**无 terminfo 数据库**的环境（容器/CI/无终端）里这会抛
`_curses.error: setupterm: could not find terminfo database` → 连 `import vit` 都失败，
上游 `test/` 两个文件在**收集阶段**就整批报错。

补丁把它包进 `try/except curses.error`，失败时把两个序列降级为空（只有真正清屏退化为无操作）：
语义不变、上游用例一行未改，且**同时修复运行时**在无终端环境下的可导入性。

## 4) 测试环境的三处适配（不改上游用例）

1. 按属主挑选 `TMPDIR`（pytest 的 `tmp_path` 校验属主，HMDFS 上构建目录属主不同）；
2. 清 `XDG_CACHE_HOME`/`XDG_CONFIG_HOME`（避免绕过用例 monkeypatch 的 HOME）；
3. 补 `/system/bin` 到 PATH（用例若 spawn 系统命令时可用）。

## 5) 测试

- **上游用例（真跑）**：`test/` 共 10 个 → 本地 `10 passed`（**10/10，100%**），用例内容未改。
- **消费者校验**：`test_package/check_vit.py` **6 项**（全部离线）→
  `checks=6 fails=0 skips=0 / RESULT: PASS`，含 `vit --help` 用法输出与**核心组件真实调用**
  （ListBatcher 分批 + 颜色映射）。

## 6) 实测（本地 conan create）

`rc=0`；上游 `10 passed`；消费者 6/6 通过。
