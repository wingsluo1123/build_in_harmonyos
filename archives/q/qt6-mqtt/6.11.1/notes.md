# qt6-mqtt 6.11.1 OHOS PC (aarch64) 适配笔记

## 概述

- 软件: qt6-mqtt（Qt MQTT 客户端模块，MQTT 3.1.1 / MQTT 5.0）
- 版本: 6.11.1
- 构建系统: CMake（Qt 模块仓库布局，依赖已发布的 qtbase/6.11.1 原生 Qt6 CMake 包）
- 平台: OpenHarmony / HarmonyOS PC (aarch64)，profile `ohos-aarch64`
- Conan: 2.29.1（OHOS 适配版）

## 源码核验

- download.qt.io 的 `official_releases/qt/6.11/6.11.1/submodules/` 目录**不包含**
  `qtmqtt-everywhere-src-6.11.1.tar.xz`（实测 HTTP 404；qtmqtt 属 additional
  libraries，开源 tarball 仅经 GitHub 发布）。
- 实际源: `https://github.com/qt/qtmqtt/archive/refs/tags/v6.11.1.tar.gz`
- sha256: `704c74568156f0fe16fa13dbae21bc3ea62629d37b97162bac70c4195a123df2`
- 源码结构核验: 顶层 `CMakeLists.txt`（`project(QtMqtt ...)` +
  `find_package(Qt6 ... COMPONENTS Core Network)` + `qt_build_repo()`）、
  `src/mqtt/`（QMqttClient/QMqttConnection/QMqttControlPacket 等）、
  `tests/auto/`（10 个测试子目录 + cmake + conformance）、`LICENSES/`。

## 依赖

- `qtbase/6.11.1`（R36: `conan download "qtbase/6.11.1" -r=ohpcd
  -p="os=OHOS AND arch=armv8 AND build_type=Release"` 下载成功，
  package id `01d92cf349a0dd98ff915f4bd99a04430171517f`，
  package revision `bc3cac65e3f838c4ef70af2d9639bb06`，EXIT=0）。
- 无其他依赖；禁止混入依赖库源码与 recipe。

## 补丁

### 0001-tests-enable-harmonyos.patch（portability）

- 上游 `tests/auto/CMakeLists.txt` 的测试注册条件是
  `if(WIN32 OR (LINUX AND NOT CMAKE_CROSSCOMPILING))`。OHOS 目标
  （`CMAKE_SYSTEM_NAME=HarmonyOS`）两个分支都不命中 → 全部测试不被注册。
- 补丁在该条件中追加 `OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"`，
  不改变其他平台行为。
- 生成方式: difflib.unified_diff（strip=0，与 patch_ng 兼容），逐 hunk
  行号断言 + patch_ng `PatchSet.apply(root, strip=0)` 在纯净副本上实测
  应用成功且内容逐行核对。

## 遇到的问题与解决方案

### 问题 1: 补丁生成器的双换行污染

- 现象: patch_ng 报 `extra lines for hunk no.1`、
  `hunk no.1 doesn't match source file at line 2`，apply 返回 False。
- 根因: `difflib.unified_diff(..., lineterm="")` 与 keepends 行组合时，
  header 行自带 `\n` 而 body 行没有，`"\n".join` + `splitlines` 后每个
  header 后多出一个空行，hunk 行数与 `-1,7 +1,7` 声明不符。
- 修复: 对全部 diff 行 `rstrip("\n")` 后统一 join，再断言 patch body
  无空行污染。

### 问题 2: CMake if 条件语法错误

- 现象: 初版补丁生成 `if(WIN32 OR (LINUX AND NOT CMAKE_CROSSCOMPILING)) OR
  CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"`，`OR` 落在 if() 右括号之外。
- 根因: `NEW = OLD + " OR ..."` 直接把条件追加到完整 if() 之后。
- 修复: 在最外层右括号前插入: `if(WIN32 OR (LINUX AND NOT
  CMAKE_CROSSCOMPILING) OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`，
  并加括号平衡断言。

### 问题 3: 上游测试对外部 MQTT broker 的硬依赖

- 现象: `tests/auto/CMakeLists.txt` 注册的 11 个 ctest 用例（首跑时
  `ctest -N` 实测）中，7 个 broker 依赖用例（conformance、qmqttclient、
  qmqttconnectionproperties、qmqttlastwillproperties、qmqttpublishproperties、
  qmqttsubscription、qmqttsubscriptionproperties）include
  `tests/common/broker_connection.h`，在 `initTestCase` 里调用
  `invokeOrInitializeBroker()`；无 `MQTT_TEST_BROKER` /
  `MQTT_TEST_BROKER_LOCATION` 环境变量时直接 `qFatal`。
- 根因: 上游不随仓库发布测试 broker（GitHub v6.11.1 的 tests/common/
  仅有 broker_connection.h；broker 由 Qt CI 外部提供，经 paho python
  broker 启动）。
- 修复: 配方 build() 用 `ctest -R "^(module_includes|
  tst_(qmqttcontrolpacket|qmqtttopicfilter|qmqtttopicname)_Tcp_4)$"` 只
  运行 4 个免 broker 用例；broker 依赖用例在 test_package/MANIFEST.yml
  的 conditional_upstream_tests 中登记（condition: MQTT_TEST_BROKER），
  不伪造结果。
- 注意: ctest 注册名带 `_Tcp_4` 变体后缀（`qt_internal` 按 TCP+MQTT
  3.1.1 协议变体生成），首跑 `-R "^tst_qmqtttopicname$"` 得到
  `No tests were found!!!`，按实际注册名修正正则后 4/4 通过。

### 问题 4: test_package API 核对

- `QMqttClient::port()` 默认值为 0（`qmqttclient_p.h` 中
  `quint16 m_port{0}`），不是 1883 —— 断言按 0 编写。
- 6.11.1 无独立 `QMqttLastWillProperties.h` 头，类声明在
  `qmqttconnectionproperties.h`；连接属性 API 是
  `setMaximumReceive()`/`maximumReceive()` 而非 setReceiveMaximum。

### 问题 5: 产物缺 DT_SONAME（E537 同族）

- 现象: 首次构建的 `libQt6Mqtt.so` 无 `DT_SONAME`，安装树无
  `.so.6` 符号链接链，`Qt6MqttTargets*.cmake` 含
  `IMPORTED_NO_SONAME TRUE`（W3 L5a/L5c 报错）。
- 根因: OHOS 的 CMake HarmonyOS 平台模块不定义 SONAME flag（本仓已知
  问题 E537），musl 加载器还会忽略 DT_RUNPATH。
- 修复: 按 `archives/q/qaccessibilityclient/0.6.0` 先例，在
  generate() 设置 `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG =
  "-Wl,-soname,"`；因 SONAME 生效后测试二进制 NEEDED 记为
  `libQt6Mqtt.so.6`，再在 build() 的 ctest 命令前置构建树 lib 目录到
  `LD_LIBRARY_PATH`。
- 结果: `llvm-readelf -d` 确认 `SONAME = libQt6Mqtt.so.6`，安装树有
  完整 `.so → .so.6 → .so.6.11.1` 链，`IMPORTED_NO_SONAME` 出现 0 次，
  4/4 上游用例与 test_package 全部通过。

## G0 clean-verify 说明

上游 `configure` 不存在（Qt 模块仓库是纯 CMake 工程，顶层
CMakeLists.txt 无 autotools 包装），G0 的固定 `./configure` 三步在本包
结构上不适用；等价洁净构建证据为 G2 `conan create`（从官方 tarball 重新
source + 打补丁 + 真实编译）与 W3 `build_and_test.sh`。

## 状态

状态: published

## 对话记录

### 对话 #1 [2026-10-14]

问题: qtmqtt 6.11.1 在 download.qt.io official_releases 子模块中 404，源 URL 如何确定？
操作: 遍历官方子模块列表确认 qtmqtt 不随 release 发布，改用 github.com/qt/qtmqtt v6.11.1 tag 归档并计算 sha256。
结果: conandata.yml 采用 GitHub 官方 qt 组织归档，G1/G2 校验通过。

### 对话 #2 [2026-10-14]

问题: OHOS 上 ctest 报 No tests were found!!!
操作: ctest -N 实测注册名带 _Tcp_4 变体后缀；根因是上游 tests/auto 门禁不含 HarmonyOS，补丁追加 CMAKE_SYSTEM_NAME 条件，并按实际注册名修正 -R 正则。
结果: 4/4 免 broker 用例通过（module_includes + 3 个单元测试）。

### 对话 #3 [2026-10-14]

问题: 7 个上游用例依赖外部 MQTT broker，缺失时 qFatal。
操作: 确认上游不随仓库发布 broker（tests/common 仅 broker_connection.h），配方只运行免 broker 用例，broker 用例登记为 conditional_upstream_tests（condition: MQTT_TEST_BROKER）。
结果: 不伪造任何测试结果，test_package 另行提供鸿蒙消费者可行性测试（16 断言通过）。
---

**编译结束**: 2026-10-14 20:03
**最终状态**: published
