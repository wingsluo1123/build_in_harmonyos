# termdebug 2.2 适配笔记

## 1. 上游是什么

termdebug 是 G.P. Halkes 写的终端录制/回放工具集（Tilde Terminal Toolkit 作者），主页
<https://os.ghalkes.nl/termdebug.html>，GPLv3。5 个命令：

| 命令 | 作用 |
|---|---|
| `tdrecord` | 启动一个程序并录制它的输入/输出 |
| `tdreplay` | 回放一段录制的输入 |
| `tdview` | 显示一段录制的输出 |
| `tdrerecord` | 回放旧录制的输入，同时录制成新录制 |
| `tdcompare` | 离线比较两段录制 |

5 个命令是**同一个 ELF**：`src/common.c` 的 `main()` 按 `basename(argv[0])` 分派到
`tdrecord_main` / `tdreplay_main` / …。上游 `make install` 用
`cd $(DESTDIR)$(prefix)/bin && ln -s termdebug tdXxx` 建软链。

**没有官方 git 仓库**（Debian salsa 的 `termdebug.git` 只有 `debian/` 打包目录），也没有
GitHub release；唯一一手归档是 `https://os.ghalkes.nl/dist/termdebug-2.2.tar.bz2`
（2026-10-05 实测 HTTP 200 / 148192 字节 / Last-Modified 2013-06-23）。Debian 的
`termdebug_2.2+dfsg.orig.tar.gz` 是剔掉文档后的重打包，sha256 不同，本配方不用它。

## 2. 构建系统：自研 configure，不是 autotools

tarball 里**没有** `configure.ac` / `Makefile.am`，只有生成好的 `configure`（533 行
`#!/bin/sh`）+ `Makefile.in` + `config.pkg`。这是 Tilde Terminal Toolkit 的配置框架：
`config.pkg` 声明 `EXTENSIONS="c pkgconfig_dep verbose_compile"`，`configure` 逐个跑
`basic_test_*` / `config`，最后 `create_makefile` 用 sed 把探测结论写进 `Makefile`：

- `CONFIGFLAGS=` → `-DHAVE_CURSES` / `-DHAVE_UNISTRING` / `-DHAVE_CAIRO` 等宏
- `CONFIGLIBS=` → `-lncursesw … -lunistring <cairo libs> <pangocairo libs>`（+ 可选 `-lutil`）
- `OPTOBJECTS=` → 可选能力对应的 .o

## 3. 适配点

### 3.1 必须就地构建

`configure`、`Makefile.in`、`config.pkg` 三者用**相对路径**互相引用
（`cat Makefile.in | sed -f .sedscript > Makefile`、`clean ${EXT}.config`、
`[ -d config.d ]` 这类检查）。Conan 的 build folder 与 source folder 是两个目录，
所以配方在 `self.source_folder` 里跑 configure + make。

同款处理见 `archives/m/magicrescue/1.1.10/conanfile.py` 与
`knowledge/DRAFT-magicrescue-1.1.10-custom-configure-source-root-cwd.md`。

### 3.2 CFLAGS 会被 sed 整行替换

`sed_rules_c()` 做 `replace_default CFLAGS "${CFLAGS}"`，即用环境里的 `$CFLAGS`
**替换** `Makefile.in` 里整行 `CFLAGS=-O2 -Isrc`。所以配方导出
`<依赖 -I/-D> -O2 -Isrc`：既拿到依赖路径，又不丢优化级别和 `src/` 相对包含路径。

### 3.3 Conan 的 VirtualBuildEnv 不给 host 依赖的 flags

Conan 2 的 `VirtualBuildEnv` 在 build scope 只 compose：profile 的 `buildenv`、
build_requires 的 `buildenv_info`/`runenv_info`、host_requires 的 `buildenv_info`。
**不会**把 host 依赖 `cpp_info` 里的 `-I/-L/-D` 变成 `CC/CFLAGS/LDFLAGS`
（CMake/AutotoolsToolchain 是另一条路，会额外生成自己的 env 脚本）。
自研 configure + 自己写的 Makefile 不走 Toolchain，所以配方用
`dep.cpp_info.aggregated_components()` 自己聚合后导出。

### 3.4 configure 认识的 pkg-config 包名和依赖声明的不一样

configure 依次找：

1. `pkgconfig tinfo` → 失败 → `pkgconfig ncurses` → 失败 → 退到 `-ltinfo` / `-lcurses` /
   `-lncurses` 三次裸链接探测
2. `-lunistring`
3. `pkgconfig cairo`
4. `pkgconfig pangocairo`

而依赖配方声明的是：

- `ncurses/6.6` → `cpp_info.set_property("pkg_config_name", "ncursesw")`
- `pango/1.58.2` → `pkg_config_name = "pango"`

即 `PkgConfigDeps` 生成的是 `ncursesw.pc` 和 `pango.pc`，configure 找不到。
**解法**：在 `generators_folder` 写两个只含 `Requires` 的转发 `.pc`
（`ncurses.pc -> ncursesw`、`pangocairo.pc -> pango`），路径全部由被转发者提供。
这是 `pango/1.58.2` 自己给 `cairo-ft` / `cairo-fc` 补转发 `.pc` 的同一手法 ——
不改上游、不改依赖包。

### 3.5 探测失败不报错 → 必须硬断言

configure 的能力探测失败时**只打一行 warning 然后继续构建**：

```
!! Warning: compiling without curses. This means visual compare will not be available.
```

也就是说一个"构建成功"的 termdebug 很可能根本没有 visual compare / 图片输出能力。
配方因此在 `./configure` 之后、`make` 之前解析生成的 `Makefile`，断言
`OPTOBJECTS` 里这 5 项全在：

| 能力 | .o |
|---|---|
| curses（terminfo 访问） | `src/curses_handling.o` |
| libunistring（字符宽度） | `src/window.o` |
| libunistring（字符串表输出） | `src/write_stringlist.o` |
| cairo + pangocairo（PNG 图片输出） | `src/write_image.o` |
| pthread（picture series） | `src/picture_queue.o` |

缺任何一个就抛 `ConanException`，不产出包。

### 3.6 `-lutil` / iconv 不用管

musl OHOS 把 `openpty` / `forkpty` / `login_tty` 收在 libc 里。configure 用
`TESTLIBS=-lutil` 探测，探不到就自动退到 `posix_openpt`，再不行看 `/dev/ptmx` ——
不需要为 `-lutil` 做适配。iconv 同理（configure 先试无参，失败才试 `-liconv`）。

### 3.7 静态 ncurses 的链接顺序

`ncurses/6.6` 是 static-only 包（`libncursesw.a`，`shared: False`）。静态链接顺序必须是
"消费者在前、核心在后"，该配方 `cpp_info.libs = ["formw", "menuw", "panelw", "ncursesw"]`
已经排好，`pkg-config --libs ncurses` 会原样给出。cairo/1.18.4.2 与 pango/1.58.2 是
shared，`-l` 即可，运行时由 DT_NEEDED 解决。

### 3.8 真机无 pkg-config

HMBS 只注入 cmake/make/ninja/python3，真机没有系统 pkg-config；制品仓的 pkgconf 只装
`bin/pkgconf`、没有 `pkg-config` 别名。所以 `tool_requires("pkgconf/3.0.5")`，并在
`build()` 里按 `tools.build:pkg_config` → pkgconf 包 → PATH 的顺序做 `--version`
握手，落一个同名 `pkg-config` shim（`exec <pkgconf> "$@"`）并把
`PKG_CONFIG_PATH=<generators_folder>` 显式导出。
`pango/1.58.2` 的 `_ensure_pkg_config_shim` 是同款先例。

### 3.9 CLI 包要签名

真机 HMDFS 拒绝执行未签名 ELF（cronutils 首轮 `PermissionError: [Errno 13]`）。
`package()` 对最终 `bin/termdebug` 做：

```sh
llvm-objcopy --remove-section .codesign bin/termdebug   # 有工具时先清旧段
binary-sign-tool sign -inFile bin/termdebug -outFile bin/termdebug.signed -selfSign 1
```

5 个命令是同一 ELF 的 argv[0] symlink，签名一次即可。本地交叉构建环境没有
`binary-sign-tool`，此时只发 warning 并继续（不谎称真机可执行）。

### 3.10 本机不能真跑：qemu + 旧 musl loader 缺 _FORTIFY 符号

本机 WSL 注册了 `binfmt_misc + qemu-aarch64`，所以"能不能执行 aarch64 ELF"的
naive 探测会给出错误答案。实测：手工执行 `bin/termdebug` 会 exit 127，并刷屏

```
Error relocating .../cairo-1.18.4.2/p/lib/libcairo.so.2: __vsnprintf_chk: symbol not found
```

—— 制品仓的 `cairo/1.18.4.2` 引用了 10 个 `__*_chk`（`_FORTIFY_SOURCE`）符号。本机实际
用的加载器是 `/lib/ld-musl-aarch64.so.1`（指向 `/opt/ohos-guest` 的旧 musl），它没有这些
符号；而 **DevEco SDK 的 `libc.so` 三个都有**（`__vsnprintf_chk` / `__memcpy_chk` /
`__strlen_chk`），真机 OHOS loader 同理。所以这是**本地模拟环境的缺陷，不是包缺陷**。

因此 test_package 用 `can_run(self)` 门控运行段（profile 里显式设了
`tools.build.cross_building:can_run=false`），并且静态段**任何环境都跑**、不是空壳：

- 静态段 25 条断言恒做，包含"五个可选能力是否真的链进 ELF"的符号检查
  （`setupterm` / `uc_width` / `uc_is_general_category_withtable` /
  `cairo_image_surface_create` / `cairo_surface_write_to_png` /
  `pango_cairo_create_layout` / `pthread_create`），这在能力上等价于运行段那三条
  `--help` 探针，只是走的是字节而不是执行。
- 运行段（3 条能力探针 + 6 个 `--help` + 5 个 `-V` + 1 条分派拒绝）留给真机 CI，
  本机明确打印 SKIP 原因，不冒充通过。

### 3.11 tarball 里的预编译残留

`src/tdcompare` 是上游 2013-06-23 打进 tarball 的一个 x86-64 预编译 ELF（208047 字节），
既不在 `OBJECTS` 也不在 `OPTOBJECTS` 里，纯残留。配方在 configure 前删掉，避免质量门禁
把它误认成构建产物。

## 4. 依赖与版本钉死

```
ncurses/6.6      static-only，armv8 OHOS Release 二进制在仓
libunistring/1.0 1.4.2 没有 OHOS 二进制，所以用 1.0
cairo/1.18.4.2     pango/1.58.2 要求 cairo/1.18.Z 且 shared=True
pango/1.58.2     pangocairo.pc 的来源
pkgconf/3.0.5    tool_requires，真机 pkg-config 桥接
```

`libunistring/1.4.2` 在 ohpcd 只有 recipe 没有 OHOS 二进制（`conan list -r=ohpcd` 的
`os: OHOS` 计数为 0），按"依赖未发布完整就放弃"的红线不选它，改用同样有 OHOS 二进制的 1.0。

## 5. 测试

**上游没有任何测试目标** —— `Makefile` 只有 `all` / `clean` / `dist-clean` / `install`，
tarball 里也没有 `tests/`。所以 L1 上游测试按 `ci/config/no_official_test.txt` 白名单豁免，
并且**不能**把 test_package 说成"上游测试通过"。

真实覆盖在 `test_package/test_termdebug.py`（20 条断言）：

恒做（交叉构建与真机都跑）：

1. `bin/termdebug` 存在、可执行
2–6. 5 个 argv[0] symlink 存在且 `readlink` 为 `termdebug`
7. `bin/termdebug` 是 ELF64 / little-endian / `EM_AARCH64`(0xB7)
8. 5 个 man page 装到 `share/man/man1/`
9. `README` / `COPYING` / `Changelog` 装到 `share/doc/termdebug/`
10–12. 符号表里能看到 curses（terminfo）、libunistring、cairo、pango、pthread 的代表符号
   —— 即"五个可选 .o 真的进了包"，静态验证能力没被砍
13. 包里没有 x86-64 预编译残留

`can_run()` 为真时再加：

14–18. 5 个命令 `--help` 的 Usage 行（顺带证明 argv[0] 分派生效）
19. `tdreplay --help` 含 `-v, --visual-compare`（HAVE_CURSES && HAVE_UNISTRING）
20. `tdreplay --help` 含 `-p<name>, --picture=<name>`（HAVE_CAIRO）
21. `tdreplay --help` 含 `-P<name>, --picture-series=<name>`（HAVE_CAIRO && HAVE_PTHREAD）
22. `-V` 输出含 `Copyright (C)` 与版本号
23. 直接运行 `termdebug`（不叫 symlink 名）输出 "Please use the tdrecord, … symlinks"

第 19–21 条是这套断言的关键：`tdreplay` 的 `--help` 文本是按
`HAVE_CURSES`/`HAVE_UNISTRING`/`HAVE_CAIRO`/`HAVE_PTHREAD` 条件编译的，
所以 `--help` 本身就是最便宜、最可靠的能力探针 —— 不需要真的去跑录制回放流程。
