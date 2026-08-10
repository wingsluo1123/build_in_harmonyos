# libgphoto2 2.5.31 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-11
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built

## 编译步骤

1. **Init**: `python3 ohc-run.py init-build libgphoto2 2.5.31 --url=https://github.com/gphoto/libgphoto2/archive/refs/tags/v2.5.31.tar.gz`
2. **Apply patches**: 5 patches applied to clean source
   - 0001: ohos-patched config.guess (aarch64-unknown-linux-ohos)
   - 0002: ohos-patched config.sub
   - 0003: pkg.m4 (pkg-config macros)
   - 0004: gettext m4 macros (autopoint not available)
   - 0005: config.rpath (for gettext lib-link support)
3. **autoreconf**: `autoreconf -fi --no-recursive -I auto-m4 -I libgphoto2_port/gphoto-m4` (top-level + subdirectory)
4. **Restore ohos patches**: config.guess/config.sub restored after autoreconf overwrites them
5. **Fix configure**: umask 077→022, ./confXXXXXX→${HOME}/tmp/confXXXXXX (same as libexif)
6. **Configure**: `./configure --prefix=$DEFAULT_PREFIX --disable-nls --without-libusb1 LTDLINCL="-I$DEFAULT_PREFIX/include" LIBLTDL="-L$DEFAULT_PREFIX/lib -lltdl"`
7. **Build**: `make -j1` — SUCCESS
8. **Install**: `make install` — SUCCESS
9. **Test**: `make check` — PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Source from git archive has no configure | Git archive doesn't include generated files | Run autoreconf -fi |
| 2 | autopoint not found | gettext not installed on OHOS | Include gettext m4 files as patches (0004, 0005) |
| 3 | Missing lib-*.m4 macros | AC_LIB_PREPARE_PREFIX etc. from gettext gnulib | Copy lib-ld.m4, lib-link.m4, lib-prefix.m4 |
| 4 | po/Makefile.in.in missing | Normally created by autopoint | Copy from gettext source |
| 5 | config.guess overwritten by autoreconf | autoreconf -f overwrites aux files | Save and restore ohos-patched versions |
| 6 | Subdirectory needs separate autoreconf | AC_CONFIG_SUBDIRS([libgphoto2_port]) | Run autoreconf in subdirectory with same -I flags |
| 7 | configure umask 077 / temp dir | SELinux restricts ./confXXXXXX | Fix umask to 022, use ${HOME}/tmp/confXXXXXX |
| 8 | libexif not detected by configure | PKG_CONFIG_PATH not set | Set PKG_CONFIG_PATH to /storage/Users/currentUser/usr/local/lib/pkgconfig |

## 源码修改

- `0001-auto-aux-config.guess.patch`: E007 OpenHarmony平台识别
- `0002-auto-aux-config.sub.patch`: E007 ohos-linux三元组支持
- `0003-auto-m4-pkg.m4.patch`: 添加pkg-config m4宏到项目本地
- `0004-auto-m4-gettext-macros.patch`: 添加gettext m4宏(autopoint不可用)
- `0005-auto-aux-config.rpath.patch`: 添加config.rpath用于gettext lib-link支持

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libtool (provides libltdl) | 2.5.4 | 已安装 |
| libexif | 0.6.26 | 已安装 |
| popt | 1.16 | Conan repo (ohpcd) |
| zlib | 1.3.1 | Conan repo (ohpcd) |

## 验证结果

```bash
$ pkg-config --modversion libgphoto2
2.5.31
$ pkg-config --cflags libgphoto2
-I/storage/Users/currentUser/usr/local/include -I/storage/Users/currentUser/usr/local/include/gphoto2
$ pkg-config --libs libgphoto2
-L/storage/Users/currentUser/usr/local/lib -lgphoto2 -lm -lgphoto2_port -lm
$ pkg-config --modversion libgphoto2_port
0.12.2
$ sh auto-aux/config.guess
aarch64-unknown-linux-ohos
```

## 注意事项

- USB IOLib已disabled(--without-libusb1)，因OpenHarmony libusb1 API差异
- NLS已disabled(--disable-nls)，避免gettext复杂性
- libltdl需先构建安装才能配置libgphoto2 (libtool/2.5.4)
- autoreconf需手动指定-I路径（auto-m4和gphoto-m4）
- git checkout版本不含configure，需autoreconf生成
- gettext m4宏作为补丁包含(autopoint在CI环境不可用)
- configure需修复umask和临时目录问题(same as libexif)

---
**编译结束**: 2026-08-11 00:50
**最终状态**: built
---

**编译结束**: 2026-08-11 02:04
**最终状态**: built
