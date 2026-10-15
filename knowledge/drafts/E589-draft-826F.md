# E589 — CI worker 有 pip 无 setuptools：`--no-build-isolation` 下 PEP 517 后端不可导入

## 错误特征

```
RUN: python3 -m pip wheel . --no-deps --no-build-isolation -w .../wheels
ERROR: Exception:
Traceback (most recent call last):
  ...
  File ".../pip/_internal/utils/misc.py", line 721, in prepare_metadata_for_build_wheel
  File ".../pip/_vendor/pyproject_hooks/_impl.py", line 402, in _call_hook
    raise BackendUnavailable(
pip._vendor.pyproject_hooks._impl.BackendUnavailable: Cannot import 'setuptools.build_meta'
```

同一配方在开发机 W3 里**全绿**，只在 CI 的 `build()` 阶段炸——这正是本模式最迷惑人之处。

## 触发条件

- 工具链: `pip`（走 PEP 517 构建 wheel）
- 阶段: build（CI 侧的 `conan-build-test`）
- 关键参数: `--no-build-isolation`
- 环境: 构建解释器**有 pip、没有 setuptools**（Python 3.12 起解释器不再附带 setuptools）

## 根因分析

`--no-build-isolation` 的语义就是"**不要**为我建隔离环境，用当前解释器里的构建后端"。
于是 pip 必须从**当前解释器**导入 `setuptools.build_meta`；解释器里没有 setuptools，
后端就不可导入，报 `BackendUnavailable`。

本地/CI 之所以结论相反，是因为**两边跑的根本不是同一个解释器**：

| 环境 | 构建解释器（`sys.executable`） | 有 setuptools? | 结果 |
|------|------------------------------|---------------|------|
| 开发机 W3 | `/data/service/hnp/python.org/python_3.12/bin/python3.12` | ✅ | 绿 |
| CI worker | `/data/service/hnp/bin/python3`（HNP 自带，只有 pip） | ❌ | `BackendUnavailable` |

所以"W3 通过"**不能**推断"CI 的构建后端可用"——W3 验证的是另一台/另一个解释器的能力。

## 解决方案

### 推荐方案：按解释器能力择路

构建前探测 `setuptools` 是否可导入，再决定是否加 `--no-build-isolation`：

```python
has_setuptools = (
    self.run(
        f'{python} -c "import importlib.util, sys; '
        f"sys.exit(0 if importlib.util.find_spec('setuptools') else 1)\"",
        ignore_errors=True,
    )
    == 0
)
isolation = "--no-build-isolation" if has_setuptools else ""
self.run(f"{python} -m pip wheel . --no-deps {isolation} -w {dist}")
```

- 有 setuptools → 保留 `--no-build-isolation`：不联网、行为与原先逐字一致；
- 没有 → 去掉该参数，交给 pip 自建**隔离构建环境**：setuptools 装进临时 venv，
  **不污染 worker 的共享解释器**（对比"直接 `pip install setuptools`"会往共享环境里写东西）。

### 复现 CI 条件（无需第二台机器）

Python 3.12 的 `venv` **不带** setuptools，恰好与 worker 同构：

```bash
python3 -m venv /tmp/kc-venv312
/tmp/kc-venv312/bin/python -c "import setuptools"     # ModuleNotFoundError —— 同构环境已就绪
```

### 禁止做法

- ❌ 无条件保留 `--no-build-isolation`，靠"本地 W3 通过"背书
- ❌ 默认用 `pip install setuptools` 往 worker 共享解释器里装包（跨任务污染，R49 同源问题）
- ❌ 只在本地环境复现就宣布修好——必须先造出与 worker 同构的解释器再验

## 验证

```bash
python3 -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('setuptools') else 1)"; echo rc=$?
# rc=0 → 保留 --no-build-isolation；rc=1 → 去掉该参数（隔离构建）
```

实测（kitchen 1.2.6，PR #13191 CI build #84754）：以 3.12.8 的无 setuptools venv 作构建
解释器跑真实 `conan create`（profile 与 CI 相同）→ 日志打印
`setuptools missing (isolated build env)`、wheel 构建成功、`Ran 126 tests / OK (skipped=3)`、
补跑执行器 `ran=464 unexpected_failures=0 known_drift=3`、test_package 8/8、退出码 0。

## 关联条目

- 相关: E586（同为"本地复验手段本身的局限"：GNU patch 假通过 vs pip 后端不可见）
