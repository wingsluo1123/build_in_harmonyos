# imaptool

imaptool 是一个 X11/Athena 部件的小工具，用于制作 HTML 客户端图像映射（client-side
image map）：它把一张 JPEG 或 GIF 图片显示在窗口中，让用户用鼠标标出矩形、圆形和多边形
热区，然后导出对应的 `<area>` HTML 片段。

## 功能概述

- 载入 JPEG（libjpeg，`-DUSE_JPEG_LIB`）与 GIF（内嵌 `dgif_lib.c` 解码器）图片
- 在图片上交互式绘制矩形 / 圆形 / 多边形热区
- 导出小写或大写的 HTML `<area>` 图像映射（`-l` / `-u` 选项）
- `-v` / `--version` 打印版本；`-h` / `--help` 打印用法

## OHOS 适配

- **构建系统**：上游是手写 GNU Makefile（2000 年），无 `configure`、无 `check/test`
  目标。Makefile 把 `CC=gcc -I/usr/X11R6/include/`、`JPEG_INCLUDE=-I/usr/local/include/`、
  `LIBDIR=-L/usr/local/lib -L/usr/X11R6/lib` 写死；本配方在 `make` 命令行用**同名变量**
  覆盖这些值（命令行定义优先级最高），指向 Conan 依赖的真实 include/lib 目录，
  因此不需要改上游 Makefile、也不需要打补丁。
- **依赖栈**：Athena 部件应用，依赖制品仓已发布的 X11 图
  `libxaw/1.0.14 + libxt/1.3.1 + libxmu/1.3.1.1 + libxext/6.4.0.1 + libx11/1.8.13 +
  xorgproto/2025.1`（与 `xfontsel 1.1.2` 同一图），JPEG 用静态 `libjpeg/10`；
  GIF 用上游内嵌解码器，无外部 giflib 依赖。
- **运行期**：OHOS 不预装 X 库，运行期靠依赖包 libdir 经 `LD_LIBRARY_PATH` / `LD_PRELOAD`
  解析（`libXaw7.so.7` → `libXmu`/`libXext`/`libXt`，`libX11.so.6` → `libxcb`/`libXau`/`libXdmcp`）。
- **签名**：`package()` 对 `bin/imaptool` 做 OHOS 自签（`binary-sign-tool`），并用
  `llvm-readelf -SW` 断言恰有 1 个 `.codesign` 段，fail-closed。
- **已知限制**：imaptool 是 GUI 工具，需要 X server。设备与 CI worker 都没有 X server
  （镜像内无 Xorg/Xvfb，制品仓未发布 OHOS xorg-server）。且 `imaptool.c` 在
  `parseparams()` **之前**调用 `XtVaAppInitialize()`（`imaptool.c:171` → `:178`），
  连 `-h`/`-v` 也需要 display。因此消费者测试断言的是：无 DISPLAY / 伪造 DISPLAY 时
  进程非零退出且输出 Xt 的 `Can't open display` 诊断（证明整条动态依赖链已加载并执行到
  Xt 显示初始化，且不挂起、不静默成功），以及 ELF 的 `DT_NEEDED` 与 `.codesign`。

## 依赖关系

- 编译依赖：`libxaw`、`libxt`、`libxmu`、`libxext`、`libx11`、`xorgproto`、`libjpeg`
- 运行依赖：`libxaw`、`libxt`、`libxmu`、`libxext`、`libx11`、`libxcb`、`libxau`、`libxdmcp`

## 参考资料

- 上游主页：http://www.sspitzer.org/imaptool/ （已不可达，2026-10-19 实测）
- 源码：Debian 稳定源包 pool `imaptool_0.9.orig.tar.gz`
  （https://deb.debian.org/debian/pool/main/i/imaptool/）
- Debian 打包：`imaptool 0.9-24`（Maintainer Colin Watson）
