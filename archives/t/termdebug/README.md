# termdebug

## 简介

termdebug 是 G.P. Halkes 的终端程序输入/输出录制与回放工具集。它的价值在于
**同时录输入和输出** —— `termrec`/`nethack-recorder`/`script` 这类工具只录输出，
而调试交互式终端程序时输入往往才是关键。

## 功能概述

| 命令 | 作用 |
|---|---|
| `tdrecord` | 启动一个程序并录制它的输入/输出 |
| `tdreplay` | 回放一段录制的输入，可选按显示效果（visual compare）校验输出 |
| `tdview` | 显示一段录制的输出 |
| `tdrerecord` | 回放旧录制的输入，同时录制成新录制 |
| `tdcompare` | 离线比较两段录制（字节级或按显示效果） |

5 个命令是**同一个 ELF** 的 argv[0] 符号链接（`src/common.c` 的 `main()` 按
`basename(argv[0])` 分派）。

## 使用

```console
$ tdrecord -o session.dat vim notes.txt
$ tdreplay session.dat
$ tdcompare -v old.dat new.dat
```

## 产物

| 路径 | 说明 |
|---|---|
| `bin/termdebug` | 唯一的 ELF，5 个命令都是它的 argv[0] symlink |
| `share/man/man1/td*.1` | 6 个 man page（`termdebug.1` + 5 个命令） |
| `share/doc/termdebug/` | 上游 `README` / `COPYING` / `Changelog` |

## 依赖

编译期（全部来自制品仓 ohpcd）：

- `ncurses/6.6` — terminfo 访问（`setupterm`/`putp`），static-only
- `libunistring/1.0` — Unicode 字符宽度（visual compare 需要）
- `cairo/1.18.4.2` + `pango/1.58.2` — 把差异渲染成 PNG（`tdreplay -p` / `tdcompare -p`）
- `pkgconf/3.0.5`（tool_requires）— 上游 configure 只认 `pkg-config`

## OHOS 适配

### 适配要点

- **构建系统**：Tilde Terminal Toolkit 的自研 `configure`（`config.pkg`），
  不是 autotools —— tarball 里只有 `configure` + `Makefile.in`，没有 `configure.ac`
- **就地构建**：`configure`/`Makefile.in`/`config.pkg` 相对路径互引，只能在源码根目录
  运行；配方改用 `cwd=self.source_folder`（与 `magicrescue/1.1.10` 同款）
- **CFLAGS 被 sed 整行替换**：配方导出 `<依赖 -I/-D> -O2 -Isrc` 补回上游默认值
- **pkg-config 包名错位**：configure 找 `tinfo`/`ncurses`/`cairo`/`pangocairo`，
  而依赖声明的是 `ncursesw`/`pango`/`cairo`/`pango` → 配方补两个转发 `.pc`
- **降级静默**：configure 探测失败只打一行 warning 并继续，会产出功能残缺的包
  → 配方构建后硬断言 5 个可选 `.o` 全部产出，缺一即失败
- **签名**：真机 HMDFS 拒绝执行未签名 ELF，`package()` 对 `bin/termdebug`
  做 `binary-sign-tool -selfSign 1`
- **上游源码零改动**：无任何补丁，适配全在构建环境层

### 测试

- 上游**没有**任何测试目标（`Makefile` 只有 `all`/`clean`/`dist-clean`/`install`），
  L1 上游测试按 `ci/config/no_official_test.txt` 白名单豁免
- 消费者测试 `test_package/test_termdebug.py`，20+ 条断言：
  包内容 / ELF64-AArch64 / 5 个 argv[0] symlink / man page / 静态链接符号；
  可运行时再执行 6 个 `--help`（含 `tdreplay --help` 里的 `--visual-compare`、
  `--picture=`、`--picture-series=` 三条**条件编译能力探针**）、5 个 `-V`，
  以及直接运行 `termdebug` 的分派拒绝消息

## 参考

- 主页：<https://os.ghalkes.nl/termdebug.html>
- 源码归档：<https://os.ghalkes.nl/dist/termdebug-2.2.tar.bz2>
  （sha256 `06bd95bb6eeb1581bc4fbadc0111500f1d016ca0ba34c21ddf39b78857de5969`）
