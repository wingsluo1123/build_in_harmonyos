# keydb

KeyDB 是 Redis 6.3 的高性能多线程分支（C++ 重写），提供完整的键值数据库服务，
兼容 Redis 协议与数据结构，本目录记录它在 HarmonyOS/OpenHarmony (aarch64) 上的适配。

## 功能概述

- 兼容 Redis 协议的键值数据库：字符串、列表、集合、哈希、有序集合、流等类型
- 多线程架构：按线程分片的事件循环、自旋锁、异步写回线程池、显式 CPU 亲和性
- 持久化：RDB 快照与 AOF 追加日志；主从复制与部分重同步
- 附带 CLI 客户端、压测工具与 RDB/AOF 检查工具

## 产物

`keydb-server`、`keydb-cli`、`keydb-benchmark`、`keydb-check-rdb`、`keydb-check-aof`
（check-rdb / check-aof 与 keydb-server 内容完全相同：上游 install 规则把它们做成 `keydb-server` 的硬链接，Conan 打包时按普通文件复制，故包内是三份同内容的独立副本），均为
aarch64 / musl 的 PIE 可执行文件，解释器 `/lib/ld-musl-aarch64.so.1`。

## OHOS 适配要点

- musl 不提供 glibc 的 `pthread_setaffinity_np` / `pthread_getaffinity_np` /
  `pthread_cancel` / `pthread_setcancelstate` / `pthread_setcanceltype`，
  以兼容层转发到 `sched_setaffinity` 等 POSIX 接口
- musl 亦无 `program_invocation_name` / `program_invocation_short_name`，
  需在 `spt_init()` 中按 glibc 语义从 `argv[0]` 赋值，否则 `strdup(NULL)` 启动即崩
- OHOS 内核不支持 `madvise(MADV_FREE)`（EINVAL），上游 arm64 fork-bug 探测处的
  断言需改为跳过探测并记录日志
- 内嵌 jemalloc/memkind 无法在本平台编译，使用 `MALLOC=libc`
- AArch64 原子操作来自编译器内建，无需 `-latomic`
- 内嵌自旋锁汇编为 x86 专用，且 Makefile 用 `uname -m` 判断，需固定 `USEASM=no`
- 构建不启用 TLS（`BUILD_TLS=no`）：`tls-rotation` 等指令随构建开关存在

## 依赖

- 编译依赖（Conan）：`uuid/2.40.1`（OHOS sysroot 无 libuuid）、`openssl/1.1.1w`（libcrypto）
- 仅原生构建时的测试工具依赖：`tcl/8.6.16`（驱动上游 Tcl 套件）
- 内嵌并自行构建：hiredis、linenoise、lua、hdr_histogram

## 参考资料

- 上游仓库：https://github.com/Snapchat/KeyDB
- 版本级适配记录：`6.3.4/notes.md`
- 构建与测试：`conan create archives/k/keydb/6.3.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
