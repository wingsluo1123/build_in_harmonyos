# kcharselect 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake（ECM/KDE release-service）
- 编译日期: 2026-10-15
- 编译器: clang 15 / clang++ 15（OHOS aarch64，libc++，Release）
- 状态: built

## 范围

KDE Gear 26.04.0 的字符选择器（KCharSelect），invent.kde.org/utilities/kcharselect。
单一 Qt6 Widgets 可执行 `bin/kcharselect`：把 KCharSelect 部件（KF6::WidgetsAddons）放进
KXmlGuiWindow，加 KDE 书签菜单（KF6::Bookmarks / KBookmarkMenu）、配色方案菜单
（KColorSchemeMenu）与崩溃处理（KF6::Crash），并安装 .desktop / appdata.xml。

## 上游形态（26.04.0 tarball）

- CMake 项目：`find_package(ECM 6.6.0 REQUIRED NO_MODULE)`、
  `find_package(Qt6 CONFIG REQUIRED COMPONENTS Core Widgets)`、
  `find_package(KF6 REQUIRED COMPONENTS Bookmarks CoreAddons Crash I18n WidgetsAddons
  XmlGui ConfigWidgets IconThemes)`；`find_package(KF6DocTools)` 为**可选**（无 REQUIRED）。
- 唯一目标：`add_executable(kcharselect)` + `target_sources(kcharselect PRIVATE
  kcharselectdia.cc kcharselectdia.h main.cc kcharselect.qrc)`；
  `ecm_add_app_icon(...)`（非 Windows/macOS 平台不产出图标）、
  `install(TARGETS ...)` + desktop + appdata + `kdoctools_install(po)`（仅当
  KF6DocTools 找到）+ `ki18n_install(po)`。
- **无上游测试**（0 用例）：tarball 无 autotests/、无 tests/ 目录（顶层仅 doc/、pics/、
  po/、LICENSES/）；CMakeLists.txt 未注册任何测试（无 add_test/enable_testing/
  ecm_add_test，亦无 BUILD_TESTING 守卫；tarball 中仅有的两处 BUILD_TESTING 位于
  CMakePresets.json 与 snapcraft.yaml，均只是传 `-DBUILD_TESTING=OFF`）；
  doc/CMakeLists.txt 仅 `kdoctools_create_handbook`；.kde-ci.yml 未声明测试目标；
  .gitlab-ci.yml 引入 9 个 KDE 共享模板（linux-qt6 / linux-qt6-next / freebsd-qt6 /
  windows-qt6 / craft-windows-x86-64-qt6 / flatpak / snap-snapcraft-lxd + xml-lint /
  yaml-lint），这些模板做构建/打包/lint，仅在项目注册测试时才跑 ctest——本项目未注册，
  故 CI 无测试可跑。R51 第一步清点见表 test_package/MANIFEST.yml（`upstream_tests: []`）。
- 许可：COPYING 为 GPL、`LICENSES/GPL-2.0-or-later.txt`、appdata.xml
  `<project_license>GPL-2.0+</project_license>`、源码 SPDX 头 `GPL-2.0-or-later`
  → Conan `license = "GPL-2.0-or-later"`；`main.cc` 的 KAboutData 传
  `KAboutLicense::GPL`，`--license` 运行时输出 "This program is distributed under the
  terms of the GPL v2." + GNU GPL v2 全文（与 SPDX 声明一致）。

## 编译步骤

```bash
# 1) 依赖发布检查（W0/R35：conan download 探测，非 conan list）
bash ci/scripts/preflight_check.sh kcharselect/26.04.0 --deps \
  "qtbase/6.11.1 kbookmarks/6.18.0 kcoreaddons/6.18.0 kcrash/6.18.0 ki18n/6.18.0 \
   kwidgetsaddons/6.18.0 kxmlgui/6.18.0 kconfigwidgets/6.18.0 kiconthemes/6.18.0 ecm/6.26.0"
# → 10/10 已发布；kcharselect/26.04.0 版本号未被占用
# 2) 隔离工作树（防并发互相影响）
git worktree add /storage/Users/currentUser/runner32/wt/kcharselect-26.04.0 \
  -b feat/kcharselect-26.04.0 origin/main
# 3) 依赖闭包解析（确认运行时 DT_NEEDED 闭包）
conan graph info --no-remote -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --requires=... --format=json   # 23 个节点
# 4) 配方构建 + 消费者验证（W3 同源命令）
conan create archives/k/kcharselect/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="kcharselect/*"
```

## 适配要点（本包无需上游源码补丁）

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：OHOS 不在 KDE 平台列表。
- `KF_SKIP_PO_PROCESSING=ON`：`ki18n_install(po)` 需要 gettext msgfmt/lconvert，
  .qm 目录非必需（kcolorchooser/kteatime/kblocks 同款）。
- `BUILD_TESTING=OFF`：上游 0 用例；验证由 test_package 承担。
- **KF6DocTools 不提供**：上游 `find_package(KF6DocTools)` 是可选依赖，未找到时只报
  CMake Warning 且 `KF6DocTools_FOUND=FALSE` → `add_subdirectory(doc)` 与
  `kdoctools_install(po)` 整段被配置掉。本包**不**声明 kdoctools 依赖
  （ohpcd 仅有 kdoctools/6.19.0，且手册非 smoke 交付所需），feature summary 如实列出
  `KF6DocTools (OPTIONAL packages have not been found)`，构建/安装不受影响。
- `ECM_MODULE_PATH` 手工注入 + 手写 `conan_cmakedeps_paths.cmake`：CMakeDeps 对
  `cmake_find_mode=none` 的 qtbase/KF6 包不加 CMAKE_PREFIX_PATH，且其生成的
  ECMConfig.cmake 不传播 ECM_MODULE_PATH。
- `CMAKE_BUILD_RPATH/CMAKE_INSTALL_RPATH` 指向全部依赖 lib 目录 +
  `-Wl,--disable-new-dtags`（若产出动态标签则为 DT_RPATH 而非 DT_RUNPATH）。
  **实测（readelf -d）**：最终产物 `.dynamic` 中**没有** DT_RPATH/DT_RUNPATH 条目
  —— CMake 只在链接期已产出 RPATH 时才做安装期改写，而按绝对路径链接依赖库时
  链接行根本没有 `-rpath`。因此运行期依赖解析靠 `package_info()` 导出的
  `runenv_info`（`LD_LIBRARY_PATH`），消费者用例即在此环境下完成 closure 加载。
- `-Wl,-z,max-page-size=0x1000`：OHOS musl 加载器不接受 lld 默认 0x10000 多 RW-LOAD 布局。
- `package()` 内 DT_NEEDED 净化：已发布 KF6 6.18.0 产物无 DT_SONAME，链接器把
  conan 缓存绝对路径写进 `bin/kcharselect` 的 DT_NEEDED；就地 .dynstr 改写为纯
  basename，再用 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool` 重签名
  （OHOS 要求有效 .codesign）。实测改写 **13** 条。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(KF6DocTools)` 未找到（CMake Warning） | 上游把 KF6DocTools 声明为可选，但 ohpcd 制品仓只有 kdoctools/6.19.0，且手册生成依赖 docbook 工具链 | 不声明 kdoctools 依赖，依赖上游可选语义把 doc/ 与 `kdoctools_install(po)` 配置掉（feature summary 如实记录 "OPTIONAL packages have not been found"），构建/安装/消费者用例全通过 |
| 2 | 消费者用例在归档 `test_package/` 下留下 Qt 状态文件 `.local/state/kcharselectstaterc` | `main()` 在 QApplication 之前调用 `KIconTheme::initTheme()` + `KStyleManager::initStyle()`，二者把状态写入 `$HOME/.local/state/`；而 test_type="explicit" 的 test_package 构建目录就是 `test_package/` 本身，原配方把 `HOME` 指向了那里 | test_package 把 `HOME`/`XDG_*` 指向源码树外的临时目录（`$TMPDIR/kcharselect-test-runtime`），归档树不再被应用运行时污染（JC/junk 门禁友好） |
| 3 | 已发布 KF6 库相对 DT_NEEDED：`libKF6BookmarksWidgets.so` 记录 `../../bin/libKF6Bookmarks.so` | OHOS 按**符号链接路径**（非 realpath）解析相对条目，多包 KF6 布局下必然失败 | test_package `_fix_relative_needed()`：`llvm-objcopy --remove-section .codesign` → `patchelf --replace-needed <rel> <soname>` → 重签名（**首轮**实测 1 条；依赖 cache 已就地归一化，复跑不再打印该 info 行；并建 link farm 与绝对路径兜底） |
| 4 | 上游无测试 → R51 无 ctest 可跑 | 项目本身 smoke-only | 如实申报 0 用例（附五项清点证据），验证面转为 test_package 消费者用例 |
| 5 | `QFontDatabase: Cannot find font directory .../lib/fonts`（告警） | Qt6 起不再自带字体，offscreen 平台无 fontconfig 时打印告警 | 不影响用例判定（不属链接/元数据失败），如实记录为已知无害告警 |
| 6 | 配方配置了 `CMAKE_BUILD_RPATH/CMAKE_INSTALL_RPATH`，但产物 `readelf -d` 里没有 RPATH | CMake 的安装期 RPATH 只**改写**链接期已产出的 RPATH；本次链接行无 `-rpath`（依赖库以绝对路径给出），故无条目可改写 | 不追求"自包含 RPATH"（指向 conan 缓存绝对路径本就不可移植）：DT_NEEDED 净化为 basename 后，运行期由 `package_info()` 导出的 `runenv_info`（`LD_LIBRARY_PATH`）解析；本地 CI 的 L2 冒烟因此 skip（非阻断，先例 kcolorchooser） |

## 源码修改

无（conandata.yml 无 patches 段；配方内平台适配全部在 `generate()`/`package()` 内完成）。

## 依赖版本

qtbase/6.11.1 + KF6 6.18.0 闭包（kbookmarks、kcodecs、kcolorscheme、kconfig、
kconfigwidgets、kcoreaddons、kcrash、kguiaddons、ki18n、kiconthemes、kitemviews、
kwidgetsaddons、kxmlgui；传递：karchive/6.19.0、qtsvg/6.11.1、gettext/0.22.5.1、
libiconv/1.17、openssl/3.5.6.1、zlib/1.3.1.1、zstd/1.5.7）+
tool_requires ecm/6.26.0（build 闭包另含 extra-cmake-modules/6.19.0）。

## 验证结果

```bash
$ conan create archives/k/kcharselect/26.04.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --build="kcharselect/*"
-- Found KF6: success (found suitable version "6.18.0", minimum required is "6.6.0")
   found components: Bookmarks CoreAddons Crash I18n WidgetsAddons XmlGui ConfigWidgets IconThemes
-- The following OPTIONAL packages have not been found:
 * KF6DocTools (required version >= 6.6.0), Tools to generate documentation
[100%] Built target kcharselect
kcharselect/26.04.0: NEEDED sanitized in kcharselect: 13
-- Installing: .../p/bin/kcharselect
-- Installing: .../p/share/applications/org.kde.kcharselect.desktop
-- Installing: .../p/share/metainfo/org.kde.kcharselect.appdata.xml
======== Launching test_package ========
[test] ✅ 用例 1a 通过 —— 产物存在且可执行
[test] ✅ 用例 1b 通过 —— --version 报告 26.04.0
[test] ✅ 用例 2 通过 —— --help 识别 kcharselect
[test] ✅ 用例 3a 通过 —— --author 输出 KAboutData 作者
[test] ✅ 用例 3b 通过 —— --license 输出 GPL 许可证信息
[test] ✅ 用例 4 通过 —— OHOS closure 加载成功，全部 DT_NEEDED 已解析（进程退出码 143）
[test] ALL CONSUMER CASES PASSED (4 用例 / 5 断言 + 1 鸿蒙特有非断言用例)
```

> **日志转录说明（R52）**：上方 `[test]` 各行与 `reports/conan-create.log` /
> `reports/w3-local-ci.log` 逐字一致。**相对 DT_NEEDED 的归一化只在首轮 `conan create` 出现**
> （首轮日志：`patching relative DT_NEEDED ../../bin/libKF6Bookmarks.so ->
> libKF6Bookmarks.so in libKF6BookmarksWidgets.so`，1 条；该日志已被后续轮次覆盖，
> 原始首轮日志留存 `/storage/Users/currentUser/tmp/ks/conan-create.log`）——此后依赖缓存内的
> KF6 库已被就地归一化，复跑时该 info 行不再打印（与 kcolorchooser 26.04.0 先例同）。

- 上游测试：**0 用例**（项目无测试，申报证据见 MANIFEST.yml）→ N/N′ 不适用，如实申报。
- 消费者用例：**4 用例 / 5 断言全通过**，含 1 个鸿蒙特有非断言用例（共享库 closure 加载）。
- `--version` 实测输出 `kcharselect 26.04.0`；`--author` 输出
  `kcharselect was written by: Christoph Feck <cfeck@kde.org> ...`；
  `--license` 输出 `This program is distributed under the terms of the GPL v2.` + GPL v2 全文。
- 产物：`bin/kcharselect`、`share/applications/org.kde.kcharselect.desktop`、
  `share/metainfo/org.kde.kcharselect.appdata.xml`
  （上游 `ecm_add_app_icon` 在 Linux/OHOS 平台不产出图标文件，故无 icons 安装项——上游行为）。

## 知识积累（已提取为知识图谱草稿）

- ✅ KDE 可选依赖 KF6DocTools 缺失时 doc/ 与 kdoctools_install(po) 静默配置掉
  （新增草稿 `knowledge/drafts/kcharselect-26.04.0-kf6doctools-optional-upstream-doc-subdir-configured-out.kv`）
- ✅ 应用运行时状态文件污染归档树（KIconTheme/KStyleManager → $HOME/.local/state）与
  test_package HOME/XDG 隔离（新增草稿
  `knowledge/drafts/kcharselect-26.04.0-test-package-home-xdg-state-file-archive-pollution.kv`）
- ✅ 已发布 KF6 库 path-form DT_NEEDED 归一化 + 重签名（复用
  `DRAFT-14403-registry-so-no-soname-dynstr-normalize-resign` /
  `DRAFT-E5xx-registry-so-baked-absolute-needed-symlink`）
- ✅ KDE 平台开关 KF_IGNORE_PLATFORM_CHECK / KF_SKIP_PO_PROCESSING（复用
  `DRAFT-kf-metainfo-platform-whitelist-ignore-flag` /
  `DRAFT-kf-skip-po-processing-gettext-toolchain`）
- ✅ ECM_MODULE_PATH 与 conan_cmakedeps_paths.cmake 手工补齐（复用
  `DRAFT-13796-qqc2-breeze-style-6.7.5-kf6-ecm-cmakedeps-bridge`）

## 注意事项

- **R40 深适配声明（如实申报）**：本包为图形界面应用，本次验证面为
  DT_NEEDED closure 加载 + 元数据/CLI 路径（offscreen 无头）；字符表网格渲染、
  区块/字体切换、搜索、复制到剪贴板、书签菜单、配色方案菜单等交互路径
  **需真机人工确认**，本 PR 不声称已完成交互验收。
- 运行期需 Qt6/KF6 依赖库可见：包 `package_info()` 通过 `runenv_info` 导出依赖
  `LD_LIBRARY_PATH`/`QT_PLUGIN_PATH`（产物 `.dynamic` 无 RPATH，见上表第 6 条）。
- 本地/远端 CI 的 L2 冒烟（直接跑 `bin/kcharselect --version/--help`）在**不带**
  conan runenv 的环境下会失败并 skip（非阻断；GUI 应用需 Qt 插件与 KF6 库路径，
  kcolorchooser 先例同）。真实验证由 test_package 消费者用例承担（L1/L1e 已实证）。
- `test_package` 的 HOME/XDG 隔离目录固定为 `$TMPDIR/kcharselect-test-runtime`
  （跨次运行复用，无状态语义）。
- 已知无害告警：offscreen 平台 `QFontDatabase: Cannot find font directory`（Qt6 不再
  自带字体）；`make: jobserver mkfifo ... Operation not permitted`（OHOS 上 make
  jobserver 命名管道受限，仅告警）。
## W4 独立审计与整改（4 轮，每轮 verdict=pass，P0=0 / P1=0）

共 **4 轮**均由**独立子任务**（上下文隔离、只读）执行，每轮 **verdict=pass 且 P0=0 / P1=0**：
R1（快照 `c90214c3ca`，P2=4/P3=5）、R2（快照 `f7e8305af6`，P2=2/P3=4）、
R3（快照 `3a4ef8aef7`，P2=1/P3=3）、R4（快照 `d461c5981e`，P2=1/P3=5）。
各轮 P2/P3 均逐条整改或附理由拒绝；审计未修改仓库任何文件。

**已整改**
1. （P2，R34 形态）删除 `test_package/CMakeLists.txt` 与 `test_package/test_kcharselect.c`：
   该 printf-only 占位目标因 `test_package/conanfile.py` 无 `build()` 而**从不被配置/编译/运行**，
   其自带注释"满足 framework L0 structure gate"与实现不符（CI L0c 与 preflight PF3 接受 `.sh`，
   `templates/test_package-executable` 亦仅含 conanfile.py + test.sh）。真实验证面由 `test.sh`
   承担并经 CI L1e 破坏性反向验证（`bin/ moved away → Negative test confirmed`）。
2. （P2，R52）修正 DT_RPATH 申报：实测产物 `.dynamic` **无** RPATH/RUNPATH，运行期靠
   `package_info()` 导出的 `runenv_info`（`LD_LIBRARY_PATH`）；同步更正 conanfile.py docstring /
   本笔记 / 版本与软件级 manifest / README，并新增草稿
   `kcharselect-26.04.0-cmake-install-rpath-not-emitted-rely-on-runenv`。
3. （P3，R32 口径）统一 OHOS 判定写法为 `str(self.settings.os) in ("OHOS", "HarmonyOS")`
   （`generate()` 与 `_sanitize_needed_entries()` 一致）。

**未整改（附理由）**
1. **PF9 假阳性**（P2）：软件级 `archives/k/kcharselect/{README.md,commands.json,manifest.yaml}`
   被 preflight PF9 判为"缺版本目录层"，但 R38 / PF8 / CI L0k 与 `ARCHIVE-SPEC.md` 要求这些文件
   存在（PF8 与 PF9 互斥）。处置：建 PR 时以 `OHC_PREFLIGHT=0` 显式跳过 PF9 并在 PR 说明披露，
   **不删除**这三个文件（删了会转成 PF8/L0k 真失败；先例：kcolorchooser、anacron/2.3、
   cscope/15.9、bti/034、box64/0.4.4 等）。
2. `test.sh` 调用方式（P2/P3，**已据实测更正**）：`test_package/conanfile.py` 用
   `os.environ.get("CONFIG_SHELL", "/bin/sh")` 取解释器，但 profile 的 `[buildenv] CONFIG_SHELL`
   只写入生成的 `conanbuildenv-release-armv8.sh`，**不会进入 `os.environ`**，故实测调用行恒为
   `/bin/sh <归档>/test_package/test.sh`（见 `reports/conan-create.log` RUN 行与
   `reports/w3-local-ci.log`）。本机 `/bin/sh` 支持且强制 `pipefail`，实测
   `/bin/sh test.sh <bin>` 全用例通过；`test.sh` 首行 shebang 在此调用方式下不生效。
3. 用例 4 为非断言用例（按 OHOS 动态链接器行为判定，崩溃但无链接器错误也通过）（P3）：
   已如实申报；交互路径需真机人工验收（R40 声明）。
4. 依赖包 conan cache 产物被 `test()` 就地归一化（`patchelf --replace-needed` + 重签名）（P3）：
   已发布 KF6 6.18.0 产物无 DT_SONAME / 含相对 DT_NEEDED 的必要兜底，属先例做法，文档已注明。

**终审后额外整改（P2/P3，均已实测复验）**
5. （P3-①）`test_package/conanfile.py` 的平台判定与配方统一为
   `str(self.settings.os) in/not in ("OHOS", "HarmonyOS")`（原 `not in ("Linux", "OHOS")` 在
   `os=HarmonyOS` 下会静默 `return`，把消费者测试变成隐性空跑，属 R34 隐患）。
6. （P3-②）`test.sh` 的 closure 诊断日志目录改为多级兜底（`$TMPDIR` → `mktemp -d` → `$PWD`），
   避免 `mkdir` 失败时把 `*.log` 落进归档 `test_package/`（该路径的 `*.log` 未被 `.gitignore`
   覆盖，属潜在归档污染路径；`git check-ignore` 实证）。

**四轮独立核验共同结论（均不依赖本文档自述）**：上游 0 测试属实（无 `autotests/`/`tests/`，
`CMakeLists.txt` 无测试注册，全树仅 2 处 `BUILD_TESTING` 且均为 `-DBUILD_TESTING=OFF`）；
`find_package(KF6DocTools)` 无 `REQUIRED` 且 `ki18n_install(po)` 无条件调用；
`license=GPL-2.0-or-later` 与 COPYING/LICENSES/appdata/SPDX 头一致；tarball sha256 与
conandata.yml / manifest.yaml / 上游 `.tarball-sha256` 三处一致；产物 `.dynamic` 无 RPATH、
DT_NEEDED 全为 basename、`.codesign` 段存在；归档树无 `.local`/`*staterc` 状态污染；
W2 原子性通过（`git diff --name-only origin/main...HEAD` 仅 kcharselect 与本包草稿，未触碰框架文件）。
---

**编译结束**: 2026-10-15 09:23
**最终状态**: built
