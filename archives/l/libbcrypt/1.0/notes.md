# libbcrypt 1.0 适配笔记

## 软件信息
- 名称: libbcrypt
- 版本: 1.0
- 上游: https://github.com/rg3/libbcrypt
- 许可: CC0 (Public Domain)
- 构建系统: Makefile (非 autotools/非 CMake)

## 适配修改

### 1. 移除 x86 汇编 (crypt_blowfish/Makefile)
- **问题**: crypt_blowfish/Makefile 中 `BLOWFISH_OBJS` 包含 `x86.o`，编译自 `x86.S` (x86 汇编)，在 ARM64 上无法汇编
- **修复**: 从 `BLOWFISH_OBJS` 中移除 `x86.o`
- **原因**: crypt_blowfish.c 中已有 `BF_ASM` 宏，在非 x86 平台上 `BF_ASM=0`，使用纯 C 实现 `BF_body()`，x86 汇编仅为可选优化

## 编译参数
- CC=clang
- CFLAGS: 继承自 crypt_blowfish/Makefile (-W -Wall ... -O2 -fomit-frame-pointer -funroll-loops)
- 无 configure 脚本，直接 make

## 测试结果
- bcrypt_test: 通过 (salt 生成、hash、checkpw 全部 OK)
- crypt_blowfish crypt_test: 通过 (335 c/s)

## 产物
- 静态库: bcrypt.a
- 头文件: bcrypt.h
---

**编译结束**: 2026-07-15 16:50
**最终状态**: built
