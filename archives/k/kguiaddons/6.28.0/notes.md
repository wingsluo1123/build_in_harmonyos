# kguiaddons 6.28.0 适配笔记

## 版本概览

| 项目 | 6.26.0.1（已合入） | 6.28.0（本版） |
|---|---|---|
| 上游源码 URL / SHA256 | kguiaddons-6.26.0.tar.xz / `8375342f…3172` | kguiaddons-6.28.0.tar.xz / `f46aeca8…8432`（官方 URL + NJU/阿里云镜像兜底，sha256 钉同一 tarball） |
| patches | 无 | 无（`patches: {}`） |
| requires / tool_requires | qtbase/6.11.1、ecm/6.26.0 | qtbase/6.11.1、**extra-cmake-modules/6.29.0**（上游 6.28.0 要求 ECM ≥ 6.28.0） |
| 版本语义 | 适配修复后缀（DT_SONAME 注入） | 上游版本刷新（仓内首次适配 6.28.0，无后缀，R37） |

**上游 6.26 → 6.28 源码差异**（小）：ECM 最低要求提升至 6.28.0；`src/CMakeLists.txt` 新增
`qt_extract_metatypes` 并把 metatypes 文件随包安装（新增一个安装目录，不影响链接与运行）；
`kurlhandler_p.cpp` 增加 iOS 专属守卫（OHOS 路径不变）。`autotests/` 用例集合与 6.26 完全相同。

## Adaptations

沿用 6.26.0.1 全部配方适配（逐项一致），仅版本号与 ECM 引用更新：

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单。
- `WITH_WAYLAND=OFF`、`WITH_X11=OFF`、`USE_DBUS=OFF`、`BUILD_GEO_SCHEME_HANDLER=OFF`、
  `BUILD_PYTHON_BINDINGS=OFF`：OHOS 无对应运行时/组件，关闭后零补丁通过。
- `BUILD_TESTING=ON`：在 conan create 内执行上游 CTest autotests（R51）。
- `generate()` 手工注入 `ECM_MODULE_PATH` 与 qtbase 的 `lib/cmake` 路径
  （qtbase 为 `cmake_find_mode=none`，CMakeDeps 不生成该路径）。
- DT_SONAME 链接标志注入（E383/E537）：`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` /
  `_C_FLAG = -Wl,-soname,`——OHOS CMake 无 `Platform/HarmonyOS` 模块，不注入则产物无
  `DT_SONAME`，消费者会把构建机绝对路径记入 `DT_NEEDED`。
- `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`（`tc.variables` + `tc.cache_variables` 双通道）：
  设备 HMDFS 用户卷全盘拒绝 `symlink(2)`（EPERM），CMake 的版本化 .so 链
  （`libKF6GuiAddons.so.6 -> .so.6.28.0`）无法落盘、`cmake_symlink_library` 后处理失败。
  关闭版本化链后仅落一个无版本真文件 `.so`，配合上一条 SONAME 标志仍得到裸名且可重定位的
  `DT_SONAME`，下游 `DT_NEEDED` 可解析（kitemodels/kitemviews/kcontacts 6.28.0 同批先例）。
- `tool_requires("extra-cmake-modules/6.29.0")`（制品仓已发布；kconfig/kholidays 6.28.0 同批先例）。

## 上游测试执行

`BUILD_TESTING=ON` 下上游 CTest 全量 8/8 通过（无排除项）：kwordwraptest、kcolorutilstest、
kiconutilstest、kcursorsavertest、kkeysequencerecordertest、kurlhandlertest、
kcountryflagemojiiconenginetest、kgeourihandlertest。

`100% tests passed, 0 tests failed out of 8`（真机实录）。

## 消费者测试（test_package，8 用例）

经已安装包公开 CamelCase 头文件（`<KColorUtils>`、`<KWordWrap>`、`<KIconUtils>`、
`<KCountryFlagEmojiIconEngine>`）链接真库运行，QGuiApplication 走 offscreen 平台、
HOME/XDG 隔离到 build 目录：

1. kcolorutils-lighten-darken —— lighten/darken 方向与有效性
2. kcolorutils-contrast-ratio —— black/white=21.0、同色=1.0（互序）
3. kcolorutils-mix-tint —— mix 混向、tint 0/1 边界与亮度方向
4. kcolorutils-hcy-roundtrip —— getHcy/hcyColor 往返（±2/255）
5. kcolorutils-overlay-colors —— 不透明覆盖恒等、透明覆盖保底
6. kwordwrap-truncation —— 窄矩形出省略号、宽矩形保留既有换行
7. kiconutils-addoverlay —— 叠加渲染含覆盖色像素；空覆盖（null QIcon）渲染零覆盖色像素、全底 1024 像素不透明
8. kcountryflagemojiiconengine —— 空码 isNull、AT/GB-SCT/LATAM 渲染非空

逐用例打印 `TEST PASS:`/`TEST FAIL:`，末行 `TEST SUMMARY: N passed, M failed`，任一失败退出码 1。

## Verification

- 官方门禁（设备真机、标准 `ci/conan/profiles/ohos-aarch64` profile）：
  `python3 scripts/ohc-run.py conan-verify kguiaddons 6.28.0` → G1/G0/G2 全过，rc=0。
  G2 即 `conan create … -pr:h=<ci>/ohos-aarch64 -pr:b=<同> --build=missing --user=ohpcd --channel=stable`，
  配方自带 `CMAKE_PLATFORM_NO_VERSIONED_SONAME` 处理设备 symlink 墙，不依赖任何设备本地 profile。
- 上游 CTest：8/8（`100% tests passed, 0 tests failed out of 8`）。
- 消费者用例：`TEST SUMMARY: 8 passed, 0 failed`。
- 平台 conan-verify（G1/G0/G2 门禁）报告见 `reports/conan-verify-report.md`。
- 本包为纯库（产物无 `bin/`），不产生新的命令行声明；软件级 `commands.json` 由 main 既有版本维护。
