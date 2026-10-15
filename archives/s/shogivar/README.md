# shogivar

ShogiVar 是将棋（Shogi，日本将棋）的裁判与对弈程序：既能担任两名人类棋手之间的裁判，
也内置电脑对手，覆盖 17 种古代与现代将棋变体（从 5×5 的 Micro 将棋到 25×25 的大大将棋）。
最初的 1.55a 是 16-bit Visual Basic 程序；H.G. Muller 把棋规逻辑改写为 C，并接上改编自
GNU XBoard 的 GTK 前端，即本包归档的 **C-port** 分支。

## 功能概述

- 17 种变体的完整棋规：Shogi、Mini、Micro、Heian、Heiansho、Judkin、Wa、Whale、Yari、
  Tori、Sho、Chu、Dai、DaiDai、Maka、Tai、Tenjiku（General.rul 为共用规则）
- 棋盘/棋子图形资产：1028 个棋子与棋盘 PNG、25 个变体标题图、24 张棋子说明图
- 人机对弈（除 Tenjiku 外各变体均有内置引擎）、双人裁判模式、棋谱存取
- 传统日文棋子表示与西式棋子表示两套外观
- 安装 `share/man/man6/shogivar.6` 手册页

## OHOS 适配

| 主题 | 处理 |
|------|------|
| 平台三元组 | 随包的 config.guess/config.sub 是 2014 年版，补 HarmonyOS 识别与 `linux-ohos` 白名单（E007/E072）。**不使用 `--build/--host` 绕过**，避免 configure 误判为交叉编译而跳过运行时探测 |
| 前端工具包 | 上游为 GTK+ 2；OHOS 制品仓只发布 GTK3（gtk/3.24.43），故按 GTK3 API 移植（菜单/组合框/GDK_KEY_*/draw 信号等） |
| 死依赖清理 | `librsvg` 只在 configure 与两行 `#include` 里出现，全树零 `rsvg_*` 调用 —— 直接去掉；否则还会把 cairo-gobject 顶到与 gtk 二进制不兼容的版本 |
| 构建期 HMDFS 语义 | autoconf 生成的 config.status 用 `umask 077 && mktemp -d` 建临时目录，HMDFS 下随后不可遍历；在 configure 内改写该段 |
| 工具链缺失 | OHOS worker 无 automake/aclocal/libtool，需屏蔽 automake maintainer-mode；无 makeinfo，configure 的该检查降级为告警 |
| 并行 make | OHOS 禁止 GNU make jobserver 建 FIFO，所有 make 一律 `-j1` |
| 资源目录 | 编译期 `DATADIR` 在 conan 默认 `--prefix=/` 下会变成 `/share/games/shogivar`；程序改为启动时按可执行文件位置解析 `../share/games/shogivar`，失败才回落编译期默认值，因此包可放在任意前缀下。`shogivar --help` 会打印实际解析结果 |
| 无显示环境 | GTK3 前端必须有窗口系统；`-v/--version` 与 `-h/--help` 在 `gtk_init()` 之前处理并 `exit(0)`，供无头环境（CI、安装脚本的首次执行预触发）做冒烟验证 |

**已知限制**：图形棋盘需要窗口系统（X11/Wayland/Broadway）。CI 无显示，因此图形交互
路径只能验证「确实需要显示且以错误码干净退出」，不伪造图形用例通过。

## 依赖关系

编译期与运行期（均为 Conan 包）：

| 依赖 | 版本 | 用途 |
|------|------|------|
| gtk | 3.24.43 | GTK+ 3 前端（broadway 后端；传递带入 glib/pango/gdk-pixbuf/atk/fribidi/libepoxy/cairo-gobject） |
| cairo | 1.18.4 | draw.c 与 gtk/*.c 直接使用的绘图库 |

上游 configure 还要求 `librsvg-2.0`，但源码零引用，已去掉（见上表）。

## 上游测试

上游**没有**任何自动化测试：源码包内无 tests 目录、无测试文件，`Makefile.am` 无
`TESTS`/`check_PROGRAMS`，`make check` 是 automake 的空壳规则（输出仅
`cd <srcdir> && true`）。因此本包的功能验证由 `1.55b/test_package/` 的鸿蒙消费者用例
提供（15 条 shell 断言 + 6 条 ELF/动态链接契约断言）。

## 参考

- 作者主页：<https://hgm.nubati.net/>（原 gitweb 源码仓库已下线）
- 源码：Debian 归档中的 pristine 上游快照 `shogivar_1.55b.orig.tar.gz`
- Debian 打包（GTK3 移植思路的参考实现）：<https://salsa.debian.org/debian/shogivar>
