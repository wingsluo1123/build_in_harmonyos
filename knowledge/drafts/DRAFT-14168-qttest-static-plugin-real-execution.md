# draft-14168-qttest-static-plugin-real-execution

## 背景

积分赛评审（pc-pr-review）rule4 对"上游 51 用例 0 执行"判 FAIL：**"无论任何理由
（平台限制/缺依赖/无环境等）均不通过，请解决后真实执行上游测试用例"**。此前以
`platform_limitation`（"OHOS 无传感器 HAL，设备类用例不可运行"）豁免、只做
`-functions` 计数——豁免声明未经实测，被评审与实测双重证伪。

## 根因：上游测试自带 mock 后端，"无 HAL"不成立

`tst_qsensor` 的 CMakeLists 用 `qt_internal_add_test(... DEFINES QT_STATICPLUGIN ...)`
把 `test_sensorplugin.cpp`（`Q_PLUGIN_METADATA` + `Q_INTERFACES(QSensorPluginInterface)`，
注册 TestSensor/TestSensor2 mock 后端）经 `Q_IMPORT_PLUGIN(TestSensorPlugin)`
**静态编入测试本体**——测试进程自带传感器后端，不依赖任何传感器 HAL。上游的
设计意图就是让这类测试在无硬件的 CI 机器上跑。声称"不可运行"前必须先试跑。

## 方法：独立 CMake 工程镜像 qt_internal_add_test

1. 解析上游 `tests/auto/<dir>/CMakeLists.txt` 的 `qt_internal_add_test` 块，
   SOURCES/DEFINES/LIBRARIES 原样取用（上游测试源码零改动）；
2. `find_package(Qt6 REQUIRED COMPONENTS Core Test Sensors)`——Qt6 私有模块
   （`Qt6CorePrivate` 等）在 conan 安装包里是 **header-only config（无库可链）**：
   链公共目标即可，私有头 include 根手动补**两级**（`include/QtSensors/6.11.1` 与
   `include/QtSensors/6.11.1/QtSensors`——`private/qsensor_p.h` 与
   `QtCore/private/qglobal_p.h` 两种引用形态都要能解析）；
3. `DEFINES` 原样带——`QT_STATICPLUGIN` 是能跑的关键；
4. 构建：HNP clang（`/data/service/hnp/bin/clang++`）+ `/data/service/hnp/bin/make`
   （系统无 make；configure 失败后 make 报的 jobserver mkfifo 是并发症状，configure
   过了就没事）；
5. 运行：`LD_LIBRARY_PATH=<qtbase>/lib:<qtsensors>/lib`、`QT_QPA_PLATFORM=offscreen`、
   `./tst_qsensor -o result.txt,txt`。

实测（2026-10-14）：`Totals: 39 passed, 0 failed, 0 skipped, 0 blacklisted, 6ms`，rc=0。

## 顺带的平台契约实证（消费者断言必须按实证写）

- `QSensor::type()` 返回**后端类型键 = 类名字符串**（`"QAccelerometer"`），不是
  QML 小写名 `"accelerometer"`；
- 无 HAL 平台 `QSensor::sensorTypes()` **预期为空**：generic 插件 `main.cpp` 的
  `registerSensors()` 仅当 `defaultSensorForType(QAccelerometer::sensorType)` 非空
  （已存在 accelerometer 后端）时才注册派生后端；
- 消费者断言应写**不变式**（"注册表为空，或非空则含 accelerometer 类型"），而不是
  想当然的"非空"——本轮断言修复初版就因此抓出 2 个假 FAIL，追查后得到上述实证。

## 豁免的规范窄化

QML 两目标（`tst_sensors_qmlcpp`/`tst_sensors_qmlquick`）依赖 `Qt::Qml`/
`QtSensorsQuickPrivate`（qtdeclarative 模块），本仓无 qtdeclarative 包 → 按 §3.3 以
`missing_dependency` **只圈这两个目标**；C++ 核心目标必须真跑。原则：
**先实测、再写豁免；写不成立的豁免会被评审直接打回。**

## 工程坑

- 工作目录放**无空格路径**（空格拆 `-I`）；
- conan2 `test()` 结束后清理构建目录，CMakeCache 级取证要从独立工程做；
- CMake 对 HarmonyOS 的 "System is unknown" 告警可忽略，不影响 configure。

## 判据小结

| 现象 | 结论 |
|---|---|
| 想以"无硬件/无 HAL"豁免上游 QtTest | 先查测试 CMakeLists 是否 `QT_STATICPLUGIN` + `Q_IMPORT_PLUGIN`（mock 后端静态编入）——是则能真跑，豁免不成立 |
| 链接报 `Qt6::XPrivate` 找不到 | conan 包私有模块是 header-only：链公共目标 + 手动补两级私有头根 |
| `private/qobject_p.h` / `QtCore/private/...` 找不到 | 除模块级私有目录外还要补**版本化父目录**（`include/QtCore/6.11.1`） |
| 消费者断言抓出"意外 FAIL" | 先实证 API 真实行为再定契约——写不变式，别写想当然的断言 |
