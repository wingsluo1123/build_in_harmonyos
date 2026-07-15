# nsxiv 34 适配笔记

## 软件概述

nsxiv (Neo Simple X Image Viewer) 是 sxiv 的 fork，是一个轻量级 X11 图像查看器。
支持基本图像操作（缩放、平移、旋转）、缩略图模式、脚本化等。

## 编译环境

- 构建系统: makefile (plain Makefile + config.mk)
- 源码版本: v34 (tag v34, commit 054859b)
- 编译器: clang/clang++
- 安装前缀: ~/usr/local
- 状态: published

## 依赖

### 必需依赖
- **imlib2** (>= 1.11, built WITH X11 display support)
- **libX11**

### 可选依赖（已禁用）
- inotify — OHOS 内核不提供，HAVE_INOTIFY=0
- libXft + fontconfig + freetype2 — libXft 无预编译包，HAVE_LIBFONTS=0（禁用状态栏）

### 可选依赖（已启用）
- libexif — 预编译包可用，HAVE_LIBEXIF=1

### 间接依赖
- libXext — imlib2 X11 模块需要
- libpng — imlib2 PNG loader 需要
- zlib — imlib2 zlib loader 需要

## 编译步骤

```bash
cd $BUILD_SRC_DIR

# 创建 config.h
cp config.def.h config.h

# 创建 version.h 和 .git/index（Makefile 依赖）
mkdir -p .git && touch .git/index
printf '#define VERSION "34"\n' > version.h

# 编译
make CC=clang \
  HAVE_INOTIFY=0 HAVE_LIBFONTS=0 HAVE_LIBEXIF=1 \
  CFLAGS="-Wall -pedantic -O2 -DNDEBUG -fPIC" \
  CPPFLAGS="-I$HOME/usr/local/include -I$HOME/usr/local/include/X11" \
  LDLIBS="-L$HOME/usr/local/lib" -j1

# 安装
make install PREFIX=$HOME/usr/local
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | inotify 不可用 | OHOS 内核不提供 inotify API | HAVE_INOTIFY=0 禁用自动重载 |
| 2 | libXft 不可用 | 无预编译包 | HAVE_LIBFONTS=0 禁用状态栏 |
| 3 | imlib2 无 X11 display 函数 | 预编译 imlib2 使用 --without-x 构建 | 重新编译 imlib2 1.12.5 启用 X11 |
| 4 | make jobserver mkfifo 失败 | HMDFS 不支持 mkfifo | 使用 -j1 |
| 5 | version.h 依赖 .git/index | Makefile 规则需要 git | 创建空 .git/index |

## 关键决策

### 无需补丁
nsxiv 的 Makefile 支持通过命令行参数覆盖 config.mk 中的变量。
因此 HAVE_INOTIFY、HAVE_LIBFONTS、HAVE_LIBEXIF、CFLAGS、CPPFLAGS、LDLIBS
全部通过 make 参数传递，无需修改 config.mk。

### imlib2 重建
预编译的 imlib2 1.12.6 使用 --without-x 构建，缺少 X11 display 函数
（imlib_context_set_display 等）。nsxiv 依赖这些函数。
解决方案：从 Gitee 镜像获取 imlib2 1.12.5 源码，启用 X11 支持重新编译。

## 源码修改

无源码修改。所有适配通过 make 命令行参数完成。
---

**编译结束**: 2026-07-16 00:52
**最终状态**: built
