# solid 6.28.0 — HarmonyOS PC 适配笔记

## 基本信息

- 包名 / 版本：`solid` 6.28.0（KDE Frameworks 6.28.0）
- 源码：`https://download.kde.org/stable/frameworks/6.28/solid-6.28.0.tar.xz`
  （sha256 `47fa84db…a19b3d`；conandata 带 mirrors.nju.edu.cn 同路径兜底——设备上
  download.kde.org 对 tarball 两次 wget 均 404，PC 侧拉取正常）
- 适配日期：2026-10-17；真机验证通过（conan-verify PASS）
- 依赖 / 工具链：
  - 运行依赖：`qtbase/6.11.1`
  - 构建依赖：`ecm/6.28.0`（上游 `CMakeLists.txt:7` 的 `find_package(ECM 6.28.0 NO_MODULE)`
    硬要求，制品仓直接满足，无需像 kpeople 那样打补丁降级）、`bison/3.8.2`、`flex/2.6.4.2`、`m4/1.4.19`
  - 编译器：clang/clang++；hnp cmake；Unix Makefiles；原生编译（host=build）

## 上游结构（2 个产物 + 4 套测试）

| 目标 | 位置 | 说明 |
| --- | --- | --- |
| `KF6Solid` | src/solid/ | 核心库：Device / DeviceManager / 谓词解析 / 后端框架 |
| `solid-hardware6` | src/solid/tools/ | 命令行工具（L2 冒烟对象） |
| 后端插件 | src/solid/devices/backends/ | OHOS 上只构建 `fakehw`（fakecomputer.xml 假计算机） |

autotests/ 四个测试目录：`fakehardwaretest`、`solidhwtest`、`solidmttest`、`predicatetest`。

## 坑与解法

### 坑 1：C++20 必须由配方显式覆盖（cppstd=20）

- 6.28.0 源码用了 C++20：`src/solid/devices/frontend/device.cpp:226` 的 `std::map::contains`。
- conan profile 默认 `cppstd=17`，且 `conan_toolchain.cmake` 在 `project()` **之前**就设置
  `CMAKE_CXX_STANDARD=17` → ECM KDECompilerSettings 里「用户没设标准就自动判 C++20」
  的 `if (NOT CMAKE_CXX_STANDARD)` 分支不会走 → 编译按 C++17，`contains` 报错。
- 修复：`configure()` 覆盖 `self.settings.compiler.cppstd = "20"`。注意覆盖点必须在
  `configure()`（settings 层），放进 CMake 变量层就晚了（toolchain 已写盘）。

### 坑 2：OHOS 无 CMake 平台模块 → SONAME 全空

- `CMAKE_SYSTEM_NAME=HarmonyOS` 时 CMake 提示 `System is unknown to cmake, create:
  Platform/HarmonyOS`；`Platform/Linux.cmake` 里设的 `CMAKE_SHARED_LIBRARY_SONAME_*_FLAG`
  因此为空 → 链接器收不到 `-Wl,-soname`：
  1. `libKF6Solid.so` 无 `DT_SONAME`；
  2. 下游 `solid-hardware6` 的 `DT_NEEDED` 退化为 `../../../bin/libKF6Solid.so` 相对路径。
- 修复（toolchain 层）：`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` +
  `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` / `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` 都设成
  `-Wl,-soname,` → 产出未版本化单文件，`DT_SONAME` 真实在位、消费者记录可重定位名
  （HMDFS 无软链也可交付；DRAFT-libharu-2.3.0-missing-dt-soname 先例）。

### 坑 3：HarmonyOS 落进上游「其它 Unix」兜底分支 → fstab 后端被带入

- 上游 `CMakeLists.txt` 的 Linux 判定不匹配 `CMAKE_SYSTEM_NAME=HarmonyOS`，落进
  "BSDs and other Unix like systems" 兜底分支，该分支自动加入 fstab 后端；
  `fstab/fstabwatcher.h` 无条件 `#include <libmount.h>`（OHOS 无该头）→ 构建失败。
- 修复：用上游自带开关关掉即可（`SolidBackendsMacros.cmake` 的
  `BUILD_DEVICE_BACKEND_<name>`）：`tc.variables["BUILD_DEVICE_BACKEND_fstab"] = "OFF"`，
  无需改上游源码（E267）。

### 坑 4：测试环境三件套 + SOLID_FAKEHW 的反向验证

- OHOS 上只构建 fakehw 后端，`Solid::Device::allDevices()` 仅在 `SOLID_FAKEHW` 指向
  `src/solid/devices/backends/fakehw/fakecomputer.xml`（源码树路径）时返回设备 →
  `solidmttest::testDeviceMatching`（`!deviceList.isEmpty()`）依赖它；
  Linux CI 由真实 udev/udisks 后端提供设备，不需要。
- 配方在 `build()` 内跑上游测试，test env 四件套：`CTEST_OUTPUT_ON_FAILURE=1`、
  `CTEST_PARALLEL_LEVEL=1`、`QT_QPA_PLATFORM=offscreen`、`SOLID_FAKEHW=<src>/.../fakecomputer.xml`，
  另把各依赖 lib 目录与 build/bin 前置进 `LD_LIBRARY_PATH`；
  ctest 调用为 `--output-on-failure --no-tests=error --timeout 90`。
- 收尾复核时的排查链（可复用）：
  1. 手工 `ctest -V` 只带包 lib + qtbase lib → 4 目标全 0.0x 秒秒挂，日志里
     `Error loading shared library libQt6Core.so.6` —— 根因是手工环境缺**传递依赖**。
  2. 改用 `generators/conanrun.sh`（conan 生成的运行环境，含全依赖链）→ 59 过 1 挂，
     挂在 `SolidMtTest::testDeviceMatching` —— 根因是漏设 `SOLID_FAKEHW`。
  3. 完全复刻配方 test env（conanrun.sh + 四件套）→ **60/60 全过**。
  这次「漏设变量即确定性挂该用例」反过来验证了坑 4 的事实：该用例在 fakehw 单后端
  环境里就是靠 SOLID_FAKEHW 吃饭的。

### 坑 5：HMDFS 拒 symlink → test_package 运行期依赖物化拷贝

- test_package 的 `_stage_runtime_libraries` 原做法 `os.symlink` 在 HMDFS 用户卷上
  EPERM（errno 13，探针 `SYMLINK_ERR 13` 实证）→ 首轮 G2 失败。
- 修复沿用 qzxing / kpeople 6.28.0 先例：`try: os.symlink(...) except OSError:
  shutil.copy2(...)`，配 `_is_same_file_copy`（size + mtime 复核）做幂等；`$ORIGIN`
  运行期契约不变（拷贝同名物）。

### 坑 6：打包产物需签名

- `package()` 用 `binary-sign-tool sign -selfSign 1` 对本包全部 ELF 逐个就地签名
  （`_sign_ohos_elf_tree`，日志 `Signed 2 OHOS package ELF file(s)`——
  `libKF6Solid.so` 与 `solid-hardware6`），不签名的 ELF 在真机不可加载。

## CMake 开关表

| 开关 | 值 | 原因 |
| --- | --- | --- |
| `BUILD_SHARED_LIBS` | ON | 交付共享库 |
| `BUILD_TESTING` | ON | 跑上游 4 套测试 |
| `BUILD_DESIGNERPLUGIN` | OFF | 无 Qt Designer 工具链 |
| `KF_IGNORE_PLATFORM_CHECK` | TRUE | 非 Linux 平台放行 |
| `KF_SKIP_PO_PROCESSING` | ON | 无 Qt Linguist |
| `USE_DBUS` | OFF | 无会话总线，走进程内路径 |
| `UDEV_DISABLED` | ON | OHOS 无 libudev |
| `BUILD_DEVICE_BACKEND_fstab` | OFF | 坑 3：libmount.h 缺 |
| `CMAKE_DISABLE_FIND_PACKAGE_IMobileDevice` / `_PList` | ON | 无 iOS 设备库/无 libplist |
| `CMAKE_PLATFORM_NO_VERSIONED_SONAME` | TRUE | 坑 2：HMDFS 拒软链 |
| `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG` | `-Wl,-soname,` | 坑 2：补平台模块缺失 |
| profile `compiler.cppstd` | **20** | 坑 1：6.28.0 源码用 C++20 |

## 上游测试（R51 口径）

- 四个 ctest 目标、共 **60 个用例数据点**（ctest Totals 口径 3/38/16/3）：
  - `fakehardwaretest`（3）：testFakeBackend（含 init/cleanupTestCase）
  - `solidhwtest`（38）：testAllDevices / testDeviceBasicFeatures / testDeviceExistence /
    testDeviceInterfaceIntrospection(+CornerCases) / testDeviceInterfaces / testDeviceSignals /
    testDeviceVendorProduct / testInvalidPredicate / testListFromTypeInvalid /
    testListFromTypeProcessor / testManagerSignals / testPredicate /
    testQueryStorageVolumeOrProcessor / testQueryStorageVolumeOrStorageAccess /
    testQueryWithParentUdi / testSetupTeardown / testStorageAccessFromPath
    （testPredicate 等为数据驱动，数据点计数多于函数数）
  - `solidmttest`（16）：testDeviceMatching / testTextPredicates(+Extended) /
    testThreadedPredicate / testWorkerThread（testTextPredicates 数据驱动多行）
  - `predicatetest`（3）：testParsing（含 init/cleanupTestCase）
- 真机全量 **60/60 通过**（2026-10-17，完全复刻配方 test env 的 `ctest -V` 复核）：
  fakehardwaretest 14ms、solidhwtest 13ms、solidmttest 23ms、predicatetest 2ms。
- L2 冒烟：`solid-hardware6 --version` → `solid-hardware 0.1a`；
  `SOLID_FAKEHW=... solid-hardware6 list` → 正常输出 fake 机 UDI 列表
  （acpi_AC / acpi_BAT0 / acpi_BAT1 / acpi_CPU0 / acpi_CPU1 / computer / fstab …）。

## 验证结果（真机 conan-verify，2026-10-17）

- `conan create`：成功；`rrev:pkgid` = `solid/6.28.0@ohpcd/stable#17d8b220e29dbec217dec47296b30e52:00ab6c1b220a661c8bdfde4b593b245dce7ddfe9`
  （pkgid 与 6.26.0.1 相同 = 依赖图未变）；打包 45 文件；签名 2 个 ELF；
  build() 内 ctest 4/4 目标（60/60 用例）。
- `test_package`：消费者用例 PASS（`Solid block-device query returned 0 valid entries`——
  fake 环境无块设备属预期分支）。
- 制品 md5：`libKF6Solid.so` = `1a6824c05c26eb7495f20b92a3046d5d`；
  `solid-hardware6` = `aaf7678e0b79a189e288b16bb0803468`。
- 报告：`reports/conan-verify-report.md`（Verdict: PASS，G0/G1/G2/G3/G4 全过、
  L2/L4/L5 无 cache 路径常态跳过）；`reports/conan-create.log` 依平台规则不随档。

## 注意事项

- 消费者接线沿用 `cmake_find_mode=none` + `conan_cmakedeps_paths.cmake` 模式，
  `builddirs=lib/cmake`，vanilla qtbase 留在 CMake 搜索路径之外。
- 与 6.26.0.1 底版的配方差异仅 4 处：docstring 版本、`version`、configure 注释版本、
  `tool_requires ecm/6.28.0`（上游硬要求）——无任何补丁，上游源码与测试零修改。
- `runenv_info` 已把本包 `lib` 前置进 `LD_LIBRARY_PATH`，`solid-hardware6` 冒烟时
  仍须把包自身 `p/lib` 与依赖链（conanrun.sh）一起带上，缺一即
  `Error loading shared library`。
