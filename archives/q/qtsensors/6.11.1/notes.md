# qtsensors 6.11.1 适配笔记

## 基本信息

- 软件名称: qtsensors（Qt Sensors 模块）
- 版本: 6.11.1
- 构建系统: cmake
- 编译日期: 2026-10-01
- 上游仓库: https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qtsensors-everywhere-src-6.11.1.tar.xz
- 适配路径: 路径 A（基础适配）

## 为什么需要这个包

PyQt6 的 `QtSensors` 绑定依赖 Qt 的 Sensors 模块，而制品仓此前没有
qtsensors 包——该绑定因此被 `_DISABLED_MODULES` 显式禁用。补齐本包后，
pyqt6 配方即可解锁 `QtSensors`。

## 依赖

- qtbase/6.11.1（唯一必需组件是 Core；Xml/Gui/Widgets/Quick/Qml/Svg/DBus/
  QuickTest 都是 OPTIONAL_COMPONENTS，缺失也不阻断构建）

## 关键适配点

1. **CMAKE_PREFIX_PATH 必需**：qtbase 使用 `cmake_find_mode=none` 并自带
   可重定位的 `Qt6Config.cmake`，必须显式把 qtbase 包目录交给 CMake，
   否则 `find_package(Qt6 ... COMPONENTS Core)` 失败。
2. **CMAKE_MODULE_PATH 指向 qtbase 的 platforms 目录**：qtbase 的安装里带
   `Platform/HarmonyOS.cmake`（内容 include Linux）。不设置时 CMake 把
   HarmonyOS 当未知平台，会跳过共享库的 SOVERSION/SONAME 规则——插件的
   `DT_NEEDED` 会退化成相对路径字面量（这正是 qtmultimedia/qttools 系列
   需要后处理 SONAME 的根因，此处从构建期规避）。
3. **无物理传感器后端**：OHOS 上没有传感器 HAL 接入，上游 `tst_qsensor`
   的设备类用例无法运行。与 qtmultimedia（无媒体后端）同样的处理：上游
   测试目标尽力构建（失败仅告警），功能覆盖由 test_package 承担。
4. **ELF 自签名**：安装产物需 `binary-sign-tool -selfSign 1`，否则 OHOS
   拒绝 dlopen（`package()` 中统一处理，与 qtserialport 一致）。

## 验证

- `conan create` 本地构建（见构建日志）
- test_package 消费者测试：传感器类型注册表 / 管理器后端可用性 /
  `QAccelerometer` 实例生命周期（无后端下不崩溃）

## 下游影响

- pyqt6 解锁 `QtSensors` 绑定（拟与本包同批提 PR）；
- `QtBluetooth`/`QtNfc` 另需 qtconnectivity 包，不在本包范围。
