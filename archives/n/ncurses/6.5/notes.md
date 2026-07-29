# ncurses 6.5 适配记录

## 编译状态

状态：built

## 配方说明

- 构建系统：Autotools。
- 构建产物：静态 wide-character 库 `formw`、`menuw`、`panelw`、`ncursesw`。
- 关键配置：`--enable-widec`、`--enable-overwrite`、`--without-shared`。
- 禁用 `progs/tests/manpages`，避免交互式终端程序、数据库安装和测试运行阶段差异。
- 应用 `config.guess/config.sub` 补丁识别 OHOS 三元组。

## 验证

新增 Conan 消费测试 `test_ncurses.c`，非交互验证：

- `curses_version()` 返回有效版本字符串；
- `keyname(KEY_LEFT)` 映射为 `KEY_LEFT`；
- `unctrl('\n')` 映射为 `^J`。

## 下游

该依赖项用于解除 `readline/8.3` 和 `ncmpcpp/0.10.1` 的 `ncurses/6.5` 依赖阻塞。
