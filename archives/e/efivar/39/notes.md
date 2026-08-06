# efivar 39 — 编译适配笔记

## 基本信息
| 项目 | 值 |
|------|------|
| 软件名 | efivar |
| 版本 | 39 |
| 构建系统 | Makefile |
| 编译器 | clang |
| 目标平台 | OpenHarmony (aarch64, musl libc) |

## 编译问题及修复
### 问题1: qsort_r 未定义
- musl libc 不提供 qsort_r (GNU 扩展)
- 修复: 创建 qsort_r_shim.h，使用 qsort + 全局变量实现

### 问题2: secure_getenv 未定义
- musl libc 不提供 secure_getenv
- 修复: 使用 getenv 替代 (OHOS 无 setuid)

### 问题3: program_invocation_short_name 未定义
- musl libc 不提供此 glibc 变量
- 修复: 使用 __progname 替代

## 补丁列表
| 补丁 | 描述 |
|------|------|
| 0001-add-musl-compat-shim.patch | 新增 musl 兼容 shim 头文件 |
| 0002-add-shim-include-list.h.patch | list.h 引入 shim |
| 0003-add-shim-include-makeguids.h.patch | makeguids.h 引入 shim |
| 0004-add-shim-include-thread-test.c.patch | thread-test.c 引入 shim |
---

**编译结束**: 2026-08-07 00:38
**最终状态**: built
