# qtconnectivity 6.11.1 适配笔记

## 基本信息

- 软件名称: qtconnectivity（Qt Connectivity —— QtBluetooth + QtNfc）
- 版本: 6.11.1
- 构建系统: cmake
- 编译日期: 2026-10-01
- 上游仓库: https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qtconnectivity-everywhere-src-6.11.1.tar.xz
- 适配路径: 路径 A（基础适配）

## 为什么需要这个包

PyQt6 的 `QtBluetooth` 与 `QtNfc` 绑定依赖 Qt 的 Connectivity 模块，而
制品仓此前没有 qtconnectivity 包——两个绑定因此被 `_DISABLED_MODULES`
显式禁用。补齐本包后，pyqt6 配方即可同时解锁这两个绑定。

## 模块构成

| 模块 | 库 | 必需依赖 |
|---|---|---|
| Connectivity（global） | libQt6Connectivity | Qt::Core |
| Bluetooth | libQt6Bluetooth | Qt::Core + Qt::Network |
| Nfc | libQt6Nfc | Qt::Core |

顶层只 REQUIRED `Core`；`Network DBus Gui Widgets Quick QuickControls2`
都是 OPTIONAL_COMPONENTS，缺失不阻断构建。

## 关键适配点

1. **bluetooth 特性不依赖 BlueZ**：`configure.cmake` 里 `qt_feature("bluetooth")`
   的 CONDITION 仅为 `TARGET Qt::Network`；`bluez` 是可选后端特性
   （CONDITION `BLUEZ_FOUND AND TEST_bluez AND QT_FEATURE_dbus`）。OHOS 无
   BlueZ，关闭 `FEATURE_bluez` 后 Qt 用树内 dummy 后端补齐 API 库。
2. **NFC 后端同样关闭**：`pcsclite`（需 PCSCLite 库）与 `neard`（需 dbus）
   在 OHOS 都不存在，两个特性显式 OFF；QtNfc 的数据类型 API 仍完整构建。
3. **CMAKE_PREFIX_PATH / CMAKE_MODULE_PATH**：qtbase 使用
   `cmake_find_mode=none` 并自带可重定位 Qt6Config.cmake，需显式指向；
   同时把 qtbase 的 `lib/cmake/Qt6/platforms` 加入 CMAKE_MODULE_PATH，
   否则 CMake 视 HarmonyOS 为未知平台、跳过 SOVERSION/SONAME 规则。
4. **无硬件后端**：上游测试全是设备/后端驱动（设备发现、配对、NFC 目标），
   OHOS 上不可运行，故配方不构建上游测试套件，功能覆盖由 test_package
   承担：蓝牙地址/UUID/设备信息数据类、NFC NDEF 记录往返、无适配器时
   `QBluetoothLocalDevice::isValid()` 的优雅报告。
5. **ELF 自签名**：安装产物需 `binary-sign-tool -selfSign 1`（与
   qtserialport/qtsensors 一致）。

## 验证

- `conan create` 本地构建（见构建日志）
- test_package 消费者测试输出 `QTCONNECTIVITY-CONSUMER-OK`

## 下游影响

- pyqt6 解锁 `QtBluetooth` / `QtNfc` 两个绑定；
- 真机功能层面：蓝牙/NFC 硬件访问需要 Qt 侧接入 OHOS 系统服务后端
  （当前为 dummy 后端，API 可用但发现不到真实设备）——属后续工作。
