# xlispstat

`xlispstat`（XLISP-STAT）是 Luke Tierney（爱荷华大学统计系）基于 XLISP 方言的交互式统计计算与动态图形环境，提供回归、方差分析、广义线性模型、矩阵运算和可旋转动态图形等能力，是 R 之前影响最大的统计编程环境之一。

上游 canonical 源码：[uiowa 官方发布 tarball](https://homepage.cs.uiowa.edu/~luke/xls/xlispstat/current/xlispstat-3-52-23.tar.gz)（GitHub 镜像 [jhbadger/xlispstat](https://github.com/jhbadger/xlispstat) 无 tag）。许可证 HPND-sell-variant。

## 功能概述

- `xlispstat` — 交互式统计环境入口（shell 包装脚本，内部执行 XLISP 解释器 + 默认工作区 xlisp.wks）
- 统计层：回归（`regression-model`）、ANOVA、GLM、非参数方法、优化
- 数据层：lists/vectors/matrices、compound data、`mean`/`variance` 等数值方法
- 图形层：直方图、散点图、可旋转 3D 散点（本包为 `--without-x` 终端模式：图形命令降级为 gnuplot 调用，无 gnuplot 时纯计算功能不受影响）

## 依赖关系

- 编译依赖：无（`--without-x` 构建，仅 libc + libm）
- 运行依赖：无（可选：`gnuplot` 存在时启用终端模式绘图）
- Conan 依赖：无（`requirements()` 为空，W0 检查通过）
- 注：X11 GUI 路径需要 libX11 + libxaw/libxmu/libxext/libxpm，其中 libxaw/libxmu/libxt 尚未入库；如需 GUI 版本应另行拆分依赖库单独适配。

## OHOS 适配要点

- 老式 autoconf 构建；上游不支持并行 make（配方固定 `-j1`）
- **构建必须原生执行解释器**：make 中途要把 `src/lsp/*.lsp` 编译为 `.fsl` 并 dump 默认工作区，因此不支持纯交叉编译；配方在非原生环境显式报错（不留假成功）
- OHOS 上在执行 lsp 编译前用 `binary-sign-tool` 对解释器签名
- 上游 Makefile 忽略环境 CFLAGS，经 configure 命令行 `UCFLAGS="$CFLAGS -O2"` 注入
- 补丁 0001 使 `xlispstat` 包装脚本优先继承 `XLISPLIB` 环境变量（包可重定位），不改任何 C 源码与测试断言

## 版本

- `3.52.23` — 前置适配完成（配方 + test_package + 本机静态验证）；待真机 shadow CI；见 [3.52.23/notes.md](3.52.23/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/xlispstat` | 统计环境入口（shell 包装脚本） |
| `share/xlispstat/xlisp` | XLISP 解释器（arm64 ELF） |
| `share/xlispstat/xlisp.wks` | 默认工作区（含编译好的统计层 .fsl） |
| `share/xlispstat/xlisp.hlp` | 帮助数据库 |
| `share/xlispstat/Autoload` `Data` `Examples` | 自动加载模块、示例数据、示例脚本 |
