# gst-plugins-bad 1.28.3 适配笔记

## 编译状态
**成功** - 所有 278 个编译步骤完成

## 编译环境
- 源码路径: GStreamer monorepo (GitHub tag 1.28.3)
- 构建系统: meson 1.11.1 + ninja 1.13.1
- 编译器: clang 15.0.4 (OHOS SDK)
- 目标平台: aarch64-unknown-linux-ohos

## 源码说明
GStreamer 1.28.x 使用 monorepo 结构，gst-plugins-bad 是其中的一个子项目。
必须从 monorepo 根目录构建，以便 meson 能够解析 gstreamer 和 gst-plugins-base 的子项目依赖。

## 依赖处理

### 系统依赖 (cmd-pkgs 安装)
- glib 2.88.0 (静态库，从 cmd-pkgs 安装)
- pcre2 10.47 (从源码编译，glib 的依赖)
- libffi 3.4.6 (从源码编译，gobject 的依赖)

### 子项目依赖 (meson subproject)
- gstreamer (核心库，从 monorepo 子项目构建)
- gst-plugins-base (基础插件，从 monorepo 子项目构建)

### 禁用的依赖 (网络不可达)
- orc (SIMD 优化，从 gitlab.freedesktop.org 无法下载)
- 各种可选插件依赖 (ogg, opus, etc.，meson wraps 无法下载)

## 关键问题及解决方案

### 1. OpenSLES 插件编译失败
**问题**: `SLES/OpenSLES_Android.h` 文件未找到
**根因**: OpenSLES 插件是 Android 专用的，使用了 Android 特有的头文件
**解决方案**: `-Dgst-plugins-bad:opensles=disabled`

### 2. glib 静态库链接缺少 pcre2 和 libffi 符号
**问题**: glib 从 cmd-pkgs 安装为静态库，但 .a 文件中引用了 pcre2 和 libffi 的符号
**解决方案**: 从 wrapdb.mesonbuild.com 下载 pcre2 和 libffi 源码，编译安装为系统库

### 3. meson 尝试下载 glib.wrap 导致超时
**问题**: glib.wrap 的 source_url 指向 GNOME 服务器 (download.gnome.org)，网络不可达
**解决方案**: 删除 glib.wrap 文件，强制 meson 使用系统安装的 glib (通过 pkg-config 发现)

### 4. llvm-ar 未找到
**问题**: meson 无法找到 llvm-ar (archiver)
**解决方案**: 使用 `--native-file` 指定完整路径的工具链

## 编译配置
```
meson setup build \
  --native-file=ohos-native.ini \
  --prefix=/storage/Users/currentUser/usr/local \
  --buildtype=release \
  --wrap-mode=nodownload \
  -Dbase=enabled -Dbad=enabled \
  -Dgood=disabled -Dugly=disabled \
  -Dlibav=disabled -Ddevtools=disabled \
  -Dges=disabled -Drtsp_server=disabled \
  -Dpython=disabled -Dsharp=disabled \
  -Dtests=disabled -Dexamples=disabled \
  -Dintrospection=disabled -Dtls=disabled \
  -Dbenchmarks=disabled -Dorc=disabled \
  -Dgpl=disabled -Dgst-full=disabled \
  -Dgst-plugins-bad:opensles=disabled
```

## 构建产物
- 102 个 GStreamer 插件 (.so)
- 36 个库文件 (libgst*.so)
- 468 个头文件
- 34 个 pkg-config 文件

---
编译时间: 2026-08-06
编译人员: AI编译助手 (OpenDesk)
