# libkdegames 24.12.3 适配笔记（HarmonyOS PC / aarch64）

## 1. 上游信息

| 项 | 值 |
|---|---|
| 上游版本 | KDE Gear 24.12.3（`RELEASE_SERVICE_VERSION_MAJOR/MINOR/MICRO = 24/12/3`） |
| 源码 | https://invent.kde.org/games/libkdegames/-/archive/v24.12.3/libkdegames-v24.12.3.tar.gz |
| sha256 | `5bd661dff44b331b36ac4394d1f1bf4175c5d1b04cad65ed0cd857ea902e50a9` |
| 构建系统 | CMake ≥ 3.16 + ECM |
| 语言 | C++（lang-preflight: detected=cpp，42 个源文件，主体占比 100%） |
| 库版本 | `LIBKDEGAMES_VERSION_LIB = 6.0`，产物 `libKDEGames6.so` / `libKDEGames6Private.so` |
| Qt/KF 下限 | `QT_MIN_VERSION 6.5.0`、`KF_MIN_VERSION 6.0.0`（Qt6/KF6 线，非 Qt5） |

24.12.3 与仓内已有的 26.04.0 同属 Qt6/KF6 构建线，配方骨架可复用；差异集中在版本号、
源码 URL/sha256，以及上游测试注册数量（见 §3）。

## 2. 依赖决策（W0 实测）

`find_package(KF6 COMPONENTS Archive ColorScheme Completion Config ConfigWidgets DNSSD
GuiAddons IconThemes I18n NewStuff XmlGui)` + `Qt6 Widgets Qml Quick Svg Test` +
`OpenAL` + `SndFile`（REQUIRED）。

映射到制品仓（逐个实测存在）：

```
qtbase/6.11.1  qtdeclarative/6.11.1  qtsvg/6.11.1
karchive/6.18.0(override)  kcolorscheme/6.18.0  kcompletion/6.18.0
kconfig/6.18.0  kconfigwidgets/6.18.0  kcoreaddons/6.18.0  kdnssd/6.29.0
kguiaddons/6.18.0  ki18n/6.18.0  kiconthemes/6.18.0  knewstuff/6.18.0
kxmlgui/6.18.0  openal-soft/1.25.2  libsndfile/1.2.2
tool_requires: ecm/6.26.0
```

- `karchive/6.18.0` 必须 `override=True` 钉版：`kiconthemes/6.18.0` 的配方要求
  `karchive/6.19.0`，而 `knewstuff/6.18.0` 要求 `karchive/6.18.0`，不钉版会在图解析阶段
  直接 `Version conflict`（实测）。
- KF6 用 6.18.0 线（≥ 上游下限 6.0.0），与仓内 26.04.0 配方保持一致，避免同工程两套 KF 闭包。

## 3. 上游测试清点（R51 申报表）

| 位置 | 注册方式 | 进 ctest | 断言数 | 说明 |
|---|---|---|---|---|
| `src/private/tests/` | `ecm_add_tests(... NAME_PREFIX "libkdegamesprivate-")` | 是（2 个） | 113 / 11 | 私有库 KGameSvgDocument / KGameProperty 测试 |
| `tests/kgamepopupitemtest` | `ecm_mark_as_test(...)` | **否** | **0** | 手工 GUI 演示程序，非自动化用例 |
| 合计 | — | **2** | 124 | `ctest --show-only` 实测只列出 2 条 |

**为什么第 3 个不进 ctest（实测，不是推断）**：

1. `tests/CMakeLists.txt` 调的是 `ecm_mark_as_test()`，而 ECM 该宏在 `BUILD_TESTING=ON`
   分支**不调用 `add_test()`**（源码：`share/ECM/modules/ECMMarkAsTest.cmake`），只有
   `BUILD_TESTING=OFF` 时才做 `add_executable(${target} EXCLUDE_FROM_ALL)` 包装。
   因此该目标被构建，但从不注册为 ctest 用例。
2. 即便手工执行 `build/Release/bin/kgamepopupitemtest`，其源码
   （`tests/kgamepopupitemtest.cpp`）**零断言**（无 `QCOMPARE`/`QVERIFY`/`QTEST_*`），
   `main()` 直接构造 QApplication + 场景后进入 `app.exec()` 事件循环——它是要人肉点击
   按钮看效果的 demo。
3. 本机无显示服务（无 X/Wayland，也无 xvfb），`QT_QPA_PLATFORM=offscreen` 与 `minimal`
   ＋`QT_QUICK_BACKEND=software` 下该程序均停在窗口显示处不再前进（60s/150s 超时实测），
   属环境限制而非用例失败。

结论：**本包上游自动化用例数为 2，不是 3**。任何"3/3 通过"的说法都是错的。

## 4. OHOS 适配要点

1. **`KF_IGNORE_PLATFORM_CHECK=TRUE`**：ECM/KDE 平台白名单不含 OHOS，不做该处置时
   configure 阶段直接拒绝。
2. **`KF_SKIP_PO_PROCESSING=ON`**：`ki18n_install(po)` 需要完整 gettext 工具链，库本身
   不需要生成的 catalog，跳过以免无谓依赖。
3. **`BUILD_SVG_CHECKS=OFF`（上游默认）**：carddecks 的 SVG 校验才需要 svgcleaner/7zip，
   默认关闭时仅 gzip 参与 SVGZ 生成。
4. **ECM_MODULE_PATH 手写**：CMakeDeps 生成的 ECMConfig 不传播上游 CMakeLists 依赖的
   `ECM_MODULE_PATH` 变量，配方中显式指向 `share/ECM/{modules,find-modules,kde-modules}`。
5. **`conan_cmakedeps_paths.cmake` 手工生成**：qtbase 与 KF6 各包以
   `cmake_find_mode=none` 发布，CMakeDeps 不会把它们的 `lib/cmake` 加进
   `CMAKE_PREFIX_PATH`，需要自己拼接。
6. **OpenAL / SndFile**：上游用 `find_package(OpenAL)`（模块模式）+ `find_package(SndFile)`，
   在 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON` 且依赖 `lib/cmake` 进入前缀路径后由上游
   `OpenALConfig.cmake` / `SndFileConfig.cmake` 命中。
7. **`try_compile(check-libsndfile-capabilities)`**：configure 阶段用 try_compile 校验
   libsndfile 的 Ogg/Vorbis 枚举，conan 的 libsndfile 1.2.2 通过。

## 5. 打包与消费契约

- `package_info()` 使用 `cmake_find_mode=none` + `builddirs=["lib/cmake"]`：工程自带
  `KDEGames6Config.cmake`（内含 `find_dependency` 链），不能让 CMakeDeps 生成同名配置遮蔽。
- `cpp_info.libs = ["KDEGames6", "KDEGames6Private"]`。
- `cpp_info.includedirs = ["include/KDEGames6", "include"]`：头文件装在
  `<prefix>/include/KDEGames6/`（如 `include/KDEGames6/KGameClock`），CMake 消费者走上游
  `KDEGames6Config` 不受影响，但 pkg-config / 手工 `-I` 必须指向子目录。
- `runenv_info` 追加 `LD_LIBRARY_PATH`（lib）、`QML2_IMPORT_PATH`（**lib/qml**）。
  本包不发 Qt 插件，QML 模块 `org.kde.games.core` 实际装在 `<prefix>/lib/qml`
  （安装日志与包目录实测），因此不再注入 `QT_PLUGIN_PATH`。

## 6. 验证结果（全部实测，非占位）

### 6.1 conan create（W3 本地）

```
conan create archives/l/libkdegames/24.12.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="libkdegames/*"
→ rc=0
→ libkdegames/24.12.3#7731c2437858b5c2e9f088cac42f5d15:53177846b8b3702149a9a58a031101b0207dd639#0aa6b5678cd82f469ddf4a697effa3da
    Package '53177846b8b3702149a9a58a031101b0207dd639' created
```

configure 19.3s 完成，`ctest --output-on-failure --no-tests=error` 返回 0。

### 6.2 上游 ctest（实跑）

```
$ ctest --test-dir <build>/Release --show-only
Total Tests: 2
  Test #1: libkdegamesprivate-kgamesvgdocumenttest  (113 断言)
  Test #2: libkdegamesprivate-kgamepropertytest     (11 断言)

$ ctest --test-dir <build>/Release --output-on-failure
100% tests passed, 0 tests failed out of 2
```

`tests/kgamepopupitemtest` 未注册、零断言、无显示环境下挂起——详见 §3，按实测上报
**2/2**，不虚构 3/3。

### 6.3 test_package（OHOS 消费者测试）

```
$ conan test archives/l/libkdegames/24.12.3/test_package libkdegames/24.12.3 \
    -pr:h=... -pr:b=...
PASS: KGameClock/KGameTheme/KGamePopupItem API OK
→ rc=0
```

覆盖（与 `test_package/test.cpp` 逐条对应，不虚报）：

- `KGameClock`：`timeString()` 非空、`setTime(65u)` → `seconds()==65`、
  `setTime(QStringLiteral("00:01:05"))` → `seconds()==65`、`pause`/`resume`/`restart`/
  `showTime` 可调用。
- `KGameTheme`：`identifier()` 一致、`setName`/`name()` 往返、`setLicense`+`setAuthor`
  → `license()`/`author()` 往返、`readFromDesktopFile("/nonexistent/theme.desktop")`
  必须返回 false（否定用例；未做真实 .desktop 正向读取）。
- `KGamePopupItem`（上游无自动化用例，此处为鸿蒙侧独有覆盖）：`hidesOnMouseClick`
  默认值与 setter、`messageTimeout()`=1500、`messageOpacity()`≈0.85、`sharpness()`
  Sharp↔Soft 往返、背景刷/文字色样式设置、`forceHide(InstantHide/AnimatedHide)` 可调用
  （`showMessage()` 的 QTimeLine 动画需活动场景视图，无头下段错误，故不断言动画）。

### 6.3.1 L5 可重定位性门禁（首轮 fail → 已修复转 pass）

首轮 W3 的 L5 为 fail（`soname_gate_failed`，5 项）：两个库缺 `DT_SONAME`；`DT_NEEDED`
含依赖包绝对路径与本包相对路径 `../../bin/libKDEGames6.so`；
`KDEGames6Targets-release.cmake` 带 `IMPORTED_NO_SONAME TRUE`。根因是 CMake 未加载
HarmonyOS 平台模块（`System is unknown to cmake`），`CMAKE_SHARED_LIBRARY_SONAME_*_FLAG`
未定义。

修复（配方内已落地，参照同仓 `libkdegames/26.04.0.1`）：

1. `generate()`：OHOS 下设 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` +
   `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG="-Wl,-soname,"`。
2. `package()` → `_sanitize_needed_entries()`：原位 `.dynstr` 字节改写路径形式 `DT_NEEDED`
   为裸基名（不改动 ELF 其他结构），再用 `llvm-objcopy --remove-section .codesign` +
   `binary-sign-tool sign -selfSign 1` 重签。**不要**改用 `patchelf --replace-needed`：
   它重写程序头表，产物被 OHOS musl 加载器拒绝。

修复后实测：`DT_NEEDED entries sanitized: 26`（主库 14 + private 12），
`L5_RESULT=pass`，`readelf -d lib/libKDEGames6.so` 确认 `SONAME` 存在且路径形式
`DT_NEEDED` 计数为 0。

### 6.4 过程中排除的两个坑（防后人重复踩）

1. **残缺二进制包**：`karchive`/`kguiaddons`/`ki18n`/`kwidgetsaddons`/`attica`/
   `kcolorscheme`/`kcoreaddons`/`kitemviews`/`kpackage` 的 6.18.0 包目录只剩裸 `.so`、
   缺 `conaninfo.txt`/`conanmanifest.txt`（解包中断），表现为
   `FindKF6 ... could not be found` 级联报错。`conan remove -c <pkg>` 后重跑 create
   即恢复——不是配方问题，也不是远端残缺发布。
2. **前缀路径必须覆盖传递依赖**：`_write_cmake_paths()` 原先只遍历直接依赖，
   `KF6ConfigWidgets -> KF6WidgetsAddons`、`KF6NewStuffCore -> KF6Attica` 这类
   `find_dependency` 链断掉；已改为递归遍历整张 host+build 依赖图并去重。
---

**编译结束**: 2026-10-17 22:53
**最终状态**: built
