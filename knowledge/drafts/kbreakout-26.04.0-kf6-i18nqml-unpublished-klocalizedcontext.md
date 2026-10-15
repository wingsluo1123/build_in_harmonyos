# KF6 QML 应用找不到 KLocalizedQmlContext：制品仓 ki18n 只发布核心 KF6::I18n

> Draft: `DRAFT-KBREAKOUT-26040-KF6-I18NQML-UNPUBLISHED-KLOCALIZEDCONTEXT`
> Stem: `kbreakout-26.04.0-kf6-i18nqml-unpublished-klocalizedcontext` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-KBREAKOUT-26040-KF6-I18NQML-UNPUBLISHED-KLOCALIZEDCONTEXT
- **严重度**: 2
- **类别**: platform|limitation|headers|qml
- **触发工具**: conan|clang
- **阶段**: compilation

## 错误特征

`conan create` 到编译阶段（configure 已通过）报：

```
src/canvaswidget.cpp:18:10: fatal error: 'KLocalizedQmlContext' file not found
#include <KLocalizedQmlContext>
         ^~~~~~~~~~~~~~~~~~~~~~
1 error generated.
```

（kbreakout 26.04.0 实测；同一缺口在 alligator 26.04.0 上以
`KLocalization::setupLocalizedContext` 形式出现。）

## 根因

上游 KF6 应用在 `KI18N_VERSION >= 6.8.0` 时改用 **KF6::I18nQml** 模块：

| 上游代码位置 | 用法 |
|---|---|
| kbreakout 26.04.0 `src/canvaswidget.cpp` | `#include <KLocalizedQmlContext>` + `new KLocalizedQmlContext(engine)` |
| alligator 26.04.0 `src/main.cpp` | `#include <KLocalizedQmlContext>` + `KLocalization::setupLocalizedContext(&engine)` |

而制品仓已发布的 `ki18n/6.18.0` 只构建了核心 **KF6::I18n**。实测包内容：

```
$ ls <ki18n>/lib
libKF6I18n.so  libKF6I18nLocaleData.so  cmake
$ ls <ki18n>/qml            -> 不存在
$ ls <ki18n>/include/KF6/KI18n/
klazylocalizedstring.h  klocalization.h  klocalizedcontext.h
klocalizedstring.h      klocalizedtranslator.h  kuitsetup.h
ki18n_export.h          ki18n_version.h
                            ^ 没有 klocalizedqmlcontext.h
```

即 `KF6::I18nQml`（ki18n 的 `src/i18n-qml` 子模块）**根本没有发布**。于是
`find_package(KF6 COMPONENTS I18n)` 成功、configure 通过，编译到使用点才失败。

同库里的等价 API `KLocalizedContext`（`include/KF6/KI18n/klocalizedcontext.h`）
提供了完全相同的 QML 上下文对象机制（`i18n()` / `i18nc()` / `i18np()` /
`xi18n*()` / `i18nd*()`，`translationDomain` 属性），只是自 KI18N 6.8 起被
标记 deprecated。

**第二个坑（只改类名仍然编译不过）**：`klocalizedcontext.h` 全文包在
`#if KI18N_ENABLE_DEPRECATED_SINCE(6, 8)` 里，而 KDE 应用模板普遍带
`ecm_set_disabled_deprecation_versions(KF <ver>)`，它把
`KF_DISABLE_DEPRECATED_BEFORE_AND_AT`（进而 `KI18N_DISABLE_DEPRECATED_BEFORE_AND_AT`）
设成 6.21 之类 → `KI18N_ENABLE_DEPRECATED_SINCE(6, 8)` 为 0 → 头文件内容整体
被 `#if` 掉，报 `use of undeclared identifier 'KLocalizedContext'`。

## 影响范围

- 所有 Qt6/KF6 **QML** 应用（`QQuickWidget` / `QQmlApplicationEngine` +
  `engine->rootContext()->setContextObject(...)`）在本仓制品仓上构建时。
- 已在仓内命中两次：alligator 26.04.0（`patches/0002-main.cpp-use-KLocalizedContext-for-ohos.patch`）、
  kbreakout 26.04.0（`patches/0002-canvaswidget-cpp-use-KLocalizedContext.patch`）。
- 纯 Qt Widgets 应用不受影响（不使用 QML i18n 上下文）。
- **不是**"上游 bug"、也不是配方参数问题：这是制品仓未发布 KF6 可选 QML 模块的平台缺口。

## 推荐方案

**方法**: `patch-to-klocalizedcontext-keep-deprecation-visible`

1. **先确认缺口在依赖侧**（免得在自己的配方里瞎调参）：查看已发布 ki18n 包内
   `lib/`、有无 `qml/`、`lib/cmake/KF6I18n/` 有无 I18nQml 目标、
   `include/KF6/KI18n/` 有无 `klocalizedqmlcontext.h`。三者皆无 → KF6::I18nQml 未发布。
2. **补丁改用 KLocalizedContext**：删掉 `#include <KLocalizedQmlContext>` 与
   `KI18N_VERSION >= QT_VERSION_CHECK(6, 8, 0)` 分支，统一
   `engine->rootContext()->setContextObject(new KLocalizedContext(engine));`。
   QML 侧 `i18n()`/`xi18n()` 表面不变，是功能等价替换，不是 stub/return 0。
3. **同时放回 deprecated 声明**：
   `target_compile_definitions(<target> PRIVATE KI18N_DISABLE_DEPRECATED_BEFORE_AND_AT=0)`。
   不要为了它删掉 `ecm_set_disabled_deprecation_versions`（会连带放开整套 KF 弃用面）。
4. 源码里若有 `if(TARGET KF6::I18nQml)` 条件链接，保持原样（目标不存在时自动跳过）。
5. **不要在本 PR 捎带修改 ki18n 配方**（W2/R36：依赖问题须独立 PR）；补丁注释里写明
   "制品仓未发布该模块 + 先例包"，便于 I18nQml 发布后回收补丁。
6. **运行期配套**（QML 应用通病）：QML 场景通常装在 `share/<app>/qml` 并由
   `QStandardPaths::AppDataLocation` 解析 → 消费方需 `XDG_DATA_DIRS` 指向包
   `share/` 目录；`org.kde.games.core` 之类依赖 QML 模块需 `QML2_IMPORT_PATH`。
   kbreakout 的 `package_info()` 已用 `runenv_info` 导出
   `LD_LIBRARY_PATH` / `QT_PLUGIN_PATH` / `QML2_IMPORT_PATH` / `XDG_DATA_DIRS`。

## 验证命令

```bash
# 缺口确认
ls <ki18n-pkg>/qml 2>&1; ls <ki18n-pkg>/include/KF6/KI18n/ | grep -i qml

# 补丁后全流程（kbreakout 26.04.0 实测）
conan create archives/k/kbreakout/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="kbreakout/*"
# RESULT: 构建成功 + test_package 4 用例 / 6 断言全通过
```

## 取证记录

- 包: kbreakout 26.04.0（`archives/k/kbreakout/26.04.0`），先例 alligator 26.04.0
  （`archives/a/alligator/26.04.0` 的 `knowledge_gained` 第一条）
- 逐字证据: `archives/k/kbreakout/26.04.0/reports/test-report.md` §4 问题 1
  （含可复现证据：失败构建目录
  `/storage/Users/currentUser/.conan2/p/b/kbrea463d97124eb31/b/src/canvaswidget.cpp`
  第 18/39 行仍保留未修补的 `KLocalizedQmlContext` 用法）。
  说明：首次失败日志已被后续成功复跑覆盖，故不以日志行号作为唯一证据。
- 关联正式条目: 本条与 E537（Conan 缓存绝对路径 DT_NEEDED 泄漏 + 重签）在同一包上
  同时命中，但根因不同：E537 管"链接期路径烙印"，本条管"制品仓缺 KF6 QML 子模块"
