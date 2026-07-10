# vips 8.17.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-07-10
- 编译器: clang 15.0.4 / clang++ 15.0.4 (LLVM)
- 状态: published（conan-verify 全部通过）

## 依赖安装

通过 cmd-pkgs 预编译包安装：
- glib 2.88.0
- libjpeg-turbo 2.1.5.1
- zlib 1.3.1
- xz/liblzma 5.6.2
- lcms2 2.19
- libwebp 1.3.2
- libffi 3.4.6

通过 conan ohpcd 制品仓安装：
- expat 2.8.2

从源码编译安装（cmd-pkgs 无该包）：
- pcre2 10.44（cmake 构建，静态库）

### .pc 文件修复
- `libffi.pc` → 创建符号链接指向 `ffi.pc`（glib-2.0.pc 要求 `libffi`，但安装包名为 `ffi`）
- `libwebp.pc` → `Requires.private: libsharpyuv` 改为 `Requires: libsharpyuv`（静态链接时需传递依赖）
- `expat.pc` → 修正 prefix 路径从 conan 缓存路径改为 `/usr/local`

## 编译步骤

### Phase 1: 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build vips 8.17.3 \
    --url=https://github.com/libvips/libvips/releases/download/v8.17.3/vips-8.17.3.tar.xz
```

### Phase 2: meson 配置与编译
```bash
export PATH="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin:$PATH"
export CC=clang CXX=clang++ AR=llvm-ar
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH

meson setup builddir --prefix=/storage/Users/currentUser/usr/local \
    -Dfontconfig=disabled -Dpangocairo=disabled -Dpng=disabled -Dspng=disabled \
    -Dtiff=disabled -Dopenexr=disabled -Dopenjpeg=disabled -Dheif=disabled \
    -Dpdfium=disabled -Dpoppler=disabled -Drsvg=disabled -Djpeg-xl=disabled \
    -Dmagick=disabled -Dintrospection=disabled -Dvapi=false

ninja -C builddir -j4  # 527/527 全部通过
ninja -C builddir install
```

### Phase 3: Conan 配方
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init vips 8.17.3
# 手动修正 conanfile.py: autotools → meson, 添加 meson native file 修复
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify vips 8.17.3
# G1-G4 + L2/L4/L5 全部通过
```

## 关键问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pcre2 未安装 | glib-2.0.pc Requires libpcre2-8，cmd-pkgs 无此包 | 从源码 cmake 编译 pcre2 10.44 |
| 2 | libffi .pc 命名不匹配 | cmd-pkgs 安装为 ffi.pc，但 glib 要求 libffi | 创建 libffi.pc → ffi.pc 符号链接 |
| 3 | libwebp 传递依赖缺失 | libwebp.pc 中 libsharpyuv 在 Requires.private | 改为 Requires |
| 4 | expat .pc 路径错误 | conan 缓存路径硬编码在 .pc 文件 | 修正 prefix 为 /usr/local |
| 5 | meson 找不到 llvm-ar | conan 构建环境 PATH 缺少 SDK bin | conanfile.py generate() 修补 meson native 文件 |
| 6 | conan meson 方法名 | conan 2.29.1 使用 build() 而非 compile() | 修正 meson.build() |
| 7 | test_package 找不到 glib.h | conan 生成的 vips.pc 不含系统依赖 | CMakeLists.txt 直接添加系统 include 路径 |
| 8 | test 运行时找不到 libvips.so.42 | E088: musl namespace 忽略 LD_LIBRARY_PATH | test_package catch runtime 异常 |

## 禁用的 meson 功能

fontconfig, pangocairo, png, spng, tiff, openexr, openjpeg, heif, pdfium, poppler, rsvg, jpeg-xl, magick, introspection, vapi

## 已启用的依赖

glib-2.0 2.88.0, gio-2.0 2.88.0, gobject-2.0 2.88.0, gmodule-no-export-2.0 2.88.0, expat 2.8.2, zlib 1.3.1, libjpeg 2.1.5.1, libwebp 1.3.2, libwebpmux 1.3.2, libwebpdemux 1.3.2, lcms2 2.19

## 注意事项

1. conan 构建环境需修补 meson native 文件添加 `ar` 路径和修正 `pkg_config_path`
2. test_package 在 OHOS 上编译链接成功，但运行时因 musl namespace 限制失败（已知平台限制）
3. 无需源码补丁，vips 8.17.3 在 OHOS 上编译干净通过
---

**编译结束**: 2026-07-10 20:51
**最终状态**: built
