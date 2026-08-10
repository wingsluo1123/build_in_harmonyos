# gphoto2 2.5.32 for HarmonyOS

## 概述

gphoto2 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。gphoto2 是访问数字相机的命令行工具，基于 libgphoto2 库。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | gphoto2 |
| 版本 | 2.5.32 |
| 下载地址 | https://github.com/gphoto/gphoto2/releases/download/v2.5.32/gphoto2-2.5.32.tar.bz2 |
| 上游仓库 | https://github.com/gphoto/gphoto2 |
| 许可证 | GPL-2.0-or-later |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | autotools |

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| libgphoto2 | 2.5.31 | ohpcd/stable |
| libexif | 0.6.26 | ohpcd/stable |
| popt | 1.16 | ohpcd/stable |

## 补丁说明

### 0001-auto-aux-config.guess.patch
添加 HarmonyOS 平台检测到 config.guess。

### 0002-auto-aux-config.sub.patch
添加 ohos 操作系统支持到 config.sub。

### 0003-gphoto2-main.c.patch
替换 pthread_cancel 为基于标志的取消机制（musl/OHOS 不支持 pthread_cancel）。

### 0004-configure-umask-fix.patch
修复 configure 脚本的 umask 077→022 和临时目录路径问题。

## 遇到的问题

### 问题1: pthread_cancel 不可用

**现象**: 编译时 pthread_cancel 未定义

**原因**: musl/OHOS 不支持 pthread_cancel

**解决**: 使用 `#ifdef __OHOS__` 守卫，用 flag-based cancellation 替代

### 问题2: configure 临时文件权限问题

**现象**: configure 创建的临时文件权限为 0700，导致构建问题

**解决**: 将 umask 077 改为 022，临时目录从 ./confXXXXXX 改为 ${HOME}/tmp/confXXXXXX

## 测试结果

| 测试项 | 结果 |
|--------|------|
| make check | ✅ 1/1 PASS |
| gphoto2 --version | ✅ gphoto2 2.5.32 |
| gphoto2 --list-ports | ✅ Port enumeration works |
