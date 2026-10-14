# E587 — termcap 时代程序的 LINES/COLS/UP 等全局与静态 libncursesw.a 重复定义

## 错误特征

链接阶段 ld.lld 报 curses 公开符号重复定义，另一处定义位于本仓 ncurses 静态归档的成员里
（levee 实测日志节选：5 条报错取 3 条，每条只保留定位行，路径已缩写）：

```
ld.lld: error: duplicate symbol: refresh
>>> defined at display.c
>>>            display.o:(refresh)
>>> defined at lib_gen.c
>>>            lib_gen.o:(.text+0x2700) in archive .../ncurses/6.6/.../lib/libncursesw.a
ld.lld: error: duplicate symbol: LINES
>>> defined at globals.c
>>>            lib_setup.o:(.bss+0x100) in archive .../libncursesw.a
ld.lld: error: duplicate symbol: UP
>>>            lib_termcap.o:(.bss+0x0) in archive .../libncursesw.a
```

GNU ld 的等价报错（宿主 gcc 最小复现实测格式）：

```
/usr/bin/ld: ./libncursesw.a(lib_setup.o):(.bss+0x0): multiple definition of `LINES'; prog.o:(.bss+0x0): first defined here
```

同一份源码在 Debian 上动态链接 libtinfo 从不报错——这是本条最容易误判的地方。

## 触发条件

- 程序使用 termcap 接口（`tgetent/tgetstr/tgoto/tputs`），且**自己定义**了与 curses/terminfo
  公开符号同名的全局：变量 `LINES`、`COLS`、`UP`、`BC`、`PC`、`ospeed`，或函数 `refresh`、`scroll`、
  `clear`、`erase`、`overwrite`……（vi 克隆、行编辑器、终端小游戏常见）
- 链接本仓 `ncurses/6.x`：按 R26 只发布静态 `libncursesw.a`（tinfo 已合入）
- 编译器为 clang 11+（默认 `-fno-common`，暂定定义也是强符号）

## 根因分析

1. 动态链接时，可执行文件中的定义会抢占（interpose）共享库里的同名符号，冲突被静默吸收。
2. 静态归档按需抽取成员：调用 `tgetent` 会拉入 `lib_termcap.o`（同时定义 `UP`/`BC`/`PC`），
   它依赖 `_nc_setupterm` 又拉入 `lib_setup.o`（定义 `LINES`/`COLS`）。
3. 本仓 ncurses/6.6 是**单体** `libncursesw.a`（tinfo 未拆成独立 libtinfo）：`lib_termcap.o` 处理
   `sgr0` 时引用的辅助函数会一路把 curses 屏幕层拉进来，最终抽出 `lib_gen.o`
   （curses 宏的函数版本：`refresh`、`scroll`、`wattrset`……），于是程序里的同名函数也冲突。
4. 结果：同一符号在程序 `.o` 与归档成员中各有一个强定义 → duplicate symbol。

`-Wl,--why-extract=<file>` 可还原抽取链（levee 实测，`成员 <- 引用方 [符号]`）：

```
lib_setup.o <- lib_termcap.o [_nc_setupterm] <- display.o [tgetent]
lib_gen.o   <- lib_slkrefr.o [wattrset] <- lib_slk.o [slk_refresh_sp] <- resizeterm.o
            <- lib_set_term.o <- lib_tstp.o <- tty_update.o <- lib_refresh.o <- lib_window.o
            <- lib_clreol.o <- lib_addch.o <- lib_addstr.o <- visbuf.o
            <- trim_sgr0.o [_nc_visbuf2] <- lib_termcap.o [_nc_trim_sgr0] <- display.o [tgetent]
```

## 解决方案

### 推荐方案：在程序中心头文件里用宏把冲突名改为私有前缀

在所有 `.c` 最先包含、且早于 `<termcap.h>`/`<curses.h>` 的头文件（levee 为 `levee.h`，紧跟
`#include "config.h"`）加入：

```c
#define LINES      levee_LINES
#define COLS       levee_COLS
#define UP         levee_UP
#define refresh    levee_refresh
#define scroll     levee_scroll
#define overwrite  levee_overwrite
```

- 只改链接名，程序行为不变；程序本来就自己调用 `tgetstr("up")`、`tgetnum("li")` 给这些变量赋值。
- `<termcap.h>` 的 `extern char *UP;` 在宏之后展开为 `extern char *levee_UP;`，与程序定义一致。
- 字符串字面量（例如 `:set scroll` 的选项名 `"scroll"`）不受宏影响。
- 冲突清单不要凭记忆写，用下面的求交集命令得到。

### 禁止做法

- ❌ `-Wl,--allow-multiple-definition` / `-z muldefs`：取哪个定义取决于归档顺序，程序与 ncurses 的
  `LINES/COLS` 被随机合并，屏幕尺寸读写错位且无告警。
- ❌ 改链动态 ncurses：违反 R26（系统同名库不产 `.so`），G3 门禁失败。
- ❌ `-fcommon`：只能让变量让位，`refresh/scroll` 等函数依旧冲突，且变量被 ncurses 定义吞并。

## 验证

```bash
# 程序自身定义的全局 ∩ 静态 ncurses 导出的定义 —— 输出非空即会冲突
llvm-nm --defined-only *.o | awk 'NF==3{print $3}' | sort -u > own.txt
llvm-nm --defined-only libncursesw.a | awk 'NF==3 && $2 ~ /[TDBRC]/ {print $3}' | sort -u | comm -12 - own.txt
# 修复后：链接通过，且程序的终端行为不变（levee test_package 9/9，含 vt100 光标寻址用例）
```

## 适用边界

- 适用：链接**静态** curses/tinfo 的 termcap/terminfo 老程序；与 OHOS 无关的 Linux 静态链接同样会触发。
- 不适用：只使用 curses 窗口 API、不自定义这些全局的程序；E163（OHOS 内核头把 `__packed` 定义成全局变量）
  虽同为 duplicate symbol，但冲突双方都在程序自身目标文件里，根因与修法不同。

## 参考

- 实例：`archives/l/levee/4.0/patches/0001-levee.h.patch`
- 查重：`engine` 对该日志误命中 E163；知识库中无「静态 ncurses 与程序全局同名」条目
