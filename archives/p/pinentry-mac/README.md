# pinentry-mac 1.3.1.1 — HarmonyOS PC 适配

## 这是什么

`pinentry` 是 GnuPG 用来输入 PIN / passphrase 的对话框集合，`gpg-agent` 通过
**Assuan 协议**（stdin/stdout）与之通信。

本任务名 `pinentry-mac` 指向 **GPGTools/pinentry** 仓库的 `v1.3.1.1` tag。
需要澄清一个容易误判的点：

> **GPGTools/pinentry 与 gnupg.org 发布的 pinentry 是同一棵源码树**，
> 只是打包 tag 不同。二者顶层目录完全一致（`curses/ tty/ qt/ qt4/ qt5/
> gtk+-2/ gnome3/ efl/ emacs/ tqt/ w32/ macosx/ secmem/ pinentry/ doc/`）。

其中 `macosx/` 是 GPGTools 维护的 macOS 专属 GUI 前端（Cocoa / Objective-C /
`.xib`→`ibtool`），它由 `configure.ac` 的 host 闸门控制：

```
configure.ac:127    *-apple-darwin*)      # 只有 Apple 宿主才置位
configure.ac:825    pinentry_macosx=no
configure.ac:826    test $have_macosx_system = yes && pinentry_macosx=yes
configure.ac:827    AM_CONDITIONAL(BUILD_PINENTRY_MACOSX, ...)
```

因此在 `aarch64-linux-ohos` 上 `pinentry_macosx=no`、`macosx/Makefile` 不生成。
**但这只是排除一个子目录** —— 顶层 `SUBDIRS`（`Makefile.am:120`）是变量拼接：

```
SUBDIRS = m4 secmem pinentry ${pinentry_curses} ${pinentry_tty} \
          ${pinentry_emacs} ${pinentry_gtk_2} ${pinentry_gnome_3} \
          ${pinentry_qt} ${pinentry_qt5} ${pinentry_qt4} ${pinentry_tqt} \
          ${pinentry_w32} ${pinentry_fltk} ${pinentry_efl} ${pinentry_macosx} ${doc}
```

`curses/` 与 `tty/` 是**纯 C 前端**，可在 OHOS 上构建。本配方正是构建这两个前端。

## 产物

| 文件 | 说明 | 架构 |
|---|---|---|
| `bin/pinentry-curses` | ncurses 全屏 PIN 输入前端（默认） | ELF 64-bit LSB pie executable, ARM aarch64 |
| `bin/pinentry-tty` | 无 ncurses 的纯终端前端 | ELF 64-bit LSB pie executable, ARM aarch64 |
| `bin/pinentry` | → `pinentry-curses` 的符号链接 | — |

## 依赖

| 依赖 | 版本 | 说明 |
|---|---|---|
| libgpg-error | 1.55 | 上游要求 ≥ 1.16（`configure.ac:247`） |
| libassuan | 3.0.2 | 上游要求 ≥ 2.1.0（`configure.ac:267`） |
| ncurses | 6.6 | 仅 `pinentry-curses` 需要 |

## 构建要点

1. **tarball 不含 `configure`**（只有 `configure.ac`）→ `source()` 必须先跑 `autoreconf -fi`。
2. **顺序陷阱**：`autoreconf -fi` 会重新生成 `build-aux/config.sub`，**冲掉**已打的
   HarmonyOS 补丁。所以必须是 `source()` 里 autoreconf → `build()` 里
   `apply_conandata_patches`。
3. **必须显式 `--target=aarch64-linux-ohos`**：OHOS SDK 的 clang 默认 target 是
   `x86_64-unknown-linux-gnu`，会调宿主 `/usr/bin/ld` 并报
   `cannot find Scrt1.o / crti.o / -lc`。还需补
   `-L<sysroot>/usr/lib/aarch64-linux-ohos`（crt 与 libc 在该子目录）。
4. **依赖的 `*-config` 脚本不可信**：实测 `libassuan-config --libs` 无视 `--prefix`
   返回 `-L/lib -lassuan`。故用 `GPG_ERROR_LIBS` / `LIBASSUAN_LIBS` /
   `NCURSES_LIBS` 等变量显式覆盖 configure 探测结果。
5. **`NCURSES_LIBS` 不能带 `-ltinfo`**：OHOS 的 ncurses/6.6 制品只有静态
   `libncursesw.a`、没有 libtinfo，而 configure 会探测出 `-lncursesw -ltinfo`
   → 链接报 `unable to find library -ltinfo`。
6. **`--disable-doc`**：否则 `pinentry.texi:80: undefined flag: UPDATED` 让 `make` 失败。
7. `/bin/sh` 不可用 → config 脚本 shebang 改为 `/data/service/hnp/bin/bash`，
   并设 `CONFIG_SHELL`/`SHELL`。

## 测试

上游 tarball **不含 `tests/` 目录**（实测 `tar tzf v1.3.1.1.tar.gz | grep -ci test` = 0，
顶层 `SUBDIRS` 不含 tests，全树无 `TESTS=` / `check_PROGRAMS` 定义），
因此 `make check` 是 no-op。

替代方案是驱动**上游真实对外接口**（gpg-agent 用的 Assuan 协议）：

- `test_package/run_upstream_tests.py` —— 16 项断言，覆盖 `pinentry-tty` 与
  `pinentry-curses` 两个前端：握手 / `GETINFO version` / `GETINFO pid` /
  未知命令 → `ERR` / 参数错误 → `ERR` / `GETPIN` 返回所输入的 PIN /
  `CONFIRM` / `MESSAGE`。
- `test_package/test_pinentry.c` —— clang 现场编译的消费者探针，真实执行两个前端的
  `--version` 并断言版本号（R34 反空壳）。

实测结果见 `manifest.yaml` 的 `test_note`。
