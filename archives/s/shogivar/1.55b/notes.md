# shogivar 1.55b 适配笔记（HarmonyOS PC / OHOS aarch64）

## 软件与上游

- ShogiVar：将棋（Shogi）裁判 + 对弈程序，支持 17 种古/现代将棋变体，内置电脑对手。
  1.55a 原为 16-bit Visual Basic 程序；H.G. Muller 把棋规逻辑改写为 C，并接上改编自
  GNU XBoard 的 GTK 前端，即本包使用的 **C-port** 分支。
- 上游只通过作者自建 gitweb（分支 C-port）以 git 快照分发，该 gitweb 已下线
  （HTTP 404），主页链接同步失效。现存唯一稳定分发件是 Debian 归档中的 pristine
  上游快照 `shogivar_1.55b.orig.tar.gz`（顶层目录 `shogivar-C-port-1.55b`，与
  `AC_INIT([shogivar],[C-port-1.55b])` 一致，包内无 debian/ 目录）。本配方取华为云
  Debian 权威镜像直链，与 deb.debian.org 上的同一文件 sha256 相同。
- 许可 GPL-3.0-or-later。

## 编译环境

- 构建系统: autotools（随包分发 configure/Makefile.in，**不**跑 autoreconf）
- 编译日期: 2026-10-14
- 编译器: clang 15.0.4（target aarch64-unknown-linux-ohos）
- 目标 profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS, os.version=6.0, arch=armv8）
- 状态: built

## 编译步骤（实测）

```bash
export CONAN_HOME=$HOME/.conan2                     # remote: ohpcd（conancenter 已禁用，与 CI 一致）
conan create archives/s/shogivar/1.55b \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=shogivar/*
```

配方内部（`conanfile.py`）：

1. `apply_conandata_patches` 应用 12 个补丁（见下）；
2. `AutotoolsToolchain` + `PkgConfigDeps` 生成工具链与 `gtk+-3.0.pc` 等；
3. `configure --prefix=/ ... --disable-update-mimedb --disable-silent-rules`
   （`--prefix=/` 是 conan 的默认值，安装走 `DESTDIR=<package_folder>`）；
4. `make -j1`（必须 -j1，见问题 4）；
5. `make check -j1` —— 上游官方测试入口（空壳，见「上游测试清点」）；
6. `make install DESTDIR=<package_folder> -j1`。

## 上游测试清点（R51）

**上游没有任何自动化测试，N = 0、N′ = 0**，清点证据（均已实测）：

| 检查 | 命令 | 结果 |
|------|------|------|
| 测试目录 | `ls -d */`（源码根） | 只有 `Data/` 与 `gtk/`，无 tests/test/t |
| 测试文件 | `find . -iname "*test*" -o -iname "check*" -o -iname "*.trs"` | 0 命中 |
| Makefile.am 测试目标 | `grep -E "^(TESTS\|check_PROGRAMS\|check_SCRIPTS\|check_LTLIBRARIES)" Makefile.am` | 无输出 |
| `make -n check` | 见下 | 仅 `cd <srcdir> && true` |
| 上游 README | 全文 | 只讲 `autogen.sh/configure/make/make install`，未提任何测试方式 |

`make check` 实测输出（退出码 0）：

```
CDPATH="${ZSH_VERSION+.}:" && cd <srcdir> && true
```

即 automake 在无 `TESTS` 时生成的空 `check` 规则，注册用例 0 个。
因此本包的上游测试通过率不适用，功能验证由 `test_package/` 的鸿蒙消费者用例提供
（21 条断言：15 条 shell 用例 + 6 条 ELF/动态链接契约）。

## 遇到的问题与解决方案

| # | 现象（首个错误） | 根因 | 解决方案 |
|---|------------------|------|----------|
| 1 | `./config.guess: unable to guess system type`（UNAME_SYSTEM = HarmonyOS） | 随包 config.guess 是 2014-03-23 版，无 HarmonyOS/OHOS 分支（E007） | 补丁 0001：在 `case ... :HarmonyOS:` 分支输出 `aarch64-unknown-linux-ohos`。注意该脚本分支必须自带 `echo`/`exit`，只赋值会落到兜底报错分支 |
| 2 | `Invalid configuration 'aarch64-linux-ohos': system 'ohos' not recognized` | config.sub 未收 linux-ohos（E072） | 补丁 0002：`linux-ohos*` 进 kernel-os 组合表、新增 `ohos-linux)` 别名、`-ohos*` 进基本 OS 白名单，并把 `-linux-ohos*` 从通用 `-linux*` 规则前拦下（否则返回 `aarch64-unknown-linux-gnu-ohos`） |
| 3 | `Package requirements ( gtk+-2.0 >= 2.16.0 gmodule-2.0 ) were not met` | 上游 2014 年的前端是 GTK2；OHOS 制品仓只发布 GTK3（gtk/3.24.43） | 补丁 0003 改 `PKG_CHECK_MODULES([GTK],[gtk+-3.0])`，补丁 0011 把 `gtk/xoptions.c` 按 GTK3 API 移植 |
| 4 | `Please install "makeinfo"` | configure 的 makeinfo 检查继承自 XBoard，但 shogivar 不含 Texinfo 手册，OHOS 亦无 makeinfo | 补丁 0003：缺失时告警并 `MINFO=cat` 继续 |
| 5 | `config.status: line 616: ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 忽略 umask/chmod 语义，`umask 077 && mktemp -d` 建出的临时目录随后不可遍历（E524 同类） | 补丁 0003：改写 configure 内该段（去掉 umask、补 `chmod 755 "$tmp"`），并保留 `--disable-update-mimedb` |
| 6 | `Makefile:997: /path/aclocal.m4 Error 127`（missing: aclocal-1.14: command not found） | OHOS worker 无 automake/aclocal/libtool，改动 configure.ac 触发 automake maintainer-mode 规则 | 补丁 0004：Makefile.in 的 ACLOCAL/AUTOCONF/AUTOHEADER/AUTOMAKE 置 `true` |
| 7 | `make: jobserver mkfifo: /…/GMfifoNNNN: Operation not permitted` | OHOS 不允许 GNU make jobserver 建 FIFO | `make -j1`；注意 conan 的 `Autotools.make()` 在未显式传 `-j` 时会补 `-j<nproc>`，因此 `check`/`install` 也要显式带 `-j1` |
| 8 | `menus.h:62:5: error: unknown type name 'ulong'` | Debian 的同类补丁假定了 X11 头；menus.h 并不包含它们 | 补丁 0012 用 `unsigned long`（`gulong` 的等价宽度） |
| 9 | `gtk/xoptions.c:461:96: error: use of undeclared identifier 'True'` | `True`/`False` 原先由 `cairo-xlib.h` 间接带入的 `Xlib.h` 提供，补丁 0008 删掉该头后即未定义 | 补丁 0011 改用 GLib 的 `TRUE`/`FALSE` |
| 10 | `ld.lld: error: duplicate symbol: currBoard`（draw.o 与 gtk/gui.o） | `currBoard` 在 draw.c 与 gtk/gui.c 各写了一份定义，clang 15 默认 `-fno-common` | 补丁 0006：common.h 声明 `extern Option *currBoard;`，只在 draw.c 定义（与 Debian 对 GCC 10 的修法一致） |
| 11 | 资源目录问题：conan 默认 `--prefix=/`，`-DDATADIR` 编译成 `/share/games/shogivar` | GUI 程序的图片/棋规文件路径是编译期常量；conan 缓存目录与 cmd-pkgs 扁平 tar 包解包目录各不相同，编译期绝对路径无法通用 | 补丁 0002/0003/0008/0009/0010：新增 `InitDataDir()`（`/proc/self/exe` → `../share/games/shogivar`，失败回落编译期默认值）与 `DataPath()`，全部 17 处 `DATADIR "…"` 拼接改走运行时解析；棋规文件目录 `Direct` 由 frontend 启动时写入（backend.c 不改，只在 backend.h 导出 `extern STRING Direct;`） |
| 12 | 路径缓冲隐患：`sprintf(Datafile, "%s/%s.dat", Direct, Choice)` | `backend.h` 的 `STRING` 沿用 16-bit 时代的 `char[80]`，却被用来承载文件系统路径 | 补丁 0005：`STRING` 放宽到 `char[512]` |

## 源码修改（patches/，12 个，由 refresh-patch --auto 按编辑追踪器逐文件生成）

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | Makefile.in | ACLOCAL/AUTOCONF/AUTOHEADER/AUTOMAKE = true（无 automake） |
| 0002 | backend.h | `typedef char STRING[80]` → `[512]`（路径缓冲写穿）；导出 `extern STRING Direct;` |
| 0003 | common.h | `extern Option *currBoard`（-fno-common）；`shogivarDataDir`/`DataPath`/`InitDataDir` 声明 |
| 0004 | config.guess | HarmonyOS 平台识别 → `aarch64-unknown-linux-ohos`（E007） |
| 0005 | config.sub | 接受 `linux-ohos` 三元组（E072） |
| 0006 | configure | gtk+-3.0；去 librsvg-2.0（零引用）；makeinfo 缺失告警；config.status 临时目录去 umask + chmod 755 |
| 0007 | configure.ac | 与 0006 对应的三处源头修改（临时目录属 autoconf 生成代码，只在 configure 改） |
| 0008 | dialogs.c | 12 处标题/帮助/方图标图片路径改 `DataPath()` |
| 0009 | draw.c | 删 3 行无用头（cairo-xlib.h、rsvg.h、rsvg-cairo.h）；4 处图片路径改 `DataPath()` |
| 0010 | gtk/gui.c | GTK_DIALOG_NO_SEPARATOR 移除；`gtk_init` 前处理 `-v/--version`、`-h/--help`；新增可重定位资源根并在 `--help` 打印 |
| 0011 | gtk/xoptions.c | GTK2→GTK3 API 移植（菜单/组合框/GDK_KEY_*/g_signal_connect_swapped/gtk_widget_get_window/draw 信号/TRUE-FALSE） |
| 0012 | menus.h | `MenuItem` 增加 `activate_id`（阻塞信号避免勾选递归） |

补丁中**不含任何 `__OHOS__` 平台宏**（全部是通用可移植性修改，符合 R8/PF5）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| gtk | 3.24.43 | GTK3（broadway 后端，x11/wayland 关闭）；传递带入 glib 2.84.0.1 / pango 1.50.14.1.1 / gdk-pixbuf 2.44.6.1 / atk 2.38.0.1.1 / fribidi 1.0.16 / libepoxy 1.5.10 / cairo-gobject 1.18.4.2 |
| cairo | 1.18.4 | draw.c / gtk/*.c 直接包含 cairo 头 |

`librsvg` **故意不引入**：上游 configure 要求它、draw.c 也 include 了它，但全树没有任何
`rsvg_*` 调用（补丁 0003 去掉 configure 要求、0008 去掉 include）。引入它还会连带把
cairo-gobject 顶到 1.18.4.3 —— 已发布的 gtk/3.24.43 二进制是针对 cairo-gobject/1.18.4.2
编译的，两者无法共存于同一依赖图（实测 `ERROR: Version conflict: Conflict between
cairo-gobject/1.18.4.3 and cairo-gobject/1.18.4.2 in the graph.`）。

## 验证结果

```bash
# W0 依赖可消费（R35/R36：用 conan install/download 而非 conan list）
conan install <probe>/conanfile.py -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=never
# → gtk/3.24.43 落到已发布 package_id 18b354b6139b782829755c01297627c8f8444702，EXIT=0

# W3 本地真实构建（含上游测试入口与 test_package）
conan create archives/s/shogivar/1.55b -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=shogivar/*
# → Package '9d069a74340868f4bf3ae39e937763cf897f9e2f' created，EXIT=0
# → 日志：.ci_logs/conan_create_shogivar_1.55b.log
#        sha256 = 337d2f869a0b14eabf3055ebfe3c26c242cdd5cb77ea341ec38667c31c5f5271
```

消费者侧实测（conan create 的 test_package 阶段，15 条 shell 断言全绿）：

```
ok 1 - bin/shogivar installed and executable
ok 2 - shogivar --version exits 0 and reports 'shogivar version C-port-1.55b'
ok 3 - shogivar -v exits 0 and reports the same version string
ok 4 - shogivar --help exits 0 and documents -v/--version and -h/--help
ok 5 - share/games/shogivar asset tree installed
ok 6 - all 18 board definitions (Data/*.dat) installed and non-empty
ok 7 - all 18 rule files (Data/*.rul, incl. General.rul) installed and non-empty
ok 8 - piece graphics: 1028 files (>= 1028)
ok 9 - variant title graphics: 25 files (>= 25)
ok 10 - piece-help graphics: 24 files (>= 24)
ok 11 - representative piece/title/help assets carry the PNG signature (89504e47)
ok 12 - no zero-length file under share/games/shogivar
ok 13 - man page share/man/man6/shogivar.6 installed and non-empty
ok 14 - binary resolves its asset tree at run time: <package>/share/games/shogivar
ok 15 - headless start exits cleanly with a display error (rc=1), no signal death
PASS: all 15 consumer checks succeeded
```

另加 6 条 ELF/动态链接契约断言（`test_package/conanfile.py` 内纯 Python 解析 ELF，
不依赖 readelf）：ELF64 小端 AArch64、`PT_INTERP = /lib/ld-musl-aarch64.so.1`，
`DT_NEEDED` 含 libgtk-3.so.0 / libcairo.so.2 / libglib-2.0.so.0 / libpango-1.0.so.0
（实测共 30 个 NEEDED）。

## 注意事项

1. **图形界面需窗口系统**：GTK3 前端在无显示环境下必然 `cannot open display` 退出
   （退出码 1）。CI worker 无显示，因此棋盘/棋规的真实交互无法在无头环境断言；本包
   只断言「确实需要显示且不崩溃」+「CLI 与资源树契约成立」，不做伪造通过。
2. **资源目录是运行时解析的**：包可以放在任意位置（conan 缓存、`conan … deploy`、
   cmd-pkgs 的扁平 tar 包解包目录）；`shogivar --help` 会打印实际解析到的
   数据目录，便于排查。
3. **`-j1` 是硬要求**：OHOS 上 GNU make 的 jobserver 建 FIFO 会被拒绝。
4. **依赖图里不要加 librsvg**，否则 cairo-gobject 版本冲突导致 gtk 二进制失配
   （见「依赖版本」）。
---

**编译结束**: 2026-10-14 19:58
**最终状态**: built
