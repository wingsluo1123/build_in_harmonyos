# ncurses 6.5 适配记录

## 编译状态

状态：built

## 配方说明

- 构建系统：Autotools。
- 构建产物：静态 wide-character 库 `formw`、`menuw`、`panelw`、`ncursesw`。
- 关键配置：`--enable-widec`、`--enable-overwrite`、`--without-shared`。
- 禁用 `progs/tests/manpages`，避免交互式终端程序、数据库安装和测试运行阶段差异。
- 构建阶段用 `replace_in_file` 让 `config.guess/config.sub` 识别 OHOS 三元组。

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
