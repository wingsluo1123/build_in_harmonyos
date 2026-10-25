# E3700 — OHOS musl 缺少 pthread_cancel，阻塞线程需改协作式取消

## 错误特征

```
ld.lld: error: undefined symbol: pthread_cancel
>>> referenced by systhread.c
>>>               systhread.c.o:(KThreadCancel)
```

运行期表现为：后台线程无法被 `pthread_cancel` 终止，`pthread_join` 永久阻塞。

## 触发条件

- 平台: OpenHarmony / HarmonyOS（musl libc）
- 代码使用 `pthread_cancel` 终止阻塞在条件变量或 I/O 上的后台线程
- 阶段: 链接期（缺符号）或运行期（线程无法退出）

## 根因分析

musl 未实现 POSIX 线程取消；依赖取消打断阻塞调用的设计在 OHOS 上既无法链接，
也没有等价语义，必须改为显式协作式取消。

## 解决方案

### 推荐方案

1. 构建期用 `check_c_source_compiles` 做链接测试，定义 `HAVE_PTHREAD_CANCEL`。
2. 有能力时保留原 `pthread_cancel` 路径；无能力时：
   - 工作线程增加 `cancel` 标志；
   - 销毁路径持锁置位并 `KConditionSignal` 唤醒所有等待者，再 join；
   - 线程在条件等待和 I/O 读取后检查标志退出；
   - 通用 `KThreadCancel` 返回 `rcUnsupported`；
   - 置位时同时设置 `rc=rcCanceled`，且线程退出时不要用局部 rc 覆盖它。
3. 已知限制：无取消能力时无法打断已阻塞的 `read()`；底层源为管道/FUSE/远端存储时，
   销毁路径可能等待当前读完成，需要配合有界读或可打断 I/O（参见 E1603）。

### 禁止做法

- ❌ 仅提供空的 `pthread_cancel` 符号（链接通过但 join 挂死；E085 的 stub 回退只用于构建期检测，不能当作取消实现）
- ❌ 用 `pthread_kill` + 信号处理函数里 `pthread_exit`（非 async-signal-safe）
- ❌ 删除后台线程但仍从它读取数据（数据竞争/悬垂指针）

## 验证

```bash
llvm-nm -D -u libncbi-vdb.so | grep pthread_cancel || echo 'no pthread_cancel dependency'
# 运行使用 BGZF/BAM 读取路径的测试，确认销毁时线程及时退出
```

## 关联条目与分工

- 前置根因: E085（musl 未实现 pthread_cancel 系列；其 stub 回退只解决链接/检测，不提供取消语义）
- 编译期守卫: E127（`pthread_cancel` undeclared 时禁用取消特性，如 libomp 的 `KMP_CANCEL_THREADS`）
- 生命周期: E513（无取消能力时仍须保证 joinable 线程可回收；可用协作式停止，不必采用其信号方案）
- 相似: E1603（meson `cc.has_function` + 有界 poll，在阻塞 `read()` 之前建立可打断等点）
- 相似: E1078（无条件移除取消 API，改为协作式退出 + 有限超时等待）
- 分工: E1603 建立可打断等点，本条把 BGZF 读线程改为协作式取消；两者叠加使用，不互相替代。
  若线程阻塞在管道/FUSE/远端存储且标志无法唤醒，先按 E1603 加有界等点，再套用本条。
- 与 E1078 的边界: 只面向 OHOS、可无条件删除取消路径时按 E1078；同一源码需兼容 glibc/musl
  （本 PR）时按本条做能力探测，保留原生取消路径，仅在探测失败时走协作式取消。
