# sip 6.16.1 — HarmonyOS PC 适配说明

## 包性质

sip 6.x 是**纯 Python**（与 4.x 系列不同）：sdist 为 `py3-none-any`，内容为
`sipbuild/`——即**生成 C/C++ 绑定并编译成扩展模块**的工具本身。包自身无需编译，
故按 `python-require` 打包，直接 copytree 到 site-packages（packaging/python-magic
同款做法）。

## 两个 OHOS 关键点

### 1. 可绕过 setuptools_scm

上游 `pyproject.toml` 里 `setuptools_scm` 只出现在**构建期**声明：

```toml
[build-system]
requires = ["setuptools>=77", "setuptools_scm>=8"]
build-backend = "setuptools.build_meta"
```

而 sdist **已自带**生成好的 `sipbuild/_version.py`（`__version__ = '6.16.1'`），
版本信息无需 VCS 插件即可获得——这正是「直接 copytree」能成立的原因。

### 2. 上游测试需预加载 libpython（否则全灭）

上游 `test/` 套件不是单纯 import：`conftest.py` 会为**每个测试目录现场编译
真实 C++ 扩展模块**再导入。在本平台上：

```
ImportError: Error relocating .../abstract_module.cpython-312-aarch64-linux-ohos.so:
             PyMem_Free: symbol not found
```

原因：解释器可执行文件未导出 CPython API（`llvm-nm -D python3` 查无 `PyMem_Free`），
且这些模块的 `DT_NEEDED` 不含 libpython。解法是预加载解释器共享库：

```bash
LD_PRELOAD=<prefix>/lib/libpython3.12.so
```

### 3. clang 15 的 narrowing 报错

`test/module_attrs` 生成的 C++ 以 `signed char` 初始化 `char`，clang 15 将
`-Wc++11-narrowing` 视为硬错误，**46 个用例全灭**（上游面向 GCC/MSVC，仅警告）。
解法：跑测试时 `CXXFLAGS="-Wno-c++11-narrowing"`，实测该目录转为 46 passed。

## 测试结果（实测）

```
415 passed, 33 skipped in 220.53s
```

| 项 | 值 |
|---|---|
| 上游用例总数 | 448（415 passed + 33 skipped） |
| 通过 | **415** |
| 失败 | **0** |
| 跳过 | 33（该平台不适用/需特定 ABI） |

命令（配方 `build()` 内执行）：

```bash
LD_PRELOAD=<libpython3.12.so> CXXFLAGS=-Wno-c++11-narrowing \
    python3 -m pytest test/ -q --basetemp=/data/storage/el2/base/cache/sip-bt
```

## CLI

上游 `[project.scripts]` 六个入口，配方生成对应 `bin/` 脚本：

```
sip-build  sip-install  sip-wheel  sip-sdist  sip-module  sip-distinfo
```

按 R38（有 bin/ 可执行即需软件级 `commands.json`），已随包提交。

## 消费关系

本包是 PyQt-builder 与 PyQt6 的构建前置：

```
PyQt6 -> PyQt-builder -> sip -> (qmake from qtbase)
```

`PyQt6` 的 `pyproject.toml` 声明 `sip >=6.15, <7`，本包 6.16.1 落在区间内。
