# gst-plugins-base 1.28.3 适配笔记

## 编译状态
**成功** - 所有编译步骤完成

## 编译环境
- 源码路径: `/storage/Users/currentUser/tmp/builds/gst-plugins-base-1.28.3`
- 归档路径: `archives/g/gst-plugins-base/1.28.3/`
- 编译器: clang (OHOS SDK)
- 构建系统: meson + ninja
- 目标平台: aarch64-unknown-linux-ohos

## 关键问题及解决方案

### 1. Python脚本执行权限问题
**问题描述**: HMDFS文件系统上的Python脚本无法直接执行，报错 Permission denied

**解决方案**: 修改meson.build，使用python3解释器调用Python脚本
- `meson-pkg-config-file-fixup.py`: 改为 `files()` + `run_command(python3, ...)`
- `extract-release-date-from-doap-file.py`: 同上
- 创建patch文件：`0001-meson.build.patch`

### 2. 外部依赖禁用
禁用以下功能以避免缺少依赖:
- gl (OpenGL)
- vorbis (Vorbis codec)
- theora (Theora codec)
- ogg (OGG container)
- orc (Optimized inner loop runtime compiler)
- orc-compiler
- iso-codes
- nls (gettext, OHOS无gettext)
- introspection (gobject-introspection)
- tools (命令行工具)

### 3. pkg-config 包装
需要创建包装 .pc 文件:
- glib2 子包: glib-2.0, gobject-2.0, gio-2.0, gmodule-2.0 等
- gstreamer 子包: gstreamer-1.0, gstreamer-base-1.0, gstreamer-net-1.0 等

## 编译配置参数
```
meson setup build \
  --prefix=... \
  --buildtype=release \
  -Ddefault_library=static \
  -Dnls=disabled \
  -Dexamples=disabled \
  -Dtests=disabled \
  -Ddoc=disabled \
  -Dintrospection=disabled \
  -Dorc=disabled \
  -Dorc-compiler=disabled \
  -Diso-codes=disabled \
  -Dgl=disabled \
  -Dvorbis=disabled \
  -Dtheora=disabled \
  -Dogg=disabled \
  -Dtools=disabled
```

## 依赖版本
- gstreamer/1.28.3
- glib2/2.88.0

## 验证结果
conan-verify G1-G4 all PASS

---

**编译结束**: 2026-08-06
**最终状态**: built
