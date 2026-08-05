# libgd

## 简介
GD graphics library for dynamically creating images. Supports PNG, JPEG, GIF, WBMP, BMP formats and Freetype text rendering.

## OHOS 适配
- 构建系统: cmake
- libgd 使用 CMake 内置的 Find 模块 (FindPNG/FindJPEG/FindFreetype/FindZLIB)
- 通过 conan cache_variables 预设依赖路径，绕过 find 模块搜索
- OHOS 需设置 ohos-cmake-rules.cmake 以生成正确的 SONAME
- 详见各版本 notes.md 获取适配详情

## 依赖
- libpng (PNG 支持)
- libjpeg (JPEG 支持)
- freetype (文本渲染)
- zlib (压缩, GD 格式)

## 功能验证
- conan create + test_package: dlopen libgd.so + gdImageCreate/gdImageDestroy + 版本检查
- 详见 2.3.3/notes.md

## 参考
- https://libgd.github.io/
- https://github.com/libgd/libgd
