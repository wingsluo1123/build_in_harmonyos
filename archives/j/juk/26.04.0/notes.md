# juk 26.04.0 适配笔记

KDE Gear 26.04 音乐播放器（application，非纯库）。CMake + ECM + KF6 + Qt6。

## 编译环境

- 构建系统: cmake（CMake 4.1.2 + ecm/6.26.0）
- 编译日期: 2026-10-02
- 编译器: clang / clang++ 15.0.4（OHOS PC aarch64，os.version 6.0，libc++，C++20）
- Profile: `ci/conan/profiles/ohos-aarch64`（host）+ `default`（build）
- 状态: built（本地 `conan create` 全绿；制品上传由合并后的 release 流水线完成）

## 编译步骤

```bash
cd archives/j/juk/26.04.0
conan create . --build=missing -pr:h ci/conan/profiles/ohos-aarch64 -pr:b default
```

流程：源码获取（strip_root）→ 应用 `patches/0001`/`0002` → `cmake.configure`（generate() 注入
Taglib/ZLIB 目标与 KF6 路径）→ `cmake.build`（内含上游 `tagguessertest`）→ `cmake.install` →
`test_package`（真实 CMake 消费方 + 运行 `bin/juk --version` + `readelf` NEEDED 断言）。

## 依赖版本矩阵（实测，2026-10-02）

| 依赖 | 版本 | 选择理由 |
|---|---|---|
| qtbase / qtsvg / qtmultimedia | 6.11.1 | 制品仓内 KF6 配方统一构建所依据的参考版本，避免引入第二套 qtbase 生态 |
| kio | **6.14.0** | juk 链接 `KF6::KIOWidgets`/`KF6::KIOFileWidgets`；6.26.0 是 `KIOCORE_ONLY`，不含 widgets |
| kconfigwidgets/kdbusaddons/kglobalaccel/knotifications/ktextwidgets/kwallet/kxmlgui | 6.18.0 | 上述模块在制品仓**没有 6.26 配方**，只能取 6.18 线 |
| kdoctools | 6.19.0 | 制品仓仅发布 6.19.0 |
| kstatusnotifieritem | 6.26.0 | 制品仓仅发布 6.26.0（其 CMake 精确要求 KF6WindowSystem 6.26.0） |
| kwindowsystem | **6.26.0** | 同时满足 kio/6.14.0（钉 6.14.0）与 kstatusnotifieritem/6.26.0（精确 6.26.0）的版本闸 |
| karchive | 6.19.0 | `kiconthemes/6.18.0` 要求 karchive/6.19.0 |
| 6.18 线共享基底（kauth/kbookmarks/kcodecs/kcolorscheme/kcompletion/kconfig/kcoreaddons/kcrash/kguiaddons/ki18n/kiconthemes/kitemviews/kjobwidgets/kservice/kwidgetsaddons/solid） | 6.18.0 | 由 kio/6.14.0 拉入但为 6.14 线；6.14 线不完整（kglobalaccel 无 6.14 配方），故整体 `override=True` 统一到 6.18 |
| zlib | **1.3.2** | 1.3.1 的静态 binary 未带 `-fPIC`（见下表），1.3.2 为 PIC |
| taglib | 2.3 | juk `find_package(Taglib 1.6 REQUIRED)` |
| ecm (tool_requires) | 6.26.0 | ECMAddTests 等 CMake 模块 |

KF6 同主版本号内保持 ABI 兼容，因此 6.14/6.18/6.19/6.26 混钉（每个模块取制品仓真能交付的版本）是安全的。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `KF6KIOWidgetsConfig.cmake` 缺失 | `kio/6.26.0` 配方是 `KIOCORE_ONLY`，不构建 widgets | 改钉 `kio/6.14.0`（全量：KIOCore + KIOWidgets + KIOFileWidgets） |
| 2 | KF6 模块版本无法统一 | 制品仓模块覆盖不均（kglobalaccel 无 6.14、kconfigwidgets 类无 6.26） | 逐模块取可用版本 + `_KF6_PINS` `override=True` 统一共享基底到 6.18 |
| 3 | `kstatusnotifieritem/6.26.0` 版本闸不满足 | 其 CMake 精确要求 KF6WindowSystem 6.26.0 | 统一钉 `kwindowsystem/6.26.0` |
| 4 | 链接 `libKF6DocTools.so` 报 `relocation R_AARCH64_ADR_PREL_PG_HI21 ... can not be used when making a shared object` | 制品仓 `zlib/1.3.1` 静态 binary 由 clang 构建且未加 `-fPIC`（zlib configure 只对 gcc 自动加） | 统一钉 `zlib/1.3.2`（PIC 版） |
| 5 | `po-uk-docs-juk-index-cache-bz2` 目标失败 | OHOS 的 `kdoctools` 不带 DocBook 4.5 DTD，handbook 链无法生成 | `patches/0001` 裁掉 `add_subdirectory( doc )` 与 `kdoctools_install(po)`（po 翻译在 `KF_SKIP_PO_PROCESSING=ON` 下本已不做） |
| 6 | `systemtray.cpp` 编译失败 | 无条件 `#include <KX11Extras>` 且调用 `KX11Extras::compositingActive()`，OHOS 无 X11 | `patches/0002` 用 `__has_include(<KX11Extras>)` 守卫头与调用点（不改 CMake 判定） |
| 7 | `find_package(Taglib)` 后目标 `Taglib::Taglib` 不存在 | conan `taglib/2.3` 导出的是 `TagLib::tag`（`TagLib::TagLib` 别名） | `generate()` 注入 wrapper：`Taglib::Taglib` → `TagLib::tag` 别名（kfilemetadata 6.28.0 范式，不改上游 CMake） |
| 8 | `ZLIB::ZLIB` 目标未定义 | taglib 目标的 INTERFACE_LINK_LIBRARIES 引用参考名 `ZLIB::ZLIB` | `generate()` 注入 `UNKNOWN IMPORTED` 的 `ZLIB::ZLIB` 目标 |
| 9 | `test_package` 运行 `juk --version` 报 `Error loading shared library ...`（exit 127） | 制品仓二进制带有**构建机绝对路径** `DT_NEEDED`（E537），且 KF6 的 `$ORIGIN` 相对项在 scratch 目录不成立 | test_package 按 alligator 范式 `_materialize_abs_deps()` 物化死绝对路径为符号链接 + scratch 链接农场（`../bin`、`../../bin` 可达 KF6 全量 `.so`）+ CWD 落在 scratch |
| 10 | 运行时 loader 找不到 Qt/KF6 库 | OHOS loader 无法处理含空白的 host `LD_LIBRARY_PATH` | `_runtime_env()` 显式列出 `/system/lib64`、`/system/lib64/platformsdk`、`/system/lib64/ndk`，并设 `QT_QPA_PLATFORM=offscreen`（无显示环境） |

## 源码修改

| 补丁 | 修改内容 | 理由 |
|---|---|---|
| `patches/0001-CMakeLists.txt.patch` | 注释掉 `add_subdirectory( doc )`（L53）与 `kdoctools_install(po)`（L217） | OHOS `kdoctools` 缺 DocBook 4.5 DTD，handbook 链无法生成；纯文档链，不影响程序功能 |
| `patches/0002-systemtray.cpp.patch` | `#include <KX11Extras>`（L26）改为 `__has_include` 条件包含；L287-288 的 X11 合成查询置于同一守卫内 | OHOS 无 X11 专用 `KX11Extras`；系统托盘在非 X11 下有既有的回退路径 |

两补丁均由源码树直接编辑后经 `refresh-patch --auto` 生成（无平台宏 `__OHOS__`，0002 用标准 `__has_include` 守卫）。

## R51 上游测试申报表

| 项目 | 结果 |
|---|---|
| 上游测试入口 | `include(ECMAddTests)`（CMakeLists.txt）+ `ecm_add_test(... tagguessertest.cpp ... Qt6::Test KF6::ConfigCore KF6::CoreAddons TEST_NAME tagguessertest)` |
| 测试源文件清点 | 1 个（`tests/tagguessertest.cpp`） |
| ctest 注册数 | 1（`tagguessertest`） |
| 实际运行 | 是：`BUILD_TESTING=ON`，随 `conan create` 的 build() 执行 ctest |
| 实测通过 | **1/1 Passed（100%）** |
| 补充用例 | `test_package/`：真实 CMake 消费方（`find_package(KF6/Qt6)` 配置层验证）+ 运行 `bin/juk --version` + `readelf -d` 断言 `libKF6KIOWidgets`/`libKF6KIOCore`/`libKF6KIOFileWidgets` 出现在 NEEDED（鸿蒙侧补充） |

## 验证结果

```bash
# 主流程
conan create . --build=missing -pr:h ci/conan/profiles/ohos-aarch64 -pr:b default
# -> Package created（41/41 依赖 Already installed），上游 tagguessertest 1/1 Passed

# test_package（探针复跑）
conan test test_package juk/26.04.0 -pr:h ci/conan/profiles/ohos-aarch64 -pr:b default
# -> rc=0：bin/juk --version 正常输出；三条 readelf NEEDED 断言全部通过
```

关/开双向证据见 `reports/kf6-matrix-gate-check.md` §6（每一项修复都有失败态与修复态的实测记录）。

## 交付物

| 路径 | 说明 |
|---|---|
| `conanfile.py` | 配方（依赖钉版 + `generate()` 目标修补 + 运行时环境） |
| `conandata.yml` | 官方源 + sha256 + 两条补丁登记 |
| `patches/0001`、`patches/0002` | 文档链裁剪 / X11 守卫 |
| `test_package/` | 真实消费方 + 运行断言（含 E537 物化） |
| `commands.json` | 软件级命令行工具声明（R38：产物含 `bin/juk`） |
| `reports/kf6-matrix-gate-check.sh/.md` | 知识库四件套（检测脚本 + 使用说明），配套草稿 `E545-draft-2301` |

## 注意事项

1. **不要用 `conan list` 判断 binary 是否存在**（R35）：`kio/6.14.0` 的配方存在且可用，但搜索 API 对 binary 返回不完整；判定一律用 `conan download <pkg>/<ver> -r=ohpcd --only-recipe`。
2. **kio 版本是硬约束**：本仓库 `kio/6.26.0` 为 `KIOCORE_ONLY`，任何需要 `KF6::KIOWidgets` 的消费方都必须钉 6.14.0。
3. **zlib 必须 PIC**：1.3.1 的静态 binary 非 PIC，会以 `relocation R_AARCH64_...` 形式在**链接期**才暴露；下游配方建议直接钉 `zlib/1.3.2`。
4. **制品仓二进制的 `DT_NEEDED` 带构建机绝对路径**（E537）：`test_package` 必须在运行时物化这些路径，不能只依赖 `LD_LIBRARY_PATH`。
5. 上游 `BUILD_TESTING=ON` 会跑 `tagguessertest`，需要 `Qt6::Test`；CI 环境无显示，测试与 smoke run 均走 `QT_QPA_PLATFORM=offscreen`。
6. **R40 适配完整性（需人工确认）**：juk 属 UI（Qt Widgets）+ 多媒体（qtmultimedia 播放）应用，本仓库的自动化验证只到「可构建 + `bin/juk --version` + `DT_NEEDED` 断言」，**不包含**设备侧窗口系统、输入事件与音频播放的功能性验证。平台适配实质改动为两处（文档链裁剪 `0001`、X11 专用 `KX11Extras` 的 `__has_include` 守卫 `0002`），无 stub / `return 0` 式伪造；GUI/播放链路的上机验证建议在真机验收阶段补充。
---

**编译结束**: 2026-10-02 23:29
**最终状态**: built
