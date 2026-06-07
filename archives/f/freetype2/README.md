# freetype2

## 简介
FreeType 是一个免费、高质量、可移植的字体引擎库，用于渲染字体。它支持多种字体格式，包括 TrueType、Type 1、OpenType、CID-keyed Type 1 和 CFF。

## 官方网站
https://freetype.org

## 版本历史
- 2.13.2 (2026-05-26): 编译成功 (built)

## 编译说明
freetype2 在 OpenHarmony 上推荐使用 CMake 构建，autotools 在 HMDFS 上有临时文件权限问题。

### 依赖
- zlib (必需)
- harfbuzz (可选)
- libpng (可选)
- bzip2 (可选)
- brotli (可选)

### 构建
```bash
cmake -DCMAKE_INSTALL_PREFIX=~/usr/local -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..
make -j4
make install
```

## pkg-config 验证
```bash
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --modversion freetype2
# 输出: 26.1.20 (libtool 格式，对应 2.13.2)
```

---
*最后更新: 2026-05-26*