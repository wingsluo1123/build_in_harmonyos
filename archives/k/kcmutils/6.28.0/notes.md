# kcmutils 6.28.0 适配笔记

## 编译环境
- 构建系统: cmake (ECM 6.28.0 tool package)
- 编译器: clang/clang++ 15 (OHOS SDK, aarch64-linux-ohos)
- 状态: built
- 基线: 已合入的 6.26.0 配方（PR #12534）逐条重放并适配 6.28.0 源码差异

## 软件简介

kcmutils 是 KDE Frameworks 6 的配置模块工具库：KCMultiDialog（多页配置
对话框）、KCModule（配置模块基类）、KCModuleLoader（插件加载）、
KPluginWidget + kcmshell6 运行器。kinfocenter（任务 #12847）的
`find_package(KF6 COMPONENTS KCMUtils ...)` 即本件。

## 上游源码核验（6.28.0）

- 上游 tag `v6.28.0` 经 `git ls-remote https://invent.kde.org/frameworks/kcmutils.git`
  核验：tag 对象 `adb147df68513e60e66167b6504288bf9cbb2c0d`，peeled commit
  `bf9134a413ca9919f3b7ab72d2460b1cd9e398f9`。
- 官方 tarball `kcmutils-6.28.0.tar.xz`：2402800 字节，SHA-256
  `9afe5ca9d1c4bd06479b2619326ec6f1e3c3998859dceaae3da9a4b7318d5a21`
  （官方源 302 到区域镜像；NJU/Aliyun 权威镜像同内容同日核验）。

## 与 6.26.0 配方的差异

| # | 变更 | 原因 |
|---|------|------|
| 1 | 版本 6.26.0 → 6.28.0；tool_requires ecm 6.26.0 → 6.28.0 | 上游 6.28.0 要求 `find_package(ECM 6.28.0)`；ecm/6.28.0 已发布 |
| 2 | 补丁 0001 新增：KF_DEP_VERSION 6.28.0 → 6.26.0 | 6.28.0 把依赖地板抬到 6.28.0，而 ohpcd 已发布的 KF6 线止于 6.26.0（kio/kxmlgui/kitemviews/ki18n）；kservice 6.28.0 同款处理 |
| 3 | kconfigwidgets 6.18.0 + override=True 顶传递依赖到 6.26（沿用） | kconfigwidgets/6.26.0 未发布（kxmlgui 6.26.0 同款方案，任务 #13725） |
| 4 | 补丁 0001：裁 src/qml（kcmutilsqmlplugin）挂 KCMUTILS_BUILD_QML_PLUGIN 开关（沿用） | **kio/6.26.0 是 KIOCORE_ONLY 基线**（无 KIOGui/KIOWidgets 目标），而 kcmutilsqmlplugin 链接 KF6::KIOGui |
| 5 | 补丁 0001：autotests 的 qmlkcm fixture、kcmloadtest、kcm_smoketestqml_test 同开关裁剪（6.28 新增 smoke 行） | 三者的 QML 加载链都 import org.kde.kcmutils（被裁插件）+ org.kde.kirigami（未上架） |
| 6 | 补丁 0001：find_package(KF6ConfigWidgets 6.18.0) + KF6KCMUtilsConfig.cmake.in find_dependency 同步降板（沿用） | kconfigwidgets cap（kxmlgui 同款两处地板） |
| 7 | 补丁 0001：KI18N_BUILD_WITH_QML 编译期回退（沿用） | ki18n 构建 BUILD_WITH_QML=OFF，无 KLocalizedQmlContext 头与 KI18nQml 目标 |
| 8 | 补丁 0001：kcmshell6 `std::ranges::sort` → `std::sort`（沿用） | clang 15 / libc++ 无 C++20 ranges 支持 |
| 9 | BUILD_TESTING=ON + _run_upstream_tests（沿用） | 上游测试在本地 arm64 OHOS 真跑 |

## QML 插件裁剪的消费者影响

- 裁掉的 kcmutilsqmlplugin 是 org.kde.kcmutils QML 模块（声明式 KCM
  框架）。KF6KCMUtilsCore / KF6KCMUtilsQuick / KF6KCMUtils 三个库完整保留。
- kinfocenter（本链最终消费者）走 Qt Widgets 路径
  （KPageDialog/KCMultiDialog），不依赖声明式 QML 插件。
- 补丁用 `if(KCMUTILS_BUILD_QML_PLUGIN)` 守卫而非删除——上游源码结构
  可追溯，未来 kio 发布 KIOGui 后可一行开关恢复。QML 插件关闭时
  KF6KCMUtilsQuick 仍可用（翻译域退化为 no-op）。

## 上游测试（N 申报口径，rule4）

上游 6.28.0 全树 QTest 测试函数/槽位定义数 = **5**：
- kcmultidialogtest.cpp：testClear、testLoadKcm
- kcmloadtest.cpp：testLoadQmlPlugin、testFallbackKCM
- module_data_codegen/module_data_test.cpp：testReadingDefaults

另有脚本型 CTest（`add_test` 直接驱动 kcmshell6）= **2**：
- kcm_smoketest_test（--smoke-test fakekcm）
- kcm_smoketestqml_test（--smoke-test kcm_testqml）

上游合计 **N=7**。QML 插件裁剪形态下实跑 4 行：
- kcmultidialogtest（2/2）
- module_data_test（1/1）
- kcm_smoketest_test（1/1，fakekcm fixture 经构建树插件命名空间解析）
裁掉 3 行（kcmloadtest 2 槽 + kcm_smoketestqml_test 1 行）：QML KCM 加载链
依赖被裁的 org.kde.kcmutils QML 模块与未上架的 org.kde.kirigami
（技术原因见 PR 正文「测试减少原因」段）。

## 依赖核验（W0，R35 conan download 口径）

qtbase-sql-dbus/6.11.1 ✅ qtdeclarative/6.11.1 ✅ kio/6.26.0 ✅
kxmlgui/6.26.0 ✅ kconfigwidgets/6.18.0 ✅（cap）kitemviews/6.26.0 ✅
openssl/3.5.6.1 ✅ zstd/1.5.7 ✅ libxml2/2.15.3 ✅ ecm/6.28.0 ✅
override 目标：kconfig/kcoreaddons/kguiaddons/ki18n/kwidgetsaddons/
kcolorscheme/kcodecs 全 6.26.0 ✅

## conan override 方案（同 kxmlgui 6.26.0 实证）

- 无 override：`Version conflict: Conflict between ki18n/6.26.0 and
  ki18n/6.18.0 in the graph`
- override 单声明后：graph 解析成功，全图唯一 6.26 版本

## 真机验证结果

真机 Huawei PC（HarmonyOS 6.0 / aarch64 / clang 15），2026-10-18。两轮复跑：

- 14:14（离线检视整改后）`python3 scripts/ohc-run.py conan-verify kcmutils 6.28.0`
  → **Verdict PASS**，上游 ctest 3/3（0.70s）。
- 15:43（CI build #98558 失败修复后，重写 test_package 运行时链接准备逻辑）
  同一命令 → **Verdict PASS**；test_package ctest 1/1 Passed 0.16s，日志
  `test_package runtime links: 0 copied (0 relative names)`——本机依赖为制品仓
  二进制（裸 SONAME），无相对 DT_NEEDED；CI 从源码构建依赖时的相对 NEEDED
  场景由同一解析/镜像逻辑覆盖（见下节）。上游 ctest 数据取自 14:14 同
  package_id 运行。

- G0 ✅（E092 CMake/OHOS 平台模块风险已在配方处理）；G1 ✅（export_sources/补丁/
  R26/conandata/test_package 全项）；G2 ✅ conan create 成功；G3 ✅（R26 无同名库冲突）；
  G4 ✅（报告「无法找到程序包 ID」为验证器展示格式，退出码 PASS）；L2/L4/L5 无 cache
  路径跳过。
- 报告：`reports/conan-verify-report.md`（1187 B，md5 `1133fc7da34c9f4c516dcd7f3a0baa15`，
  sha256 `cd703f52669e173fb5509d73d54e62cc7adfff70e50cf7c94683d9a7c8aa7c82`，日期
  `2026-10-18T15:43:10.932249`）。
- 配方 revision `6fe7049a1b09f4dc3db626ed1c7891f2`；package_id
  `00bd1040370702c80e670579d1791cb67a3c9b65`；package revision
  `e08e068b8f198b226dd7d9e7a74a76ed`（OHOS 6.0 / armv8 / Release / clang 15 /
  libc++ / shared=True）。
- 上游 CTest（BUILD_TESTING=ON，14:14 运行的真机 ctest 输出；`conan-create.log`
  按平台规则不随档）：`100% tests passed, 0 tests failed out of 3`（总耗时 0.70s）——
  kcmultidialogtest 0.17s、kcm_smoketest_test 0.39s、module_data_test 0.13s 全 Passed。
  package_id 与 15:43 复跑相同，包载荷未变。
- test_package（消费者 E2E，`test_kcmutils` + `consumer_kcm.so`）：15:43 复跑 ctest
  `100% tests passed, 0 tests failed out of 1`（0.16s）；同一测试源码直接复跑测试
  二进制输出 `E2E TEST SUMMARY: 8 passed, 0 failed`（plugin_metadata、module_load、
  module_class、module_widget、dialog_add_module、dialog_no_error、
  unknown_module_fallback、module_data_relevance 共 8 项 TEST PASS）。
- 补桩/镜像行为：复跑日志未出现 `baked DT_NEEDED path stubs` 与
  `ctest runtime links mirrored` 行（两者计数均为 0：绝对路径桩在上轮已落盘）；
  test_package 新日志 `test_package runtime links: 0 copied (0 relative names)`
  表明按 DT_NEEDED 精确镜像的逻辑已执行，本机无相对名可镜像。上游 3 行与
  test_package 仍全绿。

## CI 失败修复（build #98558：test_package 相对 DT_NEEDED）

CI worker OpenHarmonyPCDeveloper-CI-013 的 #98558 在 test_package 的 ctest 失败：

```
Error loading shared library ../../bin/libKF6ConfigCore.so:
(needed by .../conan2/p/kconf7db3dce604ff1/p/lib/libKF6ConfigGui.so)
```

- 根因：CI 从源码构建依赖闭包，kconfig 等依赖的二进制记录构建树相对 DT_NEEDED
  （`../../bin/libKF6ConfigCore.so`）；musl 对含 `/` 的名字按**进程 CWD**（ctest 的
  `self.build_folder`）解析。旧实现用 `self.cpp.build.bindirs[0]`（"bin"）相对
  conan 进程 CWD 落盘，CI 上该目录不是 ctest 的解析点，镜像缺失。本机使用制品仓
  二进制（裸 SONAME），因此本地复跑不触发该路径。
- 修复（`test_package/conanfile.py` 的 `_prepare_runtime_links`）：以
  `os.path.abspath(self.build_folder)` 为基准，扫描全部依赖 `lib/lib*.so*` 的
  DT_NEEDED，对「含 `/` 且非绝对」的条目收集基名，精确镜像到
  `normpath(build_folder/<needed>)` 的目录；symlink 失败回退 `shutil.copy2`
  （HMDFS EPERM）。日志行 `test_package runtime links: N copied (M relative names)`。
- 算法本地复核：以合成 ELF（DT_NEEDED `../../bin/libbar.so`）+ 临时目录桩运行该
  方法，结果 1 copied / 1 relative name，仅被引用的 `libbar.so` 落到
  `<build>/../../bin/`，无关库不复制。
- 设备复跑：Verdict PASS（15:43），test_package ctest 1/1 Passed 0.16s；本机
  0 relative names 属预期（制品仓二进制无相对 NEEDED），CI 侧由源码构建依赖的
  相对 NEEDED 场景按同一解析器与同一路径计算处理。
- ELF 取证：三库均带裸 SONAME（`libKF6KCMUtils.so` / `libKF6KCMUtilsCore.so` /
  `libKF6KCMUtilsQuick.so`），本项目内部 NEEDED 为裸 soname；对已发布第三方 KF6
  依赖仍为绝对 cache 路径（平台基线，由补桩机制处理）。
- 产物 md5：libKF6KCMUtils.so `897acb174d83f3119040c28ab33c9354`、
  libKF6KCMUtilsCore.so `2698b64fcf936035e18321d1941fe815`、
  libKF6KCMUtilsQuick.so `b5459a286c86568289d920e6f2bd6ee2`。

## 离线检视（R1）与整改

真机 AtomCode 离线检视（`/review staged`，基于整改前 head `01d1770b4c4a`）结论
approve with nits；P1 为检视方自证误报（补丁 hunk 行数与上游 tarball dry-run 均通过）。

- P2-1（补桩父目录仅字符串前缀判断，`/root/../etc/x`、`/database` 可绕过）：
  已整改。改用 `realpath` 后 `_under_root()` 做分隔符感知的根包含判断（home 或 /data）。
- P2-2（6 个兼容目录无差别复制全部依赖库，`build_folder/../bin` 在构建树外）：
  已整改为按依赖闭包内「构建树相对 DT_NEEDED 名」集合精确镜像；保留
  `build_folder/../bin` 一项——`../../bin/...` 字符串按 ctest 工作目录
  `<build>/autotests` 解析，删除会破坏该解析点。新头部复跑 ctest 3/3 证明镜像收缩无回归。
- P3-ELF（解析器只捕 OSError、取首个 SHT_STRTAB）：已加固为经
  `SHT_DYNAMIC.sh_link` 解析 .dynstr、全程边界检查、异常返回空表（P2-2 的前置安全项）。
- P3-unused（`import re`、局部重复 `import glob`）：已清理。
- 其余 5 项 P3 记录不改：`shared` option 与硬编码 `BUILD_SHARED_LIBS=ON`、
  test_kcmutils.cpp 的 `KCModule*` 泄漏、test_package `env="conanrun"` 无脚本
  （由手动 Environment 生效）、test_package 依赖库复制、sharedqmlengine
  translationDomain fallback 的 set/get 契约。
- 检视漏项 1（`KCMUTILS_BUILD_QML_PLUGIN` 从未定义）：已整改，补丁 0001 增加
  `option(... "..." OFF)` 显式默认 OFF，四个守卫不再依赖「未定义即假」。
- 检视漏项 2（`reports/conan-create.log` 被 notes 行号引用但按平台规则不随档）：
  已整改，notes 删除行号引用；验证报告中的 `📄 日志:` 行为验证器生成格式，保留。

## 适配期定位记录：kcmultidialogtest loadcalled=0（DT_SONAME 缺失）

首轮真机 conan-verify 中 `kcmultidialogtest` 失败：`Actual (dialog.property("loadcalled").toInt()): 0` /
`Expected (2): 2`，紧跟 `KPluginFactory could not create a KCModule instance from .../fakekcm.so`。

- 根因链：CMake 4.1.2 在 HarmonyOS 主机把 `CMAKE_SYSTEM_NAME` 探测为 `HarmonyOS`，但安装里没有
  `Platform/HarmonyOS.cmake`（只有 OHOS.cmake → include Linux），`CMAKE_SHARED_LIBRARY_SONAME_*_FLAG`
  未定义 → 三个库不带 `DT_SONAME`。于是 `DT_NEEDED` 记录的是各目标链接时的构建树相对路径：
  `kcmultidialogtest` 记 `../bin/libKF6KCMUtilsCore.so`，`fakekcm.so` 记 `../../bin/...`。OHOS musl
  按名字字符串区分已加载 DSO，同一库被加载两份，`KCModule::staticMetaObject` 指针不同 →
  `qobject_cast<KCModule*>` 失败 → `addModule` 回退 KCMError → `load()` 不被调用 → loadcalled=0。
  kcmshell6 自身与插件 NEEDED 字符串一致（同为 `../../bin/...`），故 `kcm_smoketest_test` 通过。
- 修复（E330 家族，kbookmarks 6.28.0 先例）：同时设置
  `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` / `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`（`-Wl,-soname,`）
  与 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`（variables + cache_variables 双通道）。HMDFS 拒绝
  symlink，版本化 `.so.6 -> .so` 链无法生成；NO_VERSIONED 保持无版本文件名，SONAME 旗标注入
  `DT_SONAME [libKF6KCMUtils*.so]`，消费者 `DT_NEEDED` 记为纯 soname。`_runtime_env` 同时把
  `<build>/bin` 前置进 `LD_LIBRARY_PATH`，供 ctest 解析构建树内自产库。
