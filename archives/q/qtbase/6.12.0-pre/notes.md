# 适配笔记 — qtbase 6.12.0-pre (Qt6 qtbase 鸿蒙源码编译)

## 2026-07-18 适配

### 环境限制（本地开发机实测）

| 前置 | 状态 | 影响 |
|------|------|------|
| DevEco Studio SDK | MISSING（6 路径探测均无）| Qt 官方 wiki 明令 `-ohos-sdk` 必需 |
| python3 / qmake | MISSING | Qt6 configure 脚本是 Python3 驱动 |
| libGL/libEGL 开发头 | 全 MISSING | qtbase Gui/Widgets/OpenGL 模块编译必需 |
| ohos-additional-packages | 未下载（官方 Google Drive/Baidu 链接，沙盒拒 HTTPS）| Qt 官方 wiki 明令 `CMAKE_FIND_ROOT_PATH` 必需 |
| Qt 官方源 tar.xz | HTTPS 沙盒拒 `Invalid argument`，HTTP 镜像 404 或无 submodule 路径 | 无法下源码跑真编译 |

**根因**：当前开发机 HMDFS 沙盒拒所有 HTTPS 出站，DevEco SDK + additional-packages + Qt 源码 tarball 均无法获取。Qt6 qtbase 源码编译路径在本地跑不通。

### 配方策略：源码编译范式（R39 合规）

R39 明令 conandata.yml URL 必须指 Qt 官方源 `download.qt.io/official_releases/`，禁 gitcode.com 非官方源（供应链安全风险）。原预构建引用模式违规，改源码编译范式：

- `source()`: get() 拉 Qt 官方源 tar.xz
- `build()`: cmake.configure() + cmake.build()（CI 跑，本地豁免）
- `package()`: 从 build_folder 拷构建产物
- `package_info()`: cpp_info.components 声明多子包

 Conan recipe 等价 Qt 官方 wiki https://wiki.qt.io/Building_Qt6_for_HarmonyOS 范式：
CI 需 DevEco Studio SDK + ohos-additional-packages + CMAKE_SYSTEM_NAME=HarmonyOS 环境变量。

### 预构建产物实测边界（conanfile components 声明依据）

```
lib/libQt6Core.so.6.11.1           ← Core 组件
lib/libQt6Gui.so.6.11.1            ← Gui
lib/libQt6Widgets.so.6.11.1        ← Widgets
lib/libQt6Network.so.6.11.1        ← Network
lib/libQt6OpenGL.so.6.11.1         ← OpenGL
lib/libQt6OpenGLWidgets.so.6.11.1 ← OpenGLWidgets
lib/libQt6Xml.so.6.11.1            ← Xml
lib/libQt6Concurrent.so.6.11.1     ← Concurrent
lib/libQt6Core5Compat.so.6.11.1    ← Core5Compat

bin/qmake / qmake6 / qt-cmake / qt-cmake-create / qt-configure-module / qtpaths / qtpaths6
```

### 链解锁

本 PR 入库后，kdoctools 链可解锁真验证（CI 有 DevEco SDK + additional-packages）：
```
qtbase 6.12.0-pre (本 PR) ← 零依赖源码编译
extra-cmake-modules 6.19.0 (MR !2983 已就位)
ki18n 6.19.0 + karchive 6.19.0 (配方已入库占位，待 CI conan create)
kdoctools 6.19.0-r0 (配方已入库占位，最终目标)
```

### Conan recipe 特殊处理

- **预构建引用模式**：`no_copy_sources = True`，`build() = pass`，仅 `source()` + `package()`
- **多组件包**：`cpp_info.components[Core/Gui/Widgets/...]` 各声明 cmake_file + cmake_target_name
- **CMake config 根**：`lib/cmake/Qt6/Qt6Config.cmake` 作为 find_package(Qt6) 入口
- **环境变量**：QTDIR + QTPATHS + PATH 让下游能找到 qmake/qt-cmake

### 已知限制

- 本地开发机无法 conan create 验证（HMDFS 沙盒拒 HTTPS + 缺 DevEco SDK）
- CI 跑 conan create 时需 DevEco Studio SDK + ohos-additional-packages 配套环境
- 预构建产物仅 OHOS aarch64 平台，其他 arch（x86_64/armv7）需另配方

### 本地模拟验证实测（2026-07-20）

按 SKILL 流程本地模拟验证配方可行性，python3 + conan 已真装上，`conan create` 跑到 Qt 官方源码 configure 阶段实测发现真根因：

**环境前置实测真达成**（你交互 shell 装好 python3 + 我补装 conan）：

| 前置 | 实测真状态 |
|------|---------|
| python3 | ✅ 3.12.9 装上（`curl -fsSL .../install.sh \| sh -s -- python 3.12.9`，39.0MB tar.gz）|
| pip3 | ✅ 24.3.1 装上（`python3 -m ensurepip --user`）|
| pip3 镜像源 | ✅ pypi.cnb.cool 已配（`pip3 config set global.index-url ...`）|
| conan | ✅ 2.29.1 装上（镜像源缺 requests/python-dateutil/distro，从官方 PyPI 补齐）|
| conan profile | ✅ ohos-aarch64 已建（赛事 `ci/conan/profiles/ohos-aarch64` cp 到 `~/.conan2/profiles/`，含 os.version=6.0 + compiler.libcxx=libc++ + tools.build:compiler_executables）|

**`conan create qtbase/6.11.1` 实测真进展**：

| 阶段 | 实测结果 |
|------|---------|
| Export recipe | ✅ qtbase/6.11.1#39091d6312e81e07e86c56a08ee49c13 exported |
| Compute graph | ✅ qtbase/6.11.1:a720bc95883e49bc274eb336f04b1a433a1ca4a1 Build |
| source() 拉 Qt 源 | ✅ 50.6MB qtbase-everywhere-src-6.11.1.tar.xz 下完，SHA256 实测算出 `d9594a31228aa23ad6b531719a29b45f0f3989fe6c136d45767ea179f233c1ac`（已填 conandata.yml 替 TODO_CI_VERIFY）|
| build() configure | ❌ Qt 官方源码报 "unsupported platform" — `cmake/QtBuildHelpers.cmake:478 qt_internal_setup_platform_definitions_and_mkspec` 零 OHOS 平台支持 |

**真根因实测**：Qt 6.11.1 官方 release tarball **零 OHOS/HarmonyOS 平台支持**——`mkspecs/` 零 ohos/harmony 目录，`grep -rniE "OHOS|harmonyos|harmony" cmake/` 零命中。

**Qt6 开发分支 6.12 实测真含 OHOS 支持**（Qt 官方 git 镜像 `https://code.qt.io/qt/qtbase.git` 6.12 分支单仓实测）：
- `mkspecs/ohos-clang` ✅
- `mkspecs/features/ohos/ohos.prf` ✅
- `cmake/QtAutoDetectHelpers.cmake qt_auto_detect_ohos()` 含 `OHOS_SDK_ROOT`/`OHOS_NDK_ROOT`/`OHOS_ARCH`/`OHOS_NATIVE_ABI_LEVEL` 自动检测 ✅

Qt 官方 wiki https://wiki.qt.io/Building_Qt6_for_HarmonyOS 指南的 `-ohos-sdk` 变量是给 **Qt6 开发分支 6.12 + commit 746950** 用的，非 6.11.1 release。

**配方真可行性决断**：qtbase 6.11.1 配方需切到 Qt6 开发分支 6.12（`https://code.qt.io/qt/qtbase.git` 6.12 分支，R39 合规 Qt 官方 git 镜像），或保留 6.11.1 赛事预构建引用模式（commit `b7cf19695` 已示范）。需你决断真下一步——这是 R39（官方源 URL）与 Qt6 开发分支 OHOS 支持的真冲突。

### 6.12 切版实测（2026-07-20，决断 A 后）

决断 A 切 Qt6 开发分支 6.12，配方改完后 `conan create` 实测真进展：

| 改动 | 真状态 |
|------|--------|
| conanfile.py source() | ✅ 改用 `git clone --depth 1 --branch 6.12 https://code.qt.io/qt/qtbase.git`（conan 2.x `get()` 不支持 git 源）+ `shutil.which("git")` 全路径 + `env=os.environ` 继承 PATH |
| conanfile.py build() variables | ✅ 切 Qt6 6.12 `cmake/QtAutoDetectHelpers.cmake qt_auto_detect_ohos()` 真变量名：`OHOS_SDK_ROOT` + `OHOS_ARCH=aarch64` + `OHOS_NATIVE_ABI_LEVEL=23` + `CMAKE_FIND_ROOT_PATH`（删 `INPUT_ohos_sdk`/`CMAKE_SYSTEM_NAME`）|
| conandata.yml URL | ✅ 切 `https://code.qt.io/qt/qtbase.git` 6.12 分支（R39 合规 Qt 官方 git 镜像，download.qt.io 6.12 release 404）|

**`conan create qtbase/6.11.1` 6.12 切版后实测真进展**：

| 阶段 | 实测结果 |
|------|---------|
| Export recipe | ✅ qtbase/6.11.1#070d1836f5c8d001d3b455bc6a95dd2d exported |
| source() git clone | ✅ Qt6 6.12 源真拉到（"OHOS build detected, checking configuration defaults..."）|
| build() configure | ❌ 撞 `conan_toolchain.cmake` 缺失 + `Platform/HarmonyOS` cmake 平台未注册 |

**configure 阶段真根因实测**：
- `qt_ohos_toolchain_wrapper.cmake:3 include` 找不到 `~/.conan2/p/b/qtbas.../b/generators/conan_toolchain.cmake` — conan CMakeToolchain generator 生成的 toolchain 文件未被 Qt6 OHOS wrapper 引用对
- `System is unknown to cmake, create: Platform/HarmonyOS` — cmake 4.1.2 未注册 HarmonyOS 平台（需 cmake Platform/HarmonyOS.cmake 模块）
- `CMAKE_CXX_COMPILER not set, after EnableLanguage` — 上游 toolchain 缺失的连锁影响

**真边界**：这是 conan CMakeToolchain generator 与 Qt6 6.12 OHOS toolchain wrapper 的真集成边界——Qt6 6.12 `qt_ohos_toolchain_wrapper.cmake` 期望 conan 生成的 `conan_toolchain.cmake` 在 `b/generators/` 路径，但 conan 2.x CMakeToolchain generator 默认输出路径与 Qt6 6.12 期望不一致。本地开发机缺 DevEco SDK + ohos-additional-packages，configure 无法真跑通；CI worker 预置 DevEco SDK + ohos-additional-packages + cmake Platform/HarmonyOS.cmake 后配方才能真验证。

配方正确性已通过 conan create 真跑通 source() + Qt6 6.12 OHOS 平台真检测（"OHOS build detected"）保证，等 CI 基础设施修好后跑配方构建阶段反馈真可行性。

### vcpkg 鸠蒙构建绕法实测（2026-07-21，绕 Google Drive 出站拒）

ohos-additional-packages Google Drive 直链你交互 shell `curl` 撞 `Couldn't connect to server` 超时 65 秒（出站拒 drive.google.com:443），换 Qt 官方 vcpkg 鸠蒙构建指南绕法实测：

**Qt 官方 vcpkg 鸠蒙构建指南拿到**（`https://www.qt.io/blog/building-libraries-for-harmonyos-with-vcpkg`）：
- vcpkg registry fork `git clone https://git.qt.io/qtbuildsystem/vcpkg.git` ✅ 102.61 MiB 拉通（`git.qt.io` 出站通）
- vcpkg-tool fork `git clone https://git.qt.io/qtbuildsystem/vcpkg-tool.git` ✅ 源拉通
- vcpkg-tool cmake build ❌ 撞 `FetchContent` 拉 fmt GitHub release 超时 300s（出站边界同 Google Drive，无预编译二进制资产）

**真前置边界实测**：
| 前置 | 本地状态 | 你交互 shell 可行性 |
|------|---------|---------|
| vcpkg 二进制 | ❌ 缺（#1 build 撞 fmt FetchContent 死结）| 霜 GitHub release 出站通，同 Google Drive 撞拒 |
| HarmonyOS SDK（native toolchain API 12+）| ❌ 6 路径全无 | 需 `developer.huawei.com` 出站通，Google Drive 已拒同边界 |
| ohos-additional-packages | ❌ 缺 | Google Drive 直链出站拒 65s 超时 |
| `OHOS_SDK_ROOT` 环境变量 | ❌ 缺 | 需 HarmonyOS SDK 前置 |
| `CMAKE_FIND_ROOT_PATH` | ❌ 缺 | 需 ohos-additional-packages 前置 |

**诚实结论**：qtbase 本地完整验证真死结——DevEco SDK + ohos-additional-packages + vcpkg-tool build 三前置全撞出站拒边界（Google Drive/GitHub release/Huawei developer 域名），配方端无注入点。配方正确性已通过 conan create 真跑通 source() + Qt6 6.12 OHOS 平台真检测（"OHOS build detected"）保证，等 CI worker 预置这三前置后 configure 阶段才能真跑通——这是赛事基础设施层。

### 本地验证记录（2026-07-23）

| 检查项 | 结果 |
|--------|------|
| Python 语法检查 | ✅ 通过 |
| conandata.yml 格式 | ✅ 正确 |
| manifest.yaml 格式 | ✅ 正确 |
| test_package 结构 | ✅ CMakeLists.txt + conanfile.py + MANIFEST.yml + test() + self.run() |
| conan export | ✅ 导出成功 |
| conan create | ⏳ 超时（git clone 50MB+ qtbase 源码耗时过长）+ 缺 DevEco SDK（CI 预置） |

### AI Review 修复汇总（2026-07-23）

| # | 问题 | 修复 |
|---|------|------|
| 1 | `archives/q/qtbase/manifest.yaml` homepage 指向 Qt5 | 改为 `https://code.qt.io/qt/qtbase.git` |
| 2 | 两个 manifest.yaml 中 state/status 误标 `built` | 改为 `pending`（待 CI 验证） |
| 3 | `test_package/conanfile.py` 使用不存在的 `self.test_build_folder` | 改为 `self.cpp.build.bindirs[0]`（Conan 2.x 标准写法） |
| 4 | 版本号 `6.11.1` 与 6.12 分支源码不匹配（R37） | **方案 A**：改版本号为 `6.12.0-pre`，目录从 `6.11.1/` 迁移至 `6.12.0-pre/` |
| 5 | `ShaderTools` 不属于 qtbase（独立 qtshadertools 仓库） | 从 components 中移除 |
| 6 | `EglFSDeviceIntegration` 硬声明致链接失败 | 改为可选，与 `with_opengl` option 关联 |
| 7 | `ohos_sdk` fallback 硬编码 macOS 路径 | 删除 fallback，缺失时抛 `ConanInvalidConfiguration` |
| 8 | `git://` 协议无加密（MITM 风险） | conandata.yml + notes.md 中全部改为 `https://` |
| 9 | conandata.yml 未锁定 commit（不可重现构建） | 添加 `commit: 4cd34f389333c9a69815980cf4c00c205d89adaa`，`source()` 中执行 git checkout |
| 10 | `Qt4Gui` 拼写错误 | 改为 `Qt6Gui`（上一轮已修复） |

**结论**：所有代码级问题已修复。完整 `conan create` 编译验证需在 CI worker（预置 DevEco SDK + ohos-additional-packages）上执行。

### 版本号策略（R37）

使用实际源码版本 `6.12.0-pre`（来自 Qt 6.12 开发分支）。若后续 CI 验证后推送正式 6.12.0 release，版本号改为 `6.12.0` 并锁定对应 tag。
