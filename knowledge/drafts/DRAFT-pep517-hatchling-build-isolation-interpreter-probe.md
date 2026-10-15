# DRAFT — PEP 517 后端解析 + G2 残缺解释器下的上游测试可运行性判定

> 拟提升编号：E550（最终编号由知识库主编确认）
> 来源：terminado 0.18.1 适配（2026-10-13，鸿蒙 PC 真机）

## 错误特征

三类互相独立的报错，指向两个不同技术点：

```
# 1) 关掉 build isolation 后，pip 找不到构建后端
pip._vendor.pyproject_hooks._impl.BackendUnavailable:
  ModuleNotFoundError: No module named 'hatchling'

# 2) 上游测试是 pytest 风格，stdlib unittest 无法收集
ImportError: Failed to import test module: basic_test
ModuleNotFoundError: No module named 'pytest'

# 3) 选了残缺解释器跑测试
某解释器 -m pytest → ModuleNotFoundError / 无法 fork 子进程
```

## 两个必须分开的技术点

### 点一：PEP 517 后端解析交给 pip 隔离

上游 `pyproject.toml` 声明构建后端（terminado 用 `hatchling.build`，要求 `hatchling>=1.5`）。
给 pip 传 `--no-build-isolation` 时，pip 会从**构建解释器的 site-packages** 导入后端；
构建机解释器通常没有它，直接 `BackendUnavailable`。

正确做法：**保留 build isolation**（pip 默认行为），由 pip 从社区索引
（`pypi.cnb.cool`）自动拉取 backend。

### 点二：上游测试用功能探针选解释器

上游 `tests/basic_test.py` 是 **pytest 风格**——模块级 `import pytest`，并用 `timeout` marker。
stdlib `unittest discover` 连"收集"都做不到（`Failed to import test module`）。

选解释器时有三个真实约束：

1. **`sys.executable` 不可信**：构建机可能是残缺解释器（G2：hnp python3 无 pytest
   且**装不了**包），而 `~/usr/local/bin/python3` 完好。
2. **仅 `import` 探测不够**：`lib-dynload` 里可能是非本机架构编译的 `.so`，
   `import select` 也会失败；必须做**功能探针**（实际 fork 子进程、实际 openpty）。
3. **Conan 依赖 payload 不在解释器 site-packages 里**：上游测试要
   `import tornado, ptyprocess`，而它们的 payload 只在依赖包的
   `package_folder/lib/pythonX.Y/site-packages`，必须显式加进探针的 `PYTHONPATH`。

## 关键副产物：退出码判断的两处死代码

上游测试**无论成败都要能被看见**，但两种常见写法都会让失败静默：

| 写法 | 问题 |
|------|------|
| `self.run("... \| tail -30")` | 管道返回 **tail** 的退出码（恒 0），`if r != 0` 永不触发 |
| `self.run("...")` 后 `if r != 0` | Conan 2 的 `run()` 默认 `ignore_errors=False`，非零退出**直接抛 ConanException**，`if` 分支不可达 |

正确做法：`self.run(cmd, ignore_errors=True)` 后判断返回值，或改用
`subprocess.run(...).returncode`。

## 解决方案

```python
# 1) 构建：保留 build isolation（不要加 --no-build-isolation）
self.run(f'"{python3}" -m pip wheel --no-deps -w "{wheel_dir}" .')

# 2) 上游测试：功能探针选解释器 + 依赖 payload 进 PYTHONPATH
def _test_interpreter(self):
    payload_dirs = []
    for dep_name in ("tornado", "ptyprocess"):
        try:
            folder = self.dependencies[dep_name].package_folder
        except Exception:
            folder = ""
        if folder:
            payload_dirs.append(folder)
    env = dict(os.environ)
    if payload_dirs:
        env["PYTHONPATH"] = os.pathsep.join(payload_dirs + ...)

    for cand in ("python3", "python3.12", "python"):
        path = shutil.which(cand)
        if not path:
            continue
        probe = ("import pytest, tornado, ptyprocess\n"
                 "import subprocess,sys\n"
                 "subprocess.run([sys.executable,'-c','pass'])\n")
        try:
            r = subprocess.run([path, "-c", probe], capture_output=True,
                               timeout=60, env=env)
            if r.returncode == 0:
                return path
        except (OSError, subprocess.SubprocessError):
            continue
    return None   # 无法运行 → 调用方如实记 NOT RUN，不计 PASS
```

## 验证

```bash
# 后端声明
grep -E "build-backend|requires" pyproject.toml

# 功能探针（含依赖 payload）
PYTHONPATH="<tornado_pkg>:<ptyprocess_pkg>" \
  ~/usr/local/bin/python3 -c "import pytest, tornado, ptyprocess; import subprocess,sys; subprocess.run([sys.executable,'-c','pass'])"

# 真机实测：terminado 上游 7 passed / 2 skipped（真实运行，非伪造）
```

## 推广价值

覆盖所有**非 setuptools 后端**的纯 Python 包（hatchling / flit_core / poetry-core /
PDM backends），以及**上游测试依赖 pytest + Conan 依赖**的 Python 包。
G2（hnp python3 stdlib 残缺、无法装包）是这台设备的常态，不是个例。
