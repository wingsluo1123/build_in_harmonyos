# portio

PortIO 是 **CPython 扩展模块**，把 x86 用户态端口 I/O（`in`/`out` 指令族）封装成
Python 函数：`outb/outw/outl(_p)/outsb/outsw/outsl`、`inb/inw/inl(_p)/insb/insw/insl`
以及端口权限申请 `ioperm/iopl`。上游单文件 C 源码 `portio.c`（403 行），无第三方
C 依赖（`setup.py` 中 `libraries = []`）。

- 上游仓库：<https://github.com/fabriziop/portio>（tag `0.6.2` → commit `6345900…`）
- 官网：<http://portio.inrim.it>
- 许可证：GPL-2.0-or-later

## 功能概述

| 类别 | 入口 |
|---|---|
| 字节/字/双字输出 | `outb`, `outw`, `outl`（及带 I/O 等待的 `_p` 变体） |
| 字符串输出 | `outsb`, `outsw`, `outsl` |
| 字节/字/双字输入 | `inb`, `inw`, `inl`（及 `_p` 变体） |
| 字符串输入 | `insb`, `insw`, `insl` |
| 端口权限 | `ioperm(from, extent, enable)`、`iopl(level)`（返回 0 或 errno） |

## OHOS 适配

| 项 | Linux x86 | HarmonyOS / aarch64（本仓适配） |
|---|---|---|
| 端口 I/O 实现 | `<sys/io.h>` 的 `outb/inb/...` | 平台无 x86 端口指令：18 个 I/O 入口抛 `portio.error` |
| `ioperm` / `iopl` | 调内核，返回 0 或 errno | 返回 `ENOSYS`(38) |
| 模块可导入性 | 是 | 是（20 个入口齐备，签名后可 dlopen） |
| 失败语义 | 需 root + `ioperm` 才可访问 | **显式失败**，不返回伪造的 0/None |

已知限制：

- aarch64 上不存在等价的用户态端口 I/O 机制；依赖 portio 做真实硬件访问的程序
  在 OHOS 上只能得到明确的 `portio.error`，无法工作。
- 上游样例 `toggle.py` 的 root 前置检查保留；非 root 环境打印提示后退出。

平台适配依据：`archives/p/portio/0.6.2/patches/0001-portio.c.patch`（按
`__i386__/__x86_64__` 架构宏选择实现，未引入 `__OHOS__` 平台宏）。

## 依赖关系

- 编译依赖：`python/3.12.9`（提供 `Python.h` 与 `libpython3.12`）；构建期另需
  setuptools wheel（纯 Python，配方按 pinned sha256 解包）。
- 运行依赖：CPython 3.12（`lib/python3.12/site-packages/portio.cpython-312-aarch64-linux-ohos.so`）。

## 版本索引

| 版本 | 状态 | 构建日期 |
|---|---|---|
| 0.6.2 | built | 2026-10-17 |
