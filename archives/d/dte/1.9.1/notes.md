# dte 1.9.1 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 GNU Make：`GNUmakefile` + `mk/*.mk`，无 configure）
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4（OHOS SDK / hnp 工具链；conan 侧按 R33 从 `tools.build:compiler_executables` conf 取，不读 shell `$CC`）
- 状态: built

## 编译步骤

- 源码: `https://deb.debian.org/debian/pool/main/d/dte/dte_1.9.1.orig.tar.gz`
  （sha256 `80d2732269a308b5e1126ecc16c28cda032864f625a95184821a73c054f81a2d`，Debian 官方池，http/https 实测同哈希）
- conan 配方: `build()` 依次 `make -j1 CC=<clang> TERMINFO_DISABLE=1` → `make check -j1 …`
  （上游测试必须在 build() 内真实执行）；`package()` 手工 `copy()` `bin/dte` 与
  `share/man/man1/dte.1`、`share/man/man5/{dterc.5,dte-syntax.5}` 后 `chmod 0755`。
- 本地 14 步驱动: `ohc-run.py build dte 1.9.1` —— Step2 应用补丁、Step4 make、
  Step5 make install（DESTDIR 模式）、Step6 安全冒烟、Step7 `make check`、Step8 staging 验证全绿。
- 收尾: `conan-verify`（G1 配方完整性 / G2 干净构建含 test_package / G3 无系统同名库 / G4 产物完整性）→
  `finish`（W3 本地 CI 模拟通过）→ `graph validate`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 裸 `make` 报 `cc: No such file or directory` | GNU make 内建 `CC=cc`，本平台无 `cc` 别名 | 构建期显式 `CC=clang`；conan 侧从 conf 取编译器（R33） |
| 2 | 链接 `ld.lld: duplicate symbol: erase`（连 `ncurses/6.6`） | conan ncurses 静态库的 `lib_gen.c` 定义 curses API，与 dte 自身 `erase` 同名冲突 | 判零依赖：改用上游自带开关 `TERMINFO_DISABLE=1`（零补丁），dte 落到内置 xterm/ecma48 驱动 |
| 3 | 驱动 Step5 报「安装无产物」 | 上游 `prefix ?= /usr/local`，与驱动 staging 前缀（`$DESTDIR/$DEFAULT_PREFIX`）不一致 | 起驱动前 `export prefix=$DEFAULT_PREFIX`（make 的 `?=` 不覆盖环境变量） |
| 4 | `make: install: No such file or directory` / `Error 127` | `install(1)` 不在 PATH（`/bin` 不在 PATH，toybox 版位于 `/bin/install`） | 任务级 shim 目录 `ln -s /bin/install` 并置于 PATH 最前；配方 `package()` 彻底改为手工 copy |
| 5 | 驱动 Step8 与 conan-verify L2 冒烟失败 | 上游仅实现 `-V`/`-h`，探针用 `--version`/`--help` 时 getopt 报 `unrecognized option: -` 且非零退出 | 补丁 `0001-src-main.c.patch`：仅在 `argc == 2` 形态下加 GNU 长选项别名（复用既有条目先例） |
| 6 | `self.conf.get("tools.build:compiler_executables:c")` 报 `does not exist in configuration list` | 该 conf 注册为 dict，子键路径读取不被接受 | 整读 dict 再取 `"c"` 键（`default={}` + `check_type=dict`） |
| 7 | `conan create` 报 `Patch file does not exist` | `finish` 的 `refresh-patch` 把补丁改名为 `0001-src-main.c.patch`，conandata 仍指向旧名 | conandata `patch_file` 对齐刷新产物，并把重命名落进提交 |

## 源码修改

- `patches/0001-src-main.c.patch`（`patch_type: portability`，`platform_only: True`，无条件应用）：
  在 `src/main.c` 的 `main()` 中、`init_editor_state()` 之后新增两个 `argc == 2` 分支，
  分别处理 `--version` 与 `--help`（打印与 `-V`/`-h` 完全相同的内容后 `return 0`）；
  不改任何既有短选项解析路径，常规用法行为不变。

## 依赖版本

- 外部运行/编译依赖: **无**（单二进制零依赖）
  - terminfo: 上游 `TERMINFO_DISABLE=1` 关闭（平台无 terminfo 库与 terminfo 数据库）
  - iconv: 由 libc 提供（实测 `iconv_open`/`iconv` 编译+运行通过）
  - 曾评估 `ncurses/6.6`（配方与二进制均已发布），因问题 2 放弃

## 验证结果

```bash
make check                     # 上游单元测试：build/test/test，rc=0（75 个测试函数 / 862 断言全过）
conan create …                 # G1/G2/G3/G4 全过；test_package 真实执行
bash test_package/test.sh      # dte -V/-h/-B/-b rc 冒烟 + pty 原始模式探针
python3 pty_probe.py           # raw_mode=True ICANON=N ECHO=N ISIG=N winsz=80x24 首帧输出/输入重绘
ohc-run.py build dte 1.9.1     # Step1-8 全绿（Step5 安装完成 bin=1）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `packaging/dte-1.9.1-ohos-aarch64.tar.gz` | 52764 B | aarch64 OHOS 打包产物（bin/dte + man 页面） |

## 注意事项

- 平台无 terminfo 数据库：非 xterm 类 `TERM` 会回退内置驱动，常用 `TERM=xterm*` 全功能。
- 驱动 Step5 需要 `export prefix=$DEFAULT_PREFIX` 与 PATH 内 `install` shim，两者缺一即「安装无产物」。
- `finish` 的 `refresh-patch` 会按编辑追踪重写补丁文件名，改名后必须同步 conandata 再提交。

## 适配知识（主理-N 链主，2026-10-08）

- **构建系统实为纯 GNU Make**（`GNUmakefile` + `mk/*.mk`），不是登记时写的 autotools：源码树里没有 `configure`/`configure.ac`，上游 README 的构建方式是 `make && make install`。manifest `build.system` 已改为 `makefile`。
- **能力墙判定＝甲（实测）**：`/dev/tty` 存在（0666）但在非交互会话 open 报 ENXIO（本会话无控制终端）；`openpty()` 可用；fork+`setsid`+`TIOCSCTTY` 后 `/dev/tty` 打开成功、`tcgetattr` 正常；`TIOCGWINSZ`/`TIOCSWINSZ` 24x80 双向生效。真跑 `dte` 进 pty：`raw_mode=True ICANON=N ECHO=N ISIG=N`、首帧 ANSI 画面输出、输入后重绘 —— termios 原始模式编辑循环有真实可用路径 ⇒ 完整交付。
- **terminfo 处理**：本机与 OHOS 均无 `libtinfo`/`libncurses`/terminfo 数据库；dte 的 `mk/build.mk` 默认回退 `-lcurses`（链接必败）。改用**上游自带开关 `TERMINFO_DISABLE=1`**（`#ifdef` 分支，零补丁零改动），无 terminfo 时 dte 落到内置 xterm/ecma48 驱动（`TERM=xterm*` 全功能）。曾试链接 conan `ncurses/6.6`（配方与二进制均已发布），因 `libncursesw.a` 的 `lib_gen.o` 与 dte 自身 `erase` 符号重复定义而失败 —— 与"单二进制零依赖"的包定位一致，故判零依赖。
- **iconv**：`uname -s = HarmonyOS` ⇒ makefile 不加 `-liconv`；实测 libc 提供 `iconv_open/iconv`（编译+运行通过），无需 `libiconv` 依赖。
- **CC 解析坑**：裸 `make` 的 `CC` 解析成 make 内建 `cc`（本机不存在），必须显式 `CC=clang`；conan 配方按 R33 从 `tools.build:compiler_executables` conf 整读 dict 取编译器。
- **上游测试**：`make check` 构建并运行 `build/test/test` 单元测试，本机 rc=0 全绿。
---

**编译结束**: 2026-10-08 15:05
**最终状态**: built
