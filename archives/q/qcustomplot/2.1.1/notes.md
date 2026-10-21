# qcustomplot 2.1.1 鸿蒙 PC 适配笔记

上游: <https://www.qcustomplot.com/>
版本: 2.1.1（源码归档 QCustomPlot-source.tar.gz）
目标: HarmonyOS PC（aarch64，ohos-sdk clang 15 + libc++ 15）

## 一、适配结论

产物（install 树）：

- `lib/libQCustomPlot.so`（2,353,792 B）——QCustomPlot 全部绘图能力（曲线、颜色图、
  图例、坐标轴 ticker、绘图项、导出 PNG/JPG/BMP/PDF）；
- `include/qcustomplot.h`（7,774 行）——公共头，含 `QCP::` 命名空间与全部类声明；
- `lib/cmake/QCustomPlot/`——`QCustomPlotConfig.cmake`、`QCustomPlotConfigVersion.cmake`、
  `QCustomPlotTargets.cmake`、`QCustomPlotTargets-release.cmake`，目标
  `QCustomPlot::QCustomPlot`；
- `licenses/{GPL.txt,changelog.txt}`。

ELF 关键属性（真机 readelf 实测）：

- `DT_SONAME` = `libQCustomPlot.so`（裸基名，无版本后缀）；
- `DT_NEEDED` = `libQt6Widgets.so.6`、`libQt6Gui.so.6`、`libQt6Core.so.6`、
  `libc++_shared.so`、`libc.so`；
- 运行期不依赖 `libQt6PrintSupport`（OHOS qtbase 不提供该模块）。

平台适配 **1 个补丁**（`patch_type: portability`，无平台条件编译宏，R8 合规）：

1. **0001** 给 `qcustomplot.h` 的 `<QtPrintSupport/QtPrintSupport>` 头包含加上
   `#ifndef QT_NO_PRINTER` 守卫。QCustomPlot 只在 `QCustomPlot::savePdf` 中使用
   `QPrinter`，而该函数的实现上游本就包在 `#ifdef QT_NO_PRINTER` 中；头文件守卫
   与实现守卫使用同一个能力宏，未引入任何平台判断。

## 二、问题与处置

### 问题 1：OHOS qtbase 不带 Qt6PrintSupport

OHOS qtbase/6.11.1 以 `FEATURE_printsupport=OFF` 构建：
`include/QtCore/6.11.1/QtCore/private/qconfig_p.h` 中
`QT_FEATURE_printsupport -1`，SDK 内没有 `lib/cmake/Qt6PrintSupport`，也没有
`libQt6PrintSupport.so.6`。但公共 `qconfig.h` **不定义** `QT_NO_PRINTER`，
所以不能指望 Qt 头文件自己屏蔽 Include。

处置：

- `CMakeLists.txt` 用 `find_package(Qt6 QUIET OPTIONAL_COMPONENTS PrintSupport)`
  探测组件；`Qt6PrintSupport_FOUND` 且目标存在时链接 `Qt6::PrintSupport`，
  否则 `target_compile_definitions(QCustomPlot PUBLIC QT_NO_PRINTER)`；
- `QCustomPlotConfig.cmake.in` 只在构建时存在 PrintSupport 时才
  `find_dependency(Qt6 COMPONENTS PrintSupport)`，消费者不会因缺该组件而
  `find_package` 失败；
- 导出配置使用 `SameMajorVersion`，消费者 `find_package(QCustomPlot 2.1)` 可直接命中；
- E2E 的 `save_pdf_capability` 用例在 `QT_NO_PRINTER` 分支实证
  `savePdf` 返回 false 且不产生 PDF 文件。

### 问题 2：project() 版本变量在工具链加载前展开

首轮 `conan create` 在 configure 阶段失败：

```
CMake Error at .../WriteBasicConfigVersionFile.cmake:43 (message):
  No VERSION specified for WRITE_BASIC_CONFIG_VERSION_FILE()
Call Stack: ... CMakeLists.txt:82 (write_basic_package_version_file)
```

根因：CMake 在第一个 `project()` 调用内部才加载 `CMAKE_TOOLCHAIN_FILE`
（Conan 的 `conan_toolchain.cmake`），而 `project(QCustomPlot VERSION
${QCUSTOMPLOT_VERSION})` 的参数在解析该行时就已展开，此时
`QCUSTOMPLOT_VERSION` 仍未定义。

处置：`project(QCustomPlot LANGUAGES CXX)` 不带 VERSION；project() 之后读取
`QCUSTOMPLOT_VERSION`，缺失则 `FATAL_ERROR`；再用它设置
`VERSION`/`SOVERSION`（SOVERSION 取主版本号）与
`write_basic_package_version_file`。

### 问题 3：test_package 缺少 build()

第二轮 `conan create` 主包构建成功，test_package 报：

```
Error: not a CMake build directory (missing CMakeCache.txt)
```

原因：test_package 配方没有定义 `build()`，Conan 不会自动 configure/build，
`test()` 里的 `cmake.test()` 直接找不到构建目录。

处置：test_package 增加 `build()`（`cmake.configure()` + `cmake.build()`），
`test()` 先 `cmake.test()` 跑 CTest，再直接执行同一个消费者程序以产生逐用例
`TEST PASS / TEST FAIL` 日志（满足 CI L0d 对 `self.run()` 的要求）。

### 问题 4：conan-verify G1 要求 test_package/MANIFEST.yml

首轮 conan-verify 在 G1 失败：

```
❌ test_package/MANIFEST.yml 缺失 (CI L0e 门禁要求)
```

处置：补 `test_package/MANIFEST.yml`，`upstream_tests: []` 明确记录上游无测试，
`test_package_tests` 逐文件声明 16 个消费者用例，`assertion_count: 16`。

### 问题 5：HMDFS 软链接与 SONAME

HMDFS 用户卷拒绝 `symlink(2)`，CMake 的 `libQCustomPlot.so.2.1.1 ->
libQCustomPlot.so.2 -> libQCustomPlot.so` 软链无法落地。配方在 `generate()`
中用临时文件做运行期 symlink 探测（EACCES/EPERM/ENOSYS/EOPNOTSUPP 视为不支持），
不支持时设置 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`，同时始终注入
`CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,`（OHOS CMake 走 Generic
平台模块，默认没有 SONAME 规则）。最终交付单文件 `libQCustomPlot.so`，仍带
裸 `DT_SONAME`（E330 家族）。

### 问题 6：CMakeDeps 不生成 qtbase 配置

qtbase 的 `package_info()` 设置 `cmake_find_mode=none`（保留 Qt 自带的完整
`Qt6Config.cmake`），CMakeDeps 因此不生成 Qt 配置。配方在 `generate()` 中写
`conan_cmakedeps_paths.cmake`（CMakeToolchain 会自动 include），把
`<qtbase>/lib/cmake`、`<qtbase>/lib`、`<qtbase>/include` 前置到
`CMAKE_PREFIX_PATH`/`CMAKE_LIBRARY_PATH`/`CMAKE_INCLUDE_PATH`，并设置
`Qt6_DIR=<qtbase>/lib/cmake/Qt6`；构建与 test_package 两侧采用同一手法
（futuresql/kmag 先例）。

### 问题 7：消费者定位

本卡为「依赖」类适配。在本批次归档中检索了常见 QCustomPlot 消费者
（LabPlot 2.12.1 顶层与 src 的 CMake、Cantor、gnumeric 的 configure.ac），
均未发现 `QCustomPlot` 的 `find_package`/链接引用，因此**不写入未经证实的
消费者引用**；交付以标准 relocatable CMake 包（`QCustomPlotConfig.cmake` +
`QCustomPlot::QCustomPlot`）为消费入口，并用 test_package 的 16 个具名消费者
用例证明该入口可用。

## 三、测试口径

- 上游套件：**0 个测试**（上游 2.1.1 不含构建系统与测试目录）；
  按 rule4「补全测试用例说明=是」。
- 消费者测试（`test_package/`）：**16 项**，覆盖：
  版本宏、部件构造与布局、图与数据、坐标轴范围、时间 ticker、图例、
  绘图项、颜色图、离屏 replot、toPixmap、PNG 导出（尺寸/像素方差）、
  缩放导出尺寸、removeGraph、数据容器裁剪、QCP 枚举元类型反射、
  savePdf 能力分支；Conan 内 CTest 1/1 通过，直接执行 16/16 通过。
- 真机门禁：G0–G4 全 PASS，Verdict=PASS（L2/L4/L5 纯库包无 cache 路径跳过；
  `reports/conan-verify-report.md`）。
- 真机包标识：package_id `b84c7be85f787668946d2ebcfa1dd2e2a692d9cd`，
  recipe revision `97ee6128d94ce3e92592f03301204325`，
  package revision `06254fb0c0f887f2b4639a1a24ab1ead`。
