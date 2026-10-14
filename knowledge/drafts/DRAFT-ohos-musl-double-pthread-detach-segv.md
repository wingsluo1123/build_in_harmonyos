# DRAFT: musl 双重 pthread_detach 直接 SIGSEGV（glibc 只返回 EINVAL）

## 现象

pappl 1.4.12 上游 `make test` 在 `api: papplPrinterCreate(test0)` 处以
**Error 139（SIGSEGV）** 崩溃。真机 faultlog（`/data/log/faultlog/faultlogger/
cppcrash-*`）回溯：

```
#00 pc ... ld-musl-aarch64.so.1(pthread_join+88)   ← SEGV_MAPERR@0
#01 pc ... ld-musl-aarch64.so.1(thrd_detach+52)
#02 pc ... testpappl+0x2bc87c  →  llvm-symbolizer: papplSystemRun (system.c:568)
#03 main
```

`system.c:568` 是一行 `pthread_detach(tid)` —— 而该线程在第 537 行已经用
`pthread_attr_setdetachstate(&tattr, PTHREAD_CREATE_DETACHED)` 创建。
库作者「保险起见再 detach 一次防止挂起」，在 glibc 上这个冗余调用只返回
EINVAL，于是这个模式在 Linux 上潜伏多年；OHOS musl 的实现会顺着已失效的
线程描述符走进 `pthread_join` 内部解引用 NULL，第一次执行就把整个进程带崩。

## 最小复现（真机实测）

```c
pthread_attr_t a; pthread_t t1;
pthread_attr_init(&a);
pthread_attr_setdetachstate(&a, PTHREAD_CREATE_DETACHED);
pthread_create(&t1, &a, fn, NULL);
pthread_detach(t1);   /* glibc: 返回 EINVAL 继续；OHOS musl: SIGSEGV */
```

设备输出：`A: created detached, now detaching again...` 后直接 `EXIT=139`。
同一程序在 glibc 环境存活并打印 rc=EINVAL 路径。

## 修复

删除冗余的第二次 `pthread_detach()`，保留 detached 创建（这是上游本意；
工作线程循环本来就在 printer deleted / system shutdown 时自退）。pappl 的
两处（raw-socket 线程、USB gadget 线程）删除后，上游全套 1832 个用例
（含 10×1000 并发压力类）全部通过。

## 判别要点

- **症状在运行期**，通常藏在「起服务线程的上游测试」里；faultlog 会把矛头
  指向 `pthread_join`，必须符号化**调用方**帧才看得出是 detach 语义差异。
- 先问：这个线程是怎么创建的？`PTHREAD_CREATE_DETACHED` 创建后又
  `pthread_detach` → 命中本条。**joinable 创建 + 单次 detach 是合法用法，
  不属于本条**（pappl 的 job 线程、DNS-SD 线程就是合法单次 detach，保留）。

## 禁止策略

1. 禁止吞 SIGSEGV 或包错误容忍壳 —— 掩盖双重 detach 后线程表已损坏，后续
   崩溃更随机；
2. 禁止全局把 `pthread_detach` 宏定义为空 —— 会顺带废掉合法的 joinable 线程
   detach，长时间测试线程泄漏。

## 查重证据（2026-10-08，main tip 542 条 + drafts）

- `git grep -il pthread_detach origin/main -- knowledge`：仅 E361（MPICH
  double-fork 守护进程族，不同机制）、musl-glibc 对比表（pthread_detach 双方
  「都有」，恰是漏掉语义差异的原因）、libkqueue 草稿（sigwaitinfo 族）；
- E127 覆盖 `pthread_cancel/setcancelstate` **缺失**（编译期 undeclared），
  与本条的「存在但双重调用行为分歧」不同子族；
- index.tsv 无 detach 相关行。

来源：pappl 1.4.12 适配（PR #15060，补丁 0002）。
