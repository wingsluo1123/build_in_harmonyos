# indi-playerone 0.9 - adaptation notes

## Source
- URL: https://deb.debian.org/debian/pool/contrib/i/indi-playerone/indi-playerone_0.9+20230105184731.orig.tar.gz
- sha256: 3f592574077cb79b95e2ac52de9fb557cddc3a50d471b3c34c58f1fe78a220c0
- 上游未为 indi-playerone 单独打 tag，Debian Astronomy Team contrib pool
  的 orig 包是 indilib/indi-3rdparty indi-playerone/ 子目录 0.9 版本的
  权威可下载快照（63735 字节，顶层 indi-playerone-0.9+20230105184731）。
  2026-10-15 实测 HTTP 200 且 sha256 一致。
- conan 版本号取基版本 0.9（'+' 后为快照时间戳 20230105184731 = git 提交
  时刻，与 indi-gpsnmea/indi-fishcamp 归一化口径一致，且与任务指定的
  版本号 0.9 及分支名 feat/indi-playerone-0.9 对齐）。
- License: LGPL-2.1-or-later（tarball 带 COPYING.LGPL，package() 拷贝进
  licenses/）。

## Scope
- 全部源码：playerone_ccd.cpp/h（PlayerOne CCD 驱动，继承 INDI::CCD 基类）
  + playerone_helpers.h + indi_playerone.xml.cmake（设备描述模板）+
  config.h.cmake（版本宏 0.9）+ playerone_camera_test.cpp（厂商 SDK 探测
  工具，随包安装）。cmake_modules/ 下是 indi-3rdparty 共享的 Find*.cmake
  集合（本驱动只用 FindINDI/FindPLAYERONE/FindCFITSIO/FindUSB1 +
  CMakeCommon）。
- 功能面：经厂商 libPlayerOneCamera SDK（libplayerone/3.1.0 包提供的闭源
  预编译 .so）走 USB 控制 POA 天文相机（曝光/增益/分箱/制冷/ROI），发布
  INDI 属性 CCD_EXPOSURE / CCD_GAIN / CCD_BINNING / CCD_TEMPERATURE 等。

## Build system
- 极简 CMake（cmake_minimum_required 3.0 + 自研 CMakeCommon.cmake）。
  CMake >= 4.0 移除了 <3.5 兼容，configure 必须显式
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（cli_args 真 -D 缓存变量——同
  indi-gpsnmea/indi-fishcamp 经验）。
- E092：CMake 无 HarmonyOS 平台，CMAKE_SYSTEM_NAME=Linux +
  CMAKE_SYSTEM_PROCESSOR=aarch64（与 libindi/2.2.2.1、indi-gpsnmea、
  indi-fishcamp 一致）。
- CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF（toolchain block）：Conan 默认 ON
  会遮蔽树内 cmake_modules/FindINDI.cmake / FindPLAYERONE.cmake /
  FindCFITSIO.cmake / FindUSB1.cmake，CMake 去找不存在的 CONFIG 包直接失败。
- FindPLAYERONE.cmake：find_path(PlayerOneCamera.h PATH_SUFFIXES
  libplayerone) 与 find_library(PlayerOneCamera) 经 Conan 的
  CMAKE_FIND_ROOT_PATH 直接命中 libplayerone/3.1.0 包
  （include/libplayerone/PlayerOneCamera.h + lib/libPlayerOneCamera.so），
  无需注入。
- FindUSB1.cmake：find_path(libusb.h PATH_SUFFIXES libusb-1.0) +
  find_library(usb-1.0) 同样经 find root path 命中 libusb/1.0.27 包，驱动
  自身不直接 include <libusb.h>，无需 include 叶子注入（对照
  indi-fishcamp：fishcamp_common.h 才需要）。
- CMakeLists 里 `if (CMAKE_SYSTEM_PROCESSOR MATCHES "arm*")` 链接 rt：
  aarch64 不匹配 arm*，不链接；musl libc 自带 clock_gettime，无需 librt。
- INDI_WEBSOCKET 未启用（树内无 websocket 探测宏传入），Boost 不引入。

## Patches
- 0001 FindINDI.cmake 版本号正则：与 indi-gpsnmea/indi-fishcamp 的 0001
  byte-identical（INDI 2.2.2 indiversion.h 写 INDI_VERSION "2.2.2" 带引号，
  旧正则 FATAL_ERROR failed to detect INDI version）。
- 0002 CMakeLists：C++17（INDI 2.x defaultdevice.h 用 std::any，CMakeCommon
  钉死 C++14）+ INDI_DATA_DIR 覆盖为本包 share/indi（FindINDI 报出
  libindi 包的数据目录，直接 install 会把设备 xml 装错包）。
- 无 INDI 1.x→2.x API 移植补丁：本快照（2023-01-05）已按 INDI 2.x C++ API
  编写（setExposureDuration / addCaptureFormat / PropertyText getState 等，
  对照 indi-fishcamp 0002 的移植点在本快照全部已就位）。

## 依赖（W0 已核验发布）
- libindi/2.2.2.1、libplayerone/3.1.0、cfitsio/4.6.4、zlib/1.3.1.1、
  libusb/1.0.27 —— 全部已发布到 ohpcd 制品仓（conan download/list 实测）。

## 驱动直接执行受沙箱限制（与 libplayerone/indi-fishcamp 同口径）
- 驱动需物理 POA 相机经 USB 连接；厂商 SDK 无仿真模式（对照 libfishcamp
  的 fcUsb_setSimulation）。且 CI 沙箱 OHOS 动态加载器对 conan 缓存内
  外部 .so dlopen 一律 Permission denied（libplayerone 3.1.0 归档实测）。
- 故 test_package：HC-1/2/4/5 对包内驱动二进制与设备 xml 做静态验证
  （ELF/链接/逻辑字符串/XML/loader），HC-3 用 ipo_probe.c（含厂商头、
  引用驱动实际调用的 POA API）对包内 libPlayerOneCamera.so.3 做真实
  OHOS clang 编译+链接（R34 下游可用性证明，不运行）。

## 上游测试清点（R51）
- tarball 61 个文件：无 tests/ 目录、无 CTest 注册、无 Makefile test 目标；
- 上游测试用例 N=1：`playerone_camera_test.cpp`（厂商 SDK 探测测试程序，构建产物
  `playerone_camera_test`），未纳入自动化测试框架。
- 本次补全 5 个消费者用例（HC-1..HC-5，26 项检查），全部通过。

## 上游用例实测执行（playerone_camera_test，2026-10-15 真机）
- 用包内头文件+厂商 SDK 重新编译上游测试源（绕开 HMDFS 拷贝文件不可 exec 的 SELinux
  限制）：clang++ --target=aarch64-linux-ohos 编译+链接成功（27KB aarch64 ELF），
  OHOS musl 加载器 `/lib/ld-musl-aarch64.so.1` 可启动执行；
- 运行时：`Error loading shared library libPlayerOneCamera.so.3` + 全部 POA_* reloc
  失败，退出非零；
- 未通过原因（非适配引入）：①厂商闭源预编译 .so 在本沙箱 mmap-exec/dlopen
  Permission denied（按文件限制：同环境 conan 缓存内 libusb-1.0.so.0 可正常加载，
  对照实验见 indi-fishcamp/1.1 notes；libplayerone/3.1.0 归档同结论），厂商无静态库
  无法静态链接绕过；②工具功能即枚举/打开物理 USB POA 相机，沙箱无硬件，SDK 无仿真
  模式（对照 libfishcamp 的 fcUsb_setSimulation）；
- 结论：该用例 0/1 通过，均为环境限制；编译/链接/加载器启动均成功，证明二进制在
  OHOS aarch64 上构建正确。驱动功能核心由 HC-1..HC-5 覆盖。
---

**编译结束**: 2026-10-15 14:26
**最终状态**: built
