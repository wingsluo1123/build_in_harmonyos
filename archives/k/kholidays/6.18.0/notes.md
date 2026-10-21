# kholidays 6.18.0 适配笔记

## 编译环境

- 构建系统: cmake (KDE Frameworks 6 / ECM)
- 目标平台: HarmonyOS PC / OpenHarmony 6.0, aarch64 (arch=armv8)
- 编译器: clang 15 / clang++ (compiler.libcxx=libc++, compiler.cppstd=17)
- 构建类型: Release, shared=True
- 编译日期: 2026-10-17

## 上游形态

- kholidays 6.18.0 = KDE Frameworks 6 第 6.18 发布线，产物为 `libKF6Holidays.so`
  （VERSION/SOVERSION 由 `ecm_setup_version` 从 `${KF_VERSION}=6.18.0` 派生）。
- 顶层 `CMakeLists.txt` 要求 `find_package(ECM 6.18.0 REQUIRED NO_MODULE)` 与
  `find_package(Qt6 6.7.0 CONFIG REQUIRED Core Qml)`。
- 公开能力两块：
  1. 节假日历法 —— `KHolidays::HolidayRegion` 读取内置节日计划数据；
  2. 天文事件 —— `KHolidays::SunEvents`（6.15 起的新 API）与已弃用的
     `KHolidays::SunRiseSet` 自由函数。
- 上游测试 6 个（`autotests/CMakeLists.txt`，BUILD_TESTING 下注册）：
  testlunar、testseasons、testsunriseset、testzodiac、testholidayregion、
  testsunevents。注意 6.18.0 尚无 6.28.0 才加入的 testcategories 用例。

## W0 依赖核验（精确名，开工前实测）

| 依赖 | 上游要求 | 采用的已发布形态 |
|---|---|---|
| Qt6 Core / Qt6 Test | Qt6 >= 6.7.0 | `qtbase/6.11.1`（host requires） |
| Qt6 Qml（declarative 插件） | Qt6 Qml | `qtdeclarative/6.11.1`（host requires） |
| ECM | ECM >= 6.18.0 | `ecm/6.26.0`（tool_requires） |
| Qt6LinguistTools（poqm） | `ecm_install_po_files_as_qm(poqm)` | `qt6linguisttools/6.11.1`（tool_requires） |

核验命令与读数（`conan list -r=ohpcd <精确名>/*` 与 `<精确名>:*`）：

- `qtbase/*` → 6 个版本，`qtbase/6.11.1:*` 有 OHOS/armv8/clang15/libc++/cppstd17 的二进制；
- `qtdeclarative/*` → 3 个版本，`qtdeclarative/6.11.1:*` 有同样的二进制；
- `ecm/*` → 6.20.0 / 6.26.0 / 6.28.0 / 7.0.7，`ecm/6.26.0:*` 为 build-scripts 包；
- `qt6linguisttools/*` → 仅 6.11.1，`qt6linguisttools/6.11.1:*` 有二进制；
- `kholidays/*` → 仅 6.28.0（已发布），**6.18.0 未发布** ⇒ 本次为新增版本。

ECM 版本选择的依据：上游要 `ECM >= 6.18.0`，而 ohpcd 上 `ecm` 线最早只到 6.20.0；
同仓 KF6 6.18.0 基线（kconfig / kcoreaddons / ki18n / kxmlgui / kwidgetsaddons 6.18.0）
一律用 `ecm/6.26.0`，故沿用该值。

## 与 6.28.0 先例的差异（本次判 hit 的直接依据）

同仓已有 `archives/k/kholidays/6.28.0`（首版适配）。6.18.0 的机制全部被既有条目
与 6.28.0 配方覆盖，差异只有"随着发布线变化的事实"，不构成新的解题路径：

| 维度 | 6.28.0 | 6.18.0（本次） |
|---|---|---|
| 解析器生成 | tarball 不含生成物，需 bison/flex/m4 tool_requires | tarball **自带** `src/parsers/plan2/holidayparserplan.cpp` + `holidayscannerplan.cpp`，`src/CMakeLists.txt` 直接编译，**不需要 bison/flex/m4** |
| C++ 标准 | 源码用 `std::ranges::none_of`，需移除 conan cppstd 块并设 `CMAKE_CXX_STANDARD=20`，另加 0001 可移植性补丁 | 源码用 `std::numbers::pi`（`<numbers>`，同为 C++20），**同样**需要移除 conan cppstd 块并设 `CMAKE_CXX_STANDARD=20`；但不用 ranges 算法重载，故**无需补丁** |
| 上游测试数 | 7（含 testcategories） | 6（无 testcategories） |
| ECM | `extra-cmake-modules/6.29.0` | `ecm/6.26.0`（同发布线兄弟包口径） |
| 消费者测试 API | 用 `SunRiseSet::isPolarDay/isPolarNight` 自由函数 | 改用 `SunEvents::isPolarDay/isPolarNight/isPolarTwilight` 成员函数（6.15 起自由函数已弃用） |

因此 `B判定=hit`，复用条目：`经验文档/经验库/07-08-插件与图形栈.md` §8.1–8.3
（KF6 配方骨架 / Qt6 分包组件 / KF6 运行时路径）与同仓先例
`archives/k/kholidays/6.28.0`，复用的具体方案见下节。

## 复用的具体适配方案

1. **KF_IGNORE_PLATFORM_CHECK=TRUE** —— OHOS 不在 KDE 平台白名单内；kconfig /
   kxmlgui / ki18n 6.18.0 同款。
2. **C++20（`tc.blocks.remove("cppstd")` + `CMAKE_CXX_STANDARD=20`）** ——
   源码用 `std::numbers::pi`，而 profile 固定 `cppstd=17`；与 6.28.0 完全同款。
3. **ECM_MODULE_PATH 手设** —— CMakeDeps 生成的 ECMConfig.cmake 不传播
   `ECM_MODULE_PATH`，而顶层 `CMakeLists.txt` 依赖它来找 KDEInstallDirs、
   KDECMakeSettings、ECMQmlModule、ECMPoQmTools、ECMGenerateQDoc 等模块。
4. **手写 conan_cmakedeps_paths.cmake** —— `qtbase` 用 `cmake_find_mode=none`，
   CMakeDeps 不会生成该文件，需手工把 qtbase/qtdeclarative/qt6linguisttools/
   ecm 的 `lib/cmake`、`share/ECM/cmake` 前置进 `CMAKE_PREFIX_PATH` /
   `CMAKE_MODULE_PATH`，并 `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`。
5. **QT_ADDITIONAL_PACKAGES_PREFIX_PATH** —— Qt6 顶层 Config 来自 qtbase，
   而 Qml / LinguistTools 由 qtdeclarative / qt6linguisttools 单独发布；仅扩大
   `CMAKE_PREFIX_PATH` 不足以让 `find_package(Qt6 COMPONENTS ...)` 找到它们。
6. **BUILD_TESTING=ON + ctest 真实执行** —— 6 个上游用例在配方 `build()` 内跑，
   带离屏 `QT_QPA_PLATFORM=offscreen`、隔离 HOME/XDG 与 `TZ=UTC`。
7. **LD_LIBRARY_PATH 前置 /system/lib64** —— ECM 的 KDEInstallDirs6 在 configure
   期会跑 qtbase 的 qtpaths；沙箱 LD_LIBRARY_PATH 里 arm64 bundle 下的
   libc++_shared.so 会遮蔽兼容版本（kconfig 6.18.0 / bluez-qt 6.28.0 同款）。
8. **不设 `CMAKE_SKIP_INSTALL_RPATH`** —— 与 6.28.0 先例一致；消费者测试用
   package_folder 的绝对 lib 路径拼 `LD_LIBRARY_PATH`。

## 上游测试用例修改说明

未修改任何上游测试用例（`autotests/` 原样编译执行），因此无补丁、
`patches_applied` 为空。6.18.0 在 OHOS 上必须用 C++20 编译（`std::numbers`），
见下节"遇到的问题与解决方案"§1；其余零改动。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `src/lunarphase.cpp:107:23: error: no member named 'numbers' in namespace 'std'`（`radToDeg`/`degToRad` 同时报 `no return statement in constexpr function`） | 仓库 profile 固定 `compiler.cppstd=17`，`<numbers>` 与 `std::numbers::pi` 是 C++20 库设施 | `tc.blocks.remove("cppstd")` + `CMAKE_CXX_STANDARD=20`（与 6.28.0 同款） |

### §1 的探针证据（OHOS SDK libc++ / clang 15，纯标准库 30 行级探针）

```
$ /data/service/hnp/bin/clang++ -stdlib=libc++ -std=c++17 -c probe_numbers.cpp   # 失败
error: no member named 'numbers' in namespace 'std'

$ /data/service/hnp/bin/clang++ -stdlib=libc++ -std=c++20 probe_numbers.cpp -o probe_numbers
compile_rc=0
$ ./probe_numbers
std::numbers::pi=3.1415926536
run_rc=0
```

同一次探针还确认了 6.28.0 补丁的根因在 6.18.0 上**不适用**：

```
$ /data/service/hnp/bin/clang++ -stdlib=libc++ -std=c++20 -c probe_ranges_alg.cpp
error: no member named 'none_of' in namespace 'std::ranges'
```

即 SDK libc++ 的 `<numbers>` 可用、C++20 ranges 算法重载缺失；6.18.0 源码只用到
前者（`grep -rn 'std::ranges|<ranges>' src/` 无命中），因此**既不需要补丁，也不能停在 cppstd=17**。

## 验证结果

`conan create` 干净构建（`kholidays/6.18.0@ohpcd/stable`，profile `ohos-aarch64`），
配方验证 Verdict=PASS：G0 预构建评估 / G1 配方完整性 / G2 conan create /
G3 系统同名库隔离 / G4 产物完整性 均 PASS；L2 smoke / L4 静态安全扫描 /
L5 产物基线 三项报 PASS 但实为"无 cache 路径"跳过（纯库包、G4 未解析出包 ID），
真正覆盖它们的读数是下面的 W3 本地 CI（`ci/conan/build_and_test.sh`，与平台 CI 同源）。

上游 ctest（配方 `build()` 内真实执行，`QT_QPA_PLATFORM=offscreen`、隔离 HOME/XDG、`TZ=UTC`）：

```
1/6 Test #1: testlunar ........................   Passed    0.08 sec
2/6 Test #2: testseasons ......................   Passed    0.05 sec
3/6 Test #3: testsunriseset ...................   Passed    0.06 sec
4/6 Test #4: testzodiac .......................   Passed    0.06 sec
5/6 Test #5: testholidayregion ................   Passed    0.26 sec
6/6 Test #6: testsunevents ....................   Passed    0.08 sec

100% tests passed, 0 tests failed out of 6
```

消费者测试（`test_package/test_kholidays.cpp`，设备上真实运行可执行文件）：

```
kholidays 6.18.0 consumer probe OK: 23/23 assertions passed;
Beijing solstice sunrise 2025-06-21T04:46:03 sunset 2025-06-21T19:46:18 (day 15.0042h);
DE 2025 holidays: 25
```

消费者断言分八组共 23 条：HolidayRegion 区域与元数据（4）、固定日期节假日判定（3）、
全年节假日计数（1）、节假日对象名称与类别（3）、SunEvents 事件有效性（2）、
事件顺序（4）、数值合理性（2）、极区判定与极昼暮光（4）。
逐项明细见同目录 `reports/test-report.md`。

### 测试账本（五维，逐项对应本地执行日志）

| 维度 | 上游 ctest | 消费者测试（test_package） |
|------|-----------|---------------------------|
| 静态总数 | 6（`autotests/CMakeLists.txt` 在 `BUILD_TESTING` 下注册） | 23 条断言（8 组） |
| 可执行数 | 6（全部链接成功并生成测试可执行） | 1（`test_kholidays`） |
| 实测通过数 | 6 | 23 |
| 跳过数 | 0（`ctest --no-tests=error`，注册即执行） | 0 |
| 失败数 | 0 | 0 |

上游 ctest 汇总原始日志行（`reports/w3-local-ci.log`）：

```
100% tests passed, 0 tests failed out of 6

Total Test time (real) =   0.81 sec
```

### 产物门禁遥测（不阻断，留痕）

本地 W3 与平台 CI 同源脚本（`ci/conan/build_and_test.sh`）在产物基线门禁处记录：

```
[fail] L5a: libKF6Holidays.so 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址
[fail] L5c: 1 个 .cmake 文件含 IMPORTED_NO_SONAME TRUE — 下游必须按完整路径链接
[fail] L5: SONAME quality gate failed (2 errors)
L5_RESULT=fail: soname_gate_failed
```

读数与定性：产物只有 `libKF6Holidays.so`，无 `libKF6Holidays.so.6` 版本化链接，
`readelf -d` 无 `SONAME` 条目；而上游顶层 `CMakeLists.txt` 明确请求
`ecm_setup_version(... SOVERSION 6)` ⇒ 该请求在 HarmonyOS 目标上被 CMake 丢弃
（无对应 platform module，即 G0 已记录的 E092 类环境事实）。同源脚本中该门禁只置
`L5_RESULT`，不改变脚本退出码（本次本地 W3 `exit_code=0`；平台侧该段无 `exit 1`），
故属**存量遥测、不阻断**；CMakeDeps 据此标 `IMPORTED_NO_SONAME TRUE`，下游按
完整路径链接即可正常工作（消费者测试即如此链接并通过）。定性口径依据：
`SKILL.md` v12.17 已记录「L5 存量遥测不阻断被误判 P1 引发整轮复审」。

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/k/kholidays/6.18.0/conanfile.py` | Conan 2 配方（CMakeToolchain + CMakeDeps） |
| `archives/k/kholidays/6.18.0/conandata.yml` | 官方 HTTPS tarball + 真实 SHA256 |
| `archives/k/kholidays/6.18.0/manifest.yaml` | 版本级归档元数据 |
| `archives/k/kholidays/6.18.0/test_package/` | 消费者测试（真实 API 断言） |
| `archives/k/kholidays/manifest.yaml` | 追加 6.18.0 版本索引 |
---

**编译结束**: 2026-10-18 00:20
**最终状态**: published
