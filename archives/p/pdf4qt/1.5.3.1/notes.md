# pdf4qt 1.5.3.1 适配笔记

## 基本信息
- 软件: pdf4qt
- 版本: 1.5.3.1
- 状态: published (Conan 配方已生成并验证)
- 构建系统: cmake

## 适配概述
PDF4QT 是基于 Qt6 的开源 PDF 编辑器。本次适配构建了核心库 (Pdf4QtLibCore)，
包含 PDF 文档解析、渲染、加密、签名等核心功能。

## 适配决策

### 1. 仅构建核心库 (PDF4QT_BUILD_ONLY_CORE_LIBRARY=ON)
- **原因**: Qt6Svg、Qt6PrintSupport、Qt6TextToSpeech 未在 Conan 制品仓中发布
- **影响**: 核心库 Pdf4QtLibCore 可正常构建，包含所有 PDF 处理功能
- **未构建**: Pdf4QtLibWidgets、Pdf4QtEditor、Pdf4QtViewer 等GUI组件
- **核心库不实际使用 Qt6Svg** (仅引用了 Qt::SvgMiterJoin 枚举值)

### 2. blend2d 源码内嵌
- **原因**: blend2d 及其依赖 asmjit 未在 Conan 制品仓中发布
- **方案**: 在 conanfile.py 的 source() 中下载 blend2d 和 asmjit 源码，在 build() 中先构建 blend2d 静态库
- **构建参数**: BLEND2D_STATIC=ON, BLEND2D_NO_JIT=OFF (JIT 支持 AArch64)

### 3. std::execution 并行算法替换
- **原因**: OHOS libc++ 不支持 C++17 std::execution 并行算法
- **修改文件**: pdfexecutionpolicy.h, pdfvisitor.h, pdfcolorspaces.cpp, pdfdocumentreader.cpp, pdftextlayout.cpp, pdfpattern.cpp
- **方案**: 将 std::for_each(std::execution::seq/par, ...) 替换为 std::for_each(...)

### 4. Conan 目标别名
- **原因**: Conan 包的目标名称与标准 CMake FindXXX 目标不一致
- **添加别名**: OpenSSL::SSL, OpenSSL::Crypto, Freetype::Freetype, JPEG::JPEG, openjp2

### 5. fontconfig 查找
- **原因**: 原始 CMakeLists.txt 未声明 fontconfig 依赖
- **方案**: 添加 find_package(fontconfig CONFIG) 并链接到 Pdf4QtLibCore

## 依赖列表
- qtbase/6.11.1 (Qt6 Core, Gui, Xml)
- openssl/3.5.6.1.1
- freetype/2.14.3
- openjpeg/2.5.4
- libjpeg/10
- libpng/1.6.58
- lcms2/2.19
- zlib/1.3.1.1
- fontconfig/2.18.1.1
- blend2d (vendored, from github.com/blend2d/blend2d)

## 补丁
- patches/ohos-adapt.patch: 包含所有 OHOS 平台适配修改

---
**编译结束**: 2026-08-07
**最终状态**: published
---

**编译结束**: 2026-08-07 10:11
**最终状态**: published
