# pth 2.0.7 — GNU Portable Threads

## 简介

GNU Pth (Portable Threads) 是一个基于 POSIX/ANSI-C 的用户空间线程库，
提供非抢占式的协程调度。适用于需要大量轻量级并发任务的场景。

## 构建信息

| 项目 | 值 |
|------|-----|
| 版本 | 2.0.7 |
| 构建系统 | GNU Autotools |
| 目标平台 | aarch64-unknown-linux-ohos |
| 编译器 | clang 15.0.4 (OpenHarmony SDK) |
| 链接方式 | 静态链接 (--disable-shared) |
| mctx 实现 | sjlj/ssjlj/sas |
| 许可证 | GPL-3.0 (LGPL-2.1-or-later 见源码 LICENSE) |

## 安装产物

```
lib/libpth.a       静态库
include/pth.h      公共头文件
bin/pth-config     配置脚本
man/man3/pth.3     man 手册
share/aclocal/pth.m4  autoconf 宏
```

## Conan 引用

```
pth/2.0.7@ohpcd/stable
```

## 补丁列表

| 补丁 | 说明 |
|------|------|
| 0001-config.guess.patch | 替换 config.guess 支持 OHOS 平台识别 |
| 0002-config.sub.patch | 替换 config.sub 支持 OHOS 平台识别 |
| 0003-configure.patch | 修复 Linux 检测逻辑 + TMPDIR 路径 + umask |
| 0004-shtool.patch | 修复 shtool umask 077→022 |

## 测试结果

make check 全部通过:
```
Pth: OK: aarch64-unknown-linux-ohos | sjlj/ssjlj/sas | down | 2.0.7
```
