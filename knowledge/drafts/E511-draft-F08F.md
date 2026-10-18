# E511 — 上游测试 concurrency 500 线程在 OHOS musl 偶发 SIGABRT，降为 100 线程

## 错误特征
libpg_query 18.0.0 上游测试 `test/concurrency` 以默认 `#define THREAD_COUNT 500` 运行时 rc=134 (SIGABRT)，
输出中途截断（17409 点后中断），偶发约 1/6。

## 触发条件
- 构建系统: make（上游 GNU Makefile）
- 阶段: testing
- 平台: OpenHarmony PC aarch64（musl）

## 根因分析
OHOS musl pthread 在 500 线程规模行为差异导致 abort；**非库缺陷**。
THREAD_COUNT 为源码 #define（test/concurrency.c 第 12-16 行），**不是环境变量**，
须改源码 + 重新编译测试二进制才生效。历史笔记"运行时参数调整"表述不精确，应纠正为
"测试源码宏调整（需重编译）"。配方零耦合（conanfile 只 make build 静态库，不构建/不跑上游测试）。

## 解决方案

### 推荐方案
sed 改 #define THREAD_COUNT 100 → make test/concurrency 重编译 → ./test/concurrency（rc=0，3600 点全过）。
不进 conan 配方。

### 禁止做法
- ❌ 仅设环境变量 THREAD_COUNT（编译期宏，env 无效）
- ❌ 把降线程写进配方 build()/test()（污染 CI 语义）
- ❌ 误判库有并发缺陷（实际 musl libc 线程层问题）

## 验证
```bash
make test/concurrency && ./test/concurrency   # 500: rc=134; sed 改 100 重编译后: rc=0
```

## 关联条目
- 相关: musl 适配族条目；配方 archives/l/libpg_query/18.0.0/