# xaric

Terminal IRC client in the ircII family (xaric.org).  Supports SSL
(`-s`), scripting, DCC and the classic ircII command set.

## HarmonyOS PC 适配（0.13.9）

- **构建系统**：Autotools（configure + make），无需 config.guess/config.sub
  （configure.ac 无 AC_CANONICAL_HOST）。
- **依赖**：`openssl/3.5.6.1`（AX_CHECK_OPENSSL 硬依赖，静态库）、
  `ncurses/6.6`（tgetent 来自 libncursesw.a）。
- **补丁**：`0.13.9/patches/0001-tgetent-ncursesw.patch` —— tgetent 搜索链
  插入 `-lncursesw`（OHOS 无 libtermcap/libcurses）。
- **运行要求**：stdin 必须是 TTY（`isatty(0)`），验证需用 PTY。
- **测试**：上游 `make check` 为空目标（0 用例）；新增 1 个鸿蒙特有测试
  （PTY 运行 `xaric -v`，3 个断言点）。

## 版本

| 版本 | 状态 | 日期 | 配方 |
|------|------|------|------|
| 0.13.9 | built | 2026-10-12 | `xaric/0.13.9` |
