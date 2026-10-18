# vint 0.3.21 适配说明（HarmonyOS PC / ohos-aarch64）

## 1) 身份与源

- 上游：`https://github.com/Vimjas/vint`（tag **v0.3.21**，与平台清单 `vint 0.3.21` 一致）
- 源：`https://codeload.github.com/Vimjas/vint/tar.gz/refs/tags/v0.3.21`
  （sha256 `ebbb4ffd790324331aabf82d0b8777db8ce41d72d7c4c1c328bc099359ae06d6`，96,747 字节，349 个文件）
- 它做什么：静态分析 Vim script（viml），报告语法与风格问题（未定义变量、不推荐的命令、
  缩进/空白、缺失 `scriptencoding` 等），可接入 CI 对 `.vim` 脚本做 lint。

## 2) 构建与安装

```
# 运行时依赖（走平台 pip 镜像；注意 setuptools 必须 <81，见 §3.1）
pip install --target <包>/python PyYAML ansicolor chardet "setuptools<81"
# 本体：--no-deps（见 §3.2）
pip install --no-deps --target <包>/python .
# 按上游入口生成启动脚本（见 §3.3）
<包>/bin/vint → console_scripts: vint = vint:main
```

产物：`bin/vint`（128 字节启动脚本）、`python/`（vint 本体 + 随包依赖）。

## 3) 处理过的五处问题（都是环境/依赖版本带来的，未改上游源码与用例）

### 3.1 `setuptools<81`（pkg_resources）

vint 在 `vint/linting/cli.py:4` 直接 `import pkg_resources`（用它读自身版本），却**没有把
setuptools 声明**在 requirements 里。更麻烦的是**新版 setuptools（实测 84.0.0）已移除
`pkg_resources`** → 装最新版仍报 `ModuleNotFoundError: No module named 'pkg_resources'`，
连 `import vint` 都失败。钉到 80.x 后实测正常。

### 3.2 本体用 `--no-deps`

`setup.py` 里 append 了 `enum34` / `pathlib` / `typing` 三个 **py2 backport**。在 py3.12 下装上
`pathlib` 会遮蔽标准库同名模块 → 必须用 `--no-deps` 安装本体，依赖单独装。

### 3.3 命令脚本要自建

`pip install --target` 会把 console script 写到**目标根目录**，而那里已经有同名的 `vint/` 包目录
→ pip **静默不生成**该脚本（`<包>/python` 下只有 `chardet` 等其它脚本）。另外 `vint` 没有
`__main__`，所以 `python -m vint` 也不可用。处置：按上游 `entry_points` 自己生成 `bin/vint`。

### 3.4 验收测试的三个环境前提

`test/acceptance/test_cli.py` 直接以 `['bin/vint', …]` 调**仓库内的启动脚本**，因此需要：

1. `bin/vint` 的**可执行位**（归档里是 775，下载/解包后可能丢失）→ 构建时显式 `chmod 755`；
2. 该脚本 shebang 是 **`#!/usr/bin/env python`**，而本环境只有 `python3` → 实测
   `env: exec python: No such file or directory` → 在测试环境造一个 `python` shim 并前置到 PATH；
3. **静音 Python 警告**（`PYTHONWARNINGS=ignore`）：验收测试断言输出**以 `vint ERROR:/DEBUG:` 开头**，
   而 setuptools 的 deprecation 警告、py3.12 的 `SyntaxWarning: invalid escape sequence` 会混进同一
   输出流 → 断言必挂。

> 这三条只作用于**测试环境**，不改上游源码与任何用例。

## 4) 测试

- **上游用例（真跑）**：`272` 个（49 个 `test_*.py`，unit / integration / acceptance）→
  本地 `271 passed, 1 skipped`，即 **271/271（100%）**（那 1 个 skip 是上游自身标注的，非适配引入）。
  上游 `tox.ini` 把 pytest 钉在 **3.3.2**（2018 年，py3.12 装不上）→ 用**现代 pytest 跑同一套用例**，
  这是一处**如实说明的偏离**。
- **消费者校验**：`test_package/check_vint.py` **7 项**（全部离线）→
  `checks=7 fails=0 skips=0 / RESULT: PASS`，含一条**真实 lint 行为**：
  故意写坏的 vim script（未闭合的函数调用）被报出 `unexpected token`（rc=1）。

## 5) 实测（本地 conan create）

`rc=0`；上游 `271 passed, 1 skipped`；消费者 7/7 通过。
