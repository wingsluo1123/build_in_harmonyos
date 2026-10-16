# termbox2

> Terminal I/O library for creating text-based user interfaces (TUIs). A slim
> alternative to ncurses with built-in terminal support when a terminfo db is
> not present. Successor to the original [termbox](https://github.com/termbox/termbox).

## 功能概述

- 简单的 TUI 终端 IO：`tb_init` / `tb_shutdown`、`tb_width` / `tb_height`
- 单元格渲染：`tb_set_cell` / `tb_set_cell_ex`、`tb_clear`、`tb_present`
- 输入事件：`tb_poll_event` / `tb_peek_event`，支持键盘、鼠标、resize
- 输出模式：8 位/256 色/truecolor（`tb_set_output_mode`），EGC 扩展字素簇
- 单文件头库（`termbox2.h`，MIT），兼容 `#define TB_IMPL` 或编译为 static/shared 库
- FFI/ABI 友好的公共 API（`demo/` 提供多语言调用示例）

## OHOS 适配

- 纯 GNU Make 构建，使用 Conan 工具链的 `CC`/`AR` 编译 `libtermbox2.a` 或
  `libtermbox2.so.2.0.0`，无第三方依赖，仅使用 HarmonyOS libc/POSIX 接口。
- 共享库 SONAME 为 `libtermbox2.so.2`；HMDFS 不支持软链接覆盖，打包时将签名后的
  ELF 复制为 SONAME/链接名别名。
- OHOS 加载共享库需用 `binary-sign-tool` 自签。
- 头文件自带 `_DEFAULT_SOURCE`/`_XOPEN_SOURCE` 保护，无需额外 feature 宏。
- 上游 `tests/` 为 16 个 PHP-FFI + X11 屏幕捕获比对用例（Xvfb/xterm/xvkbd +
  PHP-FFI）驱动，该工具链在无头 OHOS/aarch64 设备上不存在；已把 16 个用例逐一
  移植为原生 C 程序（`test_package/test_<name>.c`），经 PTY（`tb_init_fd`）
  调用同一真实 termbox2 API，在真机上作为上游测试套件全部执行；
  另有消费者 `test_api`/`test_ohos_pty` 对真实安装产物做 API 级验证。

## 依赖关系

- 编译依赖：无（纯 C，GNU Make）
- 运行依赖：HarmonyOS libc / POSIX（`termios`、`/dev/tty`、PTY）

## 参考资料

- 上游源码：https://github.com/termbox/termbox2
- API/文档：`termbox2.h`（含完整注释）
