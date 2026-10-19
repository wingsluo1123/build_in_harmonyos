# qtmultimedia 6.11.1.1 适配笔记

## 基本信息

- 软件名称: qtmultimedia（Qt Multimedia 模块）
- 版本: **6.11.1.1**（同上游源码 6.11.1，打包修复版）
- 构建系统: cmake
- 适配路径: 路径 A（基础适配）+ 再适配（SONAME 修复）
- 上游仓库: https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qtmultimedia-everywhere-src-6.11.1.tar.xz

## 本版（6.11.1.1）修什么

**根因**：本平台 Qt 安装产物里 `libQt6MultimediaWidgets.so` 与
`libQt6SpatialAudio.so` **没有 SONAME**，且 NEEDED 记录的是相对路径
`../../lib/libQt6Multimedia.so`。

**后果**：任何链接这两个库的消费者，其产物会继承这种"路径型" NEEDED
（以及指向构建目录的绝对路径）。运行时 dlopen 直接失败：

```
Error loading shared library ../../lib/libQt6Multimedia.so:
  (needed by .../lib/libQt6MultimediaWidgets.so)
```

直接表现为 PyQt6 的 `QtMultimediaWidgets` / `QtSpatialAudio` 绑定导入失败
（`ImportError`），即使扩展本身构建、签名都正常。

**修复**：`package()` 在 `CMake(self).install()` 之后、包封存之前，对
`lib/` 下每个 Qt6 库：

1. 若缺 SONAME → 设为规范名（`libFoo.so.6.11.1` → `libFoo.so.6`）；
2. 把每条含 `/` 的 NEEDED 改写为 basename（`../../lib/libQt6Multimedia.so`
   → `libQt6Multimedia.so`）；
3. 修改过的 ELF **重新自签名**（OHOS 拒绝 dlopen 未签名的改动 ELF）。

实测：3 个库全部修正，`path_needed=0`。

## 依赖

- qtbase/6.11.1（Core/Gui REQUIRED，提供 Qt6Config.cmake 与 harmonyos-clang mkspec）
- qtshadertools/6.11.1（qt_internal_add_shaders 宏与 qsb 宿主工具）

## 关键适配点（沿用 6.11.1）

1. **Qt6ShaderTools_DIR 必需**：src/multimedia 用 `qt_internal_add_shaders`
   预编译 shader，未设置则 configure 报 `Unknown CMake command`。
2. **qsb 宿主工具 LD_LIBRARY_PATH**：构建期需指向 qtbase/qtshadertools 包 lib。
3. **memory_resource 头缺失**：OHOS libc++ 无 `<memory_resource>`，补丁 0001。
4. **无媒体后端**：OHOS 无音频/视频后端，设备类 integration 测试声明排除。
5. **并行编译** `--parallel 4` 压缩 W3 600s 窗口。

## 验证结果

- `conan create` 干净构建通过：`Package 'ba4c19830a0f930cd762892745779329f1a30138' created`
- SONAME 规范化生效：`normalised SONAME/NEEDED on 3 lib(s)`
- 修复后断言（readelf）：`libQt6Multimedia/MultimediaWidgets/SpatialAudio`
  SONAME 齐备、`path_needed=0`
- 消费者侧复验：PyQt6 的 `QtMultimedia` / `QtMultimediaWidgets` /
  `QtSpatialAudio` 三者 `import` 全部 OK（修复前两者报
  `Error loading shared library ../../lib/libQt6Multimedia.so`）

## 未纳入本版的同类问题（已评估，无消费者侧破坏）

其它 5 个包（qtwebsockets / qtwebchannel / qtremoteobjects /
qttexttospeech / qttools）的库也普遍缺 SONAME，但实测其生成的 PyQt6 扩展
**没有路径型 NEEDED**、导入正常，无消费者侧破坏证据，故不在本版重建，
留作后续统一处理（届时 pyqt6 配方的 `_fix_farm_sonames()` 可退化为安全网）。

## 最终状态

built（本地 conan create 通过 + SONAME/消费者双重复验）→ 待 PR 合入
