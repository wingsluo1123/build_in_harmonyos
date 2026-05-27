# gtk+ 3.24.43 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-27
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

1. 下载源码 gtk+-3.24.43.tar.xz (从 GNOME FTP 镜像)
2. 使用 meson setup 配置，禁用 X11/wayland/win32/quartz 后端，启用 broadway 后端
3. 需要使用 meson native 文件指定正确的 python3 路径（因为 python3.12 直接调用存在 libiconv.so.2 加载问题）
4. 需要设置 UNINSTALLED_GLIB_SRCDIR 环境变量指向 glib 源码目录（因为 gdbus-codegen 的 codegen 模块未安装到本地）
5. 需要创建 glib 源码的 config.py 文件（gdbus-2.0/codegen/config.py）
6. 需要创建 gobject/gobjectnotifyqueue.c 的符号链接到本地 include 目录（GTK+3 编译时需要此 glib 内部文件）
7. ninja -C builddir -j2 编译
8. meson install -C builddir --destdir $TEST_PREFIX 安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | python3.12 直接调用加载 libiconv.so.2 失败 | libintl.so.8 的 RUNPATH=/pkgroot/lib 在此系统不解析 | 使用 meson native 文件指定 /data/service/hnp/bin/python3（shell wrapper） |
| 2 | gen-gtk-gresources-xml.py 生成的 XML 缺少 ?> | XML 声明行 `<?xml version='1.0' encoding='UTF-8'>` 缺少问号 | 修补为 `<?xml version='1.0' encoding='UTF-8'?>` (patch 0001) |
| 3 | gdbus-codegen 执行失败 | shebang 用了 /usr/bin/python3 (不存在) | 创建 gdbus-codegen wrapper 用 /usr/bin/env python3 |
| 4 | gobjectnotifyqueue.c 文件找不到 | GTK+3 依赖 glib 内部私有头文件 | 创建符号链接到本地 include 目录 |
| 5 | gdbus-codegen 的 codegen 模块找不到 | glib 安装时没有安装 gdbus-2.0/codegen Python 模块 | 设置 UNINSTALLED_GLIB_SRCDIR 环境变量 |

## 源码修改

- 0001-fix-xml-declaration-in-gen-gtk-gresources-xml.patch: 修复 gen-gtk-gresources-xml.py 中 XML 声明缺少 ?> 的问题

## 依赖版本

- glib-2.0: 2.84.0
- pango: 1.50.14
- fribidi: 1.0.13
- cairo: 1.18.4
- epoxy: 1.5.10
- gdk-pixbuf: 2.42.12
- atk: 2.58.3
- harfbuzz: 6.0

## 验证结果

```bash
pkg-config --modversion gtk+-3.0
# 输出: 3.24.43
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gtk+-3.24.43-ohos-aarch64.tar.gz | ~60MB | Release 预编译包 |
| gtk+-3.24.43-ohos-aarch64-debug.tar.gz | ~60MB | Debug 预编译包 |
| 0001-fix-xml-declaration-in-gen-gtk-gresources-xml.patch | 1.7KB | XML声明修复补丁 |

## 注意事项

- 需要设置 UNINSTALLED_GLIB_SRCDIR 环境变量才能运行 gdbus-codegen
- 需要确保 gobjectnotifyqueue.c 在 include 目录中可用
- broadway backend 是唯一启用的显示后端
