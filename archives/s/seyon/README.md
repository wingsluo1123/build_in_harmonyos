# seyon

seyon 是一个经典 X11/Athena (Xaw) 串行通信终端程序（modem 拨号 / 终端仿真），
带一套可脚本化的命令语言（`dial(...)`、`set(...)` 等，由 yacc 解析器
`ParseThis()` 处理）。本项目适配鸿蒙 PC（aarch64）平台。

## 功能概述

- 通过串口 / modem 进行终端通信，支持 Xaw 图形界面
- 可脚本化命令语言（yacc/bison 语法，`SeParse.y`）
- 电话簿（`phonelist`）、协议（`protocols`）、启动脚本（`startup`、`script.*`）
- 在线帮助文件（`seyon.help`）

## OHOS 适配要点

- **构建系统**：上游只提供 Imakefile（imake/X11R5）。配方用生成的 POSIX
  Makefile 重写构建（`Makefile.ohos`），逐文件编译并链接 conan 提供的
  X11/Xaw 栈（libxaw/libxmu/libxt/libx11/libxext）。
- **-fcommon**：`SeDial.c` 与 `SeTrans.c` 都对全局 `mlw` 有暂定定义；现代
  clang 默认 `-fno-common`，lld 会报重复符号。
- **bison 尾声**：`SeParse.y` 的 `#ifdef TEST` 尾声含多行字符串字面量，
  bison >= 3.0 会解析尾声并报错，需打补丁（补丁 0001）。
- **libc 冲突**：`SeDecl.h` 用 K&R 声明 `usleep()` 与 `getline()`，与 OHOS
  libc 的 `<unistd.h>` / `<stdio.h>` 冲突；`getline` 重命名为
  `seyon_getline`（补丁 0002）。
- **OHOS 签名**：`bin/seyon` 由 `binary-sign-tool` 自签，`llvm-readelf` 断言
  恰有 1 个 `.codesign` 段（fail-closed）。

## 依赖关系

编译/运行依赖（ohpcd 制品仓，os=OHOS / arch=armv8 / clang15）：

- libx11/1.8.13
- libxaw/1.0.14（传递引入 libxmu/libxt/libxext/libxpm/libice/libsm/libxcb/libxau/libxdmcp）
- libxmu/1.3.1.1
- libxt/1.3.1
- libxext/6.4.0.1

## 参考资料

- 上游主页：https://www.seyon.org/
- 源码（Debian main pool orig tarball）：
  https://deb.debian.org/debian/pool/main/s/seyon/seyon_2.20c.orig.tar.gz

## Versions

| Version | Status |
| --- | --- |
| 2.20c | built |
