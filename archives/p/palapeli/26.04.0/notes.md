# palapeli 26.04.0 鸿蒙适配记录

- 上游：KDE Gear `release-service/26.04.0`，`palapeli-26.04.0.tar.xz`
  sha256 `8bf301eec4a319bc7a979c6ce6bb42c76001794cb1773fec828b44b8d61574ab`
- 目标：HarmonyOS PC / OHOS aarch64，conan 2.29，clang 15（OHOS SDK 26.0.0.18），libstdc++11
- 归档状态：`NOT ARCHIVED`（本 PR 首次归档）
- 配套知识：`knowledge/operations/kf6-desktop-integration/`（本 PR 同批交付）

## 1. 依赖闭包的确定过程

palapeli 自身要求：

```
Qt6 6.5+ (Core Gui Svg Widgets)          → qtbase-sql-dbus/6.11.1 + qtsvg/6.11.1
KF6 6.0+ (Archive Completion Config ConfigWidgets CoreAddons Crash DBusAddons DocTools
          I18n ItemViews KIO Notifications WidgetsAddons IconThemes XmlGui)
KDEGames6 6.0+                            → libkdegames/26.04.0.1
```

制品仓实测（`conan list`）：

| 组件 | 可用的最高 6.18 线 | 说明 |
|---|---|---|
| KF6 主体（kconfig/kcoreaddons/ki18n/kcrash/karchive/kbookmarks/kauth/kcolorscheme/kcompletion/kconfigwidgets/kguiaddons/kiconthemes/kitemviews/kjobwidgets/kservice/kwidgetsaddons/kwindowsystem/solid/kdbusaddons/knotifications/kxmlgui/knewstuff/kdnssd/attica） | 6.18.0 | 全齐，统一 `override=True` 收敛 |
| `kio` | **无 6.18.0**，仅 6.14.0 / 6.26.0 | 取 6.14.0，其 `KF6 6.14` 依赖 pin 由 `override` 拉回 6.18.0 → 需源码构建 |
| `kdoctools` | **仅 6.19.0** | 与 6.18 不同线，见 §2 |
| `libkdegames` | 26.04.0.1 | 26.04.0 有 SONAME 缺陷，弃用 |
| `shared-mime-info` | 2.4 / 2.5.1 | `tool_requires` 满足 `mime/` 的 `find_package(SharedMimeInfo)` |

`kio/6.14.0` 只有与其自身依赖线匹配的二进制，override 到 6.18 后必须源码构建；
源码包（`kiconthemes/6.18.0`、`kio/6.14.0`）已按 sha256 入 `core.sources:download_cache`，
构建期不依赖外网。

## 2. 阻塞问题与处置（本库触发的共性问题）

### 2.1 KF6DocTools 版本线断裂（HARD）

未处置时的真实报错：

```
CMake Error at .../FindPackageHandleStandardArgs.cmake:227 (message):
  Could NOT find KF6 (missing: DocTools) (found suitable version "6.14.0",
  minimum required is "6.0.0")
      Reason given by package: Missing the following required components: DocTools
Call Stack (most recent call first):
  .../share/ECM/find-modules/FindKF6.cmake:100 (find_package_handle_standard_args)
  CMakeLists.txt:33 (find_package)
```

`kdoctools` 在制品仓只有 6.19.0，其配方拉 `karchive/6.19.0`、`extra-cmake-modules/6.19.0`、
`libxslt/1.1.45.1`、`libxml2/2.15.Z`、`openssl/3.5.6.1`。而本库闭包被
`libkdegames/26.04.0.1` 与 6.18 线钉住，引入 6.19.0 等于在同一个图里放两条 KF6 线。

**处置**：`patches/0001-CMakeLists.txt.patch` 可选化裁剪，三处同时处理：

| 位置 | 改动 | 单独漏改的后果 |
|---|---|---|
| `find_package(KF6 ... REQUIRED COMPONENTS ...)` | 删 `DocTools` | — |
| 顶层 `add_subdirectory(doc)` | 删除 | `doc/` 内 `kdoctools_create_handbook()` → `Unknown CMake command` |
| 顶层 `kdoctools_install(po)` | 删除 | 同上，`Unknown CMake command "kdoctools_install"` |

`ki18n_install(po)` 保留——`ki18n` 在 6.18 线内，翻译照常安装。

### 2.2 SharedMimeInfo（本次不打补丁）

`mime/CMakeLists.txt`：

```cmake
find_package(SharedMimeInfo REQUIRED)
install(FILES palapeli-mimetypes.xml DESTINATION ${KDE_INSTALL_MIMEDIR})
update_xdg_mimetypes(${KDE_INSTALL_MIMEDIR})
```

ECM 的 `FindSharedMimeInfo` 只找 `update-mime-database` **工具**，不需要同线版本。
制品仓有 `shared-mime-info/2.5.1`（OS/arch/compiler 与本 profile 匹配）→
`build_requirements` 里 `tool_requires("shared-mime-info/2.5.1")` 即可，源码零改动：

```
-- Found SharedMimeInfo: .../shared-mime-info/2.5.1/bin/update-mime-database (found version "2.5")
package(): Packaged 1 '.cache' file: mime.cache
```

`mime.cache` 的产出是 `update_xdg_mimetypes()` 真跑过的证据。

> 复核说明：早期曾计划也给 mime 打「可选化」补丁；实测确认 2.5.1 有匹配二进制后改为
> tool_requires，补丁已从 `conandata.yml` 撤除，避免多维护一份无必要的补丁。

## 3. 二进制可移植性（E537 口径）

`package_info`：`cmake_find_mode=none`、`bindirs=["bin"]`。

- **DT_NEEDED 一律裸名**：构建期出现的路径型 DT_NEEDED 采用**原地 d_val 重定向**
  （`DT_NEEDED` 槽里直接改写字符串指针指向新串，不新增动态条目），不使用 `patchelf`
  ——`patchelf` 会因重排动态段触发 E537 检查失败。
- 实测（`llvm-readelf -d`）：`bin/palapeli`、`lib/libpala.so`、
  `lib/plugins/kf6/thumbcreator/palathumbcreator.so`、
  `lib/plugins/palapelislicers/palapeli_*.so` **路径型 DT_NEEDED 数量均为 0**。
- **SONAME 缺失属平台行为，不是本包缺陷**：OHOS 构建链下 CMake 不会给共享库加版本
  号/SONAME。最小复现（普通 `add_library(SHARED)` + `VERSION`/`SOVERSION`，同一
  cmake 4.1.2 + OHOS clang 组合）也只产出 `libfoo.so`，链接命令里没有 `-Wl,-soname`，
  与 palapeli 无关。因此 `libpala.so` 无 SONAME、无 `.so.0` 版本化文件名属预期。
  对第三方消费真正关键的是导出符号完整，实测 `libpala.so` 导出
  `Pala::Slicer::process` 与 `Pala::SlicerJob::pieces`（`llvm-nm -D --defined-only`），
  `test_palapeli.sh` 因此改为断言导出符号而不是 SONAME。
- 签名：`binary-sign-tool` 对包内 ELF 统一签名。

## 4. 产物清单（实测）

```
bin/palapeli
lib/libpala.so
lib/plugins/kf6/thumbcreator/palathumbcreator.so
lib/plugins/palapelislicers/palapeli_rectslicer.so
lib/plugins/palapelislicers/palapeli_jigsawslicer.so
lib/plugins/palapelislicers/palapeli_goldbergslicer.so
share/applications/org.kde.palapeli.desktop
share/mime/packages/palapeli-mimetypes.xml
share/mime/mime.cache
include/Pala/... + lib/cmake/Pala/（PalaConfig / PalaConfigVersion / PalaTargets）
share/palapeli/（templates、pics）
etc/xdg/pala.conf、etc/xdg/palapelirc、etc/xdg/palapeli_slicers.rc（KConfig 导出）
```

## 5. 测试

上游 **无测试套件**（无 `autotests/`、无 `tests/`，全树无 `add_test` / `enable_testing` /
`ECMAddTests`），故按其鸿蒙口径补充**鸿蒙独有真实消费者测试**：

1. `test_package/consumer.cpp`：`find_package(Pala)` → 链接上游导出的 `Pala` 目标
   （上游 `install(EXPORT PalaTargets)` **没有 NAMESPACE**，导入目标就叫 `Pala`，
   不是 `Pala::Pala`，测试对两种写法都兼容）；`QPluginLoader` 加载三个已安装切片器插件，
   因插件是 `KPluginFactory` 插件（`K_PLUGIN_CLASS_WITH_JSON`），按上游
   `src/creator/slicerselector.cpp` 的同一路径用 `factory->create<Pala::Slicer>()`
   实例化（`loader.instance()` 返回工厂对象，直接 `qobject_cast<Pala::Slicer*>` 会失败）；
   用插件 `propertyList()` 默认值构造 `Pala::SlicerJob`（400×300 图）并设置
   `slicer->modes()` 的第一个模式（goldberg 无 mode 会直接 `return false`），调用公开包装
   `Slicer::process()` **真跑切图算法**；断言 `pieces()` 非空、属性键非空且不重复；
   矩形切片器额外断言「所有碎片等尺寸、面积之和 == 片数×单片面积、覆盖率 ≥ 90%」——
   上游 `slicer-rect.cpp` 的 `x == xCount` 判定永远不成立（应为 `xCount - 1`），
   整格取整的余数不会补给任何一片，故不能断言「面积之和 == 输入面积」。
2. `test_package/test_palapeli.sh`：产物清单 + ELF 断言（无路径型 DT_NEEDED、
   `bin/palapeli` 直接依赖 `libKDEGames6.so`、`libpala.so` 导出
   `Slicer::process` / `SlicerJob::pieces`、`mime.cache` 非空）。

`bin/palapeli` 本体不在 CI 中执行：它是 KXmlGui GUI 程序，启动即需 QPA 平台插件与会话环境，
无桌面会话的构建机上运行只会得到平台插件缺失的假失败；其可加载性由 ELF 与插件 ABI 断言覆盖。

## 6. 限制与已知问题

- **不交付手册与文档翻译**（`doc/` 子目录整体裁掉）。需要手册的交付物应在制品仓补发
  与闭包同线的 `kdoctools`。
- **`kio/6.14.0` 是跨线依赖**：palapeli 用到的 `KIO::ThumbnailCreator` 在两个版本间无
  ABI 差异，实测通过；但若上游后续使用 6.18+ 新增的 KIO API，需先补 `kio` 6.18 线二进制。
- **无桌面会话**：`KDBusService`（单实例）、`KNotification`（缩略图生成提示）在无会话
  环境下不会真正生效；程序不会因此崩溃（KDBusAddons 在无 session bus 时退化为独立实例），
  但单实例语义缺失。
- 缩略图插件 `palathumbcreator` 依赖 KIO 的 ThumbnailCreator 与 QImage 解码，
  在文件管理器中真正出图依赖上游会话；本包只保证插件可加载、类型正确。
- 黄金分割切片器对有解的图才有意义，测试只断言 `process()` 成功与产出非空，
  不断言具体片数（其模式与预设依赖参数组合）。
