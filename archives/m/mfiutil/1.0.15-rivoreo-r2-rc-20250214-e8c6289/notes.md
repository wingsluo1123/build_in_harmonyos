# mfiutil 1.0.15-rivoreo-r2-rc-20250214-e8c6289 适配笔记

## 软件简介

mfiutil 是 LSI MegaRAID SAS 控制器的管理工具，最初移植自 FreeBSD 的
`usr.sbin/mfiutil`，由 Rivoreo 项目维护为跨平台版本（FreeBSD /
DragonFly / GNU-Linux / Solaris / Darwin）。Linux 上通过 megaraid_sas
驱动的 ioctl 字符设备（`/dev/megaraid_sas_ioctl_node`）工作，提供
adapter/firmware 查询、BBU 属性、patrol read、foreign 配置导入、
固件刷写等管理功能。

纯 C 程序：13 个 .c 翻译单元 + 2 个头文件 + 手写 Makefile，仅依赖 libc。

## 取源

- 上游官方源码库：Rivoreo Gitiles <https://src.rivoreo.one/mfiutil>
  （项目页 <https://rivoreo.one/?id=Project:mfiutil> 声明；Debian .dsc
  的维护者 WHR <whr@rivoreo.one> 即上游作者本人）。
- 官方只为 `1.0.15-rivoreo-r1` 打过 release tag（SourceForge 同步发布
  `mfiutil-1.0.15-rivoreo-r1-src.tar.bz2`）。
- 本任务版本串 `1.0.15-rivoreo-r2-rc-20250214-e8c6289` 对应 Debian sid
  快照包 `1.0.15-rivoreo-r2~rc-20250214-e8c6289-2`，其上游即 Gitiles
  提交 `e8c62898089593cd039b7d0360e030f04f9bfb45`（2025-02-14，"Remove
  unnecessary GPL version 2 licensing option from scsi_inquiry.h"）。
- 上游 Gitiles 在该提交处的官方归档 HTTP 200，但为每次请求即时生成，
  gzip 头带当前时间戳，两次下载 sha256 不同（实测 d2d78e2b… 与
  84a6c89e…），无法在 conandata 钉校验和。
- 因此取 Debian 官方归档（deb.debian.org 为 Debian 官方 CDN，非第三方
  镜像）中同一提交的 orig tarball：
  `https://deb.debian.org/debian/pool/main/m/mfiutil/mfiutil_1.0.15-rivoreo-r2~rc-20250214-e8c6289.orig.tar.bz2`
  sha256 `21f303c6a467c45a0f32f48eeb5118e641850b23d42f8352b93e0c75a8bba63a`，
  与同目录 PGP 签名 .dsc 的 Checksums-Sha256 逐字一致；内容与上游
  Gitiles 树 `diff -r` 完全相同（仅少一个 .gitignore，Debian 剥离子
  VCS 文件的惯例，不影响构建）。仓库内已有 497 个配方以 deb.debian.org
  为源，属既有官方取源通道。
- 归档为扁平结构（无顶层目录），`strip_root=False`。

## OHOS 适配要点

1. **无源码补丁**。所有平台专属头文件都有条件编译保护：
   - `sys/ioccom.h`、`libdevinfo.h`：仅 `__SVR4`（Solaris）
   - `sys/sysctl.h`：仅 `HAVE_MFI_DRIVER`（FreeBSD）
   - `AvailabilityMacros.h`、`mach-o/getsect.h`：仅 Apple
   - `sys/endian.h`/`sys/byteorder.h`/`byteswap.h`：按平台分支
   OHOS clang（`aarch64-unknown-linux-ohos`）预定义 `__linux__`，自动
   走 Linux 路径（`sys/sysmacros.h` + `/dev/megaraid_sas_ioctl_node`）。
2. **Makefile 适配**：上游硬编码 `CC := gcc`，GNU make 语义下命令行
   赋值覆盖文件内赋值，配方只传 `make CC=<conan conf 中的 OHOS clang>`；
   CFLAGS 保持 Makefile 默认值（`-std=gnu99 -Wall -Wno-unused-value -Os
   -I include`），原生 gcc 预编译零警告。
3. **安装**：上游 `install` 目标支持 DESTDIR/PREFIX，用
   `make install DESTDIR=<pkg> PREFIX=/usr`，产物落
   `usr/sbin/mfiutil` + `usr/share/man/man8/mfiutil.8`。
4. **无第三方依赖**：不查制品仓依赖，`conan download` 无需任何依赖包。

## 测试

上游无任何测试套件（无 tests/ 目录、Makefile 无 check/test 目标，
FreeBSD 原版与 Debian 打包同样无测试）。mfiutil 的功能执行依赖
MegaRAID 控制器硬件，测试机无法提供，因此 test_package 只做可确定
执行的验证（6 条断言）：

1. 产物 ELF magic
2. `mfiutil version` → rc=0，输出精确 `mfiutil version 1.0.15-rivoreo-r2`
3. 无参数 → stderr Usage + 非零退出
4. 未知命令 → "Unknown command" + 非零退出
5. `show adapter`（无控制器）→ 非零退出（真实走到 ioctl 设备打开失败）
6. 非法选项 `-Z` → 选项错误（OHOS libc 实测措辞 unrecognized option，glibc 系 invalid option）+ 非零退出

本地交叉编译（WSL 原生 ext4 /root/ohpcd-work/build/mfiutil-...，arm64
ohpcd 工具链）后，另在 qemu-aarch64 + OHOS musl guest runtime 下实测
同一 test.sh 全 6 条通过（见 reports/ 与 PR 正文证据）。

## 已知限制

- 在装有 MegaRAID 控制器真实硬件上，`version` 之外的命令才能完整工作；
  OHOS 上 megaraid_sas 驱动的可用性不在本仓库验证范围。
- 运行时如系统加载了 megaraid_sas 模块，程序会尝试
  `mknod /dev/megaraid_sas_ioctl_node`（需要 root），失败仅 warn 不退出。
