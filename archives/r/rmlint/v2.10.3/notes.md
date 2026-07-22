# rmlint v2.10.3 适配笔记

**日期**: 2026-07-17
**状态**: 📝 首次适配

## 适配概要

rmlint 使用 **SCons** 构建系统（非标准 Autotools/CMake/Makefile），
需要先确保 scons 包已在 Conan 制品仓中可用。

## 依赖状态

| 依赖 | 版本 | 状态 |
|------|------|------|
| glib | >= 2.64 | ✅ 已适配 (2.84.0) |
| scons | 4.x | ✅ 已适配 (4.10.0) |
| json-glib | (可选) | ✅ 已适配 |
| libelf | (可选) | ❌ 未适配，禁用 |
| blkid | (可选) | ❌ 未适配，禁用 |
| gettext | (可选) | ❌ 未适配，禁用 |

## 潜在问题

1. SCons 的 `pkg-config` 检测需要 Conan 生成的 `.pc` 文件在 PKG_CONFIG_PATH 中
2. GCC 版本检测可能不兼容 OHOS 的 clang — 但 SCons 会优雅降级
3. 部分 Linux 特有功能（fiemap, btrfs, blkid）在 OHOS 上不可用，但 SCons 检测会跳过
4. `__builtin_cpu_supports` 等 x86 特有功能在 aarch64 上不可用，但 SCons 会处理

## 构建步骤

```
scons config          # 配置（检测功能可用性）
scons -j1             # 编译
scons --prefix=/ install --actual-prefix=/ DESTDIR=<target>  # 安装
```

## 测试

上游测试基于 Python pytest，需要在 conan create 环境中安装 pytest。
---

**编译结束**: 2026-07-17 11:20
**最终状态**: built
