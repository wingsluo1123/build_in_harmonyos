# ncurses 6.5 适配记录

## 编译状态

状态：built

## 配方说明

- 构建系统：Autotools。
- ncurses 6.5 的 `configure`/`config.status` 依赖源码树内的
  `include/`、`ncurses/`、`panel/`、`menu/`、`form/`、`misc/` 等目录生成
  Makefile；配方使用 in-source build，避免 out-of-tree `build-release`
  目录下缺少这些源码子目录而导致 `cd include` 失败。
- 构建产物：静态 wide-character 库 `formw`、`menuw`、`panelw`、`ncursesw`。
- 关键配置：`--enable-widec`、`--enable-overwrite`、`--without-shared`。
- `configure` 显式传入 `--srcdir=${source_folder}`，避免 OHOS CI 上
  ncurses 自动推导 `srcdir` 后在 `include/Makefile` 中生成异常
  `$(srcdir)/Caps` 路径，导致 `curses.h` 依赖找不到 `Caps`。
- 禁用 `progs/tests/manpages`，避免交互式终端程序、数据库安装和测试运行阶段差异。
- 构建阶段显式传入 `--build/--host=aarch64-unknown-linux-ohos`，并通过
  正式 patch 让 `config.sub` 接受 `linux-ohos` 三元组，避免在
  `config.guess` 中新增平台宏探测逻辑。
- 在 `source()` 阶段通过正式 patch 将上游 `configure` 中 config.status
  临时目录创建处的 `umask 077` 调整为 `umask 022`，
  避免 `config.status` 在 OHOS/HMDFS 临时目录下创建 0700 子目录后写入
  `subs.sed`、`out` 等临时文件时触发 Permission denied。

## 验证

### 上游用例口径

ncurses 6.5 上游 `test/` 与 `progs/` 目录主要提供 curses 交互式终端程序和能力演示，不是稳定的非交互自动化 `make check` 用例；当前 HarmonyOS PC 交叉构建配方也显式使用 `--without-tests`、`--without-progs`，避免把终端交互程序打入依赖库包。因此本 PR 未选择可自动执行的上游用例，上游自动化通过率记为 N/A（0/0，未选取可自动化用例）。

新增 Conan 消费测试 `test_ncurses.c`，非交互验证：

- `curses_version()` 返回有效版本字符串；
- `keyname(KEY_LEFT)` 映射为 `KEY_LEFT`；
- `unctrl('\n')` 映射为 `^J`。

替代自动化消费测试通过率：3/3，100%。

## 下游

该依赖项用于解除 `readline/8.3` 和 `ncmpcpp/0.10.1` 的 `ncurses/6.5` 依赖阻塞。
