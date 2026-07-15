# lshw for HarmonyOS

## 概述

lshw (Hardware Lister) 在 HarmonyOS/OpenHarmony (aarch64) 上的适配。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | lshw |
| 版本 | b.02.20 (上游 B.02.20) |
| 下载地址 | https://github.com/lyonel/lshw/archive/refs/tags/B.02.20.tar.gz |
| 官方文档 | https://github.com/lyonel/lshw |
| 许可证 | GPL-2.0 |
| 构建系统 | makefile |
| 类型 | 命令行工具 |

## 编译步骤

```bash
# 1. 应用补丁
patch -p1 < patches/0001-src-Makefile.patch
patch -p1 < patches/0002-src-core-pnp.cc.patch

# 2. 编译
make -C src VERSION=b.02.20 PREFIX=/usr/local -j1

# 3. 安装
make -C src install SBINDIR=/bin MANDIR=/share/man DATADIR=/share/lshw DESTDIR=<prefix>
```

## 补丁说明

### 0001-src-Makefile.patch
- 在 DEFINES 中添加 -DNONLS，禁用 NLS/gettext 支持
- 原因: OpenHarmony 平台缺少 gettext 库

### 0002-src-core-pnp.cc.patch
- 在 pnp.cc 中添加 #include "config.h"
- 原因: 修复缺失的 include 导致的编译错误

## 遇到的问题

### Conan 版本必须全小写
- 上游版本 `B.02.20` 包含大写字母，Conan 2.x 要求全小写
- 使用 `b.02.20` 作为 Conan 版本号

## 测试结果

- `lshw -version` 输出 `B.02.20` ✅
- conan create + test_package 通过 ✅
