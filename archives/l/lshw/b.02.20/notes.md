# lshw b.02.20 — 适配笔记

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | lshw |
| 版本 | b.02.20 (上游 B.02.20) |
| 状态 | built |
| 构建系统 | makefile |
| 源码路径 | https://github.com/lyonel/lshw/archive/refs/tags/B.02.20.tar.gz |
| 官方文档 | https://github.com/lyonel/lshw |
| 许可证 | GPL-2.0 |
| 类型 | 命令行工具 |

## 版本说明
上游版本为 `B.02.20`，因 Conan 2.x 要求包名和版本全小写，适配版本使用 `b.02.20`。

## 编译步骤

```bash
# 1. 下载源码
# ohc-run.py init-build 已自动处理（ghfast.top 镜像注入）

# 2. 应用补丁
patch -p1 < patches/0001-src-Makefile.patch
patch -p1 < patches/0002-src-core-pnp.cc.patch

# 3. 编译
make -C src VERSION=b.02.20 PREFIX=/usr/local -j1

# 4. 安装
make -C src install SBINDIR=/bin MANDIR=/share/man DATADIR=/share/lshw DESTDIR=<prefix>
```

## 补丁说明

### 0001-src-Makefile.patch
**目的**: 在 DEFINES 中添加 -DNONLS，禁用 NLS/gettext 支持
**原因**: OpenHarmony 平台缺少 gettext 库，禁用 NLS 可避免链接错误

### 0002-src-core-pnp.cc.patch
**目的**: 在 pnp.cc 中添加 #include "config.h"
**原因**: pnp.cc 使用 config.h 中定义的宏，缺少此 include 会导致编译错误

## 遇到的问题

### 问题1: Conan 版本必须全小写
**现象**: `ERROR: Conan packages names 'lshw/B.02.20@ohpcd/stable' must be all lowercase`
**原因**: Conan 2.x 要求包名和版本全小写，上游版本 `B.02.20` 包含大写字母
**解决**: 使用小写版本 `b.02.20`，归档目录也改为小写

### 问题2: GitHub 源码不可直接访问
**现象**: github.com 超时不可达
**原因**: 网络限制
**解决**: ohc-run.py 自动注入 ghfast.top 镜像，CI 也会使用镜像 fallback

## 验证结果
- `lshw -version` 输出 `B.02.20` ✅
- conan-verify G1-G4 全部通过 ✅
---

**编译结束**: 2026-07-15 16:35
**最终状态**: built
