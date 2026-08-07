# redict 7.3.0 适配笔记

## 编译环境
- 构建系统: makefile（基于 Redis 构建系统，无 configure 脚本）
- 编译日期: 2026-08-08
- 编译器: clang/clang++ (aarch64, clang 15.0.4)
- 状态: built

## 编译步骤

```bash
# 编译（MALLOC=libc 替代默认的 jemalloc）
make -j1 CC=clang CXX=clang++ MALLOC=libc CFLAGS="-fPIC -O2" LDFLAGS="-lm"

# 安装到 staging 目录
make install PREFIX=$TEST_PREFIX

# 验证
$TEST_PREFIX/bin/redict-server --version
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | redict 默认在 Linux 上使用 jemalloc | jemalloc 在 HarmonyOS/musl 上兼容性差 | 使用 `MALLOC=libc` 参数替代 jemalloc |
| 2 | setproctitle.c 编译错误: program_invocation_name 未定义 | musl libc 不提供 program_invocation_name/program_invocation_short_name（glibc 特有） | 使用 `#ifdef __GLIBC__` 守卫，非 glibc 时跳过此段代码 |
| 3 | 链接错误: pthread_cancel/pthread_setcancelstate/pthread_setcanceltype 未定义 | musl libc 不提供 pthread 线程取消函数 | 在 setproctitle.c 中添加 weak 符号桩函数 |

## 源码修改

- `src/setproctitle.c`:
  - 添加 `#ifdef __GLIBC__` 守卫保护 `program_invocation_name` 和 `program_invocation_short_name` 的使用
  - 添加 `pthread_cancel`、`pthread_setcancelstate`、`pthread_setcanceltype` 的 weak 符号桩实现
  - 补丁文件: `patches/0001-src-setproctitle.c.patch`

## 依赖版本

- clang 15.0.4 (target: aarch64-unknown-linux-ohos)
- musl libc (HarmonyOS)

## 验证结果

```bash
$ redict-server --version
Redis server v=7.2.4 sha=00000000:0 malloc=libc bits=64 build=ebcc85ef73a851f1
```

## 注意事项

- redict 是 Redis OSS 7.2.4 的 LGPL-3.0 分支，`--version` 输出仍显示 "Redis server v=7.2.4"
- 二进制名称从 redis-* 改为 redict-*（redict-server, redict-cli, redict-benchmark, redict-check-rdb, redict-check-aof, redict-sentinel）
- 编译时必须使用 `MALLOC=libc`，不能用默认的 jemalloc
- 源码来源: codeberg.org/redict/redict (官方源)
