# xcdplayer 2.2 适配笔记

## 编译环境
- 构建系统: 上游 Imakefile → 配方生成 POSIX Makefile（conanfile.build() 内嵌模板）
- 编译日期: 2026-10-16
- 编译器: OHOS SDK clang（`tools.build:compiler_executables`）
- 状态: built

## 软件简介

xcdplayer 2.2 是 X11R5 contrib 中的 Athena (Xaw) CD 播放器（1993-01），支持
播放/暂停/快进/编程播放/随机播放/音量控制等。上游仅带 Sun（cdrom_sun.c）与
SGI（cdrom_sgi.c）两个 CD-ROM 后端，无 Linux 后端。

## 源码溯源

- 上游唯一发布物 `xcdplayer-2.2.tar.Z`（compress/LZW，89435 字节）
- 权威指纹：FreeBSD ports `audio/xcdplayer` distinfo（PORTVERSION 2.2，
  MASTER_SITES XCONTRIB/../R5contrib）
- 下载源：`https://ftp.gwdg.de/pub/x11/x.org/R5contrib/xcdplayer-2.2.tar.Z`
  （GWDG 对 ftp.x.org 的完整 HTTPS 镜像），实测 sha256 与 distinfo 完全一致
- `.Z` 解压：qpage 3.3 同款纯 Python unlzw（配方内嵌）

## 编译步骤

1. `source()`：下载 `.tar.Z` → 内置 unlzw() 解码 → 展开 tar 并去掉顶层目录
2. `build()`：apply_conandata_patches() → 生成 Makefile.ohos（-I/-L 取自全部
   conan host 依赖的 cpp_info，链接序 Xaw→Xmu→Xt→Xpm→Xext→X11→SM→ICE→
   X11-xcb→xcb→Xau→Xdmcp）→ `make -j1`，产出 `xcdplayer` 与 `cdinfo`
3. `package()`：`bin/{xcdplayer,cdinfo}`、`share/man/man1/xcdplayer.1`、
   `share/X11/app-defaults/XCdplayer`、licenses

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 Linux CD-ROM 后端 | 上游只有 sun/sgi 后端 | 从同作者上游后续版本 2.3a 移植 cdrom_linux.c/.h（linux/cdrom.h ioctl），接口回移到 2.2 语义：disc_title 保持 `char *`（strdup/free）、get_stored_info 逻辑对齐 2.2 的 sun 后端 |
| 2 | `(Cardinal)&volbase` 报 "initializer element is not a compile-time constant" | K&R 时代允许把全局地址折叠为整数常量做静态初始化，clang 不允许 | XtResource 表移到 top_setup() 内运行时初始化；base 仍传 NULL，偏移仍是全局变量绝对地址，语义不变 |
| 3 | `<varargs.h>` 头被 clang 拒绝 | debug_printf 用 va_alist/va_dcl 老式可变参数 | 改写为 `<stdarg.h>` 标准原型 `debug_printf(int level, char *fmt, ...)` |
| 4 | `X11/bitmaps/gray` 缺失 | xbitmaps 未发布到制品仓（R36 无法新增依赖） | 把 xbitmaps 1.1.3 的标准 2x2 gray 位图原样 vendored 为 `gray.bm`，include 改本地 |
| 5 | 块作用域 `static void f();` 报错 | C23/clang 禁止块作用域 static 声明；且 K&R 代码先隐式声明再 static 定义 | 相关前置声明提升到文件作用域（main.c/logo_setup.c/button_setup.c/internals.c/program.c） |
| 6 | cdinfo.c/cdgrab.c 用 Sun 头（sys/buf.h、sun/dkio.h） | 附带诊断工具按 Sun 编写 | cdinfo.c 移植到 linux/cdrom.h + /dev/cdrom（照抄 2.3a 的 include 块）；cdgrab.c 是 raw-SCSI 抓轨工具，上游 2.3a 也未移植，OHOS 无此设备，不参与构建 |
| 7 | cdrom_open 缺 fcntl.h（O_RDONLY 未定义） | 2.3a 的 linux 后端在老 glibc 头树下未显式包含 | cdrom_linux.c 增加 `#include <fcntl.h>` |

## 依赖版本（conan，remote=ohpcd）

- libxaw/1.0.14（传递：libxmu/1.3.1.1、libxt/1.3.1、libx11/1.8.13、libxext/6.4.0.1、
  libxcb/1.17.0、libxau/1.0.11、libxdmcp/1.1.5、libice/1.1.2、libsm/1.2.6、xtrans/1.6.0）
- libxpm/3.5.17

## 验证结果

```bash
# 全量清编译：0 error（clang -Wall）
make -f Makefile.ohos clean && make -f Makefile.ohos -j4   # 0 errors
# 产物：xcdplayer（ELF aarch64, ld-musl, NEEDED libXaw/libXmu/libXt/libXpm/
#        libXext/libX11/libSM/libICE/libXau/libXdmcp/libX11-xcb/libxcb/libc）
#        cdinfo
# test_package：ELF 检查 + 无 DISPLAY 冒烟（"can't open display", exit=1）
#               + 包内产物检查，4/4 通过
```

## 注意事项

- xcdplayer 是交互式 GUI 程序，自动化测试只能覆盖"可动态链接、可启动到
  XtOpenDisplay"这一层；真实 CD 播放需真机光驱与 X server。
- 版本以 conandata.yml 的 URL/sha256 为准，与 FreeBSD ports distinfo 一致。
---

**编译结束**: 2026-10-16 15:13
**最终状态**: published
