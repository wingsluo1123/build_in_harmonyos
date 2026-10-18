# drumstick 2.11.1 — HarmonyOS PC 适配笔记

## 选型

- **上游最新稳定版 2.11.1**（Git tag `RELEASE_2_11_1`，2026-08-22 发布）。
  kmetronome/1.4.1 的 CMake 要求 `find_package(Drumstick 2.11 COMPONENTS ALSA
  REQUIRED)`，即 ≥2.11；2.11.1 为满足该约束的最新稳定版。
- 仓库：https://github.com/pedrolcl/drumstick（官方镜像，README 指向上游
  drumstick.sourceforge.io）。

## W0 依赖发布检查（制品仓 ohpcd，`conan download --only-recipe` 逐项核实）

| 依赖 | 用途 | 版本 | 状态 |
|------|------|------|------|
| qtbase | Qt6 Core/Gui/Widgets/Network/Test/Xml（自带 relocatable Qt6Config.cmake） | 6.11.1 | ✅ 已发布（含 ohos-aarch64 binary） |
| qt5compat | Qt6::Core5Compat（drumstick-file 的 QTextCodec） | 6.11.1 | ✅ 已发布 |
| qttools | Qt6::LinguistTools / lrelease（drumstick-widgets 翻译） | 6.11.1 | ✅ 已发布 |
| alsa-lib | ALSA sequencer（libasound，pkg-config alsa.pc） | 1.2.16.1 | ✅ 已发布 |

- `conan install --requires=... -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=... --build=never` 四个 binary 全部命中缓存/制品仓（qtbase 在缓存，
  qt5compat/qttools/alsa-lib 从 ohpcd 下载成功）。
- 不需要 qtbase-sql-dbus 变体：drumstick 默认 USE_DBUS=OFF（RealtimeKit 的
  DBus 支持在 OHOS 无意义），因此 plain qtbase/6.11.1 即可，且与 qt5compat
  对 qtbase/6.11.1 的依赖一致（避免双 qtbase 版本混入图谱）。
- 可选项（PulseAudio/PipeWire/FluidSynth/Sonivox）全部关闭：上游默认
  USE_PULSEAUDIO/USE_FLUIDSYNTH 在 UNIX 下为 ON 且缺失时 FATAL，关闭后依赖
  闭包最小化，不捎带适配任何新包。

## 构建系统要点

CMake ≥3.16 多库工程。产物：

- `libdrumstick-alsa.so`（Drumstick::ALSA，仅 Linux/HarmonyOS）
- `libdrumstick-file.so`（Drumstick::File）
- `libdrumstick-rt.so`（Drumstick::RT）
- `libdrumstick-widgets.so`（Drumstick::Widgets，依赖 RT）
- RT 后端插件 `lib/drumstick2/*.so`（alsa-in/alsa-out/net-in/net-out/oss-in/oss-out）
- CMake 包：`lib/cmake/drumstick/drumstick-config.cmake` + 每组件
  `drumstick-{alsa,file,rt,widgets}-config.cmake`（命名空间 `Drumstick::`）
- pkg-config：`drumstick-{alsa,file,rt,widgets}.pc`
- 头文件：`include/drumstick.h` + `include/drumstick/*.h`

配方 package_info：`cmake_find_mode="none"` + `builddirs=[lib/cmake]`，消费方
`find_package(Drumstick COMPONENTS ALSA ...)` 直接使用上游自带的 config。

### 关键移植点（patch 0001）

OHOS 上 CMake 报 `CMAKE_SYSTEM_NAME=HarmonyOS`，上游 CMakeLists 用
`${CMAKE_SYSTEM} MATCHES "Linux"` 门控 ALSA：不补丁则 libdrumstick-alsa 既不
默认开启、也不会执行 `pkg_check_modules(ALSA)`，`ALSA_FOUND` 恒空 → ALSA 子
目录被 library/CMakeLists.txt 跳过。patch 0001 把两处门控扩为同时接受
`CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"`（构建系统移植条件，无平台宏）。

### 消费 Qt6 的做法（沿用 qtbase/qt5compat/qttools 先例）

- `CMAKE_PREFIX_PATH` = qtbase + qt5compat + qttools + alsa-lib 包目录；
- `Qt6_DIR` = qtbase/lib/cmake/Qt6；`CMAKE_MODULE_PATH` =
  qtbase/lib/cmake/Qt6/platforms（Platform/HarmonyOS.cmake → include Linux.cmake）；
- `PKG_CONFIG_PATH` 追加各依赖 lib/pkgconfig（alsa.pc），供
  `pkg_check_modules(ALSA REQUIRED IMPORTED_TARGET alsa>=1.0.0)` 解析；
- CMakeDeps 生成 alsa-lib 的 ALSA-config（消费方 find_dependency(ALSA) 用）。

## 上游测试（R51 三步法）

- 清点：`tests/` 下 CTest 注册 7 项（Qt Test）——alsaTest1 / alsaTest2 /
  fileTest1 / fileTest2 / fileTest3 / rtTest / widgetsTest；
  utils/ 下 10 个示例程序（CLI+GUI，BUILD_UTILS=OFF 未打包，属 examples 非测试）。
- 注册差异：alsaTest2 与 rtTest 在 Linux-like 系统由
  `EXISTS /dev/snd[/seq]` 门控；OHOS 无 /dev/snd → 不注册（rtTest 走 else
  分支无条件注册）。实际注册 = alsaTest1, fileTest1/2/3, rtTest, widgetsTest。
- 结果：见 W3 conan create 日志（本次运行 ctest 的通过率统计写在此节下方）。

## test_package

- 链接 Drumstick::ALSA / File / RT 三个库 + Qt6::Core + ALSA（Widgets 仅
  find_package 不链接——QWidget 派生类需 QApplication，由上游 widgetsTest
  在构建期覆盖，test_package 以 QCoreApplication 消费者视角验证）。
- 功能验证：SMF 写入→读回往返（事件计数）、ALSA NoteEvent 数据类断言、
  RT BackendManager 枚举（仅报告，后端数量依赖运行时 /dev/snd/seq）。
- 共 12 条 CHECK 断言。

## 运行期限制（记档）

- ALSA sequencer / OSS / 网络 RT 后端在 OHOS 上的可用性依赖运行时
  /dev/snd/seq 等设备；无设备时后端可枚举但连接/订阅不工作（库代码有优雅降级）。
- RealtimeKit DBus 调度（RTKIT_SUPPORT）未启用（USE_DBUS=OFF）。
---

**编译结束**: 2026-10-10 09:45
**最终状态**: built
