# hexedit 1.6 适配笔记

## 编译环境
- 构建系统：autotools
- 编译日期：2026-07-14
- 编译器：clang
- 状态：published

## 编译步骤

1. 使用官方 tarball 作为源码来源
2. `configure` 中修正 `cross_compiling=no` → `maybe`
3. `configure` 中修正 `umask 077` → `022`
4. 关闭 help2man，避免宿主工具依赖
5. 链接 `ncursesw`
6. `make -j1` 构建，随后执行 smoke test

## 已知结论
- hexedit 无 `make check` 目标，CI 只能做 `--help` 或交互命令 smoke test
- 依赖 `ncurses/6.4`
