# QCustomPlot

QCustomPlot 是一个基于 Qt 的 C++ 绘图部件库：以单个 `QCustomPlot` 部件承载曲线、
散点、柱状图、颜色图、金融图等 2D 图表，内置坐标轴刻度生成、图例、绘图项、
交互缩放/拖拽与 PNG/JPG/BMP/PDF 导出，广泛用于科学计算与桌面应用的实时数据
可视化。

## 功能概述

- `QCustomPlot` 部件：多坐标轴矩形（四边坐标轴 + 次级坐标轴）、多图层
- 图元：`QCPGraph`（折线/散点）、`QCPBars`、`QCPColorMap`、`QCPFinancial`、
  `QCPStatisticalBox`、`QCPCurve`
- 坐标轴：`QCPAxisTicker` 家族（线性、对数、时间、日期、文本、固定间隔）
- 图例与布局：`QCPLegend`、`QCPLayoutGrid`、图例项自动同步
- 绘图项：线段、箭头、文本、矩形、椭圆、图片等 `QCPAbstractItem` 子类
- 导出：`toPixmap`、`savePng/saveJpg/saveBmp`（可设物理尺寸与缩放）、`savePdf`
- 对外提供 CMake 包 `QCustomPlot` 与目标 `QCustomPlot::QCustomPlot`

## OHOS 适配

- **PrintSupport 缺失**：OHOS `qtbase/6.11.1` 以 `FEATURE_printsupport=OFF`
  构建，不带 `Qt6PrintSupport` 模块。构建脚本用
  `find_package(Qt6 QUIET OPTIONAL_COMPONENTS PrintSupport)` 做能力探测：
  组件存在则链接 `Qt6::PrintSupport`；缺失则给目标定义
  `QT_NO_PRINTER`，`savePdf` 走上游自带存根（返回 false、不写文件）。补丁
  0001 给公共头的 `<QtPrintSupport/QtPrintSupport>` 包含加上同一个能力宏守卫。
- **上游无构建系统**：上游只发布 `qcustomplot.cpp` / `qcustomplot.h` /
  `GPL.txt` / `changelog.txt`。配方的 `CMakeLists.txt` 负责编译、安装与导出
  relocatable CMake 包；`cmake/QCustomPlotConfig.cmake.in` 生成
  `QCustomPlotConfig.cmake`（`find_dependency(Qt6 COMPONENTS Core Gui Widgets)`）。
- **SONAME**：OHOS CMake 使用 Generic 平台模块，没有共享库 SONAME 规则，
  配方注入 `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,`。
- **软链接**：设备存储（HMDFS）拒绝 `symlink(2)`，配方运行期探测不可用时
  设置 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`，安装单一未版本化
  `libQCustomPlot.so`（仍带裸 `DT_SONAME`）。
- **CMakeDeps**：qtbase 使用 `cmake_find_mode=none`，配方自行写
  `conan_cmakedeps_paths.cmake` 指向真实 `Qt6Config.cmake` 与 Qt 的
  lib/include 目录。

## 依赖关系

- 编译依赖：`qtbase/6.11.1`（Qt6Core、Qt6Gui、Qt6Widgets）
- 运行依赖：`qtbase/6.11.1`（`libQt6Widgets.so.6`、`libQt6Gui.so.6`、
  `libQt6Core.so.6`）

## 测试

上游不含任何测试套件（0 个测试函数）。`test_package/` 提供 16 个具名消费者
用例，覆盖图表构建、坐标轴/ticker、图例、绘图项、颜色图、离屏渲染、
PNG/PDF 导出与数据容器操作，真机 16/16 通过。

## 参考资料

- 官网：https://www.qcustomplot.com/
- 源码归档：https://www.qcustomplot.com/release/2.1.1/QCustomPlot-source.tar.gz
