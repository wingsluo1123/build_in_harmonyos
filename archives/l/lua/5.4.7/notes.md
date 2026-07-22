# lua 5.4.7 适配笔记

## 编译环境
- 构建系统: makefile (upstream `linux` target, NOT `linux-readline`)
- 编译日期: 2026-07-22
- 编译器: clang 15 (OHOS hnp toolchain)
- 状态: published

## 编译步骤

```bash
# 在 .conan2/p/b/lua*/b/src 下执行：
make -j1 \
  CC='clang -std=gnu99' \
  AR='ar rcu' \
  RANLIB='ranlib' \
  SYSCFLAGS='-DLUA_USE_LINUX' \
  SYSLIBS='-ldl' \
  SYSLDFLAGS='' \
  MYCFLAGS='' MYLDFLAGS='' MYLIBS='' \
  linux
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `gcc: No such file or directory` | Lua `src/Makefile` 第 7 行硬编码 `CC= gcc -std=gnu99`，覆盖了环境变量 `CC=clang` | 通过命令行 `make CC='clang -std=gnu99'` 覆盖（Makefile 的命令行变量优先于文件内变量） |
| 2 | `make: jobserver mkfifo: Operation not permitted` | HMDFS 不允许 `mkfifo(2)`，make 的 jobserver 模式创建命名管道失败 | 固定 `-j1`，牺牲一点速度换取稳定 |
| 3 | conan 缓存中 `<pkg>/include/src/lua.h` 而非 `<pkg>/include/lua.h` | strip_root=True 解压后 headers 落在 `<src>/src/lua.h`（与 `self.folders.source="."` 配合） | `package()` 用 `keep_path=False` 拍平到 `<pkg>/include/` |
| 4 | `VirtualRunEnv` 生成的 `conanrunenv-*.sh` 为空，consumer PATH 中找不到 lua | conan 2.29.1 偶发不聚合 library 类型的 `cpp_info.bindirs` | test_package 改用 `self.dependencies[ref].package_folder` 拿绝对路径，绕开 VirtualRunEnv |
| 5 | `mkdir: /tmp/lua-test-XXX: Read-only file system` | HMDFS `/tmp` 只读 | 改用 `$(pwd)/.lua-test-$$` 作为临时目录 |

## 源码修改

无（bionic libc 与 Lua 5.4.7 的 Linux 兼容层完全契合）

## 依赖版本

无（Lua 是 standalone，不依赖任何外部库；运行时只用 `m` 和 `dl` 两个 system lib）

## 验证结果

```bash
$ clang -std=c99 -O2 -I<include> test_lua.c <liblua.a> -lm -ldl -o test_lua
$ ./test_lua
# (silent — exit code 0)

$ ./lua -v
Lua 5.4.7  Copyright (C) 1994-2024 Lua.org, PUC-Rio

$ ./luac -v
Lua 5.4.7  Copyright (C) 1994-2024 Lua.org, PUC-Rio
```
