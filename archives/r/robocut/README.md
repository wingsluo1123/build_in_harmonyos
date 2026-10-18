# robocut

Robocut 是一个简单的图形程序，用 SVG 文件驱动 Graphtec Craft Robo 与 Silhouette
系列刻字机/绘图仪（Cameo、Portrait、SD 等）进行切割或绘制。

- 上游仓库: <https://github.com/Timmmm/robocut>
- 上游版本: `v1.0.11`（tag）
- 许可证: GPL-3.0-or-later

## 功能概述

- 读取 Inkscape 等生成的 SVG 文件并发送到刻字机
- 路径排序（普通排序 / 按包围盒排序）、介质类型、速度、压力、套刻标记（registration mark）等参数配置
- 切割动画预览（View → Animate）
- 通过 libusb 直接访问 USB 端点，无需厂商驱动（Windows 端需 WinUSB/Zadig）

## OHOS 适配

构建系统是 qmake（`Robocut.pro`）+ make。本制品仓在 HarmonyOS PC（aarch64）上的适配要点：

- **上游 `.pro` 缺少 `QT += widgets`**（只有 `QT += svg`）：Qt5 默认 `QT = core gui`，
  而 `svg` 模块 `depends = core gui`，不含 widgets；源码使用 `QApplication`、
  `QMainWindow`、`QDialog`、`QFileDialog`、`QMessageBox`、`QPushButton`。补丁
  `0001-Robocut.pro-add-qt-widgets.patch` 补齐。
- **必须使用模块化 Qt5 栈**：制品仓的单包 `qt/5.15.19` 是 `-skip qtsvg` 构建，不含
  Qt5Svg，无法满足 `QT += svg`；改用 `qt5-qtbase/5.15.2.2`（Core/Gui/Widgets）+
  `qt5-qtsvg/5.15.2.1`（QtSvg）。
- 这两个包的 `mkspecs` 与 `bin/qt.conf` 内嵌构建期绝对路径，直接调用包内 qmake 会报
  `Unknown module(s) in QT: core gui`；配方构造可重定位 qmake 视图解决（详见
  `1.0.11/notes.md`）。
- HMDFS 不接受 strip 后的 ELF，构建统一传 `QMAKE_STRIP=` / `STRIP=true`。

已知限制：GUI 交互与真实切割流程需要显示环境与 USB 切割机，本制品仓的测试只覆盖
「二进制可执行 + 自报版本 + 帮助文本」这一层。

## 依赖关系

编译依赖（Conan）:

- `qt5-qtbase/5.15.2.2` — Core / Gui / Widgets
- `qt5-qtsvg/5.15.2.1` — QtSvg（`QSvgRenderer`）
- `libusb/1.0.29` — USB 设备访问

运行依赖：Qt5（Core/Gui/Widgets/Svg）、libusb-1.0、OHOS 系统 GLESv2。

## 参考资料

- 项目主页: <https://robocut.org/>
- 源码仓库: <https://github.com/Timmmm/robocut>
