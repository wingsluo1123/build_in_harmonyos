# kdoctools 6.28.0 适配笔记（OHOS / HarmonyOS PC aarch64）

## 一、软件概述

- kdoctools：KDE Frameworks 6 的 DocBook 文档处理工具链。
  - 共享库 `libKF6DocTools.so`（SPDX 与安装辅助函数）
  - 可执行工具：`meinproc6`（DocBook 转换器）、`checkXML6`（XML 校验器）、`docbookl10nhelper`
    （DocBook XSL 本地化目录生成器，构建期宿主工具）
  - KDocTools 定制数据：`customization/dtd`（DocBook XML 4.5 扩展）、`customization/xsl` 等
- 用途：KDE 各应用的 `kdoctools_install` / handbooks / man pages 生成全部依赖本包；
  `meinproc6` 是文档构建链的执行器。
- 构建系统：CMake + ECM。上游要求 `REQUIRED_QT_VERSION`、`find_package(ECM 6.28.0 NO_MODULE)`，
  `KF_DEP_VERSION 6.28.0`（仅 KF6Archive 消费，见适配要点 6）。
- 本包 `package_type = "application"`（工具包），配套 `commands.json` 已同步登记 6.28.0（R38）。

## 二、W0 依赖预检表（实测）

| 依赖 | 版本 | 类型 | 制品仓/缓存实测 | 结论 |
|---|---|---|---|---|
| qtbase | 6.11.1 | requires | 设备缓存已有（kitemviews 等同基线） | ✅ 已发布 |
| karchive | 6.26.0 | requires | 设备缓存已有；6.28.0 线未发布 → 补丁 0003 降 KF_DEP_VERSION | ✅ 已发布 |
| openssl | 3.5.6.1 | requires | 设备缓存已有（karchive 的 find_dependency(OpenSSL) 需要） | ✅ 已发布 |
| libxml2 | 2.15.3 | requires | 设备缓存已有；与 libxslt/1.1.45.1 的依赖版本一致，避免版本冲突 | ✅ 已发布 |
| libxslt | 1.1.45.1 | requires | 设备缓存缺（首跑由制品仓拉取/源码构建补齐）；kdoctools 6.19.0 同款口径已合入 | ✅ 已发布 |
| ecm | 6.28.0 | tool_requires | 设备缓存已有 | ✅ 已发布 |

## 三、OHOS 适配要点（逐项记录）

1. **KDE 平台检查与卸载目标**：`KF_IGNORE_PLATFORM_CHECK=TRUE`（OHOS 不在 KDE 平台白名单）；
   `KDE_SKIP_UNINSTALL_TARGET=TRUE`，因为 ohpcd 的 ECM 包不带 ecm_uninstall.cmake.in 模板，
   ECMUninstallTarget 的 configure_file 会失败。
2. **SONAME-only 规则**：OHOS CMake 不带 Platform 模块，`CMAKE_SHARED_LIBRARY_SONAME_*` 为空，
   lld 默认不发 DT_SONAME → 消费者把构建机绝对路径记进 DT_NEEDED。配方用
   `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX` 恢复 `-Wl,-soname,`；同时 HMDFS 拒 symlink，
   版本化软链链（libKF6DocTools.so.6 → .so.6.28.0）无法物化，故设 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`
   只留无版本 SONAME（kitemviews 6.28.0 / kconfig 6.26.0 先例）。
   注意：`CMAKE_SHARED_LIBRARY_RUNTIME_*`（rpath）故意不定义——定义了会烘 RUNPATH，
   install() 再原地重写 ELF 去掉它，设备加载器对重写产物 dlopen 报 EACCES（kconfig 6.28.0 实锤）。
3. **ECM 注入**：CMakeDeps 生成的 ECMConfig.cmake 不设 `ECM_MODULE_PATH`，配方显式设
   `ECM_DIR` + `ECM_MODULE_PATH`（modules/find-modules/kde-modules 三项），保证
   KDEInstallDirs、FindDocBookXML4/FindDocBookXSL、KDECompilerSettings 等模块可用。
4. **qtbase 桥接**：qtbase 为 `cmake_find_mode=none`，CMakeDeps 不生成任何 Qt target；
   配方显式缓存 `Qt6_DIR` / `Qt6Core_DIR` / `KF6Archive_DIR`，并生成 paths 文件经
   `CMAKE_PROJECT_INCLUDE` 注入（PREPEND 五个依赖根到 CMAKE_PREFIX_PATH/LIBRARY_PATH/INCLUDE_PATH，
   `CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF` 让 ECM find-modules 对 DocBook 探测保持权威）。
   另注：ctest 驱动的内层消费者（`kdoctools_install` 的 `cmake --build-and-test`）依赖**环境变量**
   `CMAKE_PREFIX_PATH` 找依赖，配方须用 `os.pathsep.join` 按平台分隔符拼接——设备 CMake 对环境变量
   按 pathsep(`:`) 拆分，分号连接的串会被整体当作单个不存在的前缀（本包 G2 内层 ECM 找不到的根因，
   五发探针矩阵实证：六根分号串 FAIL / 单根 PASS / 两根冒号 PASS / 六根冒号串完整 configure 成功）。
5. **xmllint 配置期探测**：项目 `find_program(XMLLINT)` 要求库外二进制，配方以
   `LIBXML2_XMLLINT_EXECUTABLE = shutil.which("xmllint")` 直给（libxslt 包 bin/ 同族工具）。
6. **KF_DEP_VERSION 降版（补丁 0003）**：上游 6.28.0 把 KF_DEP_VERSION 提到 6.28.0，且
   KF6Archive 的 find 是它唯一消费者；ohpcd 只发布 karchive 6.26.0 线 → 降回 6.26.0
   （kbookmarks 6.28.0 先例）。
7. **DocBook 数据（本包最关键的坑）**：
   - ECM 缓存包内**没有** DocBook 模块；`FindDocBookXML4.cmake` / `FindDocBookXSL.cmake`
     来自 kdoctools 自带的 `cmake/` 目录，两模块只扫描 `CMAKE_SYSTEM_PREFIX_PATH` +
     PATH_SUFFIXES（`share/xml/docbook`、`share/sgml/docbook`、`share/docbook-xsl` 等），
     OHOS 上无 DocBook 系统树 → FOUND=FALSE。
   - 但两个模块都走 `handle_standard_args(... DocBookXML4_DTD_DIR)` / `(... DocBookXSL_DIR)`，
     即**结果变量直给即可 FOUND**。配方接线：环境变量 `KDOCTOOLS_DOCBOOK_XML4_DIR` /
     `KDOCTOOLS_DOCBOOK_XSL_DIR` 指向解包好的官方数据树时，配置期把
     `DocBookXML4_DTD_DIR` / `DocBookXSL_DIR` 写进 cache；不设时保持“数据可选”路径。
   - 数据缺席路径由补丁兜底：0002 把 ECM 的依赖描述符从 REQUIRED 改 OPTIONAL（不再报缺失），
     0004 让 docbookl10nhelper 的 POST_BUILD 在数据缺席时写入最小 all-l10n.xml，
     0006 让两个上游 autotest 仅在数据齐备时注册，0007 让 src/CMakeLists.txt 在数据缺席时
     生成不含 `DocBookXSL_DIR-NOTFOUND` 占位的 kde-include-common.xsl / kde-include-man.xsl
     （否则安装的样式表 xsl:import 指向该哨兵，checkXML6 运行期 I/O warning + exit 1）。
   - 数据齐备路径即为真机验证配置：DTD 用官方 docbook-xml-4.5（docbookx.dtd + 实体集），
     XSL 用官方 docbook-xsl-1.79.2（html/、common/、lib/ 闭包 + VERSION.xsl）。
8. **Perl URI::Escape 可选（补丁 0001）**：uriencode 分支依赖 Perl `URI::Escape`，OHOS 无该
   模块时走 `QUIET` + 返回，保留有模块时的原生分支（kdoctools 6.19.0 同款口径）。
9. **docs/ 跳过（补丁 0005）**：docs/handbook 需要完整 KDE 文档工具链，注释掉该子目录
   （kdoctools 6.19.0 先例）。

## 四、上游测试清点与实测（R51 三步法）

### 1. 清点（源码 autotests/）

- `autotests/CMakeLists.txt` 注册 **2 个 ctest 条目**：
  - `meinproc_template`：`meinproc6 --srcdir <build>/src <src>/src/template.docbook`，
    转换上游自带的 DocBook 模板。
  - `kdoctools_install`：`cmake -P` 脚本配置并构建一个下游消费者工程（`cmake --build-and-test`），
    验证 `kdoctools_install` 生成 man page 与 HTML handbook 的完整链路。
- 两者都需要系统 DocBook XML 4.5 DTD + DocBook XSL 数据；补丁 0006 加了
  `if (DocBookXML4_FOUND AND DocBookXSL_FOUND)` 能力守卫——数据缺席时不注册（跑空套件合法）。
- 真机验证配置装了官方两套数据，故 2 条全注册并真跑。

### 2. 运行（真机）

- 设备（HarmonyOS PC / aarch64）上 `conan create` 全程跑通，数据经
  `KDOCTOOLS_DOCBOOK_XML4_DIR` / `KDOCTOOLS_DOCBOOK_XSL_DIR` 注入 → 实测结果：
  CTest **2/2 全过**——Test #1 `meinproc_template` Passed 0.52s、Test #2 `kdoctools_install`
  Passed 18.82s（`100% tests passed, 0 tests failed out of 2`，Total 19.34s；ctest 输出与 reports/ 记录一致）。
- test_package（7 项检查）：**`TEST SUMMARY: 7/7 passed, 0 failed`**——meinproc6/checkXML6 存在可执行、
  `meinproc6 --version` 输出 `meinproc 5.0`、定制数据在 `share/kf6/kdoctools`、all-l10n.xml 7415 字节、
  真实 DocBook→HTML 转换 exit 0 产出 marker、checkXML6 正例 exit 0 / 负例 exit 1。
  - 1) meinproc6/checkXML6 存在可执行 2) `meinproc6 --version` 3) 安装的 KDocTools 定制数据
    （catalog.xml/dtd/xsl）在 4) all-l10n.xml 非空 5) 真实 DocBook→HTML 转换出 marker
    6) checkXML6 接受合法 XML 7) checkXML6 拒绝畸形 XML。

### 3. 回填

- 上游 2/2（100%）+ test_package 7/7（100%），见 `test_package/MANIFEST.yml`
  与版本级 `manifest.yaml`。

## 五、Verification

- 源码 SHA256：`024914031fba7a9b79982d02736b21399d9a0d09ad81323d58e17d6b2216c7b0`（download.kde.org）。
- 依赖可得性：qtbase/6.11.1、karchive/6.26.0、openssl/3.5.6.1、libxml2/2.15.3、libxslt/1.1.45.1、
  ecm/6.28.0 —— 见 W0 表。
- 真机（HarmonyOS aarch64，conan-verify 官方 runner）：**Verdict PASS**（2026-10-17T04:09:05；G0–G4 全 PASS；
  conan create 干净重建 RC=0——`conan remove` 清缓存后全链重建，单跑取得 ctest 与 test_package 同源金证据）。
  L2/L4/L5 因 runner 未解析到包缓存路径跳过（G4 同款提示，姊妹包 kitemviews/kwindowsystem/kbookmarks/kcoreaddons 6.28.0 报告同口径）。
- 七补丁全部通过 `patch_ng` 本地预检：按 conan `apply_conandata_patches` 的语义（`patch_ng.fromfile` + `apply(root=source_folder, strip=1)`）在 release tarball 新解包树上逐补丁复算——7/7 APPLY-OK、0 失败（0006 含 2 处 hunk），关键落点复验通过（`KF_DEP_VERSION 6.26.0`、`add_subdirectory(docs)` 注释、`URI::Escape QUIET`、DocBook 两个 `TYPE OPTIONAL`、l10n helper else 分支、autotests 能力守卫、kde-include 样式表在 XSL 缺席时无 `DOCBOOKXSL_DIR` 占位）。设备端由 `conan create` 实际应用，构建日志同步记录。

## 六、Notes（消费者）

- 下游应用直接 `self.requires("kdoctools/6.28.0")` 并在 CMake 里
  `find_package(KF6DocTools)` + `include(KDocTools)`（上游惯例）；`kdoctools_install` 目标
  在消费端生成 man/HTML 文档，需要系统 DocBook 数据齐备。
- 本包无 X11/GUI 依赖，offscreen 即可运行（QT_QPA_PLATFORM=offscreen）。
- `commands.json`（`archives/k/kdoctools/commands.json`）已同步登记 6.28.0 版本（R38）。

---

**编译结束**: 2026-10-17
**最终状态**: built
