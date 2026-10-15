# udpkg 1.21 (HarmonyOS 适配笔记)

## 概述

udpkg 是 Debian 安装程序（Debian-Installer）的微型 dpkg 前端。它是一个
轻量 C 程序（3 个源文件 + 1 个头文件），用 libdebian-installer 提供的内存
分配与 shell-执行辅助函数，用于在安装环境（micro-Debian/ramdisk）里解包、
配置、卸载 `.deb` 包，并打印目标架构/操作系统。

- 上游：https://salsa.debian.org/installer-team/udpkg
- 上游源码包：https://deb.debian.org/debian/pool/main/u/udpkg/ (1.21)
- tarball 结构：单一顶层目录 `udpkg-1.21/`，含 `debian/`（native 包）。

## 适配路径

路径 A（基础适配）。udpkg 依赖的唯一系统库是 `libdebian-installer`
（符号 `di_malloc/di_realloc/di_free/di_exec_shell_log/di_exec_mangle_status/
di_debug`），仓库已适配 `libdebian-installer/0.121`（static lib + 头文件），
因此 udpkg 直接 `requires("libdebian-installer/0.121")` 即可，无需自建
libdi 替代品。这是与 cdebootstrap/0.7.9 相同的依赖模式。

## 构建关键点

1. **无预生成 `configure`、无 `config.h.in`**：tarball 只有 `configure.ac`
   和 `makefile.in`，需 `autoreconf -i` 生成两者。同 libdebian-installer/
   cdebootstrap 的 SKILL：autoconf 用系统 `autoconf_2.72`（AUTOCONF 环境
   变量），aclocal/automake 用 ohpcd `automake/1.18` 包（tool_requires，
   PERL5LIB 指其 share）。本包 `configure.ac` **无** `AC_PROG_LIBTOOL`（纯
   C、无 .lo）——不需要 libtool tool_requirement（同 cdebootstrap）。

2. **AC_INIT 取版本走 dpkg-parsechangelog**：`configure.ac` 的
   `m4_esyscmd(dpkg-parsechangelog | perl ...)` 在环境无 dpkg 时
   `AC_INIT should be called` 报错（实测同 libdi/cdebootstrap）——配方
   `replace_in_file` 硬编码 `1.21`。

3. **makefile.in 依赖 `dpkg-architecture`**：
   `DEB_HOST_ARCH ?= $(shell dpkg-architecture -qDEB_HOST_ARCH)` 等两行在
   OHOS 无 dpkg-architecture 时返回空串——配方把这两行替换为硬编码
   `arm64` / `linux`（OHOS aarch64 对应 dpkg 架构 arm64，OS=linux）。

4. **in-source 构建**：`makefile.in` 用 `$(wildcard *.c)` 收集源文件——
   Autotools helper 的 out-of-source 布局（build-release）会因源文件不在
   构建目录而收集为空 `$(OBJS)`，链接报缺目标。因此**不设 `basic_layout`**
   （保持 default layout in-source），`Autotools(self).configure()`/`make()`
   直接在 source_folder 跑，产物 `source_folder/udpkg`。

5. **`--build=aarch64-unknown-linux-ohos` 显式传**：conan automake 的
   config.guess（新版）无法识别 HarmonyOS（cannot guess build type）——
   generate() 的 AutotoolsToolchain 配置 configure_args；同时 build()
   手动改 config.status 后直接 `./configure --build=...`（同 libdi）。

6. **config.status mktemp 沙箱限制**：同 SKILL——configure 执行前把
   `mktemp -d "./confXXXXXX"` 替换为 `${TMPDIR}/confXXXXXX`，并把
   TMPDIR 指可写目录 `/data/storage/el2/base/cache`（沙箱 /tmp 只读）。

7. **依赖 -I/-L 注入**：`AutotoolsToolchain` + `AutotoolsDeps` 双生成，
   缺 `AutotoolsDeps` 时 `debian-installer.h` file not found（conan create
   实测）。

8. **`--without-remove`**：ulink Remove 功能（DPKGCIDIR 相关 None 的
   `dpkg_remove`/`.list` 维护）依赖 dpkg 状态目录，本适配经
   configure 默认（默认开启 remove），但 OHOS 无真实 dpkg 状态文件，remove
   仅作二进制可用性验证（不实际 try）。保留默认 feature 集（debug/shell
   depends/loadtemplate 均默认开）。

## 测试

上游 tarball 无任何测试套件（无 test/ 目录、无 `make check` 目标；纯
ramdisk 工具，反编译验证依赖真 .deb 包——实测核对源码树）。test_package
做 OHOS 真机消费验证：

- `--print-architecture` 输出 `arm64`、退出码 0
- `--print-os` 输出 `linux`、退出码 0
- 无参数调用输出用法、退出码 0（源码 main 末尾 FPRINTF 用法后 return 0）
- ELF 头确认 + `--print-architecture` 支持 `UDPKG_QUIET` env 静默