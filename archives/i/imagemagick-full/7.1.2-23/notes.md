# imagemagick-full 7.1.2-23 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang/clang++ 15.0.4
- 状态: built
- Conan 适配: 是 (conanfile.py + conandata.yml + test_package/)

## 编译步骤

1. `init-build imagemagick-full 7.1.2-23 --url=...`
2. 应用平台补丁:
   - `0003-config-config.guess.patch` — OHOS/HarmonyOS triplet检测
   - `0004-config-config.sub.patch` — ohos-linux triplet支持
   - `0006-configure.patch` — HMDFS umask 077→022 修复
3. 安装Conan依赖 (libwebp, libxml2, lcms2, fftw 等通过conan install)
4. 手动创建缺失的pkg-config文件 (zlib.pc, liblzma.pc, libopenjp2.pc, libwebpmux.pc, libwebpdemux.pc)
5. `umask 022 && ./configure --prefix=$DEFAULT_PREFIX --enable-shared --with-jpeg --with-png --with-tiff --with-freetype --with-fontconfig --with-openjp2 --with-webp --with-xml --with-fftw --without-heic --without-djvu --without-raw --disable-openmp`
6. `make -j2 && make install DESTDIR=$TEST_PREFIX && make install`
7. 验证 `$DEFAULT_PREFIX/bin/magick --version`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E007 | config.guess/config.sub 不识别 OHOS triplet | 缺少 __OHOS__/ohos-linux 检测 | patch 0003/0004 |
| E050a | config.status 创建临时目录 Permission denied | HMDFS umask 077 权限问题 | patch 0006 umask 022 |
| 新 | zlib/liblzma 无pkg-config文件 | conan PkgConfigDeps不自动为transitive依赖生成.pc | 手动创建zlib.pc和liblzma.pc |
| 新 | ImageMagick查找libopenjp2而非openjpeg | pkg-config名称不匹配 | 创建libopenjp2.pc别名 |
| 新 | libwebpmux/libwebpdemux无.pc文件 | conan libwebp包不生成子库.pc | 手动创建libwebpmux.pc和libwebpdemux.pc |
| 新 | make check失败 | 系统lld链接器依赖libxml2.so.16但系统lib路径只读 | 非ImageMagick问题，二进制验证通过 |

## 启用的 Delegate 对比

| Delegate | 之前版本(2026-05-26) | 本次(2026-08-06) | 说明 |
|----------|---------------------|-------------------|------|
| fftw | ❌ | ✅ | 新增依赖 |
| fontconfig | ✅ | ✅ | |
| freetype | ✅ | ✅ | |
| jng | ❌ | ✅ | 随png启用 |
| jp2 | ✅ | ✅ | 现正确链接openjpeg |
| jpeg | ✅ | ✅ | |
| lzma | ✅ | ✅ | |
| png | ✅ | ✅ | |
| tiff | ✅ | ✅ | |
| webp | ❌ (禁用) | ✅ | **新增** |
| xml | ❌ (禁用) | ✅ | **新增** |
| zlib | ✅ | ✅ | |
| zstd | ❌ | ✅ | **新增** |
| djvu | ✅ | ❌ | ddjvuapi未发布 |
| lcms | ✅ | ❌ | lcms2二进制未发布 |
| heic | ❌ (禁用) | ❌ | libheif依赖链未发布 |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libjpeg-turbo | 3.2.0 | conan ohpcd |
| libpng | 1.6.58 | conan ohpcd |
| libtiff | 4.7.2 | conan ohpcd |
| freetype | 2.14.3 | conan ohpcd |
| fontconfig | 2.18.1.1 | conan ohpcd |
| openjpeg | 2.5.4 | conan ohpcd |
| libwebp | 1.6.0 | conan ohpcd |
| libxml2 | 2.15.3.1 | conan ohpcd |
| zstd | 1.5.7 | conan ohpcd |
| fftw | 3.3.10 | conan ohpcd |
| zlib | 1.3.1.1 | conan ohpcd (transitive) |
| xz/lzma | 5.6.2 | conan ohpcd (transitive) |

## 验证结果

```bash
$ magick --version
Version: ImageMagick 7.1.2-23 Q16-HDRI aarch64 6c51b2de5:20260516 https://imagemagick.org
Copyright: (C) 1999 ImageMagick Studio LLC
License: https://imagemagick.org/license/
Features: Cipher DPC HDRI
Delegates (built-in): fftw fontconfig freetype jng jp2 jpeg lzma png tiff webp xml zlib zstd
Compiler: clang (15.0.4)
```

## 待转专家分析

以下依赖库未发布到制品仓，导致对应delegate未启用：
1. **libheif** — HEIC格式支持（依赖链: libheif → libde265, x265, aom 全部缺失）
2. **lcms2** — 色彩管理（recipe已发布但binary未构建）
3. **djvulibre** — DjVu格式支持（ddjvuapi库缺失）

---

**编译结束**: 2026-08-06
**最终状态**: built (conan adapted)
