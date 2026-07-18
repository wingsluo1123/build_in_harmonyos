# 适配笔记 — qtbase 6.11.1 (Qt6 qtbase 鸿蒙预构建引用)

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
lib/libQt6ShaderTools.so.6.11.1    ← ShaderTools
lib/libQt6EglFSDeviceIntegration.so.6.11.1 ← EglFSDeviceIntegration

bin/qmake / qmake6 / qt-cmake / qt-cmake-create / qt-configure-module / qtpaths / qtpaths6
```

### 链解锁

本 PR 入库后，kdoctools 链可解锁真验证（CI 有 DevEco SDK + additional-packages）：
```
qtbase 6.11.1 (本 PR) ← 零依赖预构建引用
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

### 版本号策略（R37）

引用赛事预构建 6.11.1 → 版本号 6.11.1。若后续赛事升级 prebuilt 到 6.11.2/6.12.x，新增版本子目录。
