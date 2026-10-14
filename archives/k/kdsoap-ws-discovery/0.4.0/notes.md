# kdsoap-ws-discovery 0.4.0 HarmonyOS PC 适配记录

上游项目：KDE `kdsoap-ws-discovery-client`（基于 KDSoap 的 WS-Discovery 客户端，Qt6）。
官方源码 tarball：`https://invent.kde.org/libraries/kdsoap-ws-discovery-client/-/archive/v0.4.0/kdsoap-ws-discovery-client-v0.4.0.tar.gz`，
SHA-256 `d0fe9d51a1b641b760f3d837c94b94276ced7a91d4912559cde6bf1df6d4aafa`（37626 字节，实测下载一致）。

## 依赖与构建

- `requires`：`kdsoap/2.3.0`（`find_package(KDSoap-qt6 2.0.0 REQUIRED)`）、`qtbase/6.11.1`（Qt6 Core/Network/Xml + Test）。
- `tool_requires`：`extra-cmake-modules/6.26.0`（顶层 `find_package(ECM 5.54.0 NO_MODULE)`；项目用 `set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})` 覆盖，故 ECM_MODULE_PATH 必须非空，配方显式设置并把 ECM `share/ECM/cmake` 放到 CMAKE_PREFIX_PATH）。
- `-DQT_MAJOR_VERSION=6`、`-DBUILD_TESTING=ON`、`-DBUILD_QCH=OFF`；qtbase/kdsoap 都是 `cmake_find_mode=none`，配方手写 `conan_cmakedeps_paths.cmake` 让 `find_package(Qt6)` / `find_package(KDSoap-qt6)` 解析（adwaita-qt/libkode/kdsoap 先例）。
- `KDSOAP_GENERATE_WSDL` 在构建时调用 kdsoap 包内的 `bin/kdwsdl2cpp-qt6`（OHOS aarch64 宿主工具），故构建时把 qtbase/lib 放进 LD_LIBRARY_PATH。
- 安装的 OHOS ELF 用 `binary-sign-tool` 自签名（`.codesign` 段已核验在位）。

## 上游测试（真跑，逐条计数）

- 上游清点：`autotests/CMakeLists.txt` 用 `ecm_add_tests()` 注册 **1 个 ctest 条目** `test_wsdiscoveryclient`，
  该程序为单个 QTest，含 **4 个 QTest slot**：`testSendProbe`、`testSendResolve`、`testReceiveProbeMatch`、`testReceiveResolveMatch`。
  计数口径：discovered=1（ctest_entries）；逐条=4（QTest slot）。
- 真跑入口：配方 `build()` 内 `ctest --test-dir {build_folder} --output-on-failure --no-tests=error --timeout 120`。
- 实测结果：**ctest 1/1 passed（1 条目、4 slot 全部通过）**，`HMBS_UPSTREAM_TEST_RESULT={"status":"passed",...,"discovered":1,"executed":1,"passed":1,"failed":0,"skipped":0,"qtest_slots":4}`。
- 原始日志：构建目录 `hmbs_ctest.log`（逐行）与 `hmbs_ctest_discover.log`（`ctest -N`）。
  本任务证据副本：`$HOME/tmp/ohpc-porting/kdsoap-ws-discovery-20261014-1/evidence/`。
- 测试需要 IPv6 组播与 UDP/3702；设备实测可 bind 3702 并在全部网卡 join `FF02::C`。

## 消费者测试（真实 API，非空壳）

`test_package/test_kdsoapwsdiscovery.cpp`：`find_package(KDSoapWSDiscoveryClient)` → 链接导出目标 `KDSoap::WSDiscoveryClient`，
调用真实 API 并断言，共 **14 个 CHECK，实测 14/14 通过**（`HMBS_TEST_PACKAGE_RESULT=...discovered":14,"passedCount":14`）。
覆盖 `WSDiscoveryTargetService`（endpointReference/typeList/scopeList/xAddrList/lastSeen 与 isMatchingType/isMatchingScope）、
`WSDiscoveryServiceAggregator`（serviceUpdated 信号、同一 endpoint 复用同一 QSharedPointer、不同 endpoint 为不同指针）、
`WSDiscoveryProbeJob`（interval/addType/addScope）、安装版本头 `WSDISCOVERY_VERSION_STRING`。

## 遇到的问题与修法

1. **导出的 CMake 包配置无法被消费（P0）**：上游 `KDSoapWSDiscoveryClientConfig.cmake.in` 直接调用 `find_dependency()`，
   但没有 `include(CMakeFindDependencyMacro)`；消费者报 `Unknown CMake command "find_dependency"`。
   → 补丁 `0001`：在 `@PACKAGE_INIT@` 后加入 `include(CMakeFindDependencyMacro)`。
2. **DT_NEEDED 绝对路径（CI L5b）**：已发布的 `kdsoap/2.3.0` 的 `libkdsoap-qt6.so` **没有 DT_SONAME**，
   链接 `KDSoap::kdsoap` 时 CMake 传入其 Conan 缓存绝对路径，`ld` 把该机器私有路径写入 `DT_NEEDED`。
   → 补丁 `0002`：`target_link_directories(... PRIVATE ${KDSOAP_DEP_LIB_DIRS})` + 把 `KDSoap::kdsoap` 移到
   `INTERFACE`（对消费者保持可重定位的目标名）+ `PRIVATE -l:libkdsoap-qt6.so`；并把它与 `Qt6::Network` 的
   `INTERFACE_INCLUDE_DIRECTORIES` 以 PRIVATE 方式加回本目标编译。知识 E537（link-time SONAME basename），
   czmq/`0005-CMakeLists-link-libzmq-by-name`、kpackage/`0005-ohos-relocatable-soname-link` 同型先例。
   修复后 `readelf -d` 的 NEEDED 全部为相对名（`libkdsoap-qt6.so`/`libQt6*.so.6`/`libc++_shared.so`/`libc.so`）。
3. **共享库缺 DT_SONAME（CI L5a/L5c）**：HarmonyOS 无 CMake 平台模块，`CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG` 为空，
   即使设了 SOVERSION 也收不到 `-soname`，产物无 SONAME 且导出目标写成 `IMPORTED_NO_SONAME TRUE`。
   → 配方在 `generate()` 设 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`/`_CXX_FLAG=-Wl,-soname,` 与
   `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`（知识 E207/E537，libharu/mtxclient 先例）。修复后
   `SONAME=libKDSoapWSDiscoveryClient.so`，导出目标为 `IMPORTED_SONAME_RELEASE "libKDSoapWSDiscoveryClient.so"`（无 `IMPORTED_NO_SONAME TRUE`）。
4. **上游 autotests 运行时找不到被测库**：`KDECMakeSettings` 把库输出目录设为 `<build>/bin`，测试可执行文件没有 build RPATH。
   → 配方 `_runtime_environment()` 把 `<build>/bin` 一并加入 LD_LIBRARY_PATH（与 `lib`,`src` 并列）。
5. **链接不到 Qt Network 头**：把 `KDSoap::kdsoap` 改为 INTERFACE 后，`KDSoapUdpClient.h` 的 `QAbstractSocket` 找不到
   （原由 `KDSoap::kdsoap` 传递的 Qt6::Network 头丢失）。→ 补丁 `0002` 中额外 `PRIVATE Qt${QT_MAJOR_VERSION}::Network`。

补丁均由 `ohc-run.py refresh-patch --auto` 从干净官方源码生成（非手写 unified diff），生成前校验 orig 树未被污染。

## 门禁（真实 JOB_ID 与退出码）

- `conan-verify`（`porting run ... ohc-run.py conan-verify kdsoap-ws-discovery 0.4.0`）
  - `kdsoap-ws-discovery-0.4.0-verify-20261014-1` exit 1（G2 fail：问题 1，test_package 找不到 find_dependency）
  - `...-verify-20261014-2` exit 1（G2 fail：问题 1 仍在；同时确认 SONAME 已修复）
  - `...-verify-20261014-3` exit 1（编译失败：问题 5 QAbstractSocket）
  - `...-verify-20261014-4` exit 1（上游 ctest 0/1：问题 4；消费者 13/14：我自己的断言 bug）
  - **`...-verify-20261014-5` exit 0**：G0/G1/G2/G3 实际 PASS；G4 标 PASS 但工具未取到包 ID（未实际校验产物）；
    L2/L4/L5 因「无 cache 路径」被框架**跳过**（工具对跳过项仍写 ✅ PASS，实际未执行）。报告 `reports/conan-verify-report.md`。
    （产物的 SONAME/DT_NEEDED/签名/导出目标改由下方「数字一致性」的手工 `readelf`/`llvm-objdump` 核验，以及 CI 同构的 L5 门禁实际检查。）
- CI 同构 `ci/conan/build_and_test.sh`（CI_PACKAGES/CI_REPO_ROOT/CONAN_PROFILE 指向本库）
  - `kdsoap-ws-discovery-0.4.0-cigate-20261014-1` exit 1（JC 误报：本地无 PR diff 时按全仓判定；非本包问题）
  - **`kdsoap-ws-discovery-0.4.0-cigate-20261014-2` exit 0**（用等价 pr.diff 后）：
    `L0_RESULT=pass`、`L1_RESULT=pass`（上游测试 + test_package 执行）、`L1e` 破坏性反向验证确认消费者测试真实依赖本包、
    `L2_RESULT=skip: no bin/ dir`、`L4_RESULT=warn`、`L5_RESULT=pass`、`Build Summary: Total 1 / Success 1 / Failed 0 / Pass rate 100.0%`。
    L4 的 warn 是误报：`grep -E '...|gets|...\b'` 命中注释里 "targets" 的结尾字母（`tar***gets***`），并非真实危险函数。
    CI 日志：`reports/conan-create.log`（同构运行覆盖写入）与任务 tmp 证据副本。

## 数字一致性

- 上游 N（ctest_entries）= 1，实测 1/1；QTest slot = 4，实测 4/4。
- 消费者断言 = 14，实测 14/14。
- 以上数字与 `manifest.yaml`、`test_package/MANIFEST.yml` 一致。

## 未验证范围

- 平台 push / PR / CI / AI / 人工裁决 / 合入 / 制品发布均未执行（本任务边界禁止）。
- `pr_ci: pending` 属实：平台侧门禁与制品发布需主 Agent 在核验后执行。
