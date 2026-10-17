# xfractint 20.4.10 — HarmonyOS PC 移植说明

## 版本映射

- 包版本 `20.4.10` = 上游 `xfractint-20.04p10`（2010 年发布，C 语言，
  顶层目录 `xfractint-20.04p10/`）。
- 上游主页 <http://www.fractint.org/>；官方归档
  `http://www.fractint.org/ftp/old/linux/xfractint-20.04p10.tar.gz`。
- SHA256：`0574540d4ab87e41c4fd128a14c0407e160dd6e312764d3d55554f62abc35781`
  （设备侧实测下载后 `sha256sum` 核验一致；设备可直连官方 http 归档，
  未启用 Debian 镜像回退）。

## License

自定义 Fractint license（源码 `read.me`："Copyrighted freeware."），
Debian 归档于 non-free。配方声明 `LicenseRef-Fractint`，license 文本
随包（`licenses/LICENSE.readme`，即上游 `read.me`）。

## 构建方式

上游是手写递归 GNU Make（顶层 + `common/` + `unix/`），无 autoconf/cmake。
全部适配通过 make 命令行变量覆盖完成，源文件只打两个最小补丁：

| 覆盖项 | 值 | 理由 |
| --- | --- | --- |
| `CC` | HNP clang | 上游硬编码 `/usr/bin/gcc`，设备无 gcc |
| `CFLAGS` | `-I./headers -DXFRACT -DNOBSTRING -DBIG_ANSI_C -DLINUX -fno-builtin -fcommon -O2` + libx11/xorgproto 的 `-I` | 完整替换上游 CFLAGS；`-fcommon` 必需（clang 默认 `-fno-common`，本代码库大量跨文件 tentative definition，Debian 补丁集同款修复）；`-DNOBSTRING` 保持上游 Linux 默认 |
| `LIBS` | libx11 闭包的 `-L` + `-Wl,-rpath-link,<全闭包>` + `-lX11 -lm` | 顶层链接规则没有 `$(LDFLAGS)`，搜索路径必须写进 `LIBS`（显式链接闭包，不依赖默认搜索路径） |
| `PREFIX` | `<package>/share/xfractint` 的包根 | `SRCDIR`（fractint.hlp 与数据文件位置）按包布局烘焙，包内自洽 |

nasm 路径保持上游默认关闭（`AS=foo`）；tarball 自带的预编译 x86
`unix/calmanfx.o` 不会被使用。`HAVESTRI` 保持不定义（musl 下由
`unix.c` 的 `#ifndef HAVESTRI` 本地实现 stricmp）。

构建期会原生编译并运行帮助编译器 `./hc /c` 生成 `fractint.hlp`
（设备原生编译，无交叉问题）。

## 补丁清单（patches/）

1. `0001-unix.c-fcntl-include.patch`：`unix/unix.c` 补
   `#include <fcntl.h>`——`O_RDONLY` 未声明是硬错误（musl 头文件不透传）。
2. `0002-editpal-getw-musl.patch`：`common/editpal.c` 在
   `#ifndef __GLIBC__` 下提供 legacy `getw()`（musl 不提供，glibc 才有），
   `fread` 实现，语义与 glibc 一致；链接期唯一缺失符号。

其余 Debian 1030/1040 涉及的隐式函数声明在 clang 15 下仅告警，
不产生链接失败，按"最小补丁"原则未引入。

## 依赖

- `libx11/1.8.13.1`（ohpcd 已发布）：唯一必需外部库依赖，传递闭包
  libxcb/libxau/libxdmcp/xtrans 由该包配方携带。
- `xorgproto/2025.1`（显式 require）：`X11/X.h`、`Xatom.h` 等协议头文件
  所在包。教训（同 xworld manifest）：作为传递依赖时不会出现在本配方
  的依赖遍历里，必须显式声明，否则 `Xlib.h` 找不到 `X11/X.h`。
- 未添加 ncurses（上游可选、默认关）、zlib/png（GIF 编解码自带）。

## 运行期数据定位

`unix.c:findpath()` 的查找链：绝对路径 → `$FRACTDIR/文件` → 编译期
`SRCDIR/文件` → `./文件`。Conan 2.29 本地缓存构建期 package_folder 位于
`p/b/<hash>/p` 暂存位，包定稿后会被迁移，烘焙的 SRCDIR 只是兜底。
配方在 `package_info()` 导出 `runenv_info` 的 `FRACTDIR` 指向
`<package>/share/xfractint`，消费方（含 test_package 的 conanrun 环境）
始终拿到正确的最终包路径。

## test_package（无显示冒烟，E530/E527/E463）

设备无任何显示后端，X11 客户端只能验证"无显示优雅失败"路径：

1. 包内二进制存在且为 aarch64 ELF；
2. `readelf -d` 含 `NEEDED libX11.so.6`；
3. `readelf -h` 为 PIE；
4. `unset DISPLAY` 后真实执行：退出码 255（上游 `exit(-1)`）且 stderr
   含 `Could not open display`（`unix/xfcurses.c:Open_XDisplay` →
   `error_display`）；加载器缺库/重定位失败任何情况下判 FAIL。

conanfile 的 `test()` 显式 `self.run(...)`（经验仓 libxrender-0.9.12
round0 教训），环境用 `conanrun`（VirtualRunEnv 提供依赖 lib 目录的
`LD_LIBRARY_PATH`）。

## 上游测试情况（NO_UPSTREAM_TESTS）

上游没有任何自动化测试套件，证据清点：

- 顶层 `Makefile` 目标：`xfractint`、`fractint`、`tar`、`tidy`、`clean`、
  `install`、`uninstall`、`fractint.hlp`、`doc`、`copy`——无 test/check。
- `common/Makefile`、`unix/Makefile` 目标：`all`、`tidy`、`clean`、
  `copy` 及对象文件规则——无 test/check。
- 源码树无 `tests/`、`test/`、`check/` 目录，无 CI 配置（无
  `.github/`、`.gitlab-ci*`）。
- `./hc`（dos_help/hc.c）是帮助文件编译器（构建工具），不是测试。

因此按 `NO_UPSTREAM_TESTS` 申报：L1 门禁由配方自带 test_package 的
真实执行满足（CI 日志含 test_package 执行记录）。

## 运行说明

- 交互窗口需要 X11 显示服务；鸿蒙 PC 无显示后端时程序以
  `Could not open display` 退出（这是上游预期行为，非移植缺陷）。
- 帮助与数据文件位于包内 `share/xfractint/`（编译期烘焙的 SRCDIR）。
