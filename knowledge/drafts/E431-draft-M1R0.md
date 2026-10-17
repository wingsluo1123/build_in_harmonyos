# E431 — 空操作 pthread_cancel 回退会让 pthread_cancel + pthread_join 永久阻塞

## 错误特征

编译/链接已通过（回退符号齐全），但上游测试在运行时**卡死**：

```
libteredo-list
1..1
# Basic empty list test...
<hang —— 之后不再有任何输出>
```

现场取证：进程不再消耗 CPU，`/proc/<pid>/status` 的 `Threads:` 只剩 1、状态 `S`，
测试停在用例首行的输出之后；调用栈停在 `pthread_join`。

## 触发条件

- 平台: OHOS/musl（libc 不导出 `pthread_cancel`/`pthread_setcancelstate`/`pthread_testcancel`，
  见 E127；`readelf --dyn-syms libc.so` 四个 cancel 符号全缺）
- 代码前提: 已给上述符号打了**空操作回退**，而被取消的线程体没有自然退出条件
  （典型 `for (;;) { clock_nanosleep(...) }`），`pthread_cancel` 是其唯一停止手段
- 阶段: testing / runtime（编译期无任何告警）

## 根因分析

`pthread_cancel` 的语义是"异步终止目标线程"，`pthread_join` 依赖它让线程真正退出。
把 cancel 换成空操作后，语义变成"什么都不做"，而线程体没有任何退出条件，
于是 `pthread_join` 永远等一个不会结束的线程——表现为测试脚手架级的挂死，
比链接失败更难定位（无报错、无 core、CPU 也安静）。

单看"符号缺失"（E127）只解决了链接，**线程停止语义才是真正的适配点**。

## 解决方案

### 推荐方案（rec_priority 1）

空操作回退必须与**协作式停止**配套：

1. 给线程状态加 `volatile bool stop`（或等价的原子标志）；
2. 线程等待循环改为按分片检查（1 秒），保证停止延迟有上限：
   ```c
   while (!l->stop) {
       struct timespec ts = { .tv_sec = 1 };
       clock_nanosleep(CLOCK_MONOTONIC, 0, &ts, NULL);
   }
   ```
3. 销毁路径先置位再 join（**保留** cancel 调用，让 glibc 上仍是即时终止）：
   ```c
   l->stop = true;
   pthread_cancel(t);          /* OHOS 上为空操作 */
   pthread_join(t, NULL);
   ```
4. 去掉该线程函数上的 `noreturn` 属性（否则编译器可据此做掉退出路径假设）；
5. 显式初始化新增字段——不要依赖上游的 `memset` 初始化：miredo 1.2.6 的
   `teredo_list_create` 写的是 `memset (l, 0, sizeof (l))`（指针尺寸笔误），
   新增字段根本没被清零，表现为"加了 stop 仍然卡死"。

miredo 1.2.6 实例：`patches/0001-libteredo-peerlist.c.patch`。

### 禁止做法

- ❌ 只加空操作回退、不改线程退出条件（本条目描述的就是这种失败：必然 `pthread_join` 挂死）
- ❌ 把上游的挂死用例标 SKIP/xfail 绕过（掩盖真实适配缺陷）
- ❌ 依赖上游既有的 `memset` 初始化新字段（尺寸笔误会让它静默失效）

## 验证

```bash
readelf --dyn-syms <sysroot>/usr/lib/libc.so | grep -c pthread_cancel   # 期望 0（符号缺失）
# 运行受影响的上游用例，确认不再挂死且有明确结束
libteredo/test/list  &&  libteredo/test/stresslist
# 挂死现场判定：cat /proc/<pid>/status | grep Threads   （只剩 1 且状态 S 即为本模式）
```

参考日志：`reports/test-report.md`（miredo 1.2.6：libteredo-list / libteredo-stresslist
在修复前直接卡死，修复后 PASS）。

## 关联条目

- 相关: E127（OHOS libc 缺线程取消符号）、E432（新增头文件补丁的处置——本修复改为内联进既有文件）
