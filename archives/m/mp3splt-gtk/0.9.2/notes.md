# mp3splt-gtk 0.9.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-07
- 编译器: clang/clang++ 15.0.4
- 状态: built (conan recipe created, conan-verify failed due to missing dependency)

## 编译步骤

```bash
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX --disable-audacious --disable-gstreamer --disable-gnome --disable-doxygen_doc --disable-cutter
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 依赖 libmp3splt 缺失 | mp3splt-gtk 需 libmp3splt >= 0.9.2 | 从源码编译 libmp3splt 0.9.2 |
| 2 | 依赖 GTK3 缺失 | ohpcd 无 GTK3 包 | 从源码编译 GTK3 3.24.51 |
| 3 | GTK3 依赖 cairo-gobject 缺失 | ohpcd 的 cairo 未构建 gobject 支持 | 从源码重新编译 cairo 1.18.4 |
| 4 | GTK3 依赖 atk 缺失 | ohpcd 无 atk/at-spi2-core | 从源码编译 at-spi2-core 2.50.0 |
| 5 | OHOS 无法执行临时目录中的 ELF 二进制 | 安全限制 | 使用系统工具 + wrapper 脚本 |
| 6 | 系统的 glib-compile-resources 版本过低 | glib 2.38.2 不支持 --dependency-file | 创建 wrapper 去除不支持选项 |
| 7 | config.status 无法创建临时文件 | HMDFS 文件系统限制 | sed 修复 config.status |
| 8 | libltdl 未找到 | 系统无 libltdl 共享库 | 编译最小 libltdl wrapper |
| 9 | conan create 失败 | libmp3splt/0.9.2 未发布到制品仓 | 需先适配发布 libmp3splt |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libmp3splt | 0.9.2 | 源码编译 |
| GTK+3 | 3.24.51 | 源码编译 |
| at-spi2-core (atk) | 2.50.0 | 源码编译 |
| cairo (with gobject) | 1.18.4 | 源码编译 |
| glib | 2.84.0.1 | ohpcd |
| pango | 1.56.4 | ohpcd |
| harfbuzz | 14.2.0.1 | ohpcd |
| freetype | 2.14.3 | ohpcd |
| fontconfig | 2.18.1 | ohpcd |
| libmad | 0.15.1b | cmd-pkgs |
| libid3tag | 0.16.3 | cmd-pkgs |
| libogg | 1.3.5 | ohpcd |
| libvorbis | 1.3.7 | ohpcd |
| flac | 1.4.3 | ohpcd |
| pcre2 | 10.45 | ohpcd |

## 构建产物
- bin/mp3splt-gtk (256KB ELF executable)

## Conan 配方
- conanfile.py 已创建
- 依赖: libmp3splt/0.9.2, gtk/3.24.51, glib/2.84.0.1
- conan-verify G2 失败: libmp3splt/0.9.2 未在制品仓
- 需要先适配并发布 libmp3splt 到制品仓

---

**编译结束**: 2026-08-07
**最终状态**: built (conan recipe pending dependency)
