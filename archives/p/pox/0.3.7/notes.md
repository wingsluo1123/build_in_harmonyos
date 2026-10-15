# pox 0.3.7 — OpenHarmony PC 适配笔记

## 概览

| 项 | 值 |
|---|---|
| 包名 | pox |
| 版本 | 0.3.7 |
| 上游 | uqfoundation/pox（Mike McKerns，"utilities for filesystem exploration and automated builds"） |
| 源码 | `https://files.pythonhosted.org/packages/44/58/4385741dea1d74fe9dfed7ff42975266634ef8000f2c8e96717079c916b1/pox-0.3.7.tar.gz` |
| sha256 | `0652f6f2103fe6d4ba638beb6fa8d3e8a68fd44bcb63315c614118515bcc3afb` |
| 构建系统 | setuptools（`pyproject.toml` + `setup.py`） |
| 产物 | `lib/python3.12/site-packages/pox/`（纯 Python，无二进制） |

## 软件简介

pox 是 uqfoundation 系列（pathos / dill 等）的基础工具库，提供两类能力：

- **shell/文件系统**：`mkdir`、`walk`、`find`、`which`、`where`、`shelltype`、
  `homedir`、`rootdir`、`minpath`、`shellsub`、`expandvars`、`env` 等
- **高层工具**：`pattern`、`getvars`、`convert`、`replace`、`index_join`、
  `findpackage`、`remote`/`parse_remote`、`select`/`selectdict` 等

**注意与同名的 Noxrepo/pox 区分**：那是 Python SDN/OpenFlow 控制器，与本包
（PyPI `pox`，uqfoundation）是完全不同的软件。

## 构建要点

### 1. 纯 Python 分发的 package_type

Conan 2 没有 `python` 类型，而 `library` 会要求 shared/static 产物
（`shared` 选项校验）。沿用仓内纯 wheel 包先例
（snakeviz / aiohttp-fast-zlib）：`package_type = "build-scripts"` +
settings 四项齐全（否则 W3 L0p 拦截）。

### 2. 构建与打包

```
pip wheel . --no-deps -w dist     # 纯 Python，无外部构建依赖
# 解包 wheel（zip）到 <pkg>/lib/python3.12/site-packages
```

消费者经 `package_info()` 的 `runenv_info.prepend_path("PYTHONPATH", ...)`
直接 `import pox`；不产生 `bindirs`，故无需软件级 `commands.json`（R38）。

## 上游测试（R51）

sdist 自带 pytest 套件，两个模块、两个 test 函数（内部各含大量断言）：

| 文件 | 内容 |
|---|---|
| `pox/tests/test_utils.py` | 高层工具断言（pattern/getvars/expandvars/convert/…/homedir/username） |
| `pox/tests/test_shutils.py` | shell 工具断言（shelltype/homedir/rootdir/sep/mkdir/walk/where/env/minpath/which/find/shellsub） |

`build()` 内真实运行 `python3 -m pytest pox/tests -q`。

### 唯一一处平台适配（补丁 0001）

上游 `test_shutils` 中：

```python
folders = walk(rootdir(), '*', recurse=False, folders=True, files=False)
assert len(folders) > 0
```

本平台上 `rootdir()` 返回 `'/'`，而沙箱**拒绝列举根目录**（`EACCES`，
实测 `os.listdir('/')` 抛 `Permission denied`），因此该断言在任何环境都
不可能成立——这是平台限制而非 pox 缺陷。补丁把 walk 目标改为
`os.getcwd()`（可列），**断言本身与 `walk(folders=True)` 的语义不变**。

此外 `os.getlogin()` 在本沙箱不可用、`$USER` 为数字，但上游仅将 `username()`
与 `homedir()` 自身比较，故无需改动。

## test_package 设计（消费者视角）

`test_pox.py` 在 `env="conanrun"` 下（PYTHONPATH 指向包产物）执行：

| # | 断言 | 证明什么 |
|---|---|---|
| 1 | `POX_PACKAGE_ROOT` 在 `pox.__file__` 父链上，版本 `0.3.7` | 导入确实来自本包 |
| 2 | `expandvars("$POX_CONSUMER_PROBE") == "harmony"`、`env()` 含该变量 | 环境读取真实生效 |
| 3 | `mkdir` 建目录、`walk(folders=True)` 回查、`find` 命中临时文件 | 文件系统真实工作 |
| 4 | `pattern`/`minpath` 的文档化行为 | 纯逻辑正确 |

## 已知平台限制

- 根目录 `/` 不可列举（EACCES）——影响任何依赖遍历 `/` 的上游代码。
- 无 `bindirs`：本包只交付可导入模块。
