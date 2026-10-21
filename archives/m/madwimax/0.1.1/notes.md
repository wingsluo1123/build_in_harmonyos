# madwimax 0.1.1 适配笔记

## 结论速览
- **上游**：`ago/madwimax`（tag **v0.1.1**，GitHub 标注语言 **C**）—— WiMAX USB 设备的用户态驱动
- **产物**：`bin/madwimax`（musl 动态 ELF64/AArch64，47552 字节）+ `licenses/COPYING`
- **依赖**：**只有一个外部依赖** `libusb/1.0.27`（上游 `configure.ac:60`
  `PKG_CHECK_MODULES([libusb1], libusb-1.0, …)`）+ 系统 pthread
- **上游测试**：**0 个** → 配方里补 `--help` / `--version` 两条断言；消费者 7 项
- **状态**：built（本地 conan create 全绿：编译 ✓ + 补的断言 ✓ + 消费者 7/7 ✓）

## 三处必须知道的坑

### 1) `configure` 硬检查 asciidoc（文档工具）
上游默认生成 man 页，`configure.ac:145` 里是**硬失败**：
```
checking for asciidoc... no
configure: error: "asciidoc not found"
```
`configure.ac:128` 提供了开关 → 加上 **`--without-man-pages`** 即可绕开（文档不是适配必需品）。

### 2) musl 与内核 uapi 头重复定义 `sockaddr_storage`（本项目最关键的一处）
```
src/tap_dev.c:30  #include <sys/socket.h>
src/tap_dev.c:31  #include <linux/if.h>        → linux/socket.h 又定义一次
.../sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'
.../sysroot/usr/include/sys/socket.h:377:8: note: previous definition is here
```
**根因**：musl 侧的 `sys/socket.h:376` 是 **`#ifndef __MUSL__`** 包裹 —— 平台已经把这处交给内核头了。
**修法**：编译时加 **`-D__MUSL__`**（配方里 `tc.extra_defines.append("__MUSL__")`），musl 就不再自定义
该结构，只剩 `linux/socket.h` 那份 → 冲突消失。**一个 -D 的补丁，不改上游源码。**

### 3) 上游是 `sbin_PROGRAMS`，`make install` 没落到 `bin/`
`src/Makefile.am:1` 是 `sbin_PROGRAMS = madwimax`，实测装完在 `p/` 下找不到 `bin/madwimax`
→ 配方 `package()` 里**显式补装一次** `bin/madwimax`（`chmod 755`），保证包内布局与 `commands.json`
约定一致。

（另：autotools 的常规两项照旧 —— `automake`/`libtool` 走 `tool_requires`；`configure` 里的
`umask 077` 必须在 autoreconf **之后**改成 022。**但本包最终不走 autoreconf**：CI 构建 #94280 曾在
autoreconf 之后卡满 1 小时墙钟被判超时（`conan create TIMED OUT after 3600s`），故源改用**自带已生成
`configure`** 的 Debian orig；它内附的 `config.sub`/`config.guess` 是 2009 年版本、认不出 aarch64
三元组（configure 直接报 `config.sub aarch64-unknown-linux-musl failed`）→ 配方在 configure 前从
conan 的 `automake` 包里取现代版本覆盖这两个脚本，**只换脚本、不重跑自举**。）

## 实测结果（本地 conan create）
```
[added tests] 产物 = <build>/build-release/src/madwimax（47552 字节）
[added tests] ① `madwimax --help` 打印用法 ✓（首行：Usage: …）
[added tests] ② `madwimax --version` rc=0，输出：madwimax 0.1.1
WARN [added tests] ③ 真实驱动功能需 WiMAX USB 设备 + TAP，本环境不执行——如实记录
[package] 已补装 bin/madwimax（源：<build>/build-release/src/madwimax）
[ok]   产物齐备：bin/madwimax 存在且可执行（47552 字节）
[ok]   ELF 头自检：真 ELF64、machine=0xB7(AArch64) ✓
[ok]   真实运行：`madwimax --help` 打印用法（rc=0）
[ok]   `madwimax --version` 有输出：madwimax 0.1.1
[ok]   许可证随包：COPYING
[ok]   证据：bin/madwimax sha256=dbd7c84f7216617c…
[ok]   运行边界：真实驱动功能需 WiMAX USB 设备 + TAP 设备，本环境不执行（如实记录）
checks=7 fails=0
RESULT: PASS
```
