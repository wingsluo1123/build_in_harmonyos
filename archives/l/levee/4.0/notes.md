# levee 4.0 适配笔记

levee 是 David L Parsons 编写的小型 vi 克隆（可视模式 + exec 模式，C 语言，约 54 KB）。
本次适配目标：HarmonyOS PC（aarch64-linux-ohos），交付命令行工具 `bin/levee`。

## 编译环境

- 构建系统: makefile（`configure.sh` + `configure.inc`，作者自写的 shell 版 autoconf 模拟器，生成 `config.h` 与 `Makefile`；非 autotools）
- 编译日期: 2026-09-27
- 编译器: OHOS clang 15.0.4（profile `tools.build:compiler_executables`，`/data/service/hnp/bin/clang`）
- 构建机: x86_64 runner，`-pr:h=-pr:b=ci/conan/profiles/ohos-aarch64`；qemu-aarch64 10.x（binfmt 已注册）
- 状态: built（conan-verify 与 finish/W3 在本机通过，待设备 CI）

## 源码来源

| 项 | 值 |
|---|---|
| conandata URL | `https://github.com/Orc/levee/archive/refs/tags/v4.0.tar.gz`（作者本人仓库的 v4.0 tag） |
| sha256 | `3a625efa3d852008eb821f52b30667e16101ca36099711ff513767ceeb527f79` |
| 任务给定源 | `https://deb.debian.org/debian/pool/main/l/levee/levee_4.0.orig.tar.bz2`（sha256 `fc39d3ad51573a3878acf050b45b9ba0c02f81dbf2b0149730724cf131b39c95`） |

两份源码解包后 `diff -r` 只差 init-build 写入的 `.tarball-sha256`，48 个上游文件逐字节一致。
conandata 采用作者官方 tag 而非 Debian 地址：PF7 源 URL 闸把 `deb.debian.org` 判为「Debian 下游
重打包源」直接拦截（R39 口径是官方源优先），换成内容相同的官方源即可，不需要 `--no-preflight`。
本机直连 codeload 超时，比对时经 ghfast 镜像取同一 tag；conandata 只写官方 URL，镜像回退由
conan-verify（E017 预防）与 CI 自动处理。

## W0 / W0b

- 依赖：libc + ncurses。`conan download ncurses/6.4|6.5|6.6 -r=ohpcd --only-recipe` 三个版本均已发布；
  选用仓内引用最多的 `ncurses/6.6`（156 处），`conan install --requires=ncurses/6.6 --build=never`
  用 CI profile 取到预编译包（rrev `3dcfd3b6d759300e8997800cefe8c61f`，package `21b17f8b2bc0e9511e276e3d57a23893067cefe5`）。
- 历史：仓内无 levee 归档，`recipe-search levee -d ncurses` 无相似配方。参考了同类先例：
  openvi 7.9.33（vi 克隆 + ncurses/6.6 + `$TMPDIR` 补丁）、ren 1.0（`-static-pie` 交付、x86 经 qemu 跑
  test_package）、curseofwar 1.3.0（ncurses 运行期 terminfo）。
- 语言预检：`lang-preflight` → detected=c（26 个 C 源文件，100%），与任务兼容。

## 编译步骤

配方 `build()` 等价于（`<nc>` 为 Conan ncurses/6.6 包目录）：

```bash
CC='/data/service/hnp/bin/clang -static-pie' CFLAGS='-O2 -fPIE -I<nc>/include' \
LDFLAGS='-L<nc>/lib' LIBS='-lncursesw' bash ./configure.sh --partial-install
# 断言 config.h 含 "#define USE_TERMCAP 1" 且不含 TERMCAP_EMULATION（确认走 ncurses 的 termcap 接口）
make -j1
```

`package()` 复刻上游 `make install` 的命名：`lev` → `bin/levee`，`lv.1` → `share/man/man1/levee.1`，
另带 `licenses/COPYRIGHT`、`share/doc/levee/README`。`--partial-install` 不安装 `lv` 别名
（与同名的 lv 分页器冲突）；不直接跑 `make install`，因为其中的 `install -s` 会调用构建机的 strip。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接报 `duplicate symbol: refresh / scroll / LINES / COLS / UP`，另一处在 `libncursesw.a(lib_gen.o / lib_setup.o / lib_termcap.o)` | levee 自定义了与 curses 同名的全局；动态链接时被可执行文件符号抢占而静默通过，R26 下 ncurses 是静态单体归档，`tgetent` 拉入的成员带着同名强定义（`--why-extract` 链见 E587 草稿） | 补丁 0001：`levee.h` 用宏把 6 个名字改为 `levee_` 前缀（早于 `<termcap.h>`，其 `extern char *UP` 同步改名）。新知识草稿 **E587**（engine 误命中 E163） |
| 2 | `unixcall.c:314 error: too many arguments provided to function-like macro invocation` | musl 的 `glob()` 不支持 `GLOB_NOMAGIC`，configure 不定义 `USING_GLOB`，走 levee 内置 glob；其中一处 `logit()` 漏写双括号（上游在 glibc/BSD 上从不编译这段） | 补丁 0003 顺带把该调用改为 `logit((...))` 约定 |
| 3 | 普通 CC 下 `configure.sh` 返回 0，但 `Makefile` 残留 12 个 `@CC@` 等占位符，make 报 `CC@: No such file or directory` Error 127 | `configure.inc` 在构建机上编译并执行 `config.sed`（每次 AC_SUB）与 `mkversio`；x86 上动态链接的 AArch64 产物缺 `/lib/ld-musl-aarch64.so.1`（`config.log`: `aarch64-binfmt-P: Could not open ...`） | CC 设为 `<cc> -static-pie`：辅助程序与交付物都是无 PT_INTERP 的 static PIE，x86 经 qemu binfmt、设备上原生都能执行。新知识草稿 **E588** |
| 4 | 撤销溢出、大块 yank、`!` 过滤的临时文件写死在 `/tmp/` | `os_mktemp()` 硬编码 `static char tmp[] = "/tmp/"`，HarmonyOS PC 的 `/tmp` 只读（E002 同族，但这里是**运行期**且上游无视 `TMPDIR`） | 补丁 0003：优先 `$TMPDIR`，未设置/为空回退 `/tmp`；长度校验同步改为按实际目录计算 |
| 5 | conan-verify 的 L2 以 `bin/* --version`/`--help` 冒烟，levee 两者都不认识，会进入编辑器阻塞到超时 | 上游只有 `-e -r -t` 短选项 | 补丁 0002：`main()` 开头处理 `--version`/`--help`（打印后返回 0，不碰终端），E503 同类先例 |
| 6 | 本机 test_package 里 `TERMINFO` 指向 ncurses 包仍 `tgetent=-1`，levee 退化为行模式、读到 EOF 后空转超时 | ncurses 在 uid 0 下不读 `TERMINFO/TERMINFO_DIRS/~/.terminfo`（`_nc_env_access`），只查编译期默认 `//share/terminfo`；本机 conan 以 root 运行。改用用户命名空间后又因包内 terminfo 属主为 CI 用户、权限 640 而读不到 | `test.sh` 在 `id -u` 为 0 时复制所需条目到工作目录并经 `unshare --user --map-user=65534` 运行 levee；设备 CI 以普通用户运行不走该分支。新知识草稿 **E590** |
| 7 | 任务给定的 Debian 源被 PF7 拦截 | 见「源码来源」 | 改用内容一致的作者官方 tag |

## 源码修改

| 补丁 | 文件 | 内容 |
|---|---|---|
| `0001-levee.h.patch` | levee.h | +14：`#define LINES levee_LINES` 等 6 个改名宏（问题 1） |
| `0002-main.c.patch` | main.c | +12：`--version` 输出 `levee 4.0`、`--help` 输出 usage，均返回 0（问题 5） |
| `0003-unixcall.c.patch` | unixcall.c | +14/-7：`os_mktemp()` 跟随 `$TMPDIR`（问题 4）；`os_glob()` 的 `logit` 双括号（问题 2） |

补丁由 `refresh-patch --auto` 生成，均为通用 POSIX 写法，不含 `__OHOS__` 等平台宏。

## 上游测试清点（R51）

```bash
$ cd levee-4.0.orig
$ find . -type f ! -name .tarball-sha256 | wc -l            # 48
$ find . -mindepth 1 -type d                                  # ./os2 ./win32（平台移植文件）
$ find . -iname '*test*' -o -iname '*check*' | wc -l          # 0
$ grep -oE '^[a-zA-Z0-9_. ]+ *:' Makefile.in | tr -d ' :' | sort -u
blockio.o clean display.o distcleanspotless editcor.o exec.o find.o fixtags.o globals.o home.o
insert.o install install.bin install.man lev logit.o main.o misc.o mkversio modify.o move.o
rmxcall.o tag.o tags ucsd.o undo.o unixcall.o version.c version.o
$ grep -cwE 'check|test' Makefile.in                          # 0
```

结论：上游**没有任何测试**（v4.0 源码 48 个文件中无测试目录/源文件、无 CI 配置，Makefile 无 check/test 目标），
N = 0、N′ = 0，无法「实际运行上游测试」。功能验证全部由 test_package 补齐（下节）。

## 测试结果

test_package 以使用者身份驱动**打包出的** `bin/levee`：键盘输入走 stdin 管道，`TERM=vt100`，
`TERMINFO` 指向 ncurses/6.6 的 terminfo 数据库，`TMPDIR` 指向私有可写目录。

| # | 类别 | 用例 | 本机结果 |
|---|---|---|---|
| 1 | 集成 | `--version` 输出 `levee 4.0`、退出码 0 | ok |
| 2 | 集成 | `--help` 输出 usage、退出码 0 | ok |
| 3 | 集成 | 可视模式插入两行 + `:wq` 新建文件，字节完全一致 | ok |
| 4 | 集成 | `-r` 只读：`:w` 被拒并提示 `File is readonly`，文件不变 | ok |
| 5 | 集成 | 终端层：静态 libncursesw 从 TERMINFO 读 vt100 `cm`，高度取 `LINES=30`，屏幕含 `ESC[30;1H` | ok |
| 6 | 集成 | `2Gdd` 删除第 2 行；`2Gddu` 撤销恢复 | ok |
| 7 | 集成（负向对照） | `$TMPDIR` 不存在时 6 KiB yank 无法溢出到磁盘，put 不增加行（128 行不变） | ok |
| 8 | 集成（负向对照） | `$TMPDIR` 不存在时 `!` 过滤报 `[tempfile error]`，文件不变 | ok |
| 9 | **鸿蒙特有（消费者流程）** | levee 编辑 `consumer.c.in` → OHOS clang 编译为 AArch64 static PIE → 运行并校验编辑结果 | ok |

**鸿蒙特有测试 = 1（用例 9）**，完整消费者流程：
1. 被测包参与构建：test_package 以 OHOS profile 经 Conan 消费 `levee/4.0` 与 `ncurses/6.6`；
2. 工具产出参与消费者构建：levee 以脚本化按键编辑 `consumer.c.in`——`:1,$s` 替换 stamp 占位符、
   `4!!sort` 经 `/bin/sh` 排序 fruit 表（临时文件在 `$TMPDIR`）、`:r rows.inc` 读入 128 行后
   `128yy`（6 KiB > 4 KiB 内存 yank 缓冲，溢出到 `$TMPDIR`）再 `p` 复制——编辑结果由 profile 的 OHOS
   编译器编成 AArch64 static PIE；
3. 运行：程序逐项校验（stamp、fruit 严格有序、256 行、逐行取值），输出
   `consumer ok: stamp="edited by levee 4.0" fruit=apple,banana,fig,pear rows=256 sum=16512`；
4. 覆盖适配改动点：补丁 0003 的两条临时文件路径（HarmonyOS `/tmp` 只读），用例 7/8 以缺失 `$TMPDIR`
   做负向对照——本机 `/tmp` 可写，据此证明临时文件确实走 `$TMPDIR`；终端层走补丁 0001 改名后的
   静态 ncursesw；交付物是 static PIE。

执行证据（`reports/conan-create.log`，W3 同源）：

```
RUN: /usr/bin/bash .../test_package/test.sh .../p/b/leveea2252e5774c21/p/bin/levee .../ncurs780a5e6acf3cf/p/share/terminfo /data/service/hnp/bin/clang ...
[ok]   --version prints 'levee 4.0' and exits 0
...
       consumer ok: stamp="edited by levee 4.0" fruit=apple,banana,fig,pear rows=256 sum=16512
[ok]   levee-edited consumer.c built by /data/service/hnp/bin/clang and run: all edits verified
levee test_package: 9/9 checks passed
```

本机执行的就是 Conan 缓存里的交付物本身（static PIE，经 qemu-aarch64），**不是**另行重链的副本；
以 root 运行时 levee 在用户命名空间内以 uid 65534 执行（问题 6）。设备 CI 上 AArch64 原生执行、以普通用户
运行，走 test.sh 的非 root 分支：本机另以 `setpriv --reuid=65534` 对同一交付物实跑该分支，用例 1–8 通过、
用例 9 的 levee 编辑步骤通过（直接读取 `TERMINFO`，不经用户命名空间；结束后 `$TMPDIR` 为空）；其编译步骤因
本机 NDK 目录仅属主可访问而无法以 nobody 执行，改由 root 用同一 OHOS clang 编译这份 nobody 编辑出的
`consumer.c` 并经 qemu 运行，输出同为 `consumer ok: ... rows=256 sum=16512`。

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| ncurses | `ncurses/6.6`（本仓归档） | 静态宽字符 `libncursesw.a`（tinfo 合入），只用其 termcap 接口；运行期 terminfo 数据库在包内 `share/terminfo` |
| libc | OHOS musl | static PIE 静态链接 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/levee` | 1801136 B | AArch64 static PIE（无 PT_INTERP），BIND_NOW + GNU_RELRO + 不可执行栈；sha256 `c47e3d8ace8e5cc8624f7240c41dcebfcba4516eafce3127543ba33a82b79024`（本机构建） |
| `share/man/man1/levee.1` | 26115 B | 上游 `lv.1` |
| `licenses/COPYRIGHT` | 767 B | 上游许可原文（配方声明 `LicenseRef-levee`） |
| `share/doc/levee/README` | 2071 B | 上游说明 |

## 注意事项

1. **运行期需要 terminfo 数据库**：levee 静态链接 ncursesw，终端描述按 `TERMINFO`/`TERMINFO_DIRS`
   查找（ncurses/6.6 编译期默认 `//share/terminfo` 在设备上不存在）。ncurses 是 levee 的静态依赖，只依赖
   levee 的 Conan 消费方拿不到 ncurses 的 runenv，所以 test_package 显式 `requires("ncurses/6.6")` 取其
   `share/terminfo`；独立安装时需自行把 `TERMINFO` 指向一份 terminfo 数据库。找不到时 levee 退化为行模式；
   以 root 运行时 ncurses 会忽略 `TERMINFO`（问题 6）。
2. `!` 过滤与 `:!` 依赖 `/bin/sh`（`execl("/bin/sh", ...)`/`system()`）。
3. 临时文件（撤销溢出、大块 yank、`!` 过滤）位于 `$TMPDIR`，未设置时回退 `/tmp`——在 HarmonyOS PC
   上应保证 `$TMPDIR` 指向可写目录。
4. stdin 读到 EOF 时 levee 会在 `select+read` 循环里空转（上游行为）；脚本化使用必须以退出命令结尾，
   test.sh 另以 `timeout 60` 兜底。
5. conan-verify 的 G4/L2/L4/L5 本次被工具跳过（`conan list --format=json` 结果解析失败，见 feedback）；
   等效事实：L2 由 test_package 用例 1/2 覆盖，L4 用 `llvm-readelf -lhd` 核对为 DYN(PIE)+BIND_NOW+GNU_RELRO+GNU_STACK RW。
---

**编译结束**: 2026-09-27 07:22
**最终状态**: built
