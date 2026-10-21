# rfdump

RFDump 是一个 RFID 标签读写工具（C，GPL-2.0-or-later），通过串口连接 ACG 多标签
读写器或兼容设备，读取/修改标签 ID、类型、厂商与用户数据区，并用十六进制/ASCII
编辑器展示；附带 cookie 演示功能用于说明 RFID 的隐私风险。上游 1.6 是最后一个
发行版（2008），界面为 GtkBuilder（原 libglade）+ GTK3。

## OHOS 适配

- **源**：官方站发布归档 `https://www.rfdump.org/dl/rfdump-1.6.tar.gz`
  （sha256 与 Debian 源码包 `rfdump_1.6-9.1` 的 `.orig.tar.gz` 逐字节一致）。
- **GTK 决策**：上游 1.6 的 `configure.in` 探测 `gtk+-2.0` + `libglade-2.0`，
  制品仓两者都没有；ohpcd 的 `gtk/3.24.43` 只开 **Broadway** HTML5 后端
  （`x11_backend=false / wayland_backend=false / broadway_backend=true`），
  正好对应鸿蒙 PC 无原生显示系统的现状。因此带上 GTK3 + GtkBuilder 移植
  （`patches/0001`，改编自 Arch Linux / Debian 的 `drop-libglade.patch`），
  而不是引入 GTK2。
- **不重新生成 autotools 产物**：发布包自带 2008 年 autoconf 2.61 生成的
  `configure`/`Makefile.in`；automake 1.18 已删除 `AM_CONFIG_HEADER`，CI worker
  也没有 autoconf/automake。`patches/0004` 直接把生成产物改到与移植后的
  `configure.in`/`src/Makefile.am` 一致，并在 `build()` 里给生成产物盖章
  （否则设备的 autoconf 2.73 会被 2008 maintainer 规则触发并重写 `configure`）。
- **运行期路径**：Conan 包是可重定位的，`patches/0005` 让 `rfdump.ui` /
  `rfdump_types.xml` 先按「可执行文件同级 `../share/rfdump`」查找；同时把
  HarmonyOS 上不存在的 `/var/lock` 串口锁降级为「提示后继续」，使失败点回到
  真正的设备节点缺失。
- **无头验证入口**：`patches/0006` 增加 `--version`/`--help`（在 `gtk_init` 之前
  回答）与 `--probe-reader`（不开窗，依次跑 GtkBuilder 资源、expat 设备表、
  termios 串口 bring-up，按失败类别返回不同退出码）。
- 依赖全部来自制品仓：`gtk/3.24.43` + `expat/2.8.2.1`（GTK 闭包由 gtk 配方拉取）。

## 已知限制

- HarmonyOS PC 无 X11/Wayland，GTK3 只有 Broadway 后端。实测**主窗口无法在该后端
  上实现**：`GtkTreeView` 触发 `infinite surface size not supported`，随后 GDK 断言
  失败 `_gdk_broadway_server_window_update: assertion failed: (data != NULL)` 并 abort
  （同一后端上的最小 GTK3 程序可正常运行，故为 rfdump 控件树专有）。因此 GUI 以
  「编译+链接+资源可加载」交付，交互无法自动化验证；串口/设备表路径由
  `--probe-reader` 覆盖。
- 本机没有串口设备节点（`/dev/ttyUSB0`、`/dev/ttyS0`、`/dev/input` 全部 ABSENT），
  也没有 `/var` 目录树，故 RFID 读写只能验证到「确定性降级」为止。

## 依赖

- gtk/3.24.43、expat/2.8.2.1（cairo/pango/gdk-pixbuf/atk/glib/… 由 gtk 传递）

## 参考

- 官方站：https://www.rfdump.org/
- Debian 源码包（版本互证）：https://sources.debian.org/api/src/rfdump/
