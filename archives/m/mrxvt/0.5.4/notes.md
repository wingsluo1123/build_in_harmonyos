# mrxvt 0.5.4 — OHOS (aarch64) 适配记录

- 上游：https://sourceforge.net/projects/materm/ （项目名 materm，旧名 mrxvt）
- 源码：`mrxvt-0.5.4.tar.gz`，sha256 `f403ad5a908fcd38a55ed0a7e1b85584cb77be8781199653a39b8af1a9ad10d7`
  （官方归档 `https://sourceforge.net/projects/materm/files/mrxvt%20source/0.5.4/mrxvt-0.5.4.tar.gz`，HTTP 200，603978 字节）
- 主体语言：C（src/ 下 20 个 .c / .h，autotools 构建）→ 属 C/C++ 适配范围

## 构建要点

1. **AC_PATH_X 找不到 X11**。Conan 的依赖树不在系统默认路径，configure 的
   `AC_PATH_X` 无法定位 X11 头/库，直接 `AC_MSG_ERROR`。配方显式传
   `--x-includes=<libx11>/include --x-libraries=<libx11>/lib` 绕过。
2. **交叉编译期 AC_CHECK_SIZEOF 要跑测试程序**。OHOS 目标机上没有 shell 能执行
   刚编出来的 aarch64 ELF，故用 `tc.update_configure_args` 预置
   `ac_cv_sizeof_*` / `ac_cv_func_working_fork` / `ac_cv_func_setpgrp_void`，
   并显式给 `--build=x86_64-pc-linux-gnu --host=aarch64-unknown-linux-gnu`。
3. **configure 的 shebang 与 umask**。生成物 `configure` 首行是 `#!/bin/sh`，
   OHOS 上 `/system/bin/sh`（mksh）跑不动部分构造；配方把 shebang 换成
   `CONFIG_SHELL`，并把脚本里的 `umask 077` 放宽成 `umask 022`
   （HMDFS 会把 077 的目录掩码成不可进入的权限，实测建目录后无法在其中写文件）。
4. **重复符号 `macroFnNames`**。`src/rxvtlib.h` 第 820 行把枚举变量的定义
   `} macroFnNames;` 写在头文件里，多个 .c 同时 include → ld.lld 报
   `duplicate symbol`。补丁 `patches/mrxvt-fix-dup-symbol.patch` 去掉变量名，
   只保留枚举类型定义（各 .c 只读该枚举，不引用该变量）。

## 功能开关（为什么这么选）

- `--enable-xft`：保留 Xft 字体渲染，这是终端模拟器的核心能力；依赖
  libxft/2.3.8 + fontconfig/2.18.3 + freetype/2.14.3 轨道。
- `--disable-xpm --disable-jpeg --disable-png`：制品仓里 libxpm/3.5.17 依赖
  libx11/6.4.0（force 约束），与 libxft 需要的 libx11/1.8.13 冲突，
  无法共存于同一依赖图。背景图不是终端的核心能力，故放弃。
- `--disable-utmp --disable-wtmp --disable-lastlog --disable-sessionmgr`：
  OHOS 没有 utmp/wtmp/lastlog 服务，也没有 X session manager（SM/ICE 可装但无
  对端服务），打开会引 `utmp.h` / `X11/SM/SMlib.h` 缺失。
- `--enable-256colors`：rxvt 系终端的实用能力，无额外依赖。

## 验证

- 本地交叉编译：`conan create archives/m/mrxvt/0.5.4 -pr:h=ohos-aarch64-wsl
  -pr:b=ohos-aarch64-wsl` → rc=0，0 ERROR；产物 `bin/mrxvt` 为
  `ELF 64-bit LSB pie executable, ARM aarch64`，解释器
  `/lib/ld-linux-aarch64.so.1`。
- test_package：`test_mrxvt.sh` 对打包出的 `bin/mrxvt` 做 8 条断言（安装/可执行、
  ELF class、ELF machine、`-h` 横幅与选项表、无 DISPLAY 的报错路径与退出码）。
  交叉编译宿主机（x86_64）上加载器无法启动 aarch64 ELF（rc=126/127，
  `Error relocating .../libX11.so.6: __fd_chk`），此时 5 条运行期断言记为
  SKIP 并打印原因——不计为 PASS，避免把跑不了的测试当绿。
- 上游测试：tarball 无 tests 目录，Makefile.am 无 check 目标，上游测试为空集
  （见 test_package/MANIFEST.yml 的清点说明）。

## 已知限制

- 仅在本机 WSL 交叉环境验证；OHOS 目标机上尚未实跑 `mrxvt`（需要 X server）。
  CI 在 aarch64 OHOS runner 上会把 5 条运行期断言真正跑起来。
- 背景图（XPM/JPEG/PNG）与 tinting 未启用，见上文依赖冲突说明。
