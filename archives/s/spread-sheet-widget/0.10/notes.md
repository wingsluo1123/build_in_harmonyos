# spread-sheet-widget 0.10 适配笔记

## 编译环境

- 构建系统: autotools（tarball 自带 configure / Makefile.in / libtool，无需 autoreconf）
- 编译日期: 2026-10-18
- 编译器: clang（conan profile `tools.build:compiler_executables.c`，设备上为 `data/service/hnp/bin/clang`）
- 目标平台: HarmonyOS PC / aarch64-linux-ohos（armv8）
- 状态: built

## 本包是什么

`spread-sheet-widget`（GNU SSW）是 John Darrington 为 GNU PSPP 数据编辑器
开发的 GTK+ 3 表格控件库。它把"二维表格"拆成三层：`SswVirtualModel`
（GtkTreeModel 实现，行/列绑定到列表模型）、`SswSheetAxis`（行列尺寸与
滚动几何）和 `SswSheet`（2×2 个 `SswSheetSingle` 组成的视图，支持拆分、
框选、就地编辑、剪贴板粘贴）。发布物是纯库：`libspread-sheet-widget.so`
+ 4 个公开头 + `spread-sheet-widget.pc`；`doc/prog1`、`doc/prog2`、
`demo/demo` 是 noinst 示例，不进入安装。

## 上游审计（先于动手）

| 项 | 结论 | 证据 |
|----|------|------|
| 构建系统 | autotools，发布包已含 configure 与 Makefile.in | `configure.ac`、`Makefile.in` |
| 公共依赖 | `gtk+-3.0 >= 3.18.0`、`glib-2.0 >= 2.44` | `configure.ac` 的 `PKG_CHECK_MODULES([GTK3]/[GLIB2])` |
| 库 | `lib_LTLIBRARIES = libspread-sheet-widget.la`，链接带 `-no-undefined` | `Makefile.am:45-47` |
| 头文件 | `include_HEADERS = src/ssw-sheet.h src/ssw-sheet-axis.h src/ssw-virtual-model.h src/ssw-axis-model.h`，直接装到 `${includedir}` | `Makefile.am:65-69` |
| .pc | `spread-sheet-widget.pc`，`Requires: @gtk_dependency@ @glib_dependency@` | `spread-sheet-widget.pc.in` |
| BUILT_SOURCES | `src/ssw-marshaller.{c,h}` 由 `glib-genmarshal` 从 `src/marshall-list` 生成 | `Makefile.am:82-92` |
| info 文档 | `info_TEXINFOS = doc/spread-sheet-widget.texi`，tarball 自带 .info | `Makefile.am:30`、`doc/spread-sheet-widget.info` |
| 上游测试 | **无**：Makefile.am 没有 `TESTS`/`check_PROGRAMS`/`check_SCRIPTS`，tarball 没有 tests/ 目录，`make check` 为 automake no-op | `Makefile.am`、`grep -rn "check_PROGRAMS\|TESTS"` 无结果 |

## 编译步骤

```bash
# build() 内（R9）：configure + make
# configure 是脚本，HMDFS 拒绝直接 exec → 用 sh 显式解释
/system/bin/sh <build>/configure <conanbuild.conf 里的 configure_args>
# BUILD_SOURCES 预生成（glib-genmarshal 不能直接 exec）
python3 <glib>/bin/glib-genmarshal --body   --prefix=ssw_cclosure_marshal src/marshall-list > build/src/ssw-marshaller.c
python3 <glib>/bin/glib-genmarshal --header --prefix=ssw_cclosure_marshal src/marshall-list > build/src/ssw-marshaller.h
make -j1 INFO_DEPS= \
     MKDIR_P="/system/bin/mkdir -p" \
     INSTALL="/system/bin/install -c" INSTALL_PROGRAM="/system/bin/install -c" \
     INSTALL_SCRIPT="/system/bin/install -c" INSTALL_DATA="/system/bin/install -c -m 644"
# package()
make install DESTDIR=<package_folder> INFO_DEPS= <同上 INSTALL*/MKDIR_P 覆盖>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type` / 主机三元组异常 | config.guess (2022) 的 `case $UNAME_SYSTEM in` 只处理 Linux/GNU 等，HarmonyOS 落到 unknown | 在 case 开头插入 `HarmonyOS\|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;`（E160；gtksourceview3/3.24.11 同法），得到 `aarch64-unknown-linux-musl` |
| 2 | configure 后 config.status 阶段 `./confXXXXXX/subs1.awk: Permission denied` | `umask 077 && mktemp -d` 建 0700 目录，HMDFS 的 SGID 语义使其组不可写 | 运行时替换 configure 内嵌模板里的两处 umask（E011） |
| 3 | make 调用 `glib-genmarshal` 报 `Permission denied` | 该工具是 python 脚本；HMDFS 拒绝脚本直接 exec，而规则里是裸命令、无 configure 变量可覆盖 | make 之前用 `python3 <glib>/bin/glib-genmarshal` 预生成两个文件并刷新 mtime，make 判定已最新 |
| 4 | 无 makeinfo 时 `make` 触发 info 重建失败 | `INFO_DEPS` 默认包含 `$(srcdir)/doc/...info`，没有 makeinfo 可用 | build 与 install 都传 `INFO_DEPS=`，整体跳过 info 目标（库/头/.pc 不受影响） |
| 5 | 链接期未定义 `fabs` 的风险 | `-no-undefined` + 源码调用 fabs() | aarch64 clang 把 fabs 降为浮点指令，实测链接无未定义符号；无需 `-lm` |
| 6 | 自动 strip 会破坏 HarmonyOS ELF 签名 | llvm-strip 改写 ELF 使签名失效 | 与 gnucobol/gtk 一致，安装后对 `.so*` 先 `llvm-objcopy --remove-section .codesign` 再 `binary-sign-tool sign -selfSign 1` |
| 7 | `./configure: Permission denied`（126） | configure 是 `#!/bin/sh` 脚本，HMDFS 拒绝 execve 脚本（即使 0770、shebang 改成 `/system/bin/sh` 也一样） | 用 `/system/bin/sh <configure>` 显式解释；参数从 conanbuild.conf 的 `configure_args` 原样取用（alsa-lib 同法） |
| 8 | `config.status: Something went wrong bootstrapping makefile fragments` | config.status 的 depfiles 引导在 HMDFS 上失败 | configure 传 `--disable-dependency-tracking`（仓库内 203 个 autotools 包同法） |
| 9 | `doc/.dirstamp` 报 `install-sh: bad interpreter: Permission denied`；安装期同理 | Makefile 的 `MKDIR_P`/`INSTALL*` 是裸 `install-sh` 路径（脚本），HMDFS 拒绝 exec | `MKDIR_P="/system/bin/mkdir -p"`、`INSTALL*="/system/bin/install ..."`（toybox ELF applet）。注意 libtool `--mode=install` 只接受「单命令 + 选项」形式，`/system/bin/sh install-sh -c` 会被解析错，所以必须用 install 二进制而不是 sh 包一层 |

## 源码修改

无。上表各项全部在配方层完成（运行时改写 configure/config.guess、预生成
BUILT_SOURCES、跳过 info），不改上游源码，`patches_applied: []`。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| gtk | 3.24.43 | 唯一直接依赖（`gtk+-3.0 >= 3.18.0`），ohpcd 已发布 OHOS armv8 binary；同时提供 `bin/broadwayd` 供消费者测试起无头显示 |

glib/pango/cairo 等由 gtk 传递，均已随 gtk/3.24.43 发布（R36）。

## 验证结果

```text
# 上游测试
上游无测试用例（Makefile.am 无 TESTS/check_PROGRAMS/check_SCRIPTS；make check 为 no-op）
N=0

# test_package（pkg-config spread-sheet-widget + broadwayd :tcp66 真实建窗）
TEST PASS: gtk_init_check initialises the broadway GdkDisplay
TEST PASS: ssw_sheet_new returns an SswSheet GtkBin widget
TEST PASS: ssw_virtual_model_new implements GtkTreeModel
TEST PASS: virtual model rows/columns properties round-trip
TEST PASS: GtkTreeModel reports the configured 240x30 shape
TEST PASS: virtual model synthesises the r3c2 cell value
TEST PASS: sheet data-model property round-trips to the attached model
TEST PASS: sheet starts non-editable
TEST PASS: active cell stays unset while the sheet is not editable
TEST PASS: sheet realizes and maps in a GtkWindow on the broadway backend
TEST PASS: ssw_sheet_get_button returns the corner GtkButton
TEST PASS: attached sheet model accepts a live row insertion (240 -> 280)
TEST PASS: editable property turns the sheet editable
TEST PASS: ssw_sheet_set_active_cell/get_active_cell round-trips (2,4)
TEST PASS: selection-changed announced the new single-cell range
TEST PASS: gridlines property round-trips
TEST PASS: ssw_sheet_scroll_to moves both viewport adjustments
TEST SUMMARY: 17 passed, 0 failed
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libspread-sheet-widget.so.0(.x.y) | 运行时库（arm64 ELF 共享库） |
| lib/libspread-sheet-widget.so | 链接期名字（`-lspread-sheet-widget`） |
| include/ssw-sheet.h | 主控件与 SswRange 定义 |
| include/ssw-sheet-axis.h | 轴控件与几何 API |
| include/ssw-virtual-model.h | 测试/演示用 GtkTreeModel 实现 |
| include/ssw-axis-model.h | 轴列表模型 |
| lib/pkgconfig/spread-sheet-widget.pc | `Requires: gtk+-3.0 >= 3.18.0 glib-2.0 >= 2.44` |

## 注意事项

- 包内不含可执行程序（doc/demo 是 noinst），`package_type = "library"` 与内容一致。
- 公开头直接安装在 `include/` 根下，消费方写 `#include <ssw-sheet.h>`。
- `SswSheet` 默认 `editable=FALSE`：调用 `ssw_sheet_set_active_cell()` 前必须
  先把 `editable` 置 TRUE，否则是 no-op（上游语义，消费者测试显式覆盖）。
- `SswVirtualModel` 的 `rows`/`columns` 初值是 -1，使用前必须显式设置；
  设置 `rows` 时会向视图发 row-inserted/row-deleted/items-changed。
- GTK3 broadway 客户端忽略 `DISPLAY`，读 `BROADWAY_DISPLAY`；OHOS 上请用
  `:tcpN` 形式（TCP 9090+N），不要用纯 `:N`（HMDFS AF_UNIX 语义问题）。
- 本包无命令行产物，因此没有软件级 `commands.json`（R38 只针对可执行命令）。
