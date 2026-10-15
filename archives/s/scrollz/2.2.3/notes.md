# scrollz 2.2.3 适配笔记

## 编译环境
- 构建系统: autotools（上游自带预生成的 autoconf 2.13 `configure`，无 automake）
- 编译日期: 2026-10-15
- 编译器: clang / clang++（clang 15，目标 aarch64-unknown-linux-ohos）
- 平台: OHOS 6.0 / aarch64，**原生 build=host**（非交叉编译）
- 状态: built（本地 conan-verify 通过；未发布，未提 PR）

## 上游测试清点（R51）

上游 scrollz 2.2.3 源码树**没有任何测试套件**，清点证据（在解包后的源码树上实测）：

```text
$ find <src> -type f \( -iname "*test*" -o -iname "*check*" -o -iname "*.t" \) | wc -l
0
$ grep -nE "^(check|test|check-am|test-am|check-recursive)\s*:" <src>/Makefile.in
(无匹配)
$ grep -nE "^(check|test)\s*:" <src>/source/Makefile.in
(无匹配)
$ ls <src>/source/*.c | wc -l
67
```

- 根 `Makefile.in` 的目标只有 `all/install/installbin/installhelp/installman/
  installeverything/clean/distclean/lint/autoconf/autoheader/export` 等，无
  `check`/`test` 目标。
- `source/Makefile.in` 只构建 `scrollz`（主程序）与 `ircflush`/`ircio`/`wserv`
  辅助程序，同样无 `check`/`test` 目标。
- 全树 0 个文件名含 test/check 的文件。

因此 `upstream_test_in_build: false`，`upstream_tests: []`。上游测试计数按同一张表：
`TOTAL = PASS+FAIL+SKIP+NOT_RUN = 0+0+0+0 = 0`（无上游用例可跑，非"跳过"）。
消费者/运行时验证全部落在 `test_package/`（见下）。

## 编译步骤

1. `source()`：`get()` 下载官方 tag tarball（`ScrollZ-2.2.3.tar.gz`，
   sha256 `cba8cdbf…b2a`），`strip_root=True`。
2. `build()`：
   - `apply_conandata_patches()` 应用 `patches/0001-configure.patch`；
   - `umask 022`（OHOS 沙箱 077 下 `config.status` 无法写入 0700 目录）；
   - `Autotools.configure()` → 生成根 `Makefile` 与 `source/Makefile`；
   - `Autotools.make(args=["-j1"])` → 编译 `source/scrollz`。
3. `package()`：`autotools.install()` → 安装 `bin/scrollz`（→ `scrollz-2.2.3`）、
   `share/scrollz/{help,script,doc}`、`share/man/man1/scrollz.1`。

关键 configure 变量（由 `generate()` 注入）：
- `CPPFLAGS=-I<ncurses>/include`（经 `self.buildenv`）：本项目的 `configure` 是
  老 autoconf 2.13，**不接受 `VAR=value` 形式的命令行赋值**（会报
  `invalid host type`），只能走环境变量。
- `LDFLAGS=-L<ncurses>/lib`（经 `AutotoolsToolchain.extra_ldflags`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 报 "Can not find curses or termcap library"（G2 FAIL） | OHOS 无系统 libncurses；已发布的 ncurses 配方是**静态宽字符**版，只有 `libncursesw.a`，而上游 `AC_CHECK_LIB(ncurses, tgetent)`/`-lncurses` 探测的名字不存在 | 补丁 `0001-configure.patch`：把 tgetent 探测与成功分支里的 `-lncurses` 改成 `-lncursesw`（仅改库名，探测逻辑不动） |
| 2 | `term.c:512` 等 `incompatible integer to pointer conversion`（隐式 int 的 `tgetstr/tgetnum`） | `configure` 的头文件探测（`AC_CHECK_HEADERS termcap.h`、`AC_EGREP_CPP curses.h`）走 `$CPP`，只看 `$CPPFLAGS`，不看 `$CFLAGS`；此前只把 `-I` 放进 CFLAGS，导致 `HAVE_TERMCAP_H`/`INCLUDE_CURSES_H` 都没定义，`tgetstr/tgetnum` 无原型（隐式返回 int） | `generate()` 里用 `self.buildenv.define("CPPFLAGS", "-I<ncurses>/include")`（在 `tc.generate()` 之前）注入 CPPFLAGS；改后 `checking for termcap.h... yes`，`irc.h` 经 `<termcap.h>` 拿到原型 |

> 备注：E490（autotools helper 脚本可执行位）在本例不触发——GitHub tag
> tarball 保留了 `configure`/`bsdinstall`/`mkinstalldirs` 的 0755 执行位，
> `configure` 与 `make install` 均正常执行。

## 源码修改

- `patches/0001-configure.patch`（portability）：`configure` 中 tgetent 探测
  与成功赋值两处 `-lncurses` → `-lncursesw`（+2/-2）。由
  `ohc-run.py refresh-patch --auto` 生成。
  修改点在生成的 `configure` 上而非 `configure.in`，原因：上游 `configure`
  由 autoconf **2.13** 生成，本机只有 autoconf 2.72，无法原样重生成
  （2.13 的 `AC_INIT(file)`/`acconfig.h` 旧写法不被 2.72 接受）；仓库内
  同类先例众多（如 alpine 的 `0001-configure-ncursesw.patch`）。

## 依赖版本

- `ncurses/6.5`（ohpcd，静态宽字符；`libncursesw.a` + curses.h/termcap.h）
- 链接边界：scrollz 只 `NEEDED libc.so`，ncurses 以静态库链入，无 `.so` 污染。

## 验证结果

```text
$ porting run ... ohc-run.py conan-verify scrollz 2.2.3 --profile <ohos-aarch64>
  G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS —— exit 0
  configure: checking for termcap.h... yes
             checking for tgetent in -lncurses... yes
  ======== Launching test_package ========
  --- scrollz test_package smoke test ---
  PASS: T1 scrollz --version prints 'ircII version ...' (rc=0)
  PASS: T1 scrollz --version exits 0
  PASS: T2 scrollz -v prints version banner (rc=0)
  --- smoke test: ALL PASS ---
```

消费者测试（test_package，3 断言）：TOTAL=3，PASS=3，FAIL=0，SKIP=0，NOT_RUN=0。
上游测试：TOTAL=0（上游无测试套件，见清点）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/scrollz` → `bin/scrollz-2.2.3` | 主程序（aarch64 OHOS PIE，GNU_RELRO + NX，仅依赖 libc.so） |
| `share/scrollz/{help,script,doc}` | 运行期脚本/帮助/文档 |
| `share/man/man1/scrollz.1` | man 手册 |

## 注意事项

- 运行期终端初始化需要 terminfo（ncurses 包的 `lib/terminfo`）与设备 TTY；
  `-v/--version` 在任何终端初始化之前就 `exit(0)`，故 test_package 用它做
  非交互冒烟（真实执行二进制并断言输出，非空壳）。
- 交互式 IRC 会话未在真机演练（无 IRC 服务器/无交互终端），本任务只覆盖
  构建 + CLI 冒烟；深度交互行为未验证，属未验证项。
