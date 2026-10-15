# kbreakout 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake（CMake + ECM + Qt6/KF6；**不是** autotools）
- 编译日期: 2026-10-15
- 编译器: clang 15 / libc++（aarch64-linux-ohos，Release）
- 状态: built（conan create + test_package 通过，未 upload）
- 上游源码: https://download.kde.org/stable/release-service/26.04.0/src/kbreakout-26.04.0.tar.xz
  （sha256 `952d60415830052ad6854cb1665035a0aee65a54616fed97544e676bb510eb4e`）

## 上游形态（26.04.0 tarball）

- Qt6 6.5+/KF6 6.0+ CMake 工程；`find_package(Qt6 ... Widgets Qml Quick
  QuickWidgets)` + `find_package(KF6 ... CoreAddons Config Crash WidgetsAddons
  DBusAddons I18n ConfigWidgets XmlGui IconThemes DocTools)` +
  `find_package(KDEGames6 6.0.0 REQUIRED)`。
- 一个可执行文件 `kbreakout`（QApplication GUI，src/）；球场由 QML 场景
  `src/qml/*.qml`（`import org.kde.games.core 0.1`，来自 libkdegames）经
  QQuickWidget（src/canvaswidget.cpp）渲染，`QStandardPaths::AppDataLocation`
  定位 `qml/main.qml`。
- 数据资产：`pics/`（hicolor 图标）、`themes/`（6 个主题，SVG→SVGZ 由
  `cmake/InternalMacros.cmake::generate_svgz` 生成，7Zip 缺失时回退
  `gzip -9 -n -c`）、`levelsets/`、`src/*.desktop` + appdata、`doc/`（DocBook）。
- **上游无测试套件**（R51 清点，见 `reports/test-report.md` §2.4）：
  `find -iname "*test*"` 无输出，`grep -rn "enable_testing\|add_test\|ecm_add_test\|BUILD_TESTING"`
  无命中。

## 编译步骤

模式 B 探索 + 配方固化，全部在独立 git worktree
（`wt/kbreakout-26.04.0`，分支 `feat/kbreakout-26.04.0`，从 `origin/main`
e1206d11ce 切出）内完成，避免与主工作树的并发会话互相干扰。

```bash
# 0) W0 依赖预检：conan download <dep> --only-recipe -r=ohpcd（16 个依赖全部已发布）
# 1) 源码核验：官方 release-service tarball + sha256
# 2) 语言预检：lang-preflight -> task=cpp / detected=cpp（源文件主体 71%）
# 3) 配方编写：archives/k/kbreakout/26.04.0/{conanfile.py,conandata.yml,patches/,test_package/}
# 4) 实际构建（与 CI 同参数）
conan create archives/k/kbreakout/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="kbreakout/*"
```

关键 cmake 变量（`conanfile.py::generate()` 写入 CMakeToolchain）：

| 变量 | 值 | 目的 |
|------|----|------|
| `BUILD_TESTING` | `OFF` | 上游无测试（R51） |
| `KF_IGNORE_PLATFORM_CHECK` | `TRUE` | OHOS 不在 KDE 平台列表，跳过平台检测 |
| `KF_SKIP_PO_PROCESSING` | `ON` | 跳过 .po→.qm，无需 gettext/LinguistTools |
| `CMAKE_INSTALL_LIBDIR` | `lib` | 安装布局 |
| `CMAKE_BUILD_RPATH` | `$ORIGIN` | 运行时相对解析 |
| `CMAKE_EXE_LINKER_FLAGS` | `-Wl,--disable-new-dtags -Wl,-z,max-page-size=0x1000` | 4K 页布局（OHOS musl 拒绝 lld 默认 0x10000 多 RW-LOAD 布局） |
| `ECM_MODULE_PATH` | `<ecm>/share/ECM/{modules,find-modules,kde-modules}` | CMakeDeps 的 ECMConfig 不传递该变量 |
| `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` | `qtsvg;qtdeclarative` | Qt6 分包组件发现 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `canvaswidget.cpp:18:10: fatal error: 'KLocalizedQmlContext' file not found` | 上游在 `KI18N_VERSION >= 6.8.0` 使用 **KF6::I18nQml** 的 `KLocalizedQmlContext`，而制品仓 `ki18n/6.18.0` 只构建了核心 `KF6::I18n`（无 `qml/`、无 I18nQml 目标、无该头文件） | 补丁 0002：改用同库提供的等价 `KLocalizedContext`，并加 `KI18N_DISABLE_DEPRECATED_BEFORE_AND_AT=0`（该 API 自 KI18N 6.8 deprecated，会被 `ecm_set_disabled_deprecation_versions(KF 6.21.0)` 隐藏）。alligator 26.04.0 同类先例（第二个实例） |
| 2 | `find_package(KF6 ... DocTools)` 在 OHOS 闭包内不可用（kdoctools 未发布，且其已发布二进制依赖 karchive/6.19.0，与 libkdegames 的 karchive/6.18.0 override 冲突） | KF6 闭包裁剪 | 补丁 0001：REQUIRED 列表中移除 DocTools + 去掉 `add_subdirectory(doc)` 与 `kdoctools_install(po)`（kblocks/kfourinline 先例） |
| 3 | 已发布 KF6 6.18.0 库无 `DT_SONAME` → 链接器把 conan 缓存绝对路径写进 `bin/kbreakout` 的 `DT_NEEDED`（跨机不可加载） | E537：Conan cache absolute DT_NEEDED leakage | `package()` 内 `_normalize_needed_paths()`：按字节原位把路径形 NEEDED 归一化为裸库名（同长度，dynamic 段偏移不变），再 `llvm-objcopy` 去 `.codesign` + `binary-sign-tool -selfSign 1` 重签（E077）。实测 12 条归一化、1 个 ELF 重签 |
| 4 | 主题 SVGZ 生成需要 7Zip 或 gzip | `cmake/InternalMacros.cmake` 逻辑 | OHOS 基线无 7Zip，走 `gzip -9 -n -c` 回退（`/usr/bin/gzip` 存在），无需处理 |

## 源码修改

- `patches/0001-ohos-skip-kdoctools.patch`：`CMakeLists.txt` 移除 KF6 DocTools 组件、
  `add_subdirectory(doc)`、`kdoctools_install(po)`。
- `patches/0002-canvaswidget-cpp-use-KLocalizedContext.patch`：
  - `src/canvaswidget.cpp`：删除 `KLocalizedQmlContext` 头与 KI18N ≥ 6.8 分支，
    统一使用 `KLocalizedContext`（QML `i18n()/xi18n()` 机制等价）；
  - `src/CMakeLists.txt`：新增 `target_compile_definitions(kbreakout PRIVATE
    KI18N_DISABLE_DEPRECATED_BEFORE_AND_AT=0)`。

两个补丁都是"平台缺口绕行"（制品仓未发布 KF6 可选模块），非功能性裁剪：
QML 侧 i18n API 表面不变。若后续发布 `ki18n` 的 I18nQml 模块，可移除补丁 0002。

## 依赖版本

qtbase 6.11.1 · qtdeclarative 6.11.1 · qtsvg 6.11.1 ·
kconfig/kconfigwidgets/kcoreaddons/kcrash/kdbusaddons/ki18n/kwidgetsaddons/
kxmlgui/kiconthemes 6.18.0 · kdnssd 6.29.0 · **libkdegames 26.04.0.1**
（KDEGames6 + KDEGames6Private + `org.kde.games.core` QML 模块）· ecm 6.26.0
（tool_requires）· 强制 `karchive/6.18.0`（override=True，libkdegames 图约束）。
传递闭包另含 gettext 0.22.5.1 / expat / openssl / zstd / kcolorscheme /
kcompletion / kguiaddons / knewstuff / kitemviews / kcodecs 等。

> 说明：R36（依赖先发布）已满足——全部直接依赖在制品仓有 recipe；实测 31 个
> 依赖包中 30 个直接命中已发布 binary，仅 `kiconthemes/6.18.0` 因 karchive
> override 改变 package_id 而本地源码重建（约 2 分钟，libkdegames 26.04.0.1
> 图同源状态），CI 走同一路径。

## 验证结果

```bash
$ conan create archives/k/kbreakout/26.04.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --build="kbreakout/*"
kbreakout/26.04.0: normalized 12 DT_NEEDED path(s) in kbreakout
kbreakout/26.04.0: signed 1 OHOS ELF file(s)
kbreakout/26.04.0: Package folder /storage/Users/currentUser/.conan2/p/b/kbrea8743b39bf9299/p
[test] binary: .../bin/kbreakout
[test] 用例 1: --version      -> kbreakout 26.04.0                      ✅
[test] 用例 2: --help         -> A Breakout like game by KDE            ✅
[test] 用例 3: --author/--license -> 上游作者 / GPL                     ✅
[test] 用例 4（鸿蒙特有，非断言）: OHOS closure 加载（24 个 DT_NEEDED）  ✅
[test] ALL CONSUMER CASES PASSED (4 用例 / 6 断言)

$ readelf -d bin/kbreakout | grep NEEDED
 24 条 NEEDED 全部为裸库名（libKDEGames6.so / libKF6*.so / libQt6*.so.6 /
 libc++_shared.so / libc.so），无绝对或相对路径

$ readelf -S bin/kbreakout | grep codesign
 [41] .codesign  PROGBITS  ...   # 重签后 .codesign 有效
```

- package_id: `746c2160d3c6fe3986c11d7c780c535dfafc3126`
- package revision: `f0982e621f65cdcb49c68d20dfc3e649`
- 上游测试: N=0（清点证据见 `reports/test-report.md` §2.4）
- 完整日志（本地留存，`reports/` 被 .gitignore 忽略）：
  `reports/conan-create.log` —— 该文件是 `conan-verify` G2 复跑时的日志快照
  （330 行，末尾含 test_package 全部用例输出）；首次失败（`KLocalizedQmlContext`
  缺失）的日志已被后续复跑覆盖，其可复现证据见 `reports/test-report.md` §4 问题 1
  引用的失败构建目录。

## 注意事项

1. 这是 QML 应用：消费方需让 `share/kbreakout`（qml/themes/levelsets）进入
   `XDG_DATA_DIRS`，并让 libkdegames 的 `qml/` 进入 `QML2_IMPORT_PATH` 才能渲染
   —— 本配方 `package_info()` 的 `runenv_info` 已导出 `LD_LIBRARY_PATH` /
   `QT_PLUGIN_PATH` / `QML2_IMPORT_PATH` / `XDG_DATA_DIRS`。
2. GUI 游戏在无显示环境下需 `QT_QPA_PLATFORM=offscreen`；真机首次运行会弹
   安全确认框（首次执行二进制时），需在启动器/终端放行一次。
3. `DT_NEEDED` 已归一化为裸名，运行时依赖由 conan runenv 的
   `LD_LIBRARY_PATH` 解析（不再依赖构建机 conan 缓存路径）。
4. CI 侧 L2（`bin/kbreakout --version`）在未注入 runenv 的环境下会因找不到
   依赖库而 warn（非阻塞）；L1（conan create + test_package）是阻塞门禁且已通过。

---

## 建 PR 前置硬闸（PF1-PF9 + R52）声明

- **PF0 环境修复（非跳闸）**：本机 CPython 3.12 带 HarmonyOS 补丁的 `subprocess`
  在「裸命令名 + `cwd=None`」时走 `os.posix_spawn`（musl 的 `posix_spawn` 不搜
  PATH），使 `scripts/ohc/preflight.py` 中三处 `subprocess.run(["git", ...])`
  抛 `FileNotFoundError: 'git'` → PF0 fail-closed。已用**本地** `sitecustomize`
  （经 `PYTHONPATH` 注入，不修改仓库任何文件）把裸名按 PATH 解析后再交给
  `os.posix_spawn`，随后实测 **PF1–PF8 + R52 全部通过**——没有任何检查被跳过。
- **PF9 例外声明（书面）**：PF9 判据为 `scripts/ohc/preflight.py:570`
  `bad = [f for f in arch if len(f.split("/")) < 5]`，会命中本包的**软件级**元数据
  文件 `archives/k/kbreakout/{README.md,commands.json,manifest.yaml}`（4 段路径）。
  这与 **PF8 / R38 / CI L0k**（`package_type="application"` 或 `bindirs` 非空时
  `commands.json` **必须**位于软件级目录，塞进版本目录会报 `commands_json_r38`）
  以及 ARCHIVE-SPEC / review-memory §17 直接冲突——**判据层面互斥，非本 PR 疏漏**。
  实测复核（真实 merge-base `e1206d11ce`）：
  `python3 scripts/ohc/preflight.py . $(git merge-base origin/main HEAD) HEAD`
  → **PF1–PF8 + R52 全过，仅 PF9 命中**上述 3 个软件级文件；本 PR 版本目录层齐全
  （`archives/k/kbreakout/26.04.0/` 11 个文件）、分支名 `feat/kbreakout-26.04.0`
  合规、CI 侧 L0n / JC6 在 W3 本地 CI 实测通过。已合入先例（`git ls-tree origin/main`
  实查）：`archives/t/tarlz/commands.json`（PR #13424）、
  `archives/w/wavegain/commands.json`（PR #13442）同形且 CI 绿；仓内既有条目
  `knowledge/drafts/DRAFT-vkeybd-0.1.18d-pf8-pf9-commands-json-vs-path-gate.md`
  记录同一互斥与处方（no-preflight + 书面声明）。
  故按 SKILL 记载的逃生口以 `OHC_PREFLIGHT=0` 建 PR，并在此书面声明；
  软件级文件予以保留（删除会让 CI L0k 真实失败）。该误报已写入
  `feedback/SKILL_FEEDBACK_*.md` 建议项。
- **R40 适配完整性申报**：本包为图形/UI 类，编译通过与消费者用例通过 ≠ 渲染/交互
  适配已完整验证。已覆盖：可执行文件加载、QML 运行时依赖 closure 解析、
  KAboutData/命令行接口；**未**覆盖：QML 场景实际渲染、键盘/鼠标输入、音频输出
  （本机无显示/音频环境）。配方未对渲染或输入路径做任何 stub/裁剪，需真机人工
  确认完整性（本声明同时写入版本级 `manifest.yaml` 的 `known_issues`）。

---

### 对话 #1（2026-10-15 会话）

- 用户指令：读取适配 skill，按流程适配 kbreakout 26.04.0；先建立分支与独立工作树，
  防止并发互相影响。
- 执行记录：W0 依赖预检（16 依赖全发布）→ W1 同步 main（e1206d11ce）→ 独立
  worktree `wt/kbreakout-26.04.0` + 分支 `feat/kbreakout-26.04.0` → lang-preflight
  通过（cpp）→ 源码核验（官方 tarball sha256）→ 配方首稿（参照 kblocks 26.04.0
  已验证闭包）→ conan create 首轮暴露 `KLocalizedQmlContext` 缺失 → 补丁 0002
  （alligator 26.04.0 先例）→ conan create 全通过（含 4 用例 / 6 断言消费者验证）
  → 产物 readelf 校验（24 NEEDED 裸名 + 有效 .codesign）。
- 关键决策：依赖闭包按 libkdegames 26.04.0.1 图对齐（qtdeclarative 为 QML 新增）；
  上游无测试 → 走 R51 清点 + 消费者验证路径；DT_NEEDED 归一化 + 重签（E537/E077）。

### W3 本地 CI 模拟（finish step 5/10，`ci/conan/build_and_test.sh`）

```
L0_RESULT=pass  (结构/依赖发布/版本占用/commands.json 等全通过)
L1_RESULT=pass  (conan create + test_package 实际执行)
L1e             [ok] 破坏性反向验证通过 —— 移走 bin/ 后 test_package 失败，
                     证明测试真实依赖被测包（R34）
L2_RESULT=skip  bin/kbreakout --version 在未注入 conan runenv 的环境下
                找不到依赖库（非阻塞；DT_NEEDED 已归一化为裸名，靠 runenv 的
                LD_LIBRARY_PATH 解析，test_package 用例 1 已覆盖同一断言）
L4_RESULT=warn  误报：扫描规则 (strcpy|sprintf|gets|strcat)\b 命中补丁 0001 的
                上下文行 "ConfigWidgets "（ConfigWid**gets**），非真实危险函数
L5_RESULT=pass  bin/ has content
Build Summary: Total 1 / Success 1 / Pass rate 100.0%
```

> W3 首次运行（00:41–00:45）在编译到 90%（canvaswidget.cpp 后、链接前）被
> **SIGTERM** 打断（conan 打印 `Signal 15` / `Error 143`，非编译错误）：同机
> 并发负载极高（loadavg 49→78 / 8 核，PSI memory some avg10=76%）。
> 降低本地编译并行度（`CONAN_CPU_COUNT=2`）重跑即通过；产物与配方未改动。
>
> **验证边界（审计透明性）**：W3/conan-verify 通过后，仅对
> `test_package/CMakeLists.txt`、`test_package/test_kbreakout.c`（注释说明）与
> `notes.md`/`manifest.yaml`/`reports/*`（文档）做了改动；
> `conanfile.py`、`conandata.yml`、`patches/`、`test_package/conanfile.py`、
> `test_package/test.sh` 与构建期完全一致，故上述 W3/conan-verify 证据对最终
> 提交内容仍然成立（package_id `746c2160…` 不变；两个 CMake/C 文件不被
> `test()` 编译，仅满足 L0c 结构门禁）。

**编译结束**: 2026-10-15 00:49
**最终状态**: built
