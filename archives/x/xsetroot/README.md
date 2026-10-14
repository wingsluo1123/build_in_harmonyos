# xsetroot

## 软件描述

`xsetroot` 是 X.Org 的**根窗口属性设置工具**：用于设置 X 显示（display）根窗口的
背景、光标与名称。典型用途是在轻量窗口管理器/无桌面环境下定制桌面外观。

功能选项（上游完整集合）：

| 选项 | 作用 |
|---|---|
| `-solid <color>` | 用纯色填充根窗口 |
| `-gray` / `-grey` | 整个背景设为灰色 |
| `-bitmap <filename>` | 用指定位图文件作为背景 |
| `-mod <x> <y>` | 使用网格状图案 |
| `-cursor <cursorfile> <maskfile>` | 自定义指针光标（文件形式） |
| `-cursor_name <name>` | 使用光标字体中的指针 |
| `-xcf <cursorfile> <cursorsize>` | 从 Xcursor 文件加载光标 |
| `-bg` / `-fg` / `-rv` | 设置背景色 / 前景色 / 交换前后景 |
| `-name <string>` | 设置根窗口名称 |
| `-def` / `-default` | 重置未指定的属性 |
| `-display <display>` | 指定要连接的服务器 |
| `-version` / `-help` | 打印版本 / 帮助 |

上游项目：<https://gitlab.freedesktop.org/xorg/app/xsetroot>

## 版本信息

- 当前版本：`1.1.3`（与上游 `xsetroot 1.1.3` 一致，`PACKAGE_STRING` 可验证）
- 源码：<https://www.x.org/releases/individual/app/xsetroot-1.1.3.tar.xz>
  （X.Org 官方 individual release 源）
- 许可证：MIT（X.Org 标准许可，`COPYING`）

## OHOS 适配

- **无代码补丁**：上游源码零修改（`patches: []`）；适配只做平台构建适配与配方侧处理。
- 上游 tarball **自带预生成的 `configure`**（Autoconf 2.71），无需 autoconf/xorg-macros 引导。
- 采用仓库内已验证的 HarmonyOS Autotools 交叉编译模式（与 `libxcursor` / `libxmu` 一致）：
  - `--host=aarch64-linux-ohos` 交叉编译模式（原生 `--build == --host` 模式会尝试**运行** conftest，OHOS 沙箱无法执行）。
  - 上游 `configure` 生成辅助目录时用 `umask 077`，在 OHOS worker 上会导致后续 `make` 无权读取；故经构建目录内的副本把 `umask` 改为 `022` 后再执行。
  - `make -j1` 通过 `/system/bin/sh` 运行。
- **xbitmaps 数据文件 shim**：`configure.ac` 要求 `PKG_CHECK_MODULES(... xbitmaps ...)`，但 OHOS 制品仓**未发布** `xbitmaps`。`xsetroot` 实际只需要其中的 `<X11/bitmaps/gray>`（一个 `#include`，非链接库），因此把 canonical 的 87 字节数据文件内置于配方 `files/`，并把其 include 根加入 `CPPFLAGS`。该做法与仓库中已合并的 `motif/2.3.8` 完全一致；内置字节与上游 `xbitmaps-1.1.3/gray` **逐字节相同**（sha256 `b4df654f…`）。
- 产物是**命令行程序**，故软件级提供 `commands.json`（R38/L0k）。

## 产物

| 路径 | 说明 |
|---|---|
| `bin/xsetroot` | 可执行程序（aarch64/OHOS） |
| `share/man/man1/xsetroot.1` | 上游 man page |
| `licenses/COPYING` | 上游 MIT 许可证原文 |

## 使用方式

```sh
# 设置纯色背景
xsetroot -solid steelblue

# 设置灰色背景（内置 gray 位图）
xsetroot -gray

# 设置根窗口名称
xsetroot -name "HarmonyOS Desktop"
```

> 需连接可用的 X 服务器；`-version` / `-help` 无需显示服务器即可运行。

## 测试

上游 **不含测试套件**（`Makefile.am` 无 `TESTS` / `check_PROGRAMS`）。适配后由
`test_package/` 提供消费者端到端用例（4 个具名用例、共 23 项检查），详见版本目录
`test_package/MANIFEST.yml` 与 `notes.md`。

## 版本索引

| 版本 | 状态 | 构建日期 |
|---|---|---|
| `1.1.3` | built | 2026-10-12 |
