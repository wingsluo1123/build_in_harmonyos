# HarfBuzz

HarfBuzz 是一个文本塑形（text shaping）引擎，用于将 Unicode 文本转换为正确定位的字形序列，支持 OpenType、TrueType 等字体格式。广泛应用于 Firefox、Chrome、Pango、Flutter 等项目。

- **Homepage**: https://harfbuzz.github.io/
- **License**: MIT
- **Build System**: CMake (推荐) / Meson / Autotools
- **Category**: gfx (字体/文本渲染)

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 14.2.0 | built | 2026-07-22 | 含 graphite2 支持，CMake 构建 |

## OHOS 适配要点

1. **构建系统**: 使用 CMake（meson 在 HMDFS 上有 subprocess 限制）
2. **graphite2 支持**: CMake 选项 `HB_HAVE_GRAPHITE2=ON`，依赖 graphite2/1.3.14
3. **freetype 支持**: CMake 选项 `HB_HAVE_FREETYPE=ON`，依赖 freetype/2.14.3
4. **静态编译**: `BUILD_SHARED_LIBS=OFF` (R5/R26)
5. **禁用特性**: glib/icu/cairo/gobject 不可用，`HB_BUILD_UTILS=OFF` 不构建工具
6. **头文件路径**: `package_info()` 需设置 `includedirs = ["include/harfbuzz"]`
7. **传递依赖**: `package_info()` 需设置 `cpp_info.requires = ["graphite2::graphite2", "freetype::freetype"]`
8. **test_package**: 必须使用 C++ (test.cpp)，因为 harfbuzz 和 graphite2 是 C++ 库

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| graphite2 | 1.3.14 | Conan (ohpcd) |
| freetype | 2.14.3 | Conan (ohpcd) |

## 参考
- 官网: https://harfbuzz.github.io/
- 源码: https://github.com/harfbuzz/harfbuzz
