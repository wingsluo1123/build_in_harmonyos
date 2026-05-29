# libxslt

## 简介
libxslt 是一个 C 语言实现的 XSLT (Extensible Stylesheet Language Transformations) 库，基于 libxml2 XML 解析器。它用于将 XML 文档转换为其他格式（如 HTML、文本或其他 XML）。

## 主要组件
- **libxslt**: XSLT 1.0 核心库
- **libexslt**: EXSLT 扩展库（提供额外的数学、字符串、日期等功能）
- **xsltproc**: XSLT 命令行转换工具

## 依赖
- **libxml2** >= 2.9.13

## 编译信息
- **版本**: 1.1.45
- **构建系统**: CMake（autotools 在 HMDFS 上受限）
- **编译器**: clang
- **链接器**: GNU ld.bfd（lld 依赖 libxml2）

## 平台适配要点
1. 使用 CMake 构建（避免 HMDFS 权限问题）
2. 使用 `-fuse-ld=bfd` 代替 lld
3. 手动设置 RPATH（patchelf）
4. HMDFS 上 xsltproc 可能无法直接执行（平台限制 E046）

## 资源
- 官方网站: https://gitlab.gnome.org/GNOME/libxslt
- 文档: https://gnome.pages.gitlab.gnome.org/libxslt/