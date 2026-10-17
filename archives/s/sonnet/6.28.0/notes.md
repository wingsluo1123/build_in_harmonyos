# sonnet 6.28.0 适配笔记

## 适配概况

KDE Frameworks 6 拼写检查框架 6.28.0 的 HarmonyOS PC 适配，基于已发布的
6.26.0 配方（base recipe）刷新。与 6.26.0 相比的功能增量是恢复了上游
QML 与组件（Widgets）面：ohpcd 现已发布 `qtdeclarative/6.11.1` 与
`qtshadertools/6.11.1`，`SONNET_USE_QML=ON` 得以构建并随包携带
`org.kde.sonnet` QML 模块；`SONNET_USE_WIDGETS=ON` 构建
`KF6SonnetUi`（Highlighter/Decorator），两个 widgets 上游测试也能在
`QT_QPA_PLATFORM=offscreen` 下直接运行（6.26.0 时因缺 Qt6Widgets 运行
支持被跳过）。

## 上游变化 6.26.0 -> 6.28.0（与 OHOS 适配相关）

- 上游要求 ECM >= 6.28.0，构建工具升级为 `extra-cmake-modules/6.29.0`。
- poqm 翻译步骤重新可用（`qt6linguisttools/6.11.1` 提供
  Qt6LinguistTools），6.26.0 的 `KF_SKIP_PO_PROCESSING` 规避不再需要，
  本配方未携带任何补丁（`patches: {}`）。
- 上游 autotests 共 7 个（5 个核心 + 2 个 widgets），全部在
  `BUILD_TESTING=ON` 的 conan create 内运行。

## 适配要点

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：CMake 不认识 HarmonyOS 目标平台
  （无 Platform/HarmonyOS 模块），绕开 KDE 平台检查。
- `SONNET_NO_BACKENDS=ON`：OHOS 上无 hunspell/aspell/voikko 等后端，
  Speller 报告无可用后端；Settings/GuessLanguage 的语义随之为
  "无字典配置"（见下）。
- `SONNET_USE_WIDGETS=ON` + `BUILD_DESIGNERPLUGIN=OFF`：构建
  KF6SonnetUi 但不需要 qttools 的 Qt6UiPlugin。
- `SONNET_USE_QML=ON` + `CMAKE_INSTALL_QMLDIR=lib/qml`：随包携带
  `org.kde.sonnet` QML 模块（Speller 等），消费者经
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` 找到 qtdeclarative。
- `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG="-Wl,-soname,"` +
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`（toolchain 变量与
  cache_variables 双重设置）：见"问题 1"。
- ECM_MODULE_PATH 手动设置 + `conan_cmakedeps_paths.cmake`：与 6.26.0
  相同，CMakeDeps 生成的 ECMConfig.cmake 不传播该变量。
- `bin/` 下的 `parsetrigrams6` 是随包 CLI，配方声明
  `bindirs=["bin"]` 并在 `commands.json` 注册 6.28.0（R38）。
- 上游测试环境的 `QML2_IMPORT_PATH` 由配方从构建树里 qmldir 的 `module`
  行推导：ECM 将 QML 模块生成在 `<build>/bin/org/kde/sonnet`
  （`QT_QML_OUTPUT_DIRECTORY=<build>/bin`，对齐 KDECMakeSettings 的
  `RUNTIME_OUTPUT_DIRECTORY`），导入根需按 URI 段数上溯（`org.kde.sonnet`
  → `<build>/bin`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备构建在链接/安装期报 `CMake Error: failed to create symbolic link '../../bin/libKF6SonnetCore.so.6': Permission denied`（cmake_symlink_library: System Error） | 设备 HMDFS 用户卷拒绝 symlink()（EPERM，设备级限制），CMake 默认的版本化 .so 符号链接链无法创建（E330/E331 类） | `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`（toolchain + cache 双写）使每个共享库以裸名发布；配合显式 `-soname` 标志（E383/E537）让库携带真实 DT_SONAME（kwidgetsaddons 6.28.0 同源修复、kcolorpicker/expat 先例）。构建树 readelf 验证：`SONAME=libKF6SonnetCore.so`、SonnetUi 的 NEEDED 为裸名 |
| 2 | 消费者测试断言 `Settings::setDefaultLanguage/setDefaultClient` 往返失败 | `SettingsImpl::setDefaultLanguage` 只接受 `loader->languages()` 中存在的语言（`setDefaultClient` 同理对 `clients()`）；无后端时两表为空，setter 是上游设计的 no-op，getter 保持 `restore()` 播种的 `QLocale::system().name()`/空串 | 改为断言"设置后保持不变"的 no-op 语义（这是无后端配置的真实行为），并把该语义写进测试注释与 MANIFEST |
| 3 | 消费者测试 `GuessLanguage::identify` 对英文/德文都返回空 | `GuessLanguagePrivate` 构造函数把每个 script 的语言候选表裁剪为"有已安装字典的语言"（`Loader::openLoader()->languages()`），无后端时该表恒空——即使三角模型已内嵌也无可评分语言列表 | 改为断言无字典配置下 identify() 优雅返回空（不崩溃、不悬挂）；三角数据管线本身由 `cli-parsetrigrams6` 用例覆盖（parsetrigrams6 对语料正常产出三角数据） |
| 4 | 曾在缓存中残留旧构建的 sonnet/6.28.0 包（其 libKF6SonnetUi.so 仍记录相对路径 NEEDED），消费者测试加载行为与构建树不一致 | 早期（修复前）构建产物残留于本地缓存 | `conan remove "sonnet/6.28.0@ohpcd/stable" -c` 后重新 create（勿用 rm -rf 删包目录）；收官验证即在此清缓存后的全新构建下取得 |
| 5 | 离线检视（AtomCode 真机）指出 `_run_upstream_tests` 的 QML 导入根少算一级（固定 `dirname` 上溯一层），多段 URI（`org.kde.sonnet`）的接线达不到注释声称的目的 | ECM 把模块生成在 `<build>/bin/org/kde/sonnet`，引擎按 `<importpath>/org/kde/sonnet` 解析，导入根需按 URI 段数上溯；当前 7 个上游测试均不 import 该模块，属潜伏缺陷 | 改为读取 qmldir 的 `module` 行、按 URI 段数计算导入根（单段 URI 行为不变，多段 URI 修正） |
| 6 | 离线检视指出 test_package 有 5 处 `check(desc, true)` 不可证伪，且 parsetrigrams6 用例未检查 `corpus.open()` 结果（残留旧语料可致假通过） | 冒烟式断言只记录"未崩溃"，失败路径不落 FAIL；语料写入失败后旧文件仍可驱动工具给出"成功" | 5 处全部改为按上游源码（speller.cpp/highlighter.cpp）核实的契约断言（无后端下 `isValid()==false`、`isCorrect→true`、`isMisspelled→false`、`suggest→[]`、高亮器保持挂接于文档）；语料先 `remove` 再写、`open`/`write` 计数校验，失败即 FAIL 并提前返回 |

## 验证结果

- 上游源码 SHA256 与官方 .sha256 核对一致（下载取回后按本文件值复核；
  `conandata.yml` 以官方 `download.kde.org` 为首选、NJU 镜像兜底，两处
  tarball 字节一致）：
  `66c6b439950bec7f67b730e6e49d6d30cba21dad115e4a47c4fe46014cc19c3b`。
- 设备 `conan create`（ci/conan/profiles/ohos-aarch64，armv8/Release，
  clang 15，cppstd 17，libc++，os=OHOS 6.0，shared=True；验证前已
  `conan remove` 清空缓存，为全新全量构建）。
- 上游 CTest：**7/7 通过**（BUILD_TESTING=ON，create 内运行）：
  sonnet-test_filter / test_core / test_suggest / test_settings /
  test_autodetect / test_decorator / test_highlighter，
  `100% tests passed, 0 tests failed out of 7`。
  其中 test_autodetect 等用例在无后端时按上游逻辑内部 QSKIP
  （ctest 计为通过，属上游既有行为）。
- Conan test_package：**6/6 用例、23 项断言全过**
  （Speller 生命周期 5、Settings 7、GuessLanguage 无字典语义 2、
  Highlighter 3、org.kde.sonnet QML 2、parsetrigrams6 CLI 4），
  `TEST SUMMARY: 6/6 cases passed, 23 checks, 0 failures`。
- 包引用：`sonnet/6.28.0@ohpcd/stable#3cb2de1adf4814f9b7dd01a6595927d7`
  包 ID `1b9180db9e62194d8376b684eec9400c9e837e9c`
  （离线检视整改后的全量重跑 run5：CTest 7/7、test_package 6/6 用例
  23 断言 0 失败；完整日志存证 `$HOME/sonnet-6280-run5-create.log`）。
- 交付物：`lib/libKF6SonnetCore.so`、`lib/libKF6SonnetUi.so`、
  `lib/qml/org/kde/sonnet/`（QML 模块）、`lib/cmake/KF6Sonnet/`、
  `include/`、`bin/parsetrigrams6`。

---

**编译结束**: 2026-10-17 04:08
**最终状态**: built
