# libadwaita 1.2.0.1 HarmonyOS PC 适配笔记

## 修复范围

- Conan 版本：`libadwaita/1.2.0.1`
- 上游源码：GNOME libadwaita `1.2.0`
- 官方缺陷记录：OpenHarmonyPCDeveloper/build_in_harmonyos Issue #4143
- 构建环境：HarmonyOS PC aarch64、clang 15.0.4、Conan 2.29.1、Meson
- 构建日期：2026-10-16
- 状态：built
- 支持范围：HarmonyOS PC、共享库（`shared=True`）

`1.2.0.1` 是已发布 `libadwaita/1.2.0` 的配方修复版，未修改上游 API、ABI
或源码版本。旧制品的依赖图同时装入了正常共享 GLib/GObject 与
`graphene/1.10.8` 所带的静态 `glib2`，使进程内存在两个 GObject 类型注册表。
本版改用 `graphene/1.10.8.1`，并把整张图统一到共享
`glib/2.84.0.2`。

该修复版本只发布并审计 HarmonyOS PC 共享制品。配方通过 `validate()` 明确拒绝
静态或非 OHOS 配置，避免把未经本任务验证的组合误报为受支持。

## 源码与构建

源码 URL：
`https://gitlab.gnome.org/GNOME/libadwaita/-/archive/1.2.0/libadwaita-1.2.0.tar.gz`

SHA-256：
`ab0030434af58ae0a01e6979acc56f7e88cc43ca5a2bbd53da9a3b7707403687`

Meson 选项：

- `introspection=disabled`
- `vapi=false`
- `gtk_doc=false`
- `examples=false`
- `tests=true`

关闭项均为开发文档、语言绑定或示例；核心 C 库、资源、翻译和完整上游测试
均保留。源码无需补丁，HarmonyOS 适配全部在 Conan 配方的工具链、依赖图和
测试环境中完成。

## 依赖闭包

| 依赖 | 版本 | 用途 |
|---|---:|---|
| gtk4 | 4.22.4 | 公共 GTK4 API 与 Broadway 后端 |
| glib | 2.84.0.2 (`shared=True`) | 唯一 GLib/GObject/GIO 运行时 |
| graphene | 1.10.8.1 | 避免引入第二套静态 GLib/GObject |
| fribidi | 1.0.16 | bidi 实现 |
| gettext | 0.22.5.1 | 提供 gdk-pixbuf 的 `DT_NEEDED: libintl.so.8` |
| zlib | 1.3.1.1 | 统一 GTK4 传递图版本 |
| fontconfig | 2.18.1.1 | 统一 GTK4 传递图版本与测试字体配置 |
| sassc（tool_requires） | 3.6.2 | 编译 Adwaita stylesheet |

`gettext/0.22.5.1` 的 OHOS 包实际不含其配方所声明的 `libasprintf`；本配方将
该依赖的消费者视图收窄到真实存在且闭包所需的 `libintl`，避免向消费者生成
无效 `-lasprintf`，同时保留 `libintl.so.8` 运行时传播。

Conan 以根配方的直接依赖约束为最高优先级。若下游自身也直接依赖
`gtk4/4.22.4`，下游配方必须与本包保持同一修复图，即显式选择
`graphene/1.10.8.1` 和共享 `glib/2.84.0.2`；否则根配方对旧
`graphene/1.10.8` 的精确约束会覆盖传递依赖的选择。实际下游验证使用的正是
该一致依赖图。

## 适配要点

1. 为 Meson native file 写入绝对路径 `ar`/`ranlib`，避免目标机 PATH 探测失败。
2. 补齐 PkgConfigDeps 生成的 GLib/GIO 工具变量，供
   `gnome.compile_resources()` 使用。
3. 修复 GTK4 生成的 `gtk4.pc` 中无效的 `Requires: none`，替换为真实的
   `graphene-gobject-1.0`。
4. 为 fribidi 的 `.pc` 补上 `include/fribidi`。
5. 对构建期 GLib 工具、GTK Broadway 服务和安装后的共享库执行 HarmonyOS
   自签名；只签真实 SONAME 文件，保留开发链接为符号链接。
6. 使用 GTK Broadway 后端在目标机真实运行全部 GUI 单元测试，不跳过显示相关
   测试。

## 上游测试台账

上游 `tests/meson.build` 声明并注册 37 个独立测试程序，`tests=true` 后全部生成：

1. test-about-window
2. test-action-row
3. test-animation
4. test-animation-target
5. test-application-window
6. test-avatar
7. test-bin
8. test-button-content
9. test-carousel
10. test-carousel-indicator-dots
11. test-carousel-indicator-lines
12. test-combo-row
13. test-easing
14. test-entry-row
15. test-expander-row
16. test-flap
17. test-header-bar
18. test-leaflet
19. test-message-dialog
20. test-password-entry-row
21. test-preferences-group
22. test-preferences-page
23. test-preferences-row
24. test-preferences-window
25. test-split-button
26. test-squeezer
27. test-status-page
28. test-style-manager
29. test-tab-bar
30. test-tab-view
31. test-timed-animation
32. test-toast
33. test-toast-overlay
34. test-view-switcher
35. test-view-switcher-bar
36. test-window
37. test-window-title

真机命令：`meson test -C build-release --print-errorlogs`

- 上游程序口径：37/37 通过，0 失败，0 跳过。
- GLib TAP 子测试口径：208/208 `ok`，0 `not ok`。
- 测试后端：签名后的 `gtk4-broadwayd`，`GDK_BACKEND=broadway`。

## 新增 HarmonyOS 消费者测试

`test_package/test.c` 从安装包的公开头文件和 Conan pkg-config 元数据编译链接，
并在 Broadway 上真实运行。共 8 项断言：

- 3 项运行时版本 API 与编译期宏一致；
- 编译期版本为 1.2.0；
- `ADW_CHECK_VERSION(1,2,0)` 为真；
- 初始化前 `adw_is_initialized()` 为假；
- `adw_init()` 后初始化状态为真；
- `adw_bin_new()` 创建真实 `AdwBin` 实例。

结果：1/1 消费者程序通过，8/8 断言通过。初始化和对象创建专门覆盖旧制品
双 GObject 注册表问题。

## 实际下游验证

使用 Zrythm `libpanel-detach` 的 `1.6.0-1-for-zrythm` 源码，令其直接依赖
`libadwaita/1.2.0.1`，并选择上述一致的 GLib/Graphene 图后，在同一台
HarmonyOS PC 上完成构建。其两个上游 GUI 程序在签名后的 GTK Broadway
后端真实执行：

- `test-dock`：通过（退出码 0）；
- `test-paned`：通过（退出码 0）。

结果为 2/2。验证只对该下游的测试自动退出逻辑进行适配，并移除了其测试程序
中两项在同版本 `PanelWidget` 上不存在的陈旧属性赋值；未修改
`libadwaita` 源码或 API。该验证证明真实 GTK/libadwaita 消费者可以在修复后的
单一 GObject 运行时中完成窗口、面板和 detachable-window 路径。

## 制品审计

- ELF：AArch64 HarmonyOS 共享对象。
- SONAME：`libadwaita-1.so.0`。
- 动态依赖明确包含共享 `libglib-2.0.so.0`、`libgobject-2.0.so.0`、
  `libgio-2.0.so.0`、`libgtk-4.so.1`。
- 不再定义 `g_object_new`、`g_type_register_static`、`g_malloc` 等核心 GLib/GObject
  符号。
- 无 RPATH/RUNPATH，无 Conan 构建缓存绝对路径。
- `.codesign` 存在；`libadwaita-1.so -> libadwaita-1.so.0` 链接完整。
- 安装头文件、翻译资源和 `libadwaita-1.pc` 完整。

## 交付物

| 文件 | 说明 |
|---|---|
| `conanfile.py` | Conan 2 / Meson 配方、依赖图修复、测试与制品审计 |
| `conandata.yml` | 官方源码 URL 与 SHA-256 |
| `manifest.yaml` | 版本构建元数据 |
| `test_package/` | HarmonyOS 安装包消费者测试 |
| `reports/test-report.md` | 可复核测试与制品审计报告 |

本包为库，不提供 CLI，因此不需要 `commands.json`。本次复用仓库已有的 Meson、
PkgConfigDeps、Broadway 与 ELF 重签方案，不新增知识库条目。
