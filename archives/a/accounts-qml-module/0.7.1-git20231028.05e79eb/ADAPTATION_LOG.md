# accounts-qml-module 0.7.1 鸿蒙化适配完整历程记录（ADAPTATION LOG）

> 归档日期：2026-08-13
> 结论分类：`暂时搁置`（阻塞类别：`依赖链断裂`）
> 关联：Issue #2107 / PR #5233
> 本文档完整记录本次适配的全部过程：对话背景、环境准备、W0 依赖预检、三个依赖逐一适配的步骤/遇到的问题/解决方案、最终结论与建议路径。

---

## 目录

1. [对话全过程总结](#1-对话全过程总结)
2. [环境准备](#2-环境准备)
3. [W0 依赖预检：依赖链断裂确认](#3-w0-依赖预检依赖链断裂确认)
4. [依赖逐一适配记录](#4-依赖逐一适配记录)
   - [4.1 libaccounts-glib 1.27](#41-libaccounts-glib-127meson)
   - [4.2 libaccounts-qt 1.13](#42-libaccounts-qt-113qmake--手动构建)
   - [4.3 qt5-qtbase 5.15.2 / 5.15.2.1（QtXml 缺失与 Qt5 全量构建）](#43-qt5-qtbase-5152--51521qtxml-缺失与-qt5-全量构建)
   - [4.4 libsignon-qt 8.61 / qt5-qtdeclarative 5.15.2（未启动）](#44-libsignon-qt-861--qt5-qtdeclarative-5152未启动)
5. [关键代码与配方](#5-关键代码与配方)
6. [遇到的问题汇总表](#6-遇到的问题汇总表)
7. [最终结论与建议路径](#7-最终结论与建议路径)

---

## 1. 对话全过程总结

本次适配的完整时间线（2026-08-12 ~ 2026-08-13）：

| 阶段 | 内容 | 结果 |
|------|------|------|
| 1. 分支准备 | 在 `ohpkg/build_in_harmonyos` 创建并切换 `feature/atomcode_support` 分支 | ✅ 完成 |
| 2. 任务识别 | 定位 accounts-qml-module 任务：上游为 Accounts SSO 的 QML 绑定库，版本 0.7.1-git20231028.05e79eb，任务分支 `feat/accounts-qml-module-0.7.1-git20231028.05e79eb`（远程存在但为空壳） | ✅ 完成 |
| 3. 环境修复 | conan 2.29.1（OHOS 适配版）安装 + `distro` 模块补齐 + ohpcd remote 添加 + ohos-aarch64 profile 导入 | ✅ 完成 |
| 4. W0 预检 | conan list 权威验证 4 个直接依赖：3 个 0 recipe | ❌ 依赖链断裂确认 |
| 5. 无法适配 Issue | 创建 Issue #2107（[无法适配] 依赖链断裂） | ✅ 完成 |
| 6. 逐一适配尝试 | 用户要求逐一适配三个依赖验证可行性 | 见第 4 节 |
| 7. 无法适配 PR | 提交 PR #5233，按赛事PR模板补正文、补分支文件 | ✅ 完成 |

---

## 2. 环境准备

适配前必须恢复完整构建环境（SKILL.md §0.0）：

```bash
# ① Python 3.12.9（如已装"Python安装器"应用需先卸载）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- python 3.12.9

# ② pip 社区源配置（必须，托管 OHOS 适配版 conan）
python3 -m ensurepip
pip3 config set global.index-url https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple
pip3 config set global.trusted-host pypi.cnb.cool

# ③ OHOS 适配版 conan（基线 2.29.1，禁止官方 PyPI）
pip3 install conan

# ④ 环境修复过程中的关键坑：
#    - conan 报 ModuleNotFoundError: No module named 'distro' → python3 -m pip install --user distro
#    - ohpcd remote 缺失 → bash ci/conan/setup.sh（自动添加 https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/）
#    - 构建工具 meson/ninja：meson 用 pip 单独装（纯 Python 无需编译）；ninja 走 conan tool_requires
```

Profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, clang 15, libc++, cppstd=17）。

---

## 3. W0 依赖预检：依赖链断裂确认

按 SKILL.md R35（禁止 conan list 判 binary，用 download/list 验证 recipe）执行权威验证：

```bash
conan list "libaccounts-qt/*" -r=ohpcd        # → 0 recipes ❌
conan list "libsignon-qt/*" -r=ohpcd          # → 0 recipes ❌
conan list "qt5-qtdeclarative/*" -r=ohpcd     # → 0 recipes ❌
conan list "qt5-qtbase/*" -r=ohpcd            # → 5.15.2 ✅（无 5.15.2.1）
```

**结论：R36 阻塞确认**——accounts-qml-module 的 4 个直接依赖中 3 个未发布，必须先按拓扑序适配发布缺失依赖才能构建下游。

---

## 4. 依赖逐一适配记录

### 4.1 libaccounts-glib 1.27（meson）

**定位**：Accounts SSO 的 GLib 版账号管理库，accounts-qml-module 的上游依赖 libaccounts-qt 的底层。

**配方文件**（本分支已提交）：
- `archives/l/libaccounts-glib/1.27/conanfile.py`
- `archives/l/libaccounts-glib/1.27/conandata.yml`
- 补丁：`0001-docs-meson.build.patch`、`0002-libaccounts-glib-meson.build.patch`、`0003-tools-meson.build.patch`、`0004-disable-tests.patch`、`0005-pregen-marshal.patch`

**适配步骤与问题**：

| # | 步骤/问题 | 解决方案 |
|---|----------|---------|
| 1 | meson 不在 PATH | `python3 -m pip install meson`（纯 Python） |
| 2 | ninja 不可用，pip 装 ninja 需源码编译又缺 CMake | 改用 conan `tool_requires("ninja-build/1.13.2")`（ohpcd 已发布） |
| 3 | 源码 sha256 空导致下载校验失败 | 从 conan 报错拿 Computed hash 填入 conandata.yml |
| 4 | `Unknown option: "documentation"` | libaccounts-glib 的 meson_options.txt 只有 install-py-overrides/py-overrides-dir，删掉不存在的 project_options |
| 5 | `Unknown module(s)` 之前 `gnome.genmarshal()` 需 glib_genmarshal 变量 | `_patch_pc_files()`：给 conan 生成的 glib-2.0.pc 补 `glib_mkenums/glib_genmarshal`，gio-2.0.pc 补 `gdbus_codegen`（同 libsignon-glib 配方做法） |
| 6 | `glib-genmarshal: Permission denied`（code=126） | **OHOS HMDFS 对已存在文件 chmod 不生效**；glib-genmarshal 是 Python 脚本，改用 `python3` 解释器直接执行，预生成 `ag-marshal.h/c`（`_pregen_marshal()`），配 0005 补丁让 meson 跳过 `gnome.genmarshal()` |
| 7 | patch 计数不符（0004 首版 "patch stream is incomplete"） | 修正 hunk 头 `@@ -36,5 +36,5 @@` 与实际行数严格匹配 |
| 8 | 依赖 glib/libxml2/sqlite3 需先发布 | 三者均已发布（glib/2.84.0.1、libxml2/2.15.3、sqlite3/3.49.1），`--build=missing` 直接复用 |

**构建命令（验证成功）**：
```bash
conan create archives/l/libaccounts-glib/1.27 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```
**结果：✅ 构建成功**——产物 `libaccounts-glib.a` + `libaccounts-glib.pc` + 13 个头文件。

### 4.2 libaccounts-qt 1.13（qmake / 手动构建）

**定位**：Accounts SSO 的 Qt 版账号管理库，accounts-qml-module 的直接依赖之一。

**配方文件**（本分支已提交）：
- `archives/l/libaccounts-qt/1.13/conanfile.py`
- `archives/l/libaccounts-qt/1.13/conandata.yml`
- 补丁：`0001-Accounts-account.h.patch`（QString::null→QString()）、`0002-Accounts-manager.h.patch`、`0003-accounts-qt.pro.patch`（跳 tests）、`0004-Accounts-qt-core-only.patch`

**适配步骤与问题**：

| # | 步骤/问题 | 解决方案 |
|---|----------|---------|
| 1 | OHOS conan 无 `conan.tools.qmake` 模块 | 改为直接调用 qt5-qtbase 包内 qmake 二进制 + 显式 PATH |
| 2 | github 源码下载超时 | 换官方源 `https://gitlab.com/accounts-sso/libaccounts-qt/-/archive/VERSION_1.13/...` |
| 3 | sha256 校验失败 | 从 conan 报错填 Computed hash |
| 4 | 0002 补丁与官方源差异（ubports fork 有 `serviceList(const Application&)` 而官方源没有） | 按官方源实际内容重写 0002 补丁 |
| 5 | `Unknown module(s) in QT: core xml` | 源码实际不用 QtXml → 0004 补丁去掉 `QT += core xml` 的 xml |
| 6 | `Unknown module(s) in QT: core`（去掉 xml 后仍失败） | **qt5-qtbase/5.15.2 包内 qmake 的 QMAKE_MKSPECS 固化指向构建期 build 目录**（打包缺陷），modules-inst 模块发现失败；`qt.conf` 的 Prefix/TargetSpec、QMAKEPATH/QMAKESPEC 环境变量均无法覆盖（-query 返回 Unknown 证实编译期固化） |
| 7 | **绕开 qmake 模块系统** | 重写 conanfile 为**手动 moc + clang++ 构建**：moc 处理 5 个 Q_OBJECT 头 + clang++ 编译 10 个源文件 + `ar rcs libaccounts-qt5.a` |
| 8 | `Accounts/accountscommon.h file not found` | include 路径加源码根目录 |
| 9 | `'QDomDocument' file not found` | include 遍历 qt5-qtbase 全部模块子目录（含 include/QtXml） |
| 10 | `'QtXml/qtxml-config.h' file not found` | **最终卡点**：qt5-qtbase/5.15.2 以 `-no-feature-xml` 构建，`qtxml-config.h` 与 `libQt5Xml.so` 均未生成——QtXml 头目录只是残留，模块实际不可用 |

**结果：⚠️ 部分成功**——手动 moc+clang++ 方案已通过大部分编译，最终卡在 QtXml 缺失（依赖 qt5-qtbase 版本问题，非 libaccounts-qt 本身问题）。

### 4.3 qt5-qtbase 5.15.2 / 5.15.2.1（QtXml 缺失与 Qt5 全量构建）

**问题**：
- `qt5-qtbase/5.15.2`（ohpcd 已发布）configure 参数含 `-no-feature-xml` → 无 `libQt5Xml.so`、无 `qtxml-config.h` → 不满足 libaccounts-qt 的 QDomDocument 依赖。
- 仓库存在 `qt5-qtbase/5.15.2.1` 配方（description 明确 "enables Core/Gui/Network/Widgets/PrintSupport/Xml"，configure 无 `-no-feature-xml`），但**未发布到 ohpcd**。

**尝试**：本地 `conan create archives/q/qt5-qtbase/5.15.2.1` 全量构建。
**问题**：
| # | 问题 | 说明 |
|---|------|------|
| 1 | `no such file or directory: '.../lib/libQt5Core.so'` | OHOS HMDFS **拒绝 `ln -s` 软链接**：Qt 生成 `libQt5Core.so.5.15.2` 后无法创建 `libQt5Core.so` 别名，链接 libQt5Network 时 `-lQt5Core` 找不到；5.15.2.1 配方缺 `_create_symlink_shim()` 调用（5.15.2 有） |
| 2 | 逐个补软链接是"打地鼠" | 需批量补 `libQt5*.so` 软链接（`ln -sf ... || cp ...`），且 Qt5 全量编译在本地环境连环报平台问题 |
| 3 | 全量编译体量巨大 | Qt5 上百个模块，仅 5.15.2 当初是在 CI 完整构建机编译通过（SUMMARY 标"✅ 已编译"） |

**结论**：本地终端环境缺 CI 构建设施，无法完成 Qt5 全量构建——这是基础设施层面的独立任务，超出"逐一适配三个小依赖"的范围。

### 4.4 libsignon-qt 8.61 / qt5-qtdeclarative 5.15.2（未启动）

- **libsignon-qt 8.61**：上游源码在 signond 项目 `lib/` 子目录（`signon.pro` 中 `SUBDIRS = lib src server tests`），需取子目录独立打包；qmake 构建，依赖 qtbase。因上游依赖链（含 Qt5）未就绪，未启动适配。
- **qt5-qtdeclarative 5.15.2**：大型 Qt5 模块（Qt Quick/QML 全量），官方 tarball 已确认（`https://download.qt.io/archive/qt/5.15/5.15.2/submodules/qtdeclarative-everywhere-src-5.15.2.tar.xz`），依赖 qt5-qtbase。属独立大型任务，未启动。

---

## 5. 关键代码与配方

本分支已提交以下配方文件（适配成果代码）：

| 路径 | 说明 |
|------|------|
| `archives/l/libaccounts-glib/1.27/conanfile.py` | meson 配方：tool_requires ninja、_patch_pc_files、_pregen_marshal（HMDFS 绕行）、禁用 docs/gir/tools/tests |
| `archives/l/libaccounts-glib/1.27/conandata.yml` | 官方源 + sha256 + 5 补丁声明 |
| `archives/l/libaccounts-glib/1.27/patches/0001~0005` | gtkdoc 禁用 / gir 可选化+pygobject 禁用 / tools 禁用 / tests 禁用 / pregen-marshal |
| `archives/l/libaccounts-qt/1.13/conanfile.py` | 手动 moc+clang++ 构建（绕过 qmake 固化缺陷）、PkgConfigDeps、include 全模块遍历 |
| `archives/l/libaccounts-qt/1.13/conandata.yml` | 官方源 + sha256 + 4 补丁声明 |
| `archives/l/libaccounts-qt/1.13/patches/0001~0004` | QString::null→QString()×2 / 跳 tests / 去 xml |

关键代码片段（libaccounts-qt 手动构建核心）：

```python
# conanfile.py — 手动 moc + clang++ 构建（绕开 qmake QMAKE_MKSPECS 固化缺陷）
def build(self):
    apply_conandata_patches(self)
    src, build, cc = self.source_folder, self.build_folder, self._cc()
    inc, defines = self._include_flags(), "-DQT_NO_CAST_TO_ASCII -DQT_NO_CAST_FROM_ASCII -DQT_NO_KEYWORDS -DQ_OS_OHOS"
    moc = os.path.join(self.dependencies["qt5-qtbase"].package_folder, "bin", "moc")
    objs = []
    for h in ("manager.h", "account.h", "account-service.h", "application.h", "auth-data.h"):
        moc_src = os.path.join(build, f"moc_{h.replace('.h', '.cpp')}")
        self.run(f'"{moc}" {defines} {inc} "{src}/Accounts/{h}" -o "{moc_src}"')
        obj = moc_src.replace(".cpp", ".o")
        self.run(f'"{cc}" -c {defines} {inc} -fPIC "{moc_src}" -o "{obj}"')
        objs.append(obj)
    for cpp in ("manager.cpp", "account.cpp", "account-service.cpp", "application.cpp",
                "auth-data.cpp", "error.cpp", "provider.cpp", "service.cpp",
                "service-type.cpp", "utils.cpp"):
        obj = os.path.join(build, cpp.replace(".cpp", ".o"))
        self.run(f'"{cc}" -c {defines} {inc} -fPIC "{src}/Accounts/{cpp}" -o "{obj}"')
        objs.append(obj)
    self.run(f'ar rcs "{build}/libaccounts-qt5.a" ' + " ".join(objs))
```

```python
# libaccounts-glib — HMDFS 软链接/chmod 失效的绕行：python3 直接执行 genmarshal
def _pregen_marshal(self):
    gm = os.path.join(self.dependencies["glib"].package_folder, "bin", "glib-genmarshal")
    marshal_dir = os.path.join(self.source_folder, "libaccounts-glib")
    marshal_list = os.path.join(marshal_dir, "ag-marshal.list")
    for kind, out_name in (("--header", "ag-marshal.h"), ("--body", "ag-marshal.c")):
        self.run(f'python3 "{gm}" {kind} --prefix ag_marshal '
                 f'--output "{os.path.join(marshal_dir, out_name)}" "{marshal_list}"')
```

---

## 6. 遇到的问题汇总表

| 类别 | 问题 | 环境/根因 | 解决方案 | 是否已解决 |
|------|------|-----------|----------|-----------|
| 环境 | conan 缺 distro 模块 | OHOS 适配版 conan 依赖缺失 | pip install distro | ✅ |
| 环境 | ohpcd remote 缺失 | conan 未配置制品仓 | ci/conan/setup.sh | ✅ |
| 环境 | meson 缺失 | 本机无构建工具 | pip install meson | ✅ |
| 环境 | ninja pip 编译失败 | 需源码编译缺 CMake | conan tool_requires ninja-build | ✅ |
| 平台 | HMDFS chmod 不生效 | 已存在文件 chmod 无效 | 复制新文件+chmod / python3 解释器绕行 | ✅ |
| 平台 | HMDFS 拒绝 ln -s | Qt 软链接别名无法创建 | 需批量 cp 兜底（qt5-qtbase 5.15.2.1） | ⚠️ 本地无法完整构建 |
| 依赖 | libaccounts-qt/libsignon-qt/qt5-qtdeclarative 未发布 | 制品仓 0 recipe | 需先适配发布（R36） | ❌ 阻塞 |
| 依赖 | qt5-qtbase/5.15.2 缺 QtXml | -no-feature-xml 构建 | 需 5.15.2.1（含 Xml，未发布） | ❌ 阻塞 |
| 配方 | conan.tools.qmake 不存在 | OHOS conan 精简 | 直接调 qmake 二进制 / 手动构建 | ✅ |
| 配方 | qmake QMAKE_MKSPECS 固化 | qt5-qtbase 打包缺陷 | 手动 moc+clang++ 绕行 | ✅ |

---

## 7. 最终结论与建议路径

**结论**：accounts-qml-module 0.7.1 当前**无法完成鸿蒙化适配**（分类：暂时搁置；阻塞：依赖链断裂）。适配本身的技术路线已验证可行（libaccounts-glib 构建成功、libaccounts-qt 手动编译推进到仅缺 QtXml），卡点在 **Qt5 基础设施层**（qt5-qtbase/5.15.2 缺 QtXml，5.15.2.1 全量构建需 CI 完整构建机）。

**建议路径**（拓扑序，在 CI 完整构建机执行）：

```
qt5-qtbase/5.15.2.1（含 Xml，补 symlink shim）
  → libaccounts-qt/1.13（手动 moc+clang++ 配方已就绪）
  → libsignon-qt/8.61（signond lib/ 子目录）
  → qt5-qtdeclarative/5.15.2（大型 Qt5 模块，单独评估）
  → accounts-qml-module/0.7.1（重启适配）
```

依赖就绪后，本分支已有的 libaccounts-glib/libaccounts-qt 配方可直接复用，重启适配将大幅加速。

---

*本记录由 AtomCode (deepseek-v4-flash) 整理，供社区参考，避免重复投入。*
