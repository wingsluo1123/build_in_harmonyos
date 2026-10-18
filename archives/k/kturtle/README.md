# kturtle — KDE 教育编程环境（Turtle 图形）

## 软件简介

kturtle 是 KDE Education 中的 Logo 语言编程教学环境：交互式编辑器 + 海龟
画布即时执行 Turtle 程序，内置错误对话框、方向对话框、取色器、执行速度
控制与逐步调试观察器，适合初学者学习编程思维。

**主要组件（安装于 `bin/`）**:
- `kturtle`：Qt Widgets 桌面应用（KDE Frameworks 6 + Qt6）

数据文件（安装于 `share/`）:
- `applications/org.kde.kturtle.desktop`、`metainfo/org.kde.kturtle.appdata.xml`
- `knsrcfiles/kturtle.knsrc`（Get Hot New Stuff 示例目录）
- 多语言 Turtle 关键字翻译（i18n）

## OHOS PC 适配

- **构建系统**: KDE CMake + ECM（参考先例 archives/k/kwrited）
- **交付形态**: conan 包（bin/kturtle + share/ 数据文件），R38 commands.json 已声明
- **关键适配**: PrintSupport 与 DBus 可选化（OHOS 无 CUPS/无桌面 DBus 会话，
  源码可选化裁剪，见 patches/ 4 个补丁；默认关闭，可经 conan options 启用）
- **依赖**: qtbase/6.11.1（全图归一）+ KF6（kio/knewstuff/kxmlgui/ktextwidgets
  等生态版本，override 口径见 conanfile.py）

## 验证

conan-verify 全绿（G0-G4 + L2/L4/L5），test_package 真实执行 `bin/kturtle
--help`（offscreen QPA，全 Qt6/KF6 闭包加载 + KAboutData 断言）。详见
26.04.0/reports/test-report.md 与 notes.md。

## 知识拓展

本版本附带 HMDFS 已签名 ELF 完整性治理四件套（knowledge-extension/）：
缓存体检 / 修复策略 / 文档 / 复现样例——覆盖 conan 缓存发布件被本地工具
改写后 dlopen Permission denied 的共性问题及其字节恢复策略。
