# E429 — 老项目在新 Python 环境下的三处打包/测试坑

以 **vint 0.3.21**（2018 年的项目）在 py3.12 上适配为例。三类失败**都是环境/依赖版本失配**，
上游源码与用例一行未改。

## 坑 1：`ModuleNotFoundError: No module named 'pkg_resources'`

```
vint/linting/cli.py:4: import pkg_resources
ModuleNotFoundError: No module named 'pkg_resources'
```

- 代码直接用 `pkg_resources`（setuptools 提供）读自身版本，却**没有在 requirements 里声明** setuptools；
- 更麻烦的是**新版 setuptools 已移除 `pkg_resources`** —— 实测装 `setuptools 84.0.0` 仍然报错。

```bash
pip install --target <pkg> "setuptools<81"     # 80.x 仍带 pkg_resources
```

## 坑 2：`pip install --target` 静默不生成命令脚本

`pip install --target=<pkg>` 会把 console script 写到**目标根目录**。若那里已有**同名包目录**
（vint 的包就是 `vint/`），脚本会**静默跳过**（其它脚本如 `chardetect` 照常生成）→
构建"成功"但**没有可执行入口**。

处置：按 `setup.py` 的 `entry_points` 自己生成：

```python
launcher = os.path.join(pkg, "bin", "vint")
open(launcher, "w").write('#!/bin/sh\nexec "%s" -c "import sys; from vint import main; sys.exit(main())" "$@"\n' % python)
os.chmod(launcher, 0o755)
```

顺带记住：**没有 `__main__` 的包，`python -m <mod>` 是不可用的**（本例 `python -m vint` 直接报
`'vint' is a package and cannot be directly executed`）。

## 坑 3：验收测试的"输出前缀断言"被警告污染

`test/acceptance/test_cli.py` 断言被测命令输出**以 `vint ERROR:` 开头**，实际输出却是：

```
… UserWarning: pkg_resources is deprecated as an API …        ← setuptools 80.x
… SyntaxWarning: invalid escape sequence '\+' …               ← py3.12 对老代码的警告
vint ERROR: nothing to check
```

→ 前缀断言必然落空。处置是**静音环境噪声**，而不是改用例：

```bash
export PYTHONWARNINGS=ignore
```

同源还有两个小前提：

1. 仓库内启动脚本 `bin/vint` 的可执行位可能在下载/解包后丢失 → `chmod 755`；
2. 它的 shebang 是 `#!/usr/bin/env python`，而新环境只有 `python3` → 实测
   `env: exec python: No such file or directory` → 造 `python` shim 并前置 PATH（不改上游文件）。

## 效果

| 阶段 | 结果 |
|---|---|
| 仅装依赖（未钉 setuptools） | 收集阶段 **39 errors**，`import vint` 失败 |
| 钉 `setuptools<81` | 收集通过，`263 passed / 8 failed`（8 个全是验收测试） |
| + `python` shim | `268 passed / 3 failed`（剩"输出前缀"类） |
| + `PYTHONWARNINGS=ignore` | **271 passed, 1 skipped**（上游自身 skip）|

## 禁止做法

- ❌ 用删用例/放宽断言来"通过"（`forbid_1`）—— 掩盖真实兼容性差异；
- ❌ 假设 `pip install --target` 一定会生成命令脚本（`forbid_2`）—— 交付一个没有入口的包。
