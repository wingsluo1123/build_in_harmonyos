# kapptemplate 26.04.0 — 鸿蒙原生移植笔记

平台任务 **12744**（本地卡 t_71df4cc8），attempt `kapptemplate-20261014-1`。
交付 worktree `/storage/Users/currentUser/worktrees/deliver-kapptemplate-26.04.0`，
分支 `feat/kapptemplate-26.04.0`，基线 = 官方 mainline `6425af51453d8c62913265f9a65a252499e0c42e`。

## 1. 上游与版本口径

- 上游：KDE SDK 应用 **kapptemplate**（KDE 项目模板生成器；本体是 Qt Quick/QML GUI，
  同时内置一个非交互命令行模式，可把模板工程生成到指定目录）。
- 规范仓库 `https://invent.kde.org/sdk/kapptemplate`，tag `v26.04.0`。
- 源码 tarball：`https://invent.kde.org/sdk/kapptemplate/-/archive/v26.04.0/kapptemplate-v26.04.0.tar.gz`
  sha256 `2f9ecf3954a3c90495be487691bd9d74d24f9e739b90bf802bb7d2761338817d`（设备端 `sha256sum` 实算，577764 字节）。
- 交叉核对：KDE release-service 26.04.0 亦发布同一源码归档
  `https://download.kde.org/stable/release-service/26.04.0/src/kapptemplate-26.04.0.tar.xz`
  sha256 `c69ff5f040f043666d3f17537c7c5072ac5b09c0bb6a1c459b0bb532bdfe377d`；
  `diff -rq` 两棵解压树**完全一致**（仅打包方式不同）。配方采用 invent.kde.org git-archive。
- **版本口径（实测修正）**：上游 CMake `KAPPTEMPLATE_VERSION = "0.1" + RELEASE_SERVICE_COMPACT_VERSION`，
  其中 compact = `26`+`04`+`0` = `26040`。**构建出的 `--version` 输出为 `kapptemplate 0.1.26040`**。
  交接书写作 `0.1.260400`（多一位 0），以本机实测为准。
- `lang-preflight`：语言 cpp（12 源文件 + QML 页面 + 模板数据 + 文档 + po）。

## 2. 依赖（全部取自 ohpcd 已发布 OHOS/armv8 二进制）

required：`qtbase/6.11.1`、`qtdeclarative/6.11.1`、`karchive/6.18.0`、`kconfig/6.18.0`、
`kconfigwidgets/6.18.0`、`kcoreaddons/6.18.0`、`ki18n/6.18.0`、`kiconthemes/6.18.0.1`、
`kirigami/6.18.0`、`kirigami-addons/1.13.0`、`kitemmodels/6.18.0.1`；
build：`ecm/6.26.0`（tool_requires）。传递引入 `qtbase-sql-dbus/6.11.1`（由 kirigami-addons）。

**关键决策——整组 KF6 保持 6.18.0 家族、不用 force 覆盖**：最初按交接书把 leaf 框架提到 6.26.0
并用 `force=True` 覆盖，会让 `kconfigwidgets/6.18.0`、`kiconthemes` 等下游依赖的 package_id 失效、
被迫从源码重建，而 `kconfigwidgets/6.18.0` 的源码构建因其自身上游测试环境问题失败（见 §4）。
改为整组 6.18.0（与 kirigami-addons/1.13.0、kconfigwidgets、kitemmodels 的发布口径一致）后
**零依赖重建**，图无版本冲突。

**KF6 DocTools 经补丁关闭**：`kdoctools/6.19.0`（唯一发布版本）钉 `karchive/6.19.0`，
与 `kiconthemes/6.18.0.1` 钉的 `karchive/6.18.0` 冲突；且 `karchive/6.19.0` 才传递 `zstd`
（kdoctools 的 generate() 直接用 `self.dependencies["zstd"]`，一旦 karchive 被改到无 zstd 的版本即 KeyError）。
帮助手册对生成器功能非必需，故关闭（kfourinline / ksnakeduel 26.04.x 先例）。

## 3. OHOS 适配补丁（均由 `ohc-run.py refresh-patch --auto` 生成）

- `patches/0001-CMakeLists.txt.patch`：从 `find_package(KF6 …)` 去掉 `DocTools`，去掉
  `add_subdirectory(doc)` 与 `kdoctools_install(po)`。
- `patches/0002-src-application-generator.cpp.patch`：**关键**。generator.cpp 用
  `QFile(...).copy(destName)` 落盘模板文件；**实测本机 OHOS/hmdfs 上 `QFile::copy()` 对任何文件都返回
  false**（连普通 ASCII 名也 false，独立最小程序 `test_copy3` 复现：`QFile::copy -> false`，
  手动 open/read/write → true）。这会让生成器“跑完但 0 输出”。补丁改为手动 read+write 复制。
- `patches/0003-src-templates-C++-CMakeLists.txt.patch`：ECM 的 `kde_package_app_templates()`
  固定产出 `.tar.bz2`，而 ohpcd 的 KF6Archive 一律 `WITH_BZIP2=OFF`，`KTar` 打不开 `.tar.bz2`，
  生成器 `arch->open()` 失败后**静默跳到“完成”**（0 文件）。补丁改为产出 `.zip`，
  generator.cpp 本就用 `KZip` 读 `.zip`（zlib，karchive 具备），无需再改 generator。

## 4. 上游测试（真实运行）

- 清点：`tests/CMakeLists.txt` 经 `ecm_add_test()` 注册 **2 个 QtTest 可执行目标**：
  `namevalidatortest`（`QVERIFY` 1 项）、`macrosubstitutiontest`（`QCOMPARE` 5 项）。上游无可运行项缺失。
- 运行入口：`conanfile.py` 的 `build()` 末尾 `_run_upstream_tests()` →
  `ctest --test-dir <build> --output-on-failure --no-tests=error`（`QT_QPA_PLATFORM=offscreen`，
  依赖 lib 目录与 `/system/lib64*` 注入 `LD_LIBRARY_PATH`）。失败即构建失败，无 ignore_errors。
- **结果（本机实测）**：
  ```
  1/2 Test #1: namevalidatortest ................   Passed    0.07 sec
  2/2 Test #2: macrosubstitutiontest ............   Passed    0.07 sec
  100% tests passed, 0 tests failed out of 2
  ```
  TOTAL=2，PASS=2，FAIL=0，SKIP=0，NOT_RUN=0。断言 6/6 通过。
- **原始证据**：CI 同构门禁日志
  `$HOME/.local/share/ohpc-porting/runs/kapptemplate-26.04.0-cigate-20261014-6/output.log`
  **第 497–504 行**（`RUN: ctest --test-dir …`、`1/2 … Passed`、`2/2 … Passed`、`100% tests passed, 0 tests failed out of 2`），
  同轮第 682 行 `[ok] L1c: Upstream official tests (make check/ctest) executed in build phase`，
  且该轮为**从源编译**（安装段起于日志第 247 行）。
- **口径说明**：`conan-verify`（`…-verify-20261014-14`）那一轮的 G2 为**缓存命中**（未重跑 build），
  故 ctest 的原始证据以**同构门禁那一轮**为准，`reports/conan-create.log` 不含 ctest 段。

## 5. 消费者测试（真实调用，非空壳）

`test_package/conanfile.py` 在 offscreen QPA 下真实执行打包出的 `bin/kapptemplate`：
1. `--version` → 断言输出含 `0.1.26040`；
2. `--list-templates` → 断言列出 `kde-frameworks6`、`kde-frameworks6-simple`；
3. 以 6 个位置参数驱动**真实模板生成器**（`self.run`，rc 由 harness 断言），在 `$TMPDIR` 下生成
   `kde-frameworks6` 工程，随后断言产物结构（`CMakeLists.txt`、`README`、`src/main.cpp`、
   经 `%{APPNAMELC}` 展开的 `src/mytestappwindow.cpp`、`src/mytestappview.cpp` 等）与
   **内容宏展开**（根 `CMakeLists.txt` 含 `project(mytestapp VERSION 1.2.3)`）。

E537 运行时处理：已发布 KF6 库带有 (a) build-tree 相对 `DT_NEEDED`（`../../bin/libX.so`）与
(b) 指向构建机 `$HOME/.cache/conan2/...` 的过期绝对 `DT_NEEDED`；test_package 按 accessibility 26.04.3 /
alligator 26.04.0 先例做 link farm + 绝对依赖物化后再执行真实二进制。

## 6. 门禁证据

| 门禁 | JOB_ID | 退出码 | 关键行 |
|---|---|---|---|
| conan-verify (G0–G3 + G4/L2/L4/L5) | `kapptemplate-26.04.0-verify-20261014-14` | 0 | `✅ 配方验证通过: kapptemplate 26.04.0` |
| CI 同构 `ci/conan/build_and_test.sh` | `kapptemplate-26.04.0-cigate-20261014-6` | 0 | `L0_RESULT=pass` `L1_RESULT=pass` `JC_RESULT=pass` `L5_RESULT=pass` |

- conan-verify：G0/G1/G2/G3 **PASS**；G4/L2/L4/L5 因纯可执行包无 lib/ 而记 PASS（报告
  `reports/conan-verify-report.md` 判 **Verdict: PASS**）。
- CI 同构：L0 pass、L1 pass（`L1a test_package executed`、`L1c upstream ctest executed`、`L1e negative test confirmed`）、
  KC pass、JC pass、L5 pass；L2=skip（CI 的 smoke 直接跑 `bin/kapptemplate`，未注入依赖
  `LD_LIBRARY_PATH`/`QT_QPA_PLATFORM`，无法加载 Qt 平台插件——**非阻断**，消费者测试已用完整环境真实执行）；
  L4=warn（扫描补丁里 `strcpy|sprintf|gets|strcat` 正则命中 “**Widgets**/ConfigWidgets” 的 “gets”，**误报，非阻断**）。
- 其余探索轮次（verify-1..13 / cigate-1..5）为定位过程；报告路径 `archives/k/kapptemplate/26.04.0/reports/`。
- 本机 CI 门禁按既有约定用任务私有 pr.diff 限定扫描范围（`JUNK_PR_DIFF=…/kapptemplate-20261014-1/pr.diff`，
  含本包 11 个文件）：本 worktree 的 `origin/main`（2d5de50）落后于任务基线（6425af514），
  不提供 pr.diff 时 junk_check 会退化为全树 full 模式（JC6 报 5612 包、JC1/JC5 命中**其它包**既有隐藏文件）。

## 7. 未决 / 限制

- KF6 DocTools（帮助手册）在本包关闭；生成器与 CLI 功能不受影响。
- 模板归档格式由 `.tar.bz2` 改为 `.zip`（因 karchive 无 bzip2）。
- 独立审查（W4/R52）与平台写操作（push/PR/提审）不在本 attempt 范围。
