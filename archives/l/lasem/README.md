# lasem

SVG 与 MathML 渲染库, 提供 DOM 风格 API (纯 C 实现)。

## 功能概述

- MathML 与 SVG 文档解析 (libxml2) 与 DOM 树构建
- 基于 cairo + pango 的 2D 渲染 (PNG/PDF/SVG/PS 等后端)
- 内嵌 itex2mml (LaTeX 数学公式转 MathML, flex/bison 生成)
- 附带 lasem-render-0.6 命令行渲染工具

## OHOS 适配

- meson 构建; introspection/documentation/viewer 因缺少
  gobject-introspection、gi-docgen、gtk4 而关闭, 与 pango/cairo
  等 GNOME 系配方口径一致
- 构建期需 flex/bison (itex2mml) 与 xgettext (po 翻译), 均由
  tool_requires 提供
- 安装产物含 bin/lasem-render-0.6, 已按 R38 声明 commands.json
- 与 Linux 的差异: 只读 /tmp 与 XPM 代码签名为鸿蒙特有处理,
  渲染链路本身与 Linux 行为一致

## 依赖关系

- 编译依赖: glib、cairo、pango、harfbuzz、gdk-pixbuf、libxml2
- 构建工具: meson、flex、bison、gettext

## 参考资料

- 官网: https://lasemproject.github.io/lasem/
- 源码: https://github.com/LasemProject/lasem
