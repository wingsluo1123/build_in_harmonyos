# toilet

toilet（**T**he **O**ther **I**mplementation of fig**LET**）是 Sam Hocevar 开发的命令行工具，
把普通文本渲染成大号彩色 ASCII/ANSI 艺术字——即 FIGlet 的另一种实现，并额外支持
libcaca 的全部终端能力（真彩、过滤器、多种导出格式）。

## 功能概述

- 使用 FIGlet 的 `.flf`/`.tlf` 字体渲染文本（随包提供 24 个字体）
- 渲染模式：默认 / smushing / kerning / full width / overlap（`-s -S -k -W -o`）
- 输出宽度控制（`-w`/`--termwidth`）
- libcaca 过滤器链（`-F`，如 `flip`、`metal`、`rainbow`、`gay`；`-F list` 列出全部）
- 导出格式（`-E`/`--html`/`--irc`，如 HTML 文档、IRC 颜色码）
- FIGlet 兼容 infocode（`-I`）

## OHOS 适配要点

| 要点 | 说明 |
|---|---|
| 构建脚本自举 | 源码归档（git-archive 快照）不含 `configure`/`Makefile.in`，`build()` 先执行上游自带 `bootstrap`（aclocal → autoconf → autoheader → automake） |
| automake 缺失 | 设备 `/data/service/hnp/bin` 只有 autoconf 家族；以 `tool_requires("automake/1.18")` 拉入（其 `package_info` 注入 `PERL5LIB`/`ACLOCAL_PATH`，仅在 conanbuild 环境内生效） |
| `config.guess` 不可用 | 本机 `config.guess`(2024-07-27) 不识别 HarmonyOS 内核，且 HMDFS 下 `mkdtemp` 后写 `dummy.c` 被拒 → configure 报 `cannot guess build type`；配方显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（build == host = 本机原生编译）跳过它 |
| HMDFS 权限语义 | `config.status` 的 `(umask 077 && mktemp -d ./confXXXXXX)` 生成的 2700 目录在 HMDFS 上不可写（当前 uid 靠组位通行，`chmod` 是 no-op）→ 配方把**生成**的 `configure` 中 `umask 077` 改写为 `umask 022`（该行由 autoconf 模板生成，不在源码树内） |
| 源码内构建 | 上游两个官方测试（`test/check-source`、`test/check-fonts`）按源码树相对路径取 `../src`、`../fonts`，只在 `srcdir == builddir` 时成立；配方用 `basic_layout(src_folder=".")` + `folders.build = "."` 保证源码内构建，**上游测试脚本零改动**即可原样通过 |
| 字体目录补丁 | conan 用 `--prefix=/` + `make install DESTDIR=<包目录>` 安装，使编译期 `FONTDIR` 烤成 `/share/figlet`（运行期报 `could not load font pagga`）。上游无覆盖点，故 `patches/0001` 把 `src/Makefile.am` 的 `-DFONTDIR="$(datadir)/figlet"` 改为可覆盖的 `FONTDIR ?= $(datadir)/figlet`（默认值不变、无平台宏），配方在 `make` 命令行传 `FONTDIR=<包目录>/share/figlet` |
| 依赖注入 | `configure.ac` 的 `PKG_CHECK_MODULES(CACA, caca >= 0.99.beta18)` 是硬检查；由 `PkgConfigDeps` 生成指向 conan 包目录的 `caca.pc`，`PKG_CONFIG_PATH` 指向本配方 `generators_folder`（不写共享 `/usr/local`） |

## 依赖关系

| 依赖 | 用途 | 版本 | 来源 |
|---|---|---|---|
| libcaca | 终端渲染后端与过滤器（`PKG_CHECK_MODULES(CACA, caca >= 0.99.beta18)` 硬依赖） | `libcaca/0.99.beta20.1` | 制品仓 prebuilt（其自身依赖 ncurses/6.4、zlib/1.3.1 静态） |
| automake | 构建期自举 `configure`/`Makefile.in`（设备无 automake/aclocal） | `automake/1.18`（`tool_requires`） | 制品仓 prebuilt |
| autoconf / m4 | 构建期自举（设备自带） | autoconf 2.72 / m4 1.4.x | 设备 `/data/service/hnp/bin` |

运行期：`toilet` 只依赖 libc 与包内字体（`share/figlet/*.tlf` + 编译期硬编码的 `FONTDIR`）。

## 参考资料

- 上游仓库：<https://github.com/cacalabs/toilet>
- 上游许可证：WTFPL v2（`COPYING`）
- libcaca 项目主页：<https://caca.zoy.org/>
