# spread-sheet-widget

`spread-sheet-widget`（GNU SSW）是 GTK+ 3 的表格控件库，最初由
John Darrington 为 GNU PSPP 的数据编辑器开发。它提供一套完整的
"二维表"视图：行列表头、可滚动的单元格网格、框选、就地编辑、剪贴板
粘贴，以及把任意大小模型虚拟化显示的能力。

## 功能概述

- **`SswSheet`**：主控件（`GtkBin` 子类）。内部由 2×2 个
  `SswSheetSingle` 组成，正常只显示一个；`split=TRUE` 时可同时显示
  四个角，便于对照表格两端。公开结构体暴露 `vadj[2]`/`hadj[2]` 四个
  `GtkAdjustment`、4 个 `sheet[]` 视图与 `selection` 范围。
- **`SswSheetAxis`**：行/列轴控件，负责单元格尺寸、位置查找、按单元格
  滚动（`ssw_sheet_axis_jump_start/center/end`）与表头按钮。
- **`SswVirtualModel`**：一个 GtkTreeModel 实现，每个单元格的值是
  `"r%dc%d"` 文本，用于测试/演示；`rows`/`columns` 属性变化会发出
  row-inserted / row-deleted / items-changed。
- **`SswAxisModel`**：把轴的行/列数量与偏移暴露给 `SswSheetAxis`。
- **编辑与选择**：`editable` 打开后，`ssw_sheet_set_active_cell()`
  会启动就地编辑器并发出 `selection-changed`（载荷为 `SswRange *`）；
  `ssw_sheet_get_active_cell()` 读回当前单元格。

交付边界是**纯库**：`libspread-sheet-widget.so` + 4 个公开头 +
`spread-sheet-widget.pc`。`doc/prog1`、`doc/prog2`、`demo/demo` 是
noinst 示例程序，不进入安装。

## OHOS 适配

| 要点 | 说明 |
|------|------|
| config.guess | 2022 版不识别 HarmonyOS；运行时插入 `HarmonyOS\|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;`，走 Linux 分支得到 `aarch64-unknown-linux-musl`（E160） |
| config.status tmpdir | `umask 077 && mktemp -d ./confXXXXXX` 在 HMDFS 上产生组不可写目录，config.status 随后 `Permission denied`；配方剥离两处 umask（E011） |
| glib-genmarshal | 工具本身是 python 脚本，HMDFS 拒绝脚本直接 exec；Makefile 的规则是裸命令，无法用 make 变量覆盖 → 构建期用 `python3` 预生成 `ssw-marshaller.{c,h}` 并刷新 mtime |
| texinfo | 上游 `info_TEXINFOS` 需要 makeinfo；设备无此工具，构建与安装均传 `INFO_DEPS=` 跳过（tarball 的 .info 不安装） |
| 链接 | `-no-undefined` 下 `fabs()` 在 aarch64 上是浮点指令，无 libm 未定义符号 |
| 无头显示 | GTK3 broadway 客户端忽略 `DISPLAY`、读 `BROADWAY_DISPLAY`；消费者测试起 gtk 包自带 `broadwayd :tcp66`（TCP 9156），避开 HMDFS 上 AF_UNIX socket 的问题 |

## 依赖关系

编译期 / 运行期（安装后由 `spread-sheet-widget.pc` 表达）：

- **gtk+-3.0**（`>= 3.18.0`）：控件基类、单元格渲染器、拖拽与剪贴板
- **glib-2.0**（`>= 2.44`）：GObject/GtkTreeModel 接口

本仓库中 gtk 由 **gtk/3.24.43**（broadway 后端）提供，glib/pango/cairo
等传递依赖随之发布。

## 为什么值得收进知识库

`spread-sheet-widget` 是 GNU PSPP 数据编辑器的硬依赖：PSPP 的
`configure` 要求 `spread-sheet-widget >= 0.10`，没有它就无法构建
PSPP 的图形数据视图。在它归档之前，ohpcd 上任何需要表格视图的
GTK 应用都只能自己实现或砍掉功能。

本包沉淀了三类可复用知识：

1. **老 config.guess 的 HarmonyOS 注入点**——不是替换整个脚本，而是在
   `case $UNAME_SYSTEM in` 后插入一个分支；shell 的 `case` 只执行第一个
   命中的分支，因此可以同时固定 `UNAME_SYSTEM=Linux` 与 `LIBC=musl`，
   完全跳过后续需要 `features.h` 的 libc 探测。
2. **BUILT_SOURCES 里的脚本型构建工具**——`glib-genmarshal` 这类
   python 脚本在 HMDFS 上不能直接 exec，而 Makefile 规则是裸命令；
   预生成 + touch 是比 PATH wrapper 更可靠的解法（wrapper 本身也会被
   execve 拒绝）。
3. **broadway 无头 GUI 消费者测试的完整链路**——从 pkg-config 解析
   `Requires:` 链、启动 `broadwayd :tcpN`、`gtk_init_check` 建窗，到
   驱动 `set_active_cell`/`selection-changed`/`scroll_to` 真实行为，
   可直接复用到其它 GTK3 控件库。

## 参考资料

- 上游主页：<https://www.gnu.org/software/ssw/>
- 源码包：`https://alpha.gnu.org/gnu/ssw/spread-sheet-widget-0.10.tar.gz`
- 上游仓库：<https://github.com/jdarrington/spread-sheet-widget>（镜像）
- 主要消费者：GNU PSPP（<https://www.gnu.org/software/pspp/>）
- 同仓库同族包：`archives/g/gtk`、`archives/g/gtksourceview3`、`archives/g/gspell`
