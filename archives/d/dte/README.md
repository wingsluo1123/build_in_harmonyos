# dte

小型控制台文本编辑器：多缓冲/标签、正则搜索替换、语法高亮、可定制键位与配色，
基于 termios 原始模式的编辑循环，单二进制零运行时依赖。

- 上游：<https://craigbarnes.gitlab.io/dte/>
- 构建系统：纯 GNU Make（`GNUmakefile` + `mk/*.mk`，无 configure）
- 依赖：无（terminfo 走上游 `TERMINFO_DISABLE` 开关；iconv 由 libc 提供）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.9.1 | built | 首次适配，见 `1.9.1/` |

## 构建变量（上游）

`prefix` / `bindir` / `mandir` / `DESTDIR`，测试目标 `make check`。
