# mfiutil — OpenHarmony 编译档案

## 软件简介

mfiutil 是 LSI MegaRAID SAS 控制器的管理工具，最初移植自 FreeBSD 的
`usr.sbin/mfiutil`，由 Rivoreo 项目维护为跨平台版本（FreeBSD /
DragonFly / GNU-Linux / Solaris / Darwin）。Linux 上通过 megaraid_sas
驱动的 ioctl 字符设备工作，提供 adapter/firmware 查询、BBU 属性、
patrol read、foreign 配置导入、固件刷写等管理功能。

纯 C 程序（13 个 .c + 2 个头），手写 Makefile，仅依赖 libc。

## OHOS 适配要点

- 无源码补丁：Solaris/FreeBSD/Darwin 专属头文件（`sys/ioccom.h`、
  `sys/sysctl.h`、`libdevinfo.h`、`AvailabilityMacros.h`）全部在条件
  编译块内；OHOS clang（`aarch64-unknown-linux-ohos`）预定义 `__linux__`，
  自动走 Linux 路径
- Makefile 硬编码 `CC := gcc`，GNU make 命令行赋值覆盖；CFLAGS 保持
  上游默认（`-std=gnu99 -Wall -Wno-unused-value -Os -I include`）
- 安装走上游 `install` 目标：`make install DESTDIR=<pkg> PREFIX=/usr`，
  产物 `usr/sbin/mfiutil` + man page
- 取源：Debian 官方归档的 orig tarball（与上游 Rivoreo Gitiles 提交
  e8c6289 内容逐字一致，PGP 签名 .dsc 背书；上游 Gitiles 归档每次请求
  重新生成、sha256 不稳定故不采用），扁平结构 `strip_root=False`

## 依赖关系

- 无第三方依赖（仅 libc）
- 编译器从 Conan conf `tools.build:compiler_executables` 动态获取（OHOS clang）

## 上游测试

- 上游正式测试为 0（无 tests/ 目录、Makefile 无 check/test 目标；
  FreeBSD 原版与 Debian 打包同样无测试）
- test_package 以 6 条断言覆盖可确定执行的用户land路径与硬件缺失时的
  失败路径（version / usage / 未知命令 / 无控制器 show adapter / 非法选项）

## 参考资料

- [mfiutil Rivoreo 项目页](https://rivoreo.one/?id=Project:mfiutil)
- [mfiutil 源码库（Gitiles）](https://src.rivoreo.one/mfiutil)
- [mfiutil SourceForge（r1 发布）](https://sourceforge.net/projects/mfiutil/)
- [Debian sid mfiutil 快照包](https://packages.debian.org/sid/mfiutil)
