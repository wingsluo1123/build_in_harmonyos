# libfm 1.4.0 适配笔记

## 编译环境
- 构建系统: CMake（手写 CMakeLists.txt，源码 tarball 不含 CMake 支持）
- 编译日期: 2026-10-15
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码：GitHub auto-archive `libfm-1.4.0.tar.gz`
   - sha256: 7d7b616411992389a4b7f35796109d605f30bc2ceab84d4081d1665254ebbf82
2. 生成 `fm-version.h`：由 `src/fm-version.h.in` 通过 CMake `configure_file()` 生成
3. 编译 `libfm.so`（完整核心库）+ `libfm-extra.so`（正式流程经 conan create，CMakeLists.txt 由 export_sources 复制进源码树，GLIB_ROOT/DEPS_ROOTS 由 conanfile.py generate() 注入依赖包路径）：
   ```bash
   conan create archives/l/libfm/1.4.0 --build=missing -pr harmonyos
   ```
   - `fm` target：fm.c + glib-compat.c + base/(23 文件) + job/(9 文件) + extra/fm-xml-file.c + 预生成 fm-marshal.c（对应上游 src/Makefile.am libfm_SOURCES，禁用 udisks/dbus/exif/old-actions/modules/GTK 部分）
   - `fm-extra` target：上游等价的独立 FmXmlFile 子库（soname libfm-extra.so.4）
   - `fm-marshal.h/.c` 用 glib-genmarshal 预生成后放配方 `generated/`（避免 CI 工具依赖）；`generated/config.h` 为手写最小集（宏与上游 autotools 等价，可选特性全关）
4. 产物：`lib/libfm.so.4.0.2`（SONAME libfm.so.4）、`lib/libfm-extra.so.4.1.3`、`include/libfm-4/`（fm.h、fm-seal.h、base/*.h、job/*.h、fm-marshal.h、fm-extra.h、fm-xml-file.h、fm-version.h，平铺布局与上游 libfm.pc 一致）、`lib/pkgconfig/{libfm.pc,libfm-extra.pc}`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autoreconf 失败（缺 pkg.m4/intltool.m4/gettext.m4/gtk-doc.m4） | GitHub auto-archive 不含生成的 configure 脚本和 m4 宏 | 放弃 autotools，手写 CMakeLists.txt |
| 2 | configure 即使补全 macros 也失败（PKG_CHECK_MODULES 不展开） | safe-bin 劫持 + 沙箱环境 PKG_CONFIG_PATH 问题 | CMake 绕过 |
| 3 | `glib-object.h` 找不到 | 头文件在 conan 缓存包路径而非系统目录 | conanfile generate() 注入 GLIB_ROOT/DEPS_ROOTS |
| 4 | `GETTEXT_PACKAGE` 未定义 | `fm-xml-file.c` 包含 `glib/gi18n-lib.h` 使用 `_()` 宏需此定义 | target_compile_definitions 注入 |
| 5 | SOVERSION 不生效 | HarmonyOS 平台 CMake 忽略 VERSION/SOVERSION 属性 | `target_link_options(... "LINKER:-soname,libfm.so.4")` 显式指定 |
| 6 | **E529: dlopen 运行时符号未找到** | glib 静态链接引入 libffi/libintl/libpcre2-8/libz 传递依赖；`fm-xml-file.c` 的 `g_dgettext` 需 `g_libintl_bindtextdomain` | 显式 requires pcre2/zlib/menu-cache + 链接全部传递依赖 |
| **7** | **fm.h 平铺 include 布局** | 上游 `fm.h` 用 `#include "fm-app-info.h"`（无 base/ 前缀），libfm.pc includedir 为单目录 | install 全部头文件平铺到 `include/libfm-4/`（与上游 LIBFM_INCLUDES 一致），并补漏的 `src/fm-seal.h` |
| **8** | **fm-marshal.h/.c、config.h 为生成文件** | tarball 无 autotools 产物；fm-marshal 由 glib-genmarshal 生成 | 用 glib-genmarshal 预生成放配方 `generated/`；手写最小 config.h |
| **9** | **conan zlib 静态库非 PIC，无法链入 .so（全局符号模式）** | conan zlib 包 .a 按 -fno-PIC 编译；lld 拒绝导出符号的非 PIC 重定位 `R_AARCH64_ADR_PREL_PG_HI21` | `--exclude-libs,libz.a:libpcre2-8.a:libffi.a:libintl.a:libmenu-cache.a` 选择性隐藏（这些库无 GType 跨界需求）；glib/gobject/gio/gthread/gmodule 保持导出 |
| **10** | **双 glib 实例分裂（GObject 信号失效）** | 若 libfm.so 用 `--exclude-libs,ALL` 藏 glib、而消费者又自己链一份静态 glib，则两个 GType 系统互不相认：上游 demo 报 `signal 'files-added' is invalid for instance of type '(null)'` 后挂死 | fm target 不藏 glib 系库（符号全局导出）；消费者只链 `-lfm`，从 so 获得唯一 glib 实例。实证：修复后上游 demo 正常 finished |

## 源码修改

- 无补丁文件（patches 目录为空）
- 手写 CMakeLists.txt + generated/{config.h,fm-marshal.h,fm-marshal.c} 从配方目录复制进源码树

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| glib | 2.88.0 | GObject/GIO/GThread/GModule（核心库直接依赖） |
| pcre2 | 10.45 | glib 传递依赖 (libpcre2-8，静态藏入) |
| zlib | 1.3.1 | glib 传递依赖 (libz，静态藏入) |
| menu-cache | 1.1.0 | `src/base/fm-file-info.c:41` 无条件 `#include <menu-cache.h>`（静态藏入） |
| (隐式) | — | libffi (glib), libintl (glib i18n)（静态藏入） |

## 验证结果

```bash
# conan create 成功（完整日志 reports/conan-create.log，388 行）
RC=0

# 上游/鸿蒙测试真实执行（日志 reports/upstream-tests-run.log，交叉编译 can_run=False 后目标设备手动执行）
$ LD_LIBRARY_PATH=<包lib> ./test-fm-path
ok 1 /FmPath/new_child_len
ok 2 /FmPath/path_parsing
ok 3 /FmPath/uri_parsing
ok 4 /FmPath/predefined_paths
RC=0

$ LD_LIBRARY_PATH=<包lib> ./file-search-cli-demo
URI: search:/?recursive=1&show_hidden=0
finished
RC=0

$ LD_LIBRARY_PATH=<包lib> ./test_libfm_extra_consumer
PASS: libfm-extra.so loaded and symbols resolved
RC=0

# SONAME 验证
$ readelf -d libfm.so.4.0.2 | grep SONAME
 0x000000000000000e (SONAME)    Library soname: [libfm.so.4]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libfm.so.4.0.2 | ~4.2MB | 完整核心库（SONAME: libfm.so.4，base+job+extra，无 GTK 部分） |
| lib/libfm-extra.so.4.1.3 | ~55KB | 独立 FmXmlFile 子库（SONAME: libfm-extra.so.4） |
| include/libfm-4/ | — | fm.h、fm-seal.h、base/*.h、job/*.h、fm-marshal.h、fm-extra.h、fm-xml-file.h、fm-version.h（平铺） |
| lib/pkgconfig/libfm.pc | — | 核心库 pkg-config |
| lib/pkgconfig/libfm-extra.pc | — | 子库 pkg-config |

## 上游测试清点（R51 三步法：清点→实跑→回填）

1. **清点**（2026-10-15 二次核对，含 PR 审查指出的少报修正）：上游 tarball 内测试/demo 程序共 **4 个**：
   - `src/tests/test-fm-path.c` — fm_path 单元测试（src/tests/Makefile.am:15 noinst_PROGRAMS，TEST_PROGS）
   - `src/tests/libfm-file-search-cli-demo.c` — 文件搜索 CLI demo（src/tests/Makefile.am:24-25）
   - `src/demo/libfm-demo.c` — GTK GUI demo（:22-26 `#include <gtk/gtk.h>`、`fm-gtk.h`）
   - `src/gtk/exo/test.c` — GTK 图标视图测试（:1 `#include <gtk/gtk.h>`，gtk/exo 属 libfm-gtk 源域）
   注：首轮清点仅覆盖 `src/tests/` 目录（2 个）导致少报，已修正为全树清点 4 个。
2. **实跑**（日志：`reports/upstream-tests-run.log`）：
   - ✅ `test-fm-path`：源码原样拷入 test_package 编译、链接包产物 `-lfm`，**真实执行 4 个子用例全 ok，RC=0**
   - ✅ `libfm-file-search-cli-demo`：同上，**真实执行完成（finished），RC=0**
   - ❌ `libfm-demo`（src/demo/）：**不可执行**——证据链：文件头 22-26 行 `#include <gtk/gtk.h>` + `#include "fm-gtk.h"`；`fm-gtk.h` 属 libfm-gtk（GTK3 依赖域）；上游构建系统在非 GTK 构建下不编译 src/demo；PC 鸿蒙无 GTK3 运行栈，GTK 移植超出本包范围（rule2/3 减少说明）
   - ❌ `gtk/exo/test.c`：**不可执行**——证据链：文件第 1 行 `#include <gtk/gtk.h>`，依赖 exo-icon-view（libfm-gtk 内嵌组件）；gtk/ 目录整体属 libfm-gtk 构建域，非 GTK 构建不编译
3. **回填**：test_package 提供 1 个 HarmonyOS 特有运行时测试（非断言式）：
   - 链接期依赖：直接调用 `fm_xml_file_get_type()`（二进制 NEEDED 必含 `libfm-extra.so.4`，满足 R34 L1e 负向测试）
   - 运行时验证：`dlopen("libfm-extra.so.4", RTLD_NOW)` 共享库闭包加载 + `dlsym` 逐个解析 4 个 `fm_xml_file_*` 符号
   - 实跑 PASS（日志：`reports/upstream-tests-run.log` 第 3 节）

## 注意事项

- 本包包含**完整 libfm 核心**（base+job+extra）+ 独立 libfm-extra 子库，**不含 libfm-gtk**（GTK3 依赖）与 modules/udisks/dbus/exif 可选特性
- libfm.so 链接时 glib/gobject/gio/gthread/gmodule 符号保持全局导出（消费者共享同一 glib 实例）；zlib/pcre2/ffi/intl/menu-cache 静态藏入
- fm-xml-file.c 中 `GETTEXT_PACKAGE` 宏定义不影响实际翻译（无 .mo 文件），仅消除编译错误
- 上游 demo `libfm-demo`/`gtk/exo/test.c` 需 GTK3，PC 鸿蒙无 GTK 栈，不在本包范围
---

**编译结束**: 2026-10-15 21:25
**最终状态**: published
