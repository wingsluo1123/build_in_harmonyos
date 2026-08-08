# siril 1.2.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载官方源码 tarball (gitlab.com/free-astro/siril tag 1.2.3)
2. 应用5个平台适配补丁 (configure.ac, src/Makefile.am, demosaicing.c, demosaicing_rtp.cpp, subprojects/Makefile.am)
3. 替换 intltool-based po/Makefile.am 为 msgfmt-based 版本 (intltool 不可用)
4. 运行 autoreconf --install --force (使用 aclocal-1.16 wrapper)
5. 运行 ./configure --enable-static --disable-shared
6. 修复 config.status umask 077 → 022 (OHOS setgid 权限问题)
7. make -j2
8. make install (DESTDIR staging)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | librtprocess 编译失败 | release tarball 中 librtprocess submodule 为空 | 补丁0001/0003/0004/0005: 用 HAVE_LIBRTPROCESS 守卫,使其可选 |
| 2 | intltool 不可用 | OHOS 平台无 intltool | 在 source() 中替换 po/Makefile.am 为 msgfmt-based 版本 |
| 3 | config.status Permission denied | OHOS setgid dirs + umask 077 导致临时文件创建失败 | 在 build() 中将 configure 脚本的 umask 077 替换为 022 |
| 4 | OPENCV_LIBS 硬编码 | configure.ac 中 OPENCV_LIBS 未用 pkg-config | 补丁0001: 改用 pkg-config --libs opencv4 |
| 5 | LIBHEIF/LIBRAW/EXIV2 CFLAGS 缺失 | AM_CPPFLAGS 未包含这些依赖的 CFLAGS | 补丁0001/0002: 添加到 AM_CPPFLAGS |
| 6 | glib proxy gettext 未链接 | glib 的 g_libintl_* 符号需要 -lintl | 补丁0001/0002: 添加 -lintl |
| 7 | gio-unix-2.0.pc 缺失 | conan glib 未单独生成 | build() 中手动生成 gio-unix-2.0.pc |
| 8 | aclocal 1.17 损坏 | 系统 aclocal 版本不兼容 | 创建 aclocal-1.16 wrapper 脚本 |

## 源码修改

| 补丁文件 | 修改内容 |
|---------|---------|
| 0001-configure.ac.patch | librtprocess 可选化,移除 intltool,OPENCV_LIBS 用 pkg-config,添加缺失 CFLAGS,添加 -lintl |
| 0002-src-Makefile.am.patch | 添加 LIBHEIF/LIBRAW/EXIV2 CFLAGS 和 -lintl 到 AM_CPPFLAGS |
| 0003-src-algos-demosaicing.c.patch | HAVE_LIBRTPROCESS 守卫 librtprocess 代码路径 |
| 0004-src-algos-demosaicing_rtp.cpp.patch | HAVE_LIBRTPROCESS 守卫 (修复重复 #ifdef) |
| 0005-subprojects-Makefile.am.patch | 从 SUBDIRS 移除 librtprocess (空 submodule) |

## 依赖版本

- cfitsio/4.6.4, json-glib/1.6.6, libde265/1.0.18, exiv2/0.28.7
- libraw/0.22.1, ffms2/5.0, wcslib/8.4, libheif/1.18.2
- gtk/3.24.38, gsl/2.8, fftw3f/3.3.10, opencv/4.12.0
- ffmpeg/7.1.5, libtiff/4.7.2, libjpeg/10, libpng/1.6.58
- libcurl/8.5.0, lcms2/2.19

## 验证结果

```bash
conan create archives/s/siril/1.2.3/conanfile.py --build=missing
# G2 门禁待修复 (conandata.yml patch 引用已同步,硬编码路径已修复)
```

## 注意事项

- siril 是应用程序 (package_type=application),非库; cpp_info.libs 为空,bindirs=["bin"]
- librtprocess 在 release tarball 中为空,必须保持 HAVE_LIBRTPROCESS 守卫
- po/Makefile.am 是新文件 (不在原始 tarball 中),通过 conanfile.py export_sources() 导出

---
**编译结束**: 2026-08-08 02:07
**最终状态**: built
---

**编译结束**: 2026-08-08 23:56
**最终状态**: built
