# ukopp

ukopp — disk-to-disk backup（作者 Michael Cornelison，kornelix.com）：
把挂载磁盘或目录的文件复制到另一磁盘/目录（"备份盘"），支持全量/
增量备份、备份后校验、按天/周/月保留旧版本（过期清理）、文件报告/
查找与恢复任务（按文件/目录/版本）。

上游：https://kornelix.com/ukopp（GPL-3.0-or-later）

## 功能

### ukopp（bin/，单二进制）
- GTK3 GUI：菜单 + 工具栏 + 日志窗（任务编辑/运行/校验/报告/恢复）
- 无 GUI 命令行模式：`ukopp -nogui`（输出到 STDOUT）、
  `ukopp -nogui -job jobfile`（载入任务）、
  `ukopp -nogui -run jobfile`（载入并立即执行）——适合脚本化
- 全量/增量备份 + 备份后校验 + 版本保留（按天/周/月过期清理）
- 报告：磁盘文件/差异摘要/文件版本/过期版本/查找
- 恢复：按目录/文件/版本恢复

## HarmonyOS PC (arm64) 适配说明

- 交叉编译（clang 15 / libc++ / musl）：上游裸 Makefile，
  `make -j1 SHELL=/bin/sh CXX=<conf 编译器>`（编译器从
  tools.build:compiler_executables conf 获取）
- pkg-config 依赖：gtk+-3.0.pc / glib-2.0.pc 由 PkgConfigDeps 生成
  （本机 conan 缓存绝对路径），`PKG_CONFIG_PATH` 显式注入 generators
  目录（bart-view 同款）
- 链接依赖：glib/2.84.0.1 + gtk/3.24.43（制品仓均有 OHOS/armv8 二进制）
- 上游 `make install` 依赖 xdg-desktop-menu（OHOS 无）→ package()
  手工布局：`bin/ukopp`、`share/ukopp/{data,icons}`、
  `share/doc/ukopp`、`share/man/man1/ukopp.1`、
  `share/applications/ukopp.desktop`、`licenses/copyright`
- headless 运行：`-nogui` 不调 gtk_init()；zfuncs `zinitapp()` 在
  stdin 非 tty 时把 stdout/stderr 重定向到 `$HOME/.ukopp/logfile`
  （追加模式），`$HOME` 必须设置且可写

## 依赖关系

- 编译/链接：glib/2.84.0.1、gtk/3.24.43（制品仓均有 OHOS/armv8 二进制）
- 运行：GUI 模式需 GTK3 图形环境；命令行模式（-nogui）无额外运行时

## 参考资料

- 上游主页: https://kornelix.com/ukopp
- 用户手册: data/userguide-en.html（随包安装于 share/ukopp/data/）
- man page: ukopp(1)（随包安装于 share/man/man1/）
- Debian 源码包: https://deb.debian.org/debian/pool/main/u/ukopp/
