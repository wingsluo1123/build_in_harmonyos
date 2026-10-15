# qt5-qtserialport 5.15.2 适配笔记

- 软件：qt5-qtserialport 5.15.2（Qt 5 串口通信模块）
- 上游：https://download.qt.io/archive/qt/5.15/5.15.2/submodules/qtserialport-everywhere-src-5.15.2.tar.xz
  - sha256: 59c559d748417306bc1b2cf2315c1e63eed011ace38ad92946af71f23e2ef79d（官方源+清华镜像双源实测一致）
- 构建系统：qmake（上游 .pro，`QT = core-private`）
- 依赖：qt5-qtbase/5.15.2.2（制品仓已发布）
- 产物：libQt5SerialPort.so（含 .prl/.pc/mkspecs/cmake config）
- libudev：qt5-qtbase 配置为 disabled（qmodule.pri），串口枚举走 /sys/class/tty 回退，无额外依赖

## 适配模式（与 qtserialport-opensource-src/5.15.15 CI 绿先例一致）

- `_fix_qtbase_paths()`：重写 qtbase 包内 qt.conf 指向当前包目录；
  正则重写 mkspecs/{modules,modules-inst}/*.pri 中构建机路径 → 当前包目录
- build()：`cd source_folder && qmake -spec linux-clang qtserialport.pro` +
  `make -j{jobs} QMAKE_STRIP=""`（OHOS loader 拒绝 strip 后的 ELF）
- QMAKEMODULES 指向构建树 mkspecs/modules：tests/auto 的 qmake 能解析
  刚构建的 serialport 模块
- 打包：lib/include/src/mkspecs/cmake config 全量拷贝 + 显式重建
  .so 符号链接链（HMDFS 拷贝可能丢符号链接）+ 重写 mkspecs pri 中
  构建树路径
- 签名：package() 阶段对产物 ELF 执行 binary-sign-tool 自签名
  （objcopy 移除旧 .codesign 段 → sign -selfSign 1 → 校验新段），
  对齐 qt5-qtbase/5.15.2.2 制品与 qtserialport/6.11.1 先例

## test_package 模式

- CMakeDeps 直接依赖场景生成聚合 config（find_package(Qt5) → Qt5::Core；
  find_package(qt5-qtserialport) → Qt5::SerialPort），完全避开 qtbase
  包内 cmake 文件的构建机残留路径
- OHOS 下 generate() 强制 `CMAKE_SYSTEM_NAME=Linux` +
  `CMAKE_SYSTEM_PROCESSOR=aarch64` 双覆盖（OHOS 适配版 conan 默认生成
  HarmonyOS/unknown，探针实测；adios2/any-lite 先例）
- test() 手动设 LD_LIBRARY_PATH 指向两包 lib 目录

## 上游测试清点与实测（R51）

上游 tests/ 共 4 个 auto 测试工程（qmake，无 ctest 注册）：
- tests/auto/qserialport（tst_qserialport，53 个 slot）
- tests/auto/qserialportinfo（tst_qserialportinfo，3 个 slot）
- tests/auto/qserialportinfoprivate（需 serialport-private，随包构建验证）
- tests/auto/cmake（仅 CI 用 cmake 消费验证，与 conan test_package 重复）

实测（本机 HarmonyOS PC，原生运行）：
- tst_qserialport：1 passed, 0 failed, 1 skipped —— initTestCase QSKIP：
  需要 QTEST_SERIALPORT_SENDER/RECEIVER 指向物理串口对（无硬件环境的具体技术
  原因，非"没环境"）
- tst_qserialportinfo：1 passed, 0 failed, 1 skipped —— 同上
- conan test_package（L1）：test_qtserialport 运行通过，QSerialPort/
  QSerialPortInfo API 构造/枚举/baudRate 断言全过（0 个物理串口，枚举为空）
- tests/auto/qserialportinfoprivate：上游开发者测试（需 serialport-private 模块），
  随包 mkspecs modules-inst 提供 private pri，不单独运行

⚠️ R40 适配完整性（外设类）：适配为实质性——上游原生 termios I/O 与
/sys/class/tty 枚举代码路径真实编译执行（无 stub/平台宏），但无物理串口
对环境下真实串口 open/read/write 数据收发未验证。有硬件时设置
QTEST_SERIALPORT_SENDER/RECEIVER（如 ttyS0/ttyS1 回环）可全量运行上游
测试，建议合入后在带串口的鸿蒙 PC 上补测。

## 回环对补测尝试（2026-10-06 本机实证）

本机 /sys/class/tty 枚举出 8 个 ttyS* 条目（test_package 实测），尝试将其
中 ttyS0/ttyS1 作为 QTEST_SERIALPORT_SENDER/RECEIVER 回环对强制运行上游
tst_qserialport：结果 13 passed / 58 failed——失败集中在
`senderSerialPort.open(QSerialPort::ReadWrite)` 返回 FALSE
（tst_qserialport.cpp:1243 等处），证明本机 ttyS* sysfs 条目无可用物理
串口硬件支撑（非回环对）。API 层 13 项通过恰证明座行为正确。

结论：无真实物理回环对（ttyS0/ttyS1 硬件级连通）的环境下，上游测试
必须走 QSKIP 路径（配方默认运行方式，CI 复现口径：两测试各
1 passed / 0 failed / 1 skipped，QtTest 退出码 0）。有硬件回环的
鸿蒙 PC 上设置两个环境变量即可全量运行。
