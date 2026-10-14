# levee

levee 是 David L Parsons 从 1979 年起维护的小型 vi 克隆编辑器（最初用 UCSD Pascal 编写，
80 年代转为 C）。作者称其实现了约 95% 的 vi 可视模式；exec 模式不支持 `:g`/`:v`，长行截断显示
而不折行。安装后的命令名为 `levee`。

## 功能概述

- 可视模式：移动、插入/替换、`d`/`y`/`p` 行与字符操作、计数前缀、`u` 撤销、`/` 搜索、宏映射
- exec 模式（`-e` 启动或 `:` 进入）：`:w`/`:q`/`:wq`/`:x`、`:r` 读入、`:s` 替换、`:d`/`:y`/`:pu`、`:set`、`:!` 与 `!` 过滤
- `-r` 只读打开，`-t tag` 按 tags 文件跳转，`+command` 启动后执行命令
- `--version` / `--help`（本仓补丁新增，便于脚本探测）

## OHOS 适配

- **终端层**：链接 Conan `ncurses/6.6` 的静态 `libncursesw.a`，使用其 termcap 接口
  （`tgetent/tgetstr/tgoto`）；levee 自定义的 `LINES/COLS/UP/refresh/scroll/overwrite` 与 curses
  同名，静态链接会重复定义，补丁在 `levee.h` 用宏改为私有名字。
- **临时文件**：上游把撤销溢出、大块 yank 与 `!` 过滤的临时文件写死在 `/tmp`；HarmonyOS PC 的
  `/tmp` 只读，补丁改为优先 `$TMPDIR`（未设置时回退 `/tmp`）。
- **构建**：`configure.sh` 会在构建机上执行自己编译的辅助程序，配方把编译器驱动为
  `clang -static-pie`，交付物是无动态加载器依赖的 AArch64 static PIE（保留 PIE/RELRO/BIND_NOW）。
- **不安装 `lv` 别名**（与同名的 lv 分页器冲突）。

## 运行要求

- `TERMINFO`（或 `TERMINFO_DIRS`）指向一份 terminfo 数据库，例如 Conan `ncurses/6.6` 包内的
  `share/terminfo`；找不到终端描述时 levee 退化为行模式。
- `$TMPDIR` 指向可写目录；`!` 过滤与 `:!` 需要 `/bin/sh`。

## 依赖关系

- 运行/编译依赖：`ncurses/6.6`（静态链接；运行期只需其 terminfo 数据库）
- 构建工具：clang、make、bash（运行 `configure.sh`）

## 参考资料

- 上游仓库：<https://github.com/Orc/levee>（作者 David L Parsons）
- 源码包：<https://github.com/Orc/levee/archive/refs/tags/v4.0.tar.gz>
- 许可：`COPYRIGHT`（署名 + 不得背书的简短许可），配方声明为 `LicenseRef-levee`
