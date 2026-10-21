# analitza 26.04.0 鸿蒙 PC 适配笔记

上游: <https://invent.kde.org/education/analitza>
版本: 26.04.0（KDE Gear 26.04.0 发行版；工程内部版本串 ANALITZA_VERSION=9.0.0）
目标: HarmonyOS PC（aarch64，ohos-sdk clang 15 + libc++ 15）

## 一、适配结论

产物（install 树）：

- `lib/libAnalitza.so`（887,360 B）——表达式解析/求值核心：Expression、
  Analyzer、内置方法、MathML/HTML writer（Analitza6 主体）；
- `lib/libAnalitzaPlot.so`（477,760 B）——绘图引擎：2D/3D plot item、
  PlotsModel/PlotsFactory、marching squares/cubes 后端、Plotter2D 与
  Plotter3DES（GL 场景在无 OpenGL 线上裁掉，X3D/STL 导出保留）；
- `lib/libAnalitzaGui.so`（109,120 B）——Gui 侧模型（OperatorsModel/
  VariablesModel/高亮器）；
- `lib/libAnalitzaWidgets.so`（137,792 B）——QWidget 视图
  （PlotsView2D 与 QOpenGLWidget 版 PlotsView3DES）；
- `include/Analitza6/`、`lib/cmake/Analitza6/`（Analitza6Config.cmake +
  Targets）、`lib/qml/org/kde/analitza/`（qmldir + Graph2D.qml；
  Graph3D 需要 Qt6::OpenGL，缺失时不安装）、`share/libanalitza/`、
  `share/locale/`。

平台适配 **6 个补丁**（`patch_type: portability`，均为能力探测/可选组件，
不含平台条件编译宏，R8 合规）：

1. **0001** 顶层 `find_package(Qt6)` 将 PrintSupport/OpenGL/
   OpenGLWidgets 移入 OPTIONAL_COMPONENTS；
2. **0002** AnalitzaPlot 仅在 `TARGET Qt6::PrintSupport/OpenGL` 存在时
   链接，并把 `ANALITZA_HAVE_OPENGL` 作为该 target 的 **PUBLIC 编译定义**
   导出（0/1），保证库与安装了 `plotter3d_es.h` 的消费者按同一能力值
   编译；
3. **0003** AnalitzaWidgets 仅在 Qt6::OpenGLWidgets 存在时构建/安装
   plotsview3d_es；
4. **0004** declarative/ 仅在 Qt6::OpenGL 存在时编译 Graph3D
   （QQuickFramebufferObject）并安装 qml/Graph3D.qml；
5. **0005** examples 仅在 Qt6::OpenGLWidgets 存在时构建 plots3ddemo，
   但 export3dplotdemo（X3D/STL 导出器）无条件保留——上游 4 个
   export-test-* CTest 用例因此照常运行；
6. **0006** `plotter3d_es.h` 优先使用 CMake 导出的 `ANALITZA_HAVE_OPENGL`
   （非 CMake 消费者保留 `__has_include(<QOpenGLFunctions>)` 兜底），
   `plotter3d_es.cpp` 用 `__has_include(<QPrinter>)` 探测
   ANALITZA_HAVE_PRINTSUPPORT；GPU 场景与 PDF 保存分支编译排除，
   保留 3D 数学模型与 X3D/STL 导出。

测试口径：

- 上游套件：**18 项 CTest**（14 个 QTest 程序共 45 个测试函数，8 个在
  analitza/tests、5 个在 analitzaplot/tests、1 个在 analitzagui/tests，
  加 4 个脚本型导出用例 export-test-{sin,fancy}-{stl,x3d}），
  `BUILD_TESTING=ON` 在 conan create 内实跑 **18/18 通过**；
- 消费者测试（`test_package/`，R51 第三步）：**16 项检查**
  （test_analitza 10 + test_ohos_soname 6）全部通过；
- 真机门禁：G0–G4 全 PASS，Verdict=PASS（L2/L4/L5 纯库包无 cache
  路径跳过；`reports/conan-verify-report.md`）。

## 二、问题与处置

### 问题 1：OHOS qtbase 缺 PrintSupport / OpenGL / OpenGLWidgets

上游 `find_package(Qt6 REQUIRED COMPONENTS ... PrintSupport OpenGL
OpenGLWidgets)` 直接把三个组件列为必需。已发布的 qtbase/6.11.1 线未启用
这三者（无 Qt6PrintSupport / Qt6OpenGL / Qt6OpenGLWidgets 的 CMake 目标），
configure 即失败。

**处置**（补丁 0001–0005）：顶层 find_package 改为 OPTIONAL_COMPONENTS，
并把每一处链接/源文件/安装项都放到 `if(TARGET ...)` 守卫下：
- AnalitzaPlot：`Qt6::PrintSupport`（PDF 保存）、`Qt6::OpenGL`
  （plotter3d_es GPU 场景）条件链接；
- AnalitzaWidgets：`Qt6::OpenGLWidgets` 缺失时跳过 plotsview3d_es 的
  编译与安装；
- declarative/：`Qt6::OpenGL` 缺失时跳过 Graph3D item 与 Graph3D.qml；
- examples/：plots3ddemo 需要 OpenGLWidgets，跳过；**export3dplotdemo
  无条件构建**（它只走 3D 模型 + 导出路径），保住上游 4 个导出 CTest。

### 问题 2：plotter3d_es 源码级硬依赖 QOpenGLFunctions / QPrinter

头文件无条件 include `<QOpenGLFunctions>`，实现里用 GL 函数与
QPrinter（PDF 导出）。仅靠 CMake 守卫还不够。

**处置**（补丁 0002 + 0006）：`Plotter3DES` 是导出的公共类，其基类与成员
布局受 OpenGL 能力影响。能力值不能只在每个编译单元里各自探测（消费者若
include 路径不同就会与库的类布局不一致），因此由 `analitzaplot/CMakeLists.txt`
在配置期解析 `TARGET Qt6::OpenGL`，把 `ANALITZA_HAVE_OPENGL` 作为
AnalitzaPlot target 的 **PUBLIC 编译定义**导出（0/1），随包内的
`Analitza6Targets.cmake` 一起被消费者继承；`plotter3d_es.h` 仅在宏未定义时
退回 `__has_include(<QOpenGLFunctions>)` 探测（非 CMake 消费者兜底）。
`plotter3d_es.cpp` 另用 `__has_include(<QPrinter>)` 定义
`ANALITZA_HAVE_PRINTSUPPORT`（仅实现文件使用，无 ABI 影响），把 GPU 场景
（renderGL/initializeGL 等）与 PDF 保存分支编译排除；`updatePlots`/
`exportSurfaces`（X3D/STL）等 3D 数学模型路径保持完整。该机制是平台中立的
（不写 `__OHOS__` 等宏，R8 合规），能力齐全的平台行为不变。

### 问题 3：HMDFS 拒 symlink（E330）与 install 重写 ELF 的签名封印

上游给四个库设 VERSION 9.0.0 / SOVERSION 9，CMake 链接后要创建
`libAnalitza.so.9.0.0 -> .so.9 -> .so` 软链链——设备用户卷（HMDFS）
`symlink()` 返回 EPERM，构建在链接后失败。

**处置**：
- `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`（toolchain 变量）——CMake
  直接以无版本名发出单个 `.so`，不调用 `cmake_symlink_library`；
- 用 `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` 注入 rules 文件，恢复
  `-Wl,-soname,` 与 `-Wl,-rpath,` 标志（OHOS CMake 落在 Generic 平台模块，
  默认无 SONAME 规则，E1582 同源）；产物因此带裸 `DT_SONAME`
  （`libAnalitzaPlot.so`），消费者 `DT_NEEDED` 为可重定位基名（E537）；
- `cmake install()` 会原位重写 RUNPATH，破坏 OHOS 构建期 `.codesign`
  封印（E1351 同族）——`package()` 对包内每个 ELF 执行
  `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign
  -selfSign 1` 重签（ki18n/kdiagram 先例）；四个库与消费者测试可正常
  dlopen（test_package 实测）。

### 问题 4：Qt6 拆包组件与 ECM/Qt6LinguistTools 查找

- Qt6Svg 在 qtsvg、Qt6Qml/Qt6Quick 在 qtdeclarative（qtbase 制品不含），
  Qt6Config 按 Qt6_DIR 相对查找会失败 → 设
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH=[qtbase;qtsvg;qtdeclarative]`；
- CMakeDeps 对这三个包是 `cmake_find_mode=none`，不生成
  `conan_cmakedeps_paths.cmake` → 配方手工写出该文件（PREFIX_PATH /
  LIBRARY_PATH / INCLUDE_PATH / MODULE_PATH + `FIND_PACKAGE_PREFER_CONFIG`）；
- ECM 模块路径由 ECMConfig 自己设置，但 CMakeDeps 布局不传播 →
  手工 `ECM_MODULE_PATH=<ecm>/share/ECM/{modules,find-modules,kde-modules}`；
- `ECMPoQmTools` 需要 lrelease/lconvert → tool_requires
  `qt6linguisttools/6.11.1` 并显式钉 `Qt6LinguistTools_DIR`
  （kdbusaddons 6.29.0 先例）。

### 问题 5：上游 CTest 运行环境

- ctest 在每个测试二进制自己的目录启动，构建树 `lib*.so` 需镜像到
  analitza/tests、analitzaplot/tests、analitzagui/tests、
  analitzaplot/examples、bin/、lib/（HMDFS symlink EPERM →
  `shutil.copy2` 回退）；
- 无头环境：`QT_QPA_PLATFORM=offscreen`；隔离 HOME/XDG_RUNTIME_DIR/
  XDG_CACHE_HOME/XDG_CONFIG_HOME/XDG_DATA_HOME；
- `LD_LIBRARY_PATH` 前置 `/system/lib64`（沙箱内 `libc++_shared.so`
  不兼容，kconfig 6.26.0 先例）；
- `CTEST_PARALLEL_LEVEL=1`（串行，避免多个 offscreen QApplication
  争用同一 runtime 目录）。

### 问题 6：消费者头文件路径与运行期 Qt6Svg

上游把 AnalitzaWidgets 的公共头安装到 `include/Analitza6/analitzagui/`
（没有单独的 analitzawidgets 目录，klinkitemselectionmodel 等同源命名）。
test_package 按 `<analitzagui/expressionedit.h>`、`<analitzagui/plotsview2d.h>`
引用；AnalitzaWidgets 以 PRIVATE 链接 Qt6::Svg，运行期 DT_NEEDED 含
`libQt6Svg.so.6`，test_package 的运行环境因此要求 qtsvg 包在
LD_LIBRARY_PATH 上（requires 已声明）。

## 三、验证

- 上游 tarball SHA256 本地复核：
  `2fd1803bcc011515716ed802265e63dc4d34ee6fccbdf6d523f39475eb64431f`
  （369,880 字节）。
- 六个补丁在 26.04.0 源码树上经 patch_ng 链测全部干净应用；补丁头为
  `--- a/…` / `+++ b/…` 规范形态。
- 设备 `conan-verify`（`scripts/ohc-run.py conan-verify analitza 26.04.0`，
  ohos-aarch64 profile，2026-10-17）：G0–G4 全 PASS，L2/L4/L5 跳过
  （纯库包无 cache 路径），`VERIFY_RC=0`，`Verdict=PASS`
  （`reports/conan-verify-report.md` 随档）。
- 上游 CTest（conan create 内，BUILD_TESTING=ON）：**18/18 passed**
  （`100% tests passed, 0 tests failed out of 18`）——
  analitzatest / expressiontest / exptest / mathmlpresentationtest /
  typechecktest / builtintest / commandstest / matchingtest /
  planecurvetest / spacecurvetest / surfacetest / plotsmodeltest /
  plotsdictionarymodeltest / operatorsmodeltest + 4 个
  export-test-{sin,fancy}-{stl,x3d}。
- `test_package`：**16/16 passed**（TEST SUMMARY: 10 passed, 0 failed +
  6 passed, 0 failed）——版本宏、Analyzer 求值、2D/3D 绘图管线、X3D 导出
  文档、VariablesModel/PlotsView2D/ExpressionEdit 真机运行 + SONAME/
  DT_NEEDED 消费者回归。
- 包 id：`15806506deabc0764ecddd8d5b489caf0fafa188`。
- 制品 ELF 证据（设备 readelf）：四个库均为单文件（无版本化软链），
  `DT_SONAME` 为裸基名（libAnalitza.so / libAnalitzaPlot.so /
  libAnalitzaGui.so / libAnalitzaWidgets.so）；`DT_NEEDED` 全部为裸基名
  （libQt6Core.so.6、libQt6Gui.so.6、libQt6Widgets.so.6、libQt6Svg.so.6、
  libQt6Xml.so.6、libc++_shared.so、libc.so，库间互引 libAnalitza*.so）；
  消费者 test_analitza/test_ohos_soname 的 DT_NEEDED 同为裸名且
  引用裸 libAnalitzaPlot.so（E537 回归网）。

---

**编译结束**: 2026-10-17
**最终状态**: built

## 对话记录

### 对话 #1 — 2026-10-17

- 目标：交付 `analitza/26.04.0`（kalgebra 26.04.0 的唯一强候选自导入依赖，
  `find_package(Analitza6 REQUIRED)`），分支 `feat/analitza-26.04.0`
  （= 卡面 taskBranch）。
- 配方从零编写：四库 + QML 模块、qtbase/qtsvg/qtdeclarative 依赖线、
  ECM + qt6linguisttools 工具链；6 个能力探测补丁（无平台宏）。
- 设备真机 conan create 迭代：主包一次构建成功；test_package 先后修正
  AnalitzaWidgets 头路径（analitzagui/）、内置常量导致的 VariablesModel
  行数假设、QByteArray += QString 编译错误，最终 16/16。
- conan-verify 三轮全绿：首两轮为配方本体修正（docstring 计数），第三轮在
  离线检视整改（skip_test/can_run 门控、SONAME 严格比较与 ELF 边界防护、
  OPENGL 能力定义经 target 导出）后重跑，G0–G4 全 PASS、18/18 + 16/16；
  详见上节。
- 离线检视 / MR / CI 记录：见下方追加条目（随流程推进补记）。
