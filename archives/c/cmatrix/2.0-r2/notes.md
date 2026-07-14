# cmatrix 2.0-r2 适配笔记

## 编译环境
- 构建系统：autotools
- 编译日期：2026-07-14
- 编译器：clang
- 状态：published

## 编译要点

1. 使用 GitHub release tarball 作为源码来源
2. `autoreconf -fi` 生成 configure
3. 处理源码目录权限，确保 `autom4te.cache` 可创建
4. 以 `ncurses/6.4` 为主要依赖
5. 走最小化 smoke test 验证可执行文件存在

## 已知结论
- cmatrix 需要平台识别相关补丁和 install 补丁
- test_package 适合直接验证 `cmatrix --help`
