# jigsaw-generator

Jigsaw Generator 是一个命令行工具，把 YAML 定义的拼图数据转换成可打印的拼图/卡片排序（Tarsia formulator 风格）物料，产出 LaTeX 源码（.tex）与 Markdown（.md），装 LaTeX 后可直接出 PDF。

## 功能概述

- YAML 描述拼图内容，支持多种版式：hexagon、smallhexagon、parquet、dominoes、cards、cardsort、triangle 等
- 生成 .tex（table / puzzle / solution 三类）与 .md 文件
- 默认调用 pdflatex 出 PDF（`--nomakepdf` 可跳过 LaTeX 步骤）
- 支持用户自定义版式模板与 `--texfilter` / `--mdfilter` 后处理过滤器
- `examples/` 内置示例拼图数据

## OHOS 适配

- 纯 Python 3 包：无 C/C++ 编译。构建 = 上游 `Makefile.in` build 目标的那条 `sed` 替换（生成 `jigsaw-generate` 入口脚本）+ 文件安装
- 入口脚本的 `pkgdatadir` 在打包时写死为绝对路径（与上游 `make install --prefix` 一致），指向 `<pkg>/lib/jigsaw-generator`（含 `jigsaw/` Python 包与 `templates/` 模板）
- 构建环境不含 LaTeX：上游 `make -C doc build`（生成 doc/jigsaw-generator.pdf）未执行，包内只带 .tex 源码
- 运行前提（设备端）：需要 python3 与 PyYAML；缺 pdflatex 时用 `--nomakepdf`（该模式下不写 .tex、不发起任何 LaTeX 调用，只产出 .md）

## 依赖关系

- 编译依赖：无（无编译步骤）
- 运行依赖：python3、PyYAML（ohpcd 制品仓未收录，非 conan 依赖）、pdflatex（仅生成 PDF 时）

## 参考资料

- 上游仓库：https://github.com/juliangilbey/jigsaw-generator（tag `upstream/0.2.7`）
- Debian 包：jigsaw-generator（`apt install jigsaw-generator`）
- 许可证：主体 GPL-3.0-or-later（appdirs.py 为独立许可证、goose.png 公有领域，详见包内 COPYING）
