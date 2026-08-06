# keyutils 1.6.1 — 编译适配笔记

## 基本信息
| 项目 | 值 |
|------|------|
| 软件名 | keyutils |
| 版本 | 1.6.1 |
| 构建系统 | Makefile |
| 编译器 | clang |
| 目标平台 | OpenHarmony (aarch64, musl libc) |

## 编译问题及修复
### 问题1: rindex() 和 index() 未定义
- musl libc 不提供 BSD 函数 rindex() 和 index()
- 修复: 替换为标准 C 函数 strrchr() 和 strchr()

## 补丁列表
| 补丁 | 描述 |
|------|------|
| 0001-fix-musl-rindex-index.patch | 替换 rindex->strrchr, index->strchr |
---

**编译结束**: 2026-08-07 00:41
**最终状态**: built
