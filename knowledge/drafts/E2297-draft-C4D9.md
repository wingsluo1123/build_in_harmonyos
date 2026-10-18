# E2297 — OHOS musl 缺少 pthread_cancel，阻塞线程需改协作式取消

## 错误特征

```
ld.lld: error: undefined symbol: pthread_cancel
>>> referenced by systhread.c
>>>               systhread.c.o:(KThreadCancel)
```

运行期表现为：后台线程无法被 `pthread_cancel` 终止，`pthread_join` 永久阻塞。

## 触发条件

- 平台: OpenHarmony / HarmonyOS（musl libc）
- 代码使用 `pthread_cancel` / `pthread_setcancelstate` / `pthread_testcancel`
  终止阻塞在条件变量或 I/O 上的后台线程
- 阶段: 链接期（缺符号）或运行期（线程无法退出）

## 根因分析

musl 未实现 POSIX 线程取消。依赖取消来打断阻塞调用的设计在 OHOS 上既无法链接，
也没有等价语义；必须改为显式的协作式取消。

## 解决方案

### 推荐方案

1. 为工作线程增加 `cancel` 标志（如加入 `BGZThreadFile` 结构体）。
2. 在 Whack/销毁路径：持锁置 `cancel=true`，`KConditionSignal` 唤醒所有等待者，
   再 `pthread_join`/`KThreadWait`。
3. 工作线程在每次条件等待和 I/O 读取后检查 `cancel`，置位即退出。
4. 通用 `KThreadCancel` 在 OHOS 返回 `rcUnsupported`，避免调用方误以为取消成功。
5. 置位时同时设置 `rc=rcCanceled`，唤醒可能等待数据的消费者线程。

```c
// Whack
KLockAcquire(self->lock);
self->cancel = true;
self->rc = RC(rcAlign, rcFile, rcReading, rcThread, rcCanceled);
KConditionSignal(self->need_data);
KConditionSignal(self->have_data);
KLockUnlock(self->lock);
KThreadWait(self->th, NULL);
```

### 禁止做法

- ❌ 仅提供空的 `pthread_cancel` 符号（链接通过但 join 挂死）
- ❌ 用 `pthread_kill` + 信号处理函数里 `pthread_exit`（非 async-signal-safe）
- ❌ 删除后台线程但仍从它读取数据（数据竞争/悬垂指针）

## 验证

```bash
llvm-nm -D -u libncbi-vdb.so | grep pthread_cancel || echo 'no pthread_cancel dependency'
# 运行使用 BGZF/BAM 读取路径的测试，确认销毁时线程及时退出
```

## 关联条目

- 相关: E085（musl 线程取消 API 缺失）、E092（CMake 平台识别）
