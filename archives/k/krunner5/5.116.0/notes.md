# krunner5 5.116.0 适配笔记（KDE Frameworks 5 / Qt5）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-16
- 目标平台: HarmonyOS PC (arm64, OHOS 6.0, clang 15, libc++)
- 编译器: clang/clang++（OHOS 工具链）
- 状态: built（本地 conan create 全绿：上游 ctest + test_package 31/31）
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`（host==build，原生轨）

## 依赖
| 依赖 | 版本 | 用途 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | Qt5 Core/Gui/Widgets/Network/DBus/Test 运行时与 moc/rcc/uic/qdbusxml2cpp 工具（5.15.2 为无 widgets 存根版，不可用） |
| qt5-qtdeclarative | 5.15.2 | Qt5Qml/Qt5Quick 库与头（krunner.cpp 链接 Qt5::Quick；包内无 lib/cmake，见下） |
| kconfig5 | 5.116.0 | 运行期配置（KF5::ConfigCore/Gui） |
| kcoreaddons5 | 5.116.0.1 | KPluginMetaData/KPluginFactory 与安装布局宏 |
| ki18n5 | 5.116.0 | 本地化（KF5::I18n，被 KF5::Runner 导出接口引用） |
| threadweaver5 | 5.116.0 | 并行 Runner 编排（KF5::ThreadWeaver） |
| ecm | 6.26.0 | Extra CMake Modules（tool_requires；ECM_MODULE_PATH 显式注入） |

KRunner 是 KF5 Tier 2 functional 库：插件侧（AbstractRunner，供搜索提供方实现）
+ UI 侧（RunnerManager/RunnerContext/QueryMatch/RunnerSyntax）。

## 编译步骤

1. 源码: `https://download.kde.org/stable/frameworks/5.116/krunner-5.116.0.tar.xz`
   sha256 `b87fb29e4354acb21f085b7978c7f1f49f41766a1d4f98fc86781fb9884a0841`
   （本地实测，且与官方 .sha256 sidecar 文件逐字节一致；验证时 download.kde.org
   重定向链上的镜像 TLS 不稳，改用其他官方镜像取同一文件，sha256 不变）
2. 本地构建命令（真机）:
   `conan create . -pr:h=ohos-aarch64-full -pr:b=ohos-aarch64-full --build=missing`
   流程: `cmake.configure()` → `cmake.build()` → `ctest`（build 内执行上游测试）
   → `cmake.install()` → `binary-sign-tool` 签名 → test_package。
   配置参数: `QT_MAJOR_VERSION=5`、`KF_IGNORE_PLATFORM_CHECK=TRUE`、
   `KF_SKIP_PO_PROCESSING=ON`、`BUILD_TESTING=ON`、`BUILD_QCH=OFF`、
   `BUILD_SHARED_LIBS=ON`、`CMAKE_SYSTEM_NAME=Linux`、
   `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`、`CMAKE_BUILD_PARALLEL_LEVEL=1`、
   `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + SONAME flags、
   `EXCLUDE_DEPRECATED_BEFORE_AND_AT=5.91.0`。
   ctest 运行环境: `QT_QPA_PLATFORM=offscreen`、`HOME=<build>/test-home`、
   `XDG_RUNTIME_DIR=<build>/xdg-runtime`、`LD_LIBRARY_PATH` 含依赖 lib 与
   `/system/lib64`。

## 关键适配点

- **`EXCLUDE_DEPRECATED_BEFORE_AND_AT=5.91.0`（本配方的核心开关）**: KRunner
  KF5-5.116 源码中有一大档 deprecated API 链接 KF5::Service（KPluginInfo/
  KService）、KF5::Plasma 与 KF5::KIOCore——三者都不在本链条内，必须整档排除。
  上游 ECM 机制（排除 5.91.0 及之前弃用的一切）与 tarball 中的守卫完全对齐：
  * 根 CMakeLists.txt 的 `find_package(KF5KIO/KF5Service/KF5Plasma)` 包在
    `EXCLUDE_DEPRECATED_BEFORE_AND_AT VERSION_LESS 5.91.0` 中——取 5.91.0 时
    三包根本不被查找（否则 configure 因缺包中止）；
  * src/CMakeLists.txt 的 KF5::Service/KF5::Plasma/KF5::KIOCore 链接块同一守卫；
  * src/declarative（弃用的 org.kde.runnermodel QML 插件）由 VERSION_LESS 5.0.0
    守卫，不构建；
  * abstractrunner.h / runnermanager.h 仅在
    KRUNNER_ENABLE_DEPRECATED_SINCE(5, 91) 下包含 <KPluginInfo>/<KService>；
    以 5.91.0 生成的 export 头令该宏为假，头文件走 <KPluginFactory> 分支，
    kservice 完全不进依赖图（假分支内嵌套的 `#if KSERVICE_BUILD_DEPRECATED_SINCE(...)`
    被预处理器跳过，未定义的 kservice 宏不会被求值）。
  **如实声明**: 基于 KService 的 deprecated API（KPluginInfo metadata()、
  KService::Ptr loadRunner、Plasma::Package 相关）不在本次构建范围内；
  基于 KPluginMetaData 的 API 完整。
- **Qt5 Quick 分体供给**: qt5-qtdeclarative 带 Qt5Qml/Qt5Quick 库与头但无
  lib/cmake。CMakeDeps 被要求把生成的 qt5-qtdeclarative 配置命名为 Qt5Qml
  （cmake_file_name），另有手写聚合 Qt5Config.cmake shim（位于 generators 目录，
  置于 CMAKE_PREFIX_PATH 首位）以 NO_DEFAULT_PATH 预载 qt5-qtbase 原生分模块
  配置（Core/Network/Gui/Widgets/Test/DBus），再 find_dependency(Qt5Qml)，
  并把 Qt5::Quick 前向为 Qt5::Qml 的 INTERFACE 目标（链接期用，krunner.cpp 仅
  链接级使用 Qt5::Quick）。shim 先置 Qt5_FOUND=TRUE，使 Qt5Qml 配置自身的
  find_dependency(Qt5) 不会中途回入 shim（kpeople5 先例，知识草稿
  DRAFT-E5xx-cmakedeps-shadowing）。qt5-qtbase 本体走原生配置
  （cmake_find_mode=none），因为只有原生配置带 mkspec 包含路径。
- **CMAKE_SYSTEM_NAME=Linux（UNIX-like 原生目标）**: OHOS 的 Conan toolchain 把
  `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`（CMake 无其 platform module、
  不置 UNIX，且判为 cross-compiling）。ECM 仅在非 cross 构建时
  `add_test()`，其 POSIX 标志/RPATH 处理也在 `if(UNIX)` 下；显式固定 Linux 既有
  恢复 UNIX=1 又让 6 个 autotest 目标真正注册与运行（链上通用做法）。
- **KF5::Runner 导出接口引用 KF5::I18n，但上游 KF5RunnerConfig.cmake 不带
  find_dependency(KF5I18n)**: 上游应用自行查找 I18n，消费者必须显式
  find_package(KF5I18n)——test_package 中已按此处理。
- **Qt5 DBus 工具**: autotests 用 `qt_add_dbus_adaptor()`（来自
  ../src/data/org.kde.krunner1.xml）构建 testremoterunner。顶层
  CMAKE_PROJECT_TOP_LEVEL_INCLUDES 引入包的 Qt5DBusMacros.cmake，并把
  Qt5Core_MOC/RCC/UIC 与 Qt5DBus_QDBUSXML2CPP/QDBUSCPP2XML 锁定到 qt5-qtbase
  bin/ 工具（kservice5 先例：否则宏在 configure 期未知，或空工具路径退化为
  无程序的 "-m -p ..." 自定义命令）。
- **ECM_MODULE_PATH / ECM_DIR 显式注入**: ecm 是 tool_requires（build
  context），CMakeDeps 不会把其 share/ECM 树接入 host 前缀路径。
- **mkspecs 兼容树重建**: `Qt5CoreConfigExtrasMkspecDir.cmake` 硬编码构建树路径
  `<prefix>/../b/mkspecs/linux-clang`；generate() 从包内 mkspecs/ 整树复制过去
  （kcoreaddons5/threadweaver5 先例）。
- **签名**: CMake 安装期会改写共享库 RUNPATH，使 OHOS 构建期 .codesign 段失效，
  加载器拒绝加载。安装后用 `llvm-objcopy --remove-section .codesign` +
  `binary-sign-tool sign -selfSign 1` 对包内每个 ELF 重签名。
- **E537**: OHOS 拒绝 mmap PROT_EXEC 一个链接后被改写 ELF 的共享库；
  `CMAKE_BUILD_WITH_INSTALL_RPATH=ON` 使链接器直接写入最终安装 RPATH。
- **无版本 DT_SONAME**: `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` +
  SONAME flags → 可重定位、无版本号的 DT_SONAME（W3 CI L5 门禁）。
- **HMDFS 并行限制**: make jobserver fifo 创建被拒（EPERM），
  `CMAKE_BUILD_PARALLEL_LEVEL=1`。
- **/system/lib64 置 LD_LIBRARY_PATH 首位**（host 工具与测试运行期），
  保证兼容 libc++ 胜过沙箱内那份。

## 上游测试（rule4 口径）

上游构建系统注册的测试目标数 **N=6**（autotests/CMakeLists.txt 的
ecm_add_tests；runnercontexttest 因 `EXCLUDE_DEPRECATED_BEFORE_AND_AT
VERSION_LESS 5.76.0` 守卫不注册，且其链接 KF5::KIOCore，与本档位一致）。
在 5.91.0 排除档位下，6 个类合计编译保留 **27 个 QTest 用例槽位**
（已排除 initTestCase/cleanupTestCase 与 *_data 数据提供函数）：

| # | ctest 名 | 用例数（5.91.0 档位） | 覆盖 |
|---|----------|----------------------|------|
| 1 | runnermatchmethodstest | 4（9 中 5 个 deprecated 槽位剔除） | RunnerContext addMatch/addMatches 批量与去重 |
| 2 | runnermanagerhistorytest | 4 | 启动历史 boost/建议列表（fakerunnerplugin + kcoreaddons_desktop_to_json） |
| 3 | testmetadataconversion | 1 | 旧 metadata.desktop → KPluginMetaData 转换 |
| 4 | dbusrunnertest | 9 | D-Bus runner 协议（需会话总线） |
| 5 | runnermanagersinglerunnermodetest | 6（7 中 1 个 deprecated 槽位剔除；需会话总线） | 单 runner 模式加载/禁用/不存在 id |
| 6 | runnermanagertest | 3（需会话总线） | matchesChanged 调度/重置完成信号/销毁不崩溃 |

- **会话总线自适应**: 第 4/5/6 类 spawn testremoterunner 并等待其
  org.kde.krunner1 服务注册，需要 D-Bus 会话总线。镜像同时提供
  `dbus-run-session` 与 `dbus-daemon` 时，build() 在私有总线下执行
  `dbus-run-session -- ctest`（全 6 类 27 用例）；否则打印 WARN 并以
  `-E "dbusrunnertest|runnermanagersinglerunnermodetest|runnermanagertest"`
  排除 3 个总线类，只跑 3 个无总线套件（9 用例）。**本机实测即后一分支**
  （真机无 dbus 工具链）。
- 实测结果（真机）: 无总线分支 `100% tests passed, 0 tests failed out of 3`
  （runnermatchmethodstest 0.07s / runnermanagerhistorytest 0.21s /
  testmetadataconversion 0.08s）；总线 3 类共 18 用例如实声明为
  **未在本机执行**（镜像无 dbus，非跳过即通过）。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libKF5Runner.so` | 主库，`DT_SONAME=libKF5Runner.so`，含 RUNPATH，安装后 binary-sign-tool 重签名 |
| `include/KF5/KRunner/*.h` + `KRunner/` CamelCase 头 | 公开头（AbstractRunner/QueryMatch/RunnerContext/RunnerManager/RunnerSyntax 等） |
| `lib/cmake/KF5Runner/*` | CMake 包配置（KF5::Runner 目标；find_dependency 不含 KF5I18n，见上） |
| `share/.../org.kde.krunner1.xml` | D-Bus 接口自省 XML |
| `mkspecs/modules/qt_KRunner.pri` | qmake .pri（KDE_INSTALL_USE_QT_SYS_PATHS=OFF → 包内相对路径） |

## 注意事项

- 本配方骨架与 threadweaver5/kconfig5/kcoreaddons5 同源，并新增 Qt5 Quick
  聚合 shim（qt5-qtdeclarative 供给）与 EXCLUDE_DEPRECATED_BEFORE_AND_AT 档位
  排除两个机制；后继 KF5 Tier 2/3 库（deprecated 档牵连 Service/Plasma/KIO）
  可直接沿用。
- 若下游出现 `Error loading shared library ... Permission denied`，优先检查
  是否触发 install 期 RPATH 原地改写（E537 类）与 .codesign 失效（本配方已
  双双处理）。
- **已知限制（RPATH，本配方不单独处理）**: `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`
  使安装产物 RUNPATH 固化为构建机 Conan cache 绝对路径，产物非 relocatable；
  消费者场景由 Conan RPATH / conanrun（LD_LIBRARY_PATH）兜底（链上普遍现象）。
- **API 档位声明（重复强调）**: 见"关键适配点"第一条——KService/Plasma/KIOCore
  体系 deprecated API 不在本构建内。
- R32/R33 已遵守：未用 `os == "Linux"` 做 Conan 平台判断（用
  `str(self.settings.os) == "OHOS"`）；编译参数全部来自 Conan toolchain/依赖。
- R8/R49 已遵守：无源码补丁；未向共享 `/usr/local` 注入。
- R38：纯库包（`package_type="library"`），不建 commands.json。
- R39：conandata 只写官方单条 URL（download.kde.org），未加任何镜像前缀。

## test_package 实测

**31/31 断言通过**（详见 reports/test-report.md）:
- API: KPluginMetaData（KPlugin JSON）构造 AbstractRunner 子类，
  `match() → RunnerContext::addMatch() → matches()` 全链；QueryMatch 值语义
  （isValid/拷贝/operator< 按 relevance 排序）；RunnerContext::matchesChanged
  信号、addMatches() 批量；RunnerSyntax 构造。
- 上游语义实探（写入知识库）: ① `QueryMatch::setId()` 在 runner 未开
  `hasUniqueResults()` 时把 id 组合为 `<runnerId>_<id>`（消费者可见 id 带前缀）；
  ② `RunnerSyntax` 存例子查询时会把 `:q:` 就地替换为 `<term description>`
  （i18n "search term"），`:q:` 不会原样保留。
- OHOS 特有: libKF5Runner.so 无版本 DT_SONAME、DT_RUNPATH（E537 安装 RPATH
  链接）、.codesign 段（安装后 binary-sign-tool 重签名）三断言全过。

## 干净重跑

conan-verify 的 G2 门禁以 CI profile 全量干净构建复现全绿
（`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
--build=missing --user=ohpcd --channel=stable`）：ctest 3/3 无总线套件 100%、
test_package 31/31；完整日志 reports/conan-create.log，门禁结果
G1–G4 + L2/L4/L5 全 PASS，见 reports/conan-verify-report.md。

---

- 构建日志 `reports/conan-create.log` 依平台规则不随档（reports/ 仅随档脱敏 md）；脱敏的 `reports/conan-verify-report.md` 保留随档。
