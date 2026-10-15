# kookbook 0.3.0 适配笔记

## 编译环境

- 构建系统：cmake（上游顶层 `CMakeLists.txt`；KDE ECM 模块 + Qt6）
- 目标平台：HarmonyOS PC / OHOS 6.0 / aarch64（`aarch64-linux-ohos`），**原生构建**（build = host = OHOS/aarch64，非交叉编译）
- 编译器：clang 15（`/data/service/hnp/bin/clang`，来自 `tools.build:compiler_executables`），libc++
- Conan：2.29.1（OHOS 适配版），remote `ohpcd`
- profile：`ohos`（`[settings] os=OHOS, os.version=6.0, arch=armv8, compiler=clang, compiler.version=15, compiler.libcxx=libc++, compiler.cppstd=17, build_type=Release`）
- 编译日期：2026-10-15
- 状态：built

## 任务身份与源码身份

- 目标：`kookbook` 0.3.0（KDE KookBook，结构化 Markdown 食谱管理器）
- 上游仓库：<https://invent.kde.org/utilities/kookbook>（GitHub 镜像 `KDE/kookbook`）
- 官方源码包：<https://download.kde.org/stable/kookbook/kookbook-0.3.0.tar.xz>（2026-04-11 发布，57012 字节）
- SHA-256：`c32c11e4a5a690267dcdeeb2e919829b08f5fa439da1a19da5e40f4a0649694f`
  （本机 curl 下载 + `sha256sum` 计算，并与 `conan source()` 下载结果比对一致）
- 许可证：MIT（`COPYING`，Copyright (c) 2018 Sune Vuorela），随包安装到 `licenses/COPYING`
- 分支：`feat/kookbook-0.3.0`（worktree `build_in_harmonyos-kookbook`）；本仓此前无 kookbook 任何归档，属首次适配
- R47 语言预检：`lang-preflight kookbook 0.3.0 --src <src> --lang cpp` → `detected=cpp`（build_system=cmake，源文件 23 个，cpp 22 个，主体占比 96%）

## 制品仓依赖拓扑（W0，本次适配的决定性约束）

上游顶层 `CMakeLists.txt` 硬性要求：

```
find_package(Qt6 ${QT_MIN_VER} CONFIG REQUIRED COMPONENTS Widgets PrintSupport Qml)
find_package(ECM ${KF_MIN_VERSION})   # KF_MIN_VERSION = 6.0.0
```

`KDEInstallDirs / KDECompilerSettings / KDECMakeSettings / ECMInstallIcons /
ECMAddAppIcon / ECMAddTests / ECMDeprecationSettings` 全部来自 ECM。

逐个实测（`conan download --only-recipe` + `conan install --build=never`，R35：不使用 `conan list` 判定 binary）：

| 依赖 | recipe | binary | 说明 |
|---|---|---|---|
| `extra-cmake-modules/6.29.0` | ✅ | ✅ | `conan install` 成功 |
| `qtbase/6.11.1` | ✅ | ✅ | 包内含 `libQt6Test.so` + `Qt6TestConfig.cmake`；**无** `libQt6PrintSupport.so` / `Qt6PrintSupportConfig.cmake` |
| `qtbase/6.11.1.3` | ✅ | ✅ | **有** `libQt6PrintSupport.so` + `Qt6PrintSupportConfig.cmake` |
| `qtdeclarative/6.11.1` | ✅ | ✅ | 与 `qtbase/6.11.1`、`qtshadertools/6.11.1`（package id `57ffd8c7…`）配套 |
| `qtdeclarative/6.11.1.2` | ✅ | ✅（自身） | 但其依赖 `qtshadertools/6.11.1` 在 `qtbase/6.11.1.3` 下解析到 package id `6ea9a4dd…` → **Missing prebuilt package** |

实测冲突证据：

```bash
# qtdeclarative 与 PrintSupport 线互斥
conan install --requires=qtdeclarative/6.11.1 --requires=qtbase/6.11.1.3 ...
# ERROR: Version conflict: Conflict between qtbase/6.11.1 and qtbase/6.11.1.3
#        in the graph. Conflict originates from qtdeclarative/6.11.1

# qtdeclarative/6.11.1.2（唯一面向 6.11.1.3 的版本）缺传递依赖 binary
conan graph info --requires=qtdeclarative/6.11.1.2 ...
#   qtshadertools/6.11.1#7bc99312…  pkg_id=6ea9a4ddc4d559353477  binary=Missing
```

结论：**Qt6::Qml 与 Qt6::PrintSupport 当前不可兼得**。本配方选择保留 Qml
（`kookbooktouch` 前端，上游顶层 `find_package` 强制要求），放弃 PrintSupport——
与本仓既有的 `kgraphviewer 26.04.0`、`kdiagram 3.0.1`、`kapow 1.7.0`、
`conducteo 5.0.2`、`khelpcenter 26.04.0` 同一取舍（本仓共 33 个配方引用
PrintSupport，绝大多数为裁剪）。选 `qtbase/6.11.1` 而非 `6.11.1.3` 是因为前者
是全部已发布 Qt6 模块（含 `qtdeclarative`）的构建基线（本仓 453 个配方锁 `6.11.1`）。

## 上游测试清点（R51 三步法）

`autotests/CMakeLists.txt`：

```cmake
find_package(Qt${QT_MAJOR_VERSION} ${QT_MIN_VER} CONFIG COMPONENTS Test)
add_subdirectory(parsertest)
```

`autotests/parsertest/CMakeLists.txt` 通过 ECM 的 `ecm_add_test()` 注册 2 个
QtTest 目标（`ecm_add_test` 受 `BUILD_TESTING` 开关控制）：

| ctest 项 | 源文件 | 用例数 | 断言 |
|---|---|---|---|
| `ingredientsextractortest` | `autotests/parsertest/ingredientsextractortest.cpp` | 16（`QTest::newRow`，覆盖 `*`/`-` 两种项目符号、注释截断、空输入边界） | 每行 3 个 `QCOMPARE`（amount/unit/ingredient） |
| `recipeparsertest` | `autotests/parsertest/recipeparsertest.cpp` | 9（空输入、仅标题、tags、多 author、正文+配料，以及 2 个真实食谱文件 fixture `data/couscous.recipe.md`、`data/twoingredients.recipe.md`） | 标题/tags/配料/元数据共 ≥4 个 `QCOMPARE` |

两者均为 `QTEST_APPLESS_MAIN`，不创建 `QApplication`、不依赖显示服务。
`conanfile.py` 的 `build()` 末尾用 `ctest --test-dir <build> --output-on-failure
--no-tests=error` 实跑，**不用 `ignore_errors`**：上游套件必须全绿才成包，
`--no-tests=error` 防止"空注册集被当成功"。

## 编译步骤（实际执行）

```bash
# 1. 取官方源码（init-build 内置下载 + 解压 + 环境检查）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build kookbook 0.3.0 \
  --url=https://download.kde.org/stable/kookbook/kookbook-0.3.0.tar.xz --tar=tar.xz

# 2. 探索阶段：在 work 目录直接改源码（见「源码修改」）
# 3. 由 refresh-patch --auto 从 .orig/.work 差异生成补丁（未手写 diff）
python3 $SKILL_ROOT/scripts/ohc-run.py refresh-patch --auto kookbook 0.3.0

# 4. 验证配方自包含性（W3）：等价于 CI 的 conan create 口径
conan create . -pr:h=ohos -pr:b=ohos -r=ohpcd --build=missing --build=kookbook/*
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan install --requires=qtdeclarative/6.11.1.2` 报 `Missing prebuilt package for 'qtshadertools/6.11.1'` | `qtdeclarative/6.11.1.2` 把 `qtbase` 覆盖为 `6.11.1.3`，`qtshadertools/6.11.1` 在该组合下 package id 未发布 | 不使用该组合；改用 `qtdeclarative/6.11.1` + `qtbase/6.11.1`（均已发布且相互配套） |
| 2 | `conan install --requires=qtdeclarative/6.11.1 --requires=qtbase/6.11.1.3` 报 `Version conflict` | `qtdeclarative/6.11.1`（及 6.11.1.1）在 `requirements()` 中精确声明 `qtbase/6.11.1`，非范围 | 接受拓扑约束，`qtbase` 锁 `6.11.1`；PrintSupport 裁剪 |
| 3 | 顶层 `find_package(Qt6 … COMPONENTS … PrintSupport …)` 配置失败 | `qtbase/6.11.1` 包内既无 `libQt6PrintSupport.so` 也无 `Qt6PrintSupportConfig.cmake`（FEATURE_printsupport=OFF） | 补丁 0001 移除组件；补丁 0002–0005 移除绑定 `MainPane::print/printPreview` 的两个工具栏动作与实现 |
| 4 | `find_package(ECM)` 后 `include(KDEInstallDirs)` 找不到模块 | ECM 是 `tool_requires`（build context），CMakeDeps 不会把它的 `share/ECM/*` 放进 host 的 `CMAKE_MODULE_PATH` | `generate()` 中手工注入 `ECM_MODULE_PATH`（modules/find-modules/kde-modules）并手写 `conan_cmakedeps_paths.cmake`（accessibility 26.04.3 先例） |
| 5 | `KDEInstallDirs` 解析失败 | `ECMQueryQt` 依赖 `TARGET Qt6::qtpaths`，而本 qtbase 布局的 `Qt6Config.cmake` 不加载 `Qt6CoreTools` | 注入 `QUERY_EXECUTABLE=<qtbase>/bin/qtpaths6` 与 `_cli_option=--query`（mobipocket/accessibility 先例） |
| 6 | `find_package(Qt6 COMPONENTS Qml)` 找不到 Qml | `qtbase` 使用 `cmake_find_mode=none`，`Qt6Config.cmake` 需要额外前缀才能解析 `qtdeclarative` | 注入 `QT_ADDITIONAL_PACKAGES_PREFIX_PATH`（所有含 `lib/cmake/Qt6*` 的依赖前缀），并在 `conan_cmakedeps_paths.cmake` 中 PREPEND 各依赖前缀路径 |

## 源码修改（补丁由 `refresh-patch --auto` 生成，未手写 diff）

| 补丁 | 文件 | 改动 |
|---|---|---|
| `0001-CMakeLists.txt.patch` | `CMakeLists.txt` | `find_package(Qt6 … COMPONENTS Widgets PrintSupport Qml)` → 去掉 `PrintSupport` |
| `0002-src-desktop-mainwindow.cpp.patch` | `src/desktop/mainwindow.cpp` | 移除"打印当前食谱"与"打印预览当前食谱"两个工具栏动作 |
| `0003-src-desktop-panes-CMakeLists.txt.patch` | `src/desktop/panes/CMakeLists.txt` | `panes` 目标 PUBLIC 链接去掉 `Qt::PrintSupport` |
| `0004-src-desktop-panes-mainpane.cpp.patch` | `src/desktop/panes/mainpane.cpp` | 移除 `QPrintDialog/QPrintPreviewDialog/QPrinter` 头引用与 `print()`/`printPreview()` 实现 |
| `0005-src-desktop-panes-mainpane.h.patch` | `src/desktop/panes/mainpane.h` | 移除 `print()`/`printPreview()` 槽声明 |

补丁净改动为纯删除（`+2/-36`），无平台宏、无 `#ifdef __OHOS__`、无 stub/`return 0`
（满足 R8 与 PF5）；逐个 `patch -p1 --dry-run` 在原始源码上干净应用。
被保留的全部上游功能：集合扫描（`Scanner`）、`RecipeParser`/`IngredientsExtractor`、
Markdown 渲染（`QTextDocument`）、元数据/tags/配料三个面板、随机食谱、桌面
`bin/kookbook` 与 QML `bin/kookbooktouch` 双前端、图标/desktop/appdata 元数据、
`krecipes.py` 转换数据。

## 依赖版本

- `qtbase/6.11.1`（Core/Gui/Widgets/Test；FEATURE_printsupport=OFF）
- `qtdeclarative/6.11.1`（Qt6::Qml，`kookbooktouch` 前端）
- `extra-cmake-modules/6.29.0`（`tool_requires`：ECM cmake 模块）
- 传递依赖（Conan 自动解析，均已发布）：`qtshadertools/6.11.1`、`zlib/1.3.2` 等

## 验证结果

```bash
# W3：配方自包含性 + 上游测试 + 消费者用例（CI 同口径）
cd archives/k/kookbook/0.3.0
conan create . -pr:h=ohos -pr:b=ohos -r=ohpcd --build=missing --build=kookbook/*
# → 上游 ctest: 100% tests passed, 0 tests failed out of 2
# → test_package E2E-KOOKBOOK-01: 8/8 checks passed → RESULT: PASS
# → Package 'kookbook/0.3.0' created

# 单独复跑消费者端到端用例
python3 test_package/test_kookbook_e2e.py <pkg>/bin/kookbook test_package/fixtures
```

## 规则 12：鸿蒙消费者端到端用例

**用例 ID：E2E-KOOKBOOK-01**（`test_package/test_kookbook_e2e.py`，由
`test_package/conanfile.py::test()` 在目标机上执行）

- **场景**：用户启动安装后的 KookBook 桌面应用，应用打开食谱集合目录并扫描、
  解析其中每一个 `*.recipe.md` 食谱。
- **真实输入**：`test_package/fixtures/` 下两份真实食谱——上游 autotests 自带的
  `couscous.recipe.md`（标题 `CousCous`、4 条配料、author 元数据）+ 新增的
  `ohos-kookbook-e2e.recipe.md`（含 tags 元数据）。运行时放入应用默认集合目录
  `<HOME>/Documents/recipes`（`MainWindow` 在无用户设置时的回退位置）。
- **被测产物**：本配方 `conan create` 安装后的 `bin/kookbook`（AArch64 OHOS ELF）。
- **完整流程与判定**（8 项判定，实测 8/8 PASS）：
  1. 产物为 AArch64 ELF（`e_machine=183`）；
  2. `DT_NEEDED` 含 `libQt6Core/Gui/Widgets.so.6`（真实 Qt6 运行闭包）；
  3. 以 `QT_QPA_PLATFORM=offscreen` 启动后进程存活至观测窗口结束（无启动崩溃）；
  4. stderr 出现 offscreen 平台插件诊断，说明真实 QWidget 窗口已创建；
  5. stderr 无动态链接失败（未落到系统同名库）；
  6. `couscous.recipe.md` 被运行中的应用 OPEN + ACCESS（inotify 实测）；
  7. `ohos-kookbook-e2e.recipe.md` 同样被 OPEN + ACCESS；
  8. 应用打开了集合目录本身。
- **业务输出判定依据**：读取集合内全部食谱是 `Scanner::setRootPath` →
  `parseThingsInDifferentThread` → `QFile::open` → `RecipeParser::parseRecipe`
  这一扫描/解析业务步骤对外可观测的副作用，即应用真实消费了交给解析器的食谱字节；
  配合 offscreen QPA 下真实窗口创建与 Qt6 闭包加载，构成完整业务链路。
- **观测手段说明（含被排除的方案）**：
  - 应用无 CLI、无业务 stdout、不会自行退出；Qt 未安装信号处理器，SIGINT/SIGTERM
    直接终止进程（实测无 `QSettings` 写回），故无法用退出码/设置回写做判定。
  - 本机 hmdfs/tmpfs **atime 不更新**（对照实验：`cat` 读取后 atime 保持 2020 年），
    不能用 atime 作为读取证据；改用 inotify（`inotify_init1` 实测可用，对照实验
    确认目录 watch 可捕获子文件 OPEN/ACCESS/CLOSE_NOWRITE）。
  - `QTextDocument` 对 markdown 相对路径图片为惰性加载（仅绘制到视口时
    `loadResource`），offscreen QPA 下实测未加载引用的 PNG，故不作为渲染证据，
    相关 fixture 未纳入用例。
  - `QSettings  [General] location` 手工预置实测**未被应用采用**（应用读取了
    `$XDG_CONFIG_HOME/kde.org/Kookbook.conf` 但未使用该键，多组对照均复现），
    因此用例改用应用自身的默认集合目录，不依赖设置注入。

## 后续可做（未纳入本次范围）

- `qtshadertools` 针对 `qtbase/6.11.1.3` 重建并发布后，可改为
  `qtbase/6.11.1.3 + qtdeclarative/6.11.1.2`，从而恢复 `Qt6::PrintSupport`
  打印/打印预览功能（属独立依赖项任务）。
- `QSettings location` 未被采用的现象值得单独定位（可能与 OHOS 上 Qt 的
  `QSettings` 后端有关），当前不影响本用例判定。
---

**编译结束**: 2026-10-15 15:19
**最终状态**: built
