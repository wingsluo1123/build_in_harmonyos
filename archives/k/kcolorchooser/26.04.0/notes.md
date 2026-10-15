# kcolorchooser 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake（ECM/KDE release-service）
- 编译日期: 2026-10-15
- 编译器: clang 15 / clang++ 15（OHOS aarch64，libc++，Release）
- 状态: built

## 范围

KDE Gear 26.04.0 的调色板/颜色选择器（KColorChooser），invent.kde.org/graphics/kcolorchooser。
单一 Qt6 Widgets 可执行 `bin/kcolorchooser`：封装 `QColorDialog`，加 KDE 命令行接口
（`--color` 初始颜色、`--print` 输出所选颜色、`--author`/`--license` KAboutData 元数据），
并安装 .desktop / hicolor 图标 / appdata.xml。

## 上游形态（26.04.0 tarball）

- CMake 项目，`find_package(ECM 6.9.0 REQUIRED)`，`find_package(Qt6 6.5.0 COMPONENTS Core Gui Widgets)`，
  `find_package(KF6 6.9.0 REQUIRED COMPONENTS CoreAddons I18n XmlGui)`。
- 唯一目标：`add_executable(kcolorchooser)` + `target_sources(kcolorchooser PRIVATE
  kcolorchooser.cpp)`（113 行单文件），
  `install(TARGETS ...)` + desktop + `ecm_install_icons` + appdata + `ki18n_install(po)`。
- **无上游测试**（0 用例）：无 autotests/、无 tests/；CMakeLists.txt 未注册任何测试
  （无 add_test/enable_testing/BUILD_TESTING/ecm_add_test）；.kde-ci.yml 未声明测试目标；
  .gitlab-ci.yml 引入 9 个 KDE 共享模板（linux-qt6 / linux-qt6-next / freebsd-qt6 /
  windows-qt6 / flatpak / snap-snapcraft-lxd + clang-format / xml-lint / yaml-lint），
  这些模板做构建/打包/lint，仅在项目注册测试时才跑 ctest——本项目未注册，故 CI 无测试可跑。
  R51 第一步清点见表 test_package/MANIFEST.yml（`upstream_tests: []`）。
- 许可：COPYING 与 appdata.xml 为 **MIT**（Conan `license = "MIT"`）；注意
  `kcolorchooser.cpp:51` 的 KAboutData 传 `BSD_2_Clause`，`--license` 运行时输出 BSD 文本
  （上游自身不一致，消费者用例断言的是运行时元数据路径）。

## 编译步骤

```bash
# 1) 依赖发布检查（W0/R35：conan download 探测，非 conan list）
conan download qtbase/6.11.1 -r=ohpcd --only-recipe   # 及 KF6 6.18.0 闭包各包 → 全部 OK
# 2) 隔离工作树（防并发互相影响）
git worktree add ../kcolorchooser-wt -b feat/kcolorchooser-26.04.0 main
# 3) 配方构建 + 消费者验证（W3 同源命令）
conan create archives/k/kcolorchooser/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="kcolorchooser/*"
```

## 适配要点（本包无需上游源码补丁）

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：OHOS 不在 KDE 平台列表。
- `KF_SKIP_PO_PROCESSING=ON`：`ki18n_install(po)` 需要 gettext msgfmt/lconvert，
  .qm 目录非必需（kteatime/kblocks 同款）。
- `BUILD_TESTING=OFF`：上游 0 用例；验证由 test_package 承担。
- `ECM_MODULE_PATH` 手工注入 + 手写 `conan_cmakedeps_paths.cmake`：CMakeDeps 对
  `cmake_find_mode=none` 的 qtbase/KF6 包不加 CMAKE_PREFIX_PATH，且其生成的
  ECMConfig.cmake 不传播 ECM_MODULE_PATH。
- `CMAKE_BUILD_RPATH/CMAKE_INSTALL_RPATH` 指向全部依赖 lib 目录 +
  `-Wl,--disable-new-dtags`（保留 DT_RPATH）：OHOS 加载器否则落入已发布 KF6 库
  自身的坏 RPATH 条目。
- `-Wl,-z,max-page-size=0x1000`：OHOS musl 加载器不接受 lld 默认 0x10000 多 RW-LOAD 布局。
- `package()` 内 DT_NEEDED 净化：已发布 KF6 6.18.0 产物无 DT_SONAME，链接器把
  conan 缓存绝对路径写进 `bin/kcolorchooser` 的 DT_NEEDED；就地 .dynstr 改写为纯
  basename，再用 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool` 重签名
  （OHOS 要求有效 .codesign）。实测改写 8 条。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费者用例全挂：`Could not find the Qt platform plugin "offscreen"` + Signal 6 core dumped | `Conan Environment.append()` 对普通变量用**空格**连接（而非 os.pathsep），`QT_QPA_PLATFORM_PLUGIN_PATH` 变成 `"dirA dirA"` 一个无效目录 | 改用 `Environment.define()` 显式注入 `os.pathsep.join(...)`，并对 plugin/platform 目录去重（QT_DEBUG_PLUGINS=1 定位） |
| 2 | 已发布 KF6 库相对 DT_NEEDED：`../../bin/libKF6IconThemes.so` 等（libKF6IconWidgets / libKF6ConfigGui / libKF6I18nLocaleData 实测命中） | OHOS 按**符号链接路径**（非 realpath）解析相对条目，多包 KF6 布局下必然失败 | test_package `_fix_relative_needed()`：`llvm-objcopy --remove-section .codesign` → `patchelf --replace-needed <rel> <soname>` → 重签名（首轮实测 3 条）；并建 link farm 兜底 |
| 3 | 已发布 KF6 库构建机绝对 DT_NEEDED 在别的机器不存在 | 构建期 CONAN_HOME 不同，路径被烤死 | test_package `_fix_absolute_needed()`：按 basename 索引依赖库，为缺失绝对路径建符号链接（首轮实测 12 条） |
| 4 | 上游无测试 → R51 无 ctest 可跑 | 项目本身 smoke-only | 如实申报 0 用例（附四项清点证据），验证面转为 test_package 消费者用例 |

## 源码修改

无（conandata.yml 无 patches 段；配方内平台适配全部在 `generate()`/`package()` 内完成）。

## 依赖版本

qtbase/6.11.1 + KF6 6.18.0 闭包（kconfig、kconfigwidgets、kcoreaddons、kguiaddons、
ki18n、kiconthemes、kitemviews、kwidgetsaddons、kxmlgui；传递：kcolorscheme、
kcodecs、karchive/6.19.0、qtsvg/6.11.1、gettext/0.22.5.1）+
tool_requires ecm/6.26.0。

## 验证结果

```bash
$ conan create archives/k/kcolorchooser/26.04.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --build="kcolorchooser/*"
...
-- Found KF6: success (found suitable version "6.18.0", minimum required is "6.9.0")
   found components: CoreAddons I18n XmlGui
[100%] Built target kcolorchooser
kcolorchooser/26.04.0: NEEDED sanitized in kcolorchooser: 8
======== Launching test_package ========
[test] ✅ 用例 1a 通过 —— 产物存在且可执行
[test] ✅ 用例 1b 通过 —— --version 报告 26.04.0
[test] ✅ 用例 2 通过 —— --help 识别 kcolorchooser
[test] ✅ 用例 3a 通过 —— --author 输出作者信息
[test] ✅ 用例 3b 通过 —— --license 输出 BSD 许可证信息
[test] ✅ 用例 4 通过 —— OHOS closure 加载成功，全部 DT_NEEDED 已解析（进程退出码 143）
[test] ALL CONSUMER CASES PASSED (4 用例 / 5 断言 + 1 鸿蒙特有非断言用例)
```

- 上游测试：**0 用例**（项目无测试，申报证据见 MANIFEST.yml）→ N/N′ 不适用，如实申报。
- 消费者用例：**4 用例 / 5 断言全通过**，含 1 个鸿蒙特有非断言用例（共享库 closure 加载）。
- 产物：`bin/kcolorchooser`、`share/applications/org.kde.kcolorchooser.desktop`、
  `share/icons/hicolor/{16x16,22x22}/apps/kcolorchooser.png`、
  `share/metainfo/org.kde.kcolorchooser.appdata.xml`。

## 知识积累（已提取为知识图谱草稿）

- ✅ Conan `Environment.append()` 空格连接路径变量 → Qt 插件目录失效（新草稿
  `knowledge/drafts/kcolorchooser-26.04.0-conan-env-append-space-joined-qt-plugin-path.kv`）
- ✅ 已发布 KF6 库 path-form DT_NEEDED 归一化 + 重签名（复用
  `DRAFT-14403-registry-so-no-soname-dynstr-normalize-resign` /
  `DRAFT-E5xx-registry-so-baked-absolute-needed-symlink`）
- ✅ KDE 平台开关 KF_IGNORE_PLATFORM_CHECK / KF_SKIP_PO_PROCESSING（复用
  `DRAFT-kf-metainfo-platform-whitelist-ignore-flag` /
  `DRAFT-kf-skip-po-processing-gettext-toolchain`）
- ✅ ECM_MODULE_PATH 与 conan_cmakedeps_paths.cmake 手工补齐（复用
  `DRAFT-13796-qqc2-breeze-style-6.7.5-kf6-ecm-cmakedeps-bridge`）

## 注意事项

- `--print` 需人工关闭对话框后才输出颜色，无法在无头环境自动断言；消费者用例只覆盖
  可在 offscreen 下确定的元数据/接口路径 + 完整 closure 加载。
- **R40 深适配声明（如实申报）**：本包为图形界面应用，本次验证面为
  DT_NEEDED closure 加载 + 元数据/CLI 路径（offscreen 无头）；窗口交互、
  鼠标/键盘输入、剪贴板取色、`--color` 初始色、`--print` 输出等交互路径
  **需真机人工确认**，本 PR 不声称已完成交互验收。
- DT_NEEDED 归一化的计数（相对 3 条 / 绝对回退 12 条）来自**首轮** `conan create`；
  此后依赖缓存内的 KF6 库已被就地归一化，复跑时计数不再重现（对数日志仍可核对
  `.dynstr` 现状：libKF6I18nLocaleData.so 已是 basename 形式，libKF6IconWidgets.so
  仍有构建机绝对条目）。
- 运行期需 Qt6/KF6 依赖库可见：包 `package_info()` 通过 `runenv_info` 导出依赖
  `LD_LIBRARY_PATH`/`QT_PLUGIN_PATH`。

## W4 审计整改（审计 verdict=pass，P0=0/P1=0，P2 已整改）

- P2-1 证据表述失真 → 更正 `.gitlab-ci.yml` 表述（实为 9 个共享模板：构建/打包/lint，
  项目未注册测试故无测试可跑），同步更正 conanfile.py docstring、MANIFEST.yml、
  manifest.yaml、README.md、reports/test-report.md。
- P2-2 `license` 字段错误 → 由 `BSD-2-Clause` 改为 `MIT`（COPYING + appdata.xml 口径；
  上游 cpp 的 KAboutData 传 BSD 属上游自身不一致，已在配方 docstring/README/notes 注明，
  消费者 `--license` 用例断言的是运行时输出而非 SPDX 字段）。
- P2-3 R40 深适配未申报 → manifest.yaml 新增 `test_results.r40_note`，notes 增加
  R40 声明（交互路径需人工确认）。
- 改配方后已重跑 conan-verify（G0–G4/L2/L4/L5 全绿）与 W3 本地 CI 模拟
  （JC/L0/L1/L1e/L4/L5 pass，Success 1/1），`.ci-result.json` 已按新配方重新生成。
- P3 观察项（不整改，非本 PR 引入）：framework L2 冒烟 skip（CI 不带 Qt 运行环境跑
  `bin/kcolorchooser`，如实记录）；gen_summary 的 `'str' object has no attribute
  'append'` 为仓库既有 infra bug；knowledge graph 中 E219/E253/E305 字段为空为存量条目；
  工作树内 `archives/l/libXext/*` 的未提交改动属其它会话，本 PR 未纳入（W2 原子性已核）。
- 第二轮独立审计（针对上述整改后的内容）verdict=pass，P0=0/P1=0/P2=1/P3=5；其
  1 个 P2（`test.sh` 裸 `|| true` 缺注释，code-style §10）与 3 个可修 P3
  （上游 `add_executable` 引文改为逐字 = `add_executable` + `target_sources`、
  `test_package/CMakeLists.txt` 注释澄清该 placeholder 目标在 `conan create` 中
  并不被编译、补齐 `MANIFEST.yml` 的 `upstream_check_command`）已在本轮一并修正。

## PF9 前置闸假阳性留痕（PF8/R38 ⟷ PF9 规则冲突）

✅ 实测（`scripts/ohc/preflight.py` 全闸）：**PF1–PF8 全过 + R52 交叉校验无命中，
  唯一 findings = PF9**：

  ```
  PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）
  ——CI 将报 No packages to build（490 例）:
  archives/k/kcolorchooser/README.md, archives/k/kcolorchooser/commands.json
  ```

✅ 根因：PF9 `check_branch_and_paths()` 判 `len(f.split("/")) < 5`，把**软件级**
  `archives/<字母>/<包>/` 下的文件一律判为「缺版本目录层」；而 R38 / PF8 / CI L0k
  与 `ARCHIVE-SPEC.md` **强制要求** CLI 包在该层级提供 `commands.json`（`README.md`
  亦为 SPEC 要求）。两者互斥 ⇒ **既有工具假阳性，非本包引入**。
✅ 先例（同假阳性、已合入 main）：anacron/2.3、cscope/15.9、bti/034、box64/0.4.4，
  以及 vamps/0.99.2、pforth/2.0.1（各带 3 个软件级文件正常合入）。
✅ 交叉证据：真实 CI 侧 L0m/L0j/L0k 与 JC6 对软件级 `commands.json`/`README.md` 零命中；
  本包 W3 本地 CI 模拟（与远端 CI 同源脚本）**JC/L0/L1/L1e/L4/L5 全 pass**，
  `Success 1/1 (100%)`，`L0k: commands.json` 校验 OK。
✅ 处置：**不删除** `commands.json`（删除会转成 PF8/L0k 真失败，且违反 R38）；
  PR 创建以 `OHC_PREFLIGHT=0`（preflight 侧开关，等价 `create-pr --no-preflight`）
  显式跳过 PF9，并在 PR 说明/本笔记中披露本留痕。
✅ 环境备注（与规则无关）：本机 CPython 无法以**裸名** spawn 子进程（musl 下
  `execvp` 的 PATH 搜索失效：裸 `git` 报 `FileNotFoundError: [Errno 2]`，绝对路径正常，
  `sh -c 'git ...'` 正常），因此 `preflight.py:74` 直接运行会先报 PF0；
  上述 PF1–PF8 结论是把裸命令解析为绝对路径后实测所得（`create-pr` 侧
  `_git_toplevel()` 在 `OHC_PREFLIGHT=0` 路径下不会被调用，不影响建 PR）。
---

**编译结束**: 2026-10-15 01:37
**最终状态**: built
