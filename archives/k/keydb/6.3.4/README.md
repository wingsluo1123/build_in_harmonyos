# keydb 6.3.4 for HarmonyOS

## 概述

KeyDB 是 Redis 6.3 的高性能多线程分支（Snapchat 出品），本目录记录它在
HarmonyOS/OpenHarmony (aarch64) 上的适配过程与验证结果。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | keydb |
| 版本 | 6.3.4 |
| 下载地址 | https://github.com/Snapchat/KeyDB/archive/refs/tags/v6.3.4.tar.gz |
| 上游仓库 | https://github.com/Snapchat/KeyDB |
| 许可证 | BSD-3-Clause |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS 6.0 |
| 架构 | aarch64 |
| 编译器 | clang 15 (LLVM, OHOS SDK) |
| 构建系统 | Makefile（Redis 系） |

## 编译步骤

```bash
conan create archives/k/keydb/6.3.4 \
    -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64
```

## 补丁说明

| 补丁 | 目的 |
|------|------|
| 0001-src-Makefile.patch | 把 pthread 兼容对象加入 server 目标；`mkreleasehdr.sh` 与 `./runtest` 显式经 `sh` 运行；AArch64 OHOS 构建允许不链接外部 `libatomic` |
| 0002-src-config.h.patch | 由 `config.h` 引入兼容头，使所有编译单元都能看到被补齐的入口点 |
| 0003-src-pthread_compat.cpp.patch | 新增文件：musl 缺失的 GNU pthread 亲和性/取消入口点，转发到平台实际提供的 POSIX 接口 |
| 0004-src-pthread_compat.h.patch | 新增文件：兼容入口点声明（自行 `#define _GNU_SOURCE` 以保证 `cpu_set_t` 可见） |
| 0005-src-server.cpp.patch | `madvise(MADV_FREE)` 不受支持时按「无法探测」处理而非断言退出（OHOS 内核返回 EINVAL） |
| 0006-src-setproctitle.c.patch | 补齐 musl 未导出的 glibc program-name 全局量，并按 glibc 语义从 `argv[0]` 赋值，避免 `spt_init()` 中 `strdup(NULL)` 启动崩溃 |
| 0007-tests-support-tmpfile.tcl.patch | 让 Tcl 套件使用可配置的短临时根目录（`KEYDB_TEST_TMPDIR`），规避 OHOS Unix socket 路径长度限制 |

## 遇到的问题

详见 [notes.md](./notes.md)。

## 测试结果

详见 [reports/](./reports/)。

| 测试项 | 结果 |
|--------|------|
| 原生构建（HarmonyOS PC, aarch64, clang 15） | 通过（EXIT=0） |
| 上游 Tcl 套件（79 单元 = 55 unit/* + 24 integration/*） | 2105 用例，2102 通过 / 3 失败，通过率 99.86%；另一次完整运行 79/79 单元、2110/2114 = 99.81%。失败项逐条归因见 notes.md |
| 消费者测试（真机） | 通过：`keydb 6.3.4 service test passed`（版本/PING/SET/GET/DEL） |

## 验证安装

```bash
keydb-server --version
keydb-cli --version
```

## 经验总结

1. KeyDB 的 `deps/` 内嵌 jemalloc/memkind 无法在本机交叉编译，改用 `MALLOC=libc`。
2. libuuid 不在 OHOS sysroot 中，需用 Conan 的 `uuid` 包（静态）。
3. 上游多线程亲和性代码用的是 GNU 扩展，musl 上替换为 `sched_setaffinity`。
