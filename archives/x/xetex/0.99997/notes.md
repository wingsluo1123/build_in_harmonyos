# xetex 0.99997 适配笔记

## 编译环境
- 构建系统: custom (autotools + 手动编译)
- 编译日期: 2026-07-09
- 编译器: clang/clang++
- 状态: built

## HMDFS 兼容性修复

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | umask 077 目录不可写 | HMDFS setgid 位导致 700 目录无法创建文件 | 全局 sed 替换 umask 077→022 |
| 2 | ../../ 路径遍历不稳定 | HMDFS 对多级 ../ 解析不一致 | 子目录创建本地 build-aux |
| 3 | getcwd 失败 | HMDFS 无法解析含 ../ 的当前路径 | 预配置子目录避免递归 make |
| 4 | config.guess 不认识 HarmonyOS | 缺少 HarmonyOS 枚举 | 添加 HarmonyOS 到 Linux 分支 |
| 5 | automake/libtool 缺失 | 系统未预装 | 从源码手动安装到 $HOME/.local |
| 6 | fontconfig 官方源 403 | freedesktop.org 拒绝访问 | 用 meson 从 GitHub 源码构建 |
| 7 | harfbuzz autotools 宏未展开 | PKG_CHECK_MODULES/AX_PTHREAD 缺 m4 | 直接编译源文件绕过 autotools |
| 8 | graphite2 cmake 只建 .so | CMakeLists.txt 硬编码 SHARED | 修改为 STATIC |
| 9 | AC_HEADER_STDC 检查失败 | OHOS 头文件检测差异 | 设置 ac_cv_header_stdc=yes |

## 依赖构建

| 依赖 | 来源 | 构建方式 |
|------|------|---------|
| freetype/2.14.3 | conan 缓存 | 预构建 |
| zlib/1.3.1.1 | conan 缓存 | 预构建 |
| expat/2.8.2 | conan 缓存 | 预构建 |
| fontconfig/2.16.0 | GitHub 源码 | meson 构建 |
| ICU 55.1 | XeTeX 内置源码 | autotools（修复 PKG_ 宏） |
| graphite2 | XeTeX 内置源码 | cmake（SHARED→STATIC） |
| harfbuzz 1.3.2 | XeTeX 内置源码 | 直接编译 .cc 文件 |
| libpng 1.6.16 | XeTeX 内置源码 | 直接编译 .c 文件 |
| poppler/xpdf | XeTeX 内置源码 | 部分编译 + stub |
| teckit | stub | 空 stub 实现 |

## 编译步骤

```bash
# 1. 安装 automake/libtool 到 $HOME/.local
# 2. 下载源码，复制 build-aux 文件
# 3. 修正 config.guess、umask、AC_CONFIG_AUX_DIR
# 4. 生成 configure（顶层 + 子目录）
# 5. 构建 fontconfig（meson）、ICU、graphite2（cmake）、harfbuzz（直接编译）、libpng
# 6. 顶层 configure + make
# 7. make -C texk/web2c xetex
```
---

**编译结束**: 2026-07-09 21:57
**最终状态**: built
