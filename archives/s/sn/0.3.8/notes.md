# sn 0.3.8 适配笔记

## 编译环境
- 构建系统: makefile（上游自有 make 体系，非 autotools）
- 编译日期: 2026-10-14
- 编译器: OHOS clang 15（target aarch64-unknown-linux-ohos，DevEco SDK 15.0.4，
  lld，sysroot /mnt/c/Users/13909/ohos-sysroot），WSL 本地交叉
- 状态: built

## 上游与源码

- 上游: Patrik Fältström 的小型 Usenet 新闻系统（抓取器 + NNTP 服务器 + spool 管理
  工具），面向几十个小站/家用的低速连接场景，2004 年前后发布，GPL 许可证（COPYING）。
- 源站 <http://www.iki.fi/patrik/sn/> 已不再提供 0.3.8 归档；采用 Debian pool 的
  纯净上游 tarball（https 权威镜像，R39，同 jpegpixi 1.1.1 先例）：
  `https://deb.debian.org/debian/pool/main/s/sn/sn_0.3.8.orig.tar.gz`
  sha256 `e415a019c556ffbf148d052ee84cdb990a6385cb272f438013d448d90914d8e1`（HTTP 200 实测，
  与 PureOS 发行版登记的同文件 sha256 一致）。

## 编译步骤

```bash
# zlib/1.3.1 (ohpcd) 的头文件在构建期拷入 lib/（已在 -I 路径），libdir 经 ZLIB 变量传入
make -j1 CC=<ohos-clang> LD=<ohos-clang> ZLIB="-L<zlib-libdir> -lz"
```

- R9: -j1。
- ZLIB 非空使 cc-flags 自动加 -DUSE_ZLIB，启用文章压缩路径（cache.c/store.c）。
- cc-flags 无 CFLAGS 变量：zlib.h/zconf.h 的注入点只能是已在 -I 路径上的 lib/
  目录（构建期拷贝，不改源码）。
- Makefile 硬编码 ar/ranlib（无 $(AR)/$(RANLIB) 变量）：宿主 GNU binutils 2.38
  直接处理 arm64 对象（ar 仅打包、ranlib 建索引），无需工具 shim。
- 产物: 14 个二进制 + 3 个脚本（SNHELLO/SNPOST/dot-outgoing.ex，.in 经 sed 生成）
  + 3 个符号链接（sncat/sncancel→snscan，snstore→snsend）+ 17 个 man 页（man8）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `error: use of undeclared identifier 'caddr_t'`（6 文件 9 处） | caddr_t 为 glibc 遗留类型（void* 别名，2004 年代码），musl/OHOS libc 不提供 | 补丁 0001：munmap 强转统一替换为语义等价的 `void *` |

## 源码修改

| 补丁 | 文件 | 内容 |
|---|------|------|
| patches/0001-portability-caddr_t-to-void.patch | allocate.c, dh_find.c, group.c, newsgroup.c, store.c, times.c | 9 处 `munmap((caddr_t) ...)` 强转替换为 `munmap((void *) ...)`（caddr_t 本就是 void* 别名，零行为变化） |

## 依赖版本

- zlib/1.3.1（ohpcd 制品仓，活查 conan list 确认已发布）：静态链接。
  snscan 实测 NEEDED 仅 libc.so，zlib 符号（inflate_fast 等）静态并入二进制
  （readelf 确认）。

## __fd_chk 与本地运行环境（重要）

- OHOS sysroot `sys/select.h` 的 FD_SET/FD_CLR 宏内联调用 `__fd_chk(fd)`
  边界检查（fd 不在 [0,1024) 即 abort）。sn 的 4 处 FD_SET 调用点
  （get.c×2、lib/readln.c×1、sngetd.c×1）使 14 个二进制中 8 个
  （snprimedb/snntpd/snsend/snmail/snget/sngetd/snfetch/snsplit，
  其余 6 个的调用路径被编译器消除）动态引用 `__fd_chk`。
- 设备端无问题：`__fd_chk` 由 OHOS 官方 musl 导出（openharmony/third_party_musl
  的 libc.map.txt 版本脚本含 `__fd_chk` 条目），SDK sysroot 的 libc.so 亦导出
  （readelf 确认）。
- 本地 WSL qemu 仿真 guest（/opt/ohos-guest）的旧 musl 缺该符号：test_sn.sh 在
  检测到 QEMU_LD_PREFIX 且 guest 存在 libfdchkshim.so 时自动 LD_PRELOAD
  补齐；设备上 QEMU_LD_PREFIX 未设置，该分支为 no-op，原生直接执行。

## 验证结果

上游无测试套件（0.3.8 为 2004 年发布，源码树无 test 目标/脚本）。

包验证（test_package，14 条断言，全部对打包后的 aarch64 二进制实跑，
WSL qemu + libfdchkshim.so 本地全量通过 14/14；设备上原生直接执行）：

| 工具 | 调用 | 期望 rc | 输出断言 |
|------|------|---------|----------|
| snexpire | -h | 1 | Usage:snexpire |
| snsend | -h | 1 | Usage: snsend [-rcnva] |
| snget | -h | 1 | Usage:snget |
| sngetd | -h | 1 | Usage:sngetd |
| snfetch | -h | 1 | Usage:snfetch |
| snnewgroup | -h | 1 | Usage:snnewgroup |
| sndelgroup | -h | 1 | Usage:sndelgroup |
| snlockf | -h | 1 | Usage: snlockf (no arguments or options) |
| snsplit | -h | 1 | Usage: snsplit |
| snprimedb | -h | 2 | Can't find spool directory |
| snscan | -h | 2 | Can't find spool directory |
| snntpd | -h | 2 | Can't find spool directory |
| snmail | -h | 2 | Can't find spool directory |
| sndumpdb | -h | 2 | Can't find spool directory |

- 断言全部为无网络、无 spool、无端口绑定的确定性路径（snntpd -h 在绑定端口
  之前即进入 spool 检查，实测 rc=2 后退出）。
- 二进制加固（readelf）: ELF64 AArch64、Type=DYN(PIE)、GNU_STACK RW（NX）、
  -z relro；NEEDED 仅 libc.so。

---
**编译结束**: 2026-10-14 16:55
**最终状态**: built
