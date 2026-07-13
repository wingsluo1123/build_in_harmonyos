# libvisio 0.1.5

## 简介

libvisio 是一个用于解析和渲染 Microsoft Visio 文档（.vsd/.vss）的 C++ 库。它是 Document Liberation Project 的一部分，为 LibreOffice 等办公软件提供 Visio 文件格式支持。

## 构建信息

| 项目 | 值 |
|------|-----|
| 版本 | 0.1.5 |
| 构建系统 | autotools |
| 目标平台 | aarch64-unknown-linux-ohos (HarmonyOS) |
| 编译器 | clang / clang++ |
| 构建状态 | ✅ built |
| 构建日期 | 2026-06-25 |

## 源码

- **下载地址**: https://dev-www.libreoffice.org/src/libvisio/libvisio-0.1.5.tar.xz
- **SHA256**: `430a067903660bb1b97daf4b045e408a1bb75ca45e615cf05fb1a4da65fc5a8c`
- **格式**: tar.xz

## 依赖

| 依赖 | 版本 |
|------|------|
| librevenge | 0.0.5 |
| libxml2 | 2.9.8 |
| zlib | 1.3.1 |
| icu4c | 77 |

## 补丁

| 补丁 | 类型 | 说明 |
|------|------|------|
| 0001-config.guess.patch | 平台适配 | 添加 HarmonyOS 平台识别（`__OHOS__` 宏检测、LIBC case、echo/exit 输出） |
| 0002-config.sub.patch | 平台适配 | 添加 `linux-ohos*` 到 maybe_os 和 OS 列表，防止 `-linux*)` 兜底替换 |

## 构建命令

```bash
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/share/pkgconfig"
export CPPFLAGS="-I$PREFIX/include"
export LDFLAGS="-L$PREFIX/lib"

./configure --prefix=$PREFIX --disable-tests --host=aarch64-unknown-linux-ohos
./config.status

# 移除 -Werror（clang 弃用警告兼容）
find . -name Makefile -exec sed -i 's/-Werror//g' {} \;

make -j1
make install DESTDIR=$DESTDIR
```

## 交付物

- `lib/libvisio-0.1.so.1.0.5` — 共享库
- `lib/pkgconfig/libvisio-0.1.pc` — pkg-config 配置
- `include/libvisio-0.1/libvisio/` — 头文件（libvisio.h, VisioDocument.h）
- `bin/vsd2raw` — VSD 文档转换工具
- `bin/vss2raw` — VSS 模板转换工具
- `bin/vsd2xhtml` — VSD→SVG 转换工具
- `bin/vss2xhtml` — VSS→SVG 转换工具
- `bin/vsd2text` — VSD→文本转换工具
- `bin/vss2text` — VSS→文本转换工具

## 已知限制

1. 测试已禁用（`--disable-tests`），因为 cppunit 在 HarmonyOS 上不可用
2. 共享库未 strip，包含调试符号（约 33MB）
3. 运行时需确保 `libxml2.so.16` 符号链接存在
4. 不要使用 `autoreconf -fi`，会导致 autoconf 2.72 兼容性问题
