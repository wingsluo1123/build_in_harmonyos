# 阻塞事件循环的跨线程状态发布必须配对等待集主动唤醒

- **草稿 ID**: `DRAFT-live-2025.05.24-select-event-trigger-wakeup`
- **来源**: LIVE555 2025.05.24 HarmonyOS PC 适配与真机三臂验证
- **状态**: 随 B 类 PR 提交的知识草稿

## 问题

允许外部线程调用事件触发 API 的 scheduler 往往用 atomic flag 保存 pending
状态。但原子操作只解决可见性，不能让已经阻塞在 `select()`、`poll()` 或
`epoll_wait()` 的事件线程返回。使用固定周期 timer 虽能保证最终处理，却会让
受控空闲循环持续醒来；仅删除 timer 则失去活性。

若触发 ID 是 bitmask，另一个容易遗漏的不变量是：一次 API 调用可以让多个位
同时从 idle 变为 pending。事件循环每次只处理一个 pending 位时，通知也必须按
新置位数建立单位，而不是每次 API 调用只通知一次。

## 正确模式

1. 创建非阻塞、close-on-exec 的 pipe/socketpair/eventfd，将读端注册到事件循环
   等待集，并检查描述符范围和注册结果。
2. 发布方先写关联数据，再对每个事件位原子执行 idle→pending。
3. 仅对真正发生 idle→pending 的位通知；重复发布同一 pending 位不追加通知。
4. 等待线程排空就绪通知，按既有轮转逻辑分派一个 pending 事件；如果仍有
   可枚举的 pending 位，退出本轮前必须重新把通道置为可读。
5. 写入遇到 `EINTR` 重试。只有通道保持可读、pending 状态仍可枚举且分派后会对
   剩余状态重臂时，`EAGAIN` 才可视为安全合并。
6. 初始化、描述符范围或注册失败时保留有界轮询回退；销毁前先停止并 join 生产
   线程，再注销和关闭通道。

## 错误方案

- 只把 wall clock 换成 monotonic clock：改善计时，不能唤醒等待。
- 只取消周期 tick：空闲指标变好，但事件由 watchdog 或其他偶然 I/O 才处理。
- 一次 `triggerEvent(mask)` 只写一个字节：事件循环处理一个 bit 后重新阻塞，
  其余 bit 没有通知。
- 通过未定义的“销毁后继续触发”或无限重复同一 ID 人为塞满通道：不能证明合法
  API 下的不变量。

## LIVE555 实证

同一 HarmonyOS PC AArch64 真机、同一源码、消费者和判定器的三个独立制品：

| 实现 | 250 ms idle returns | max latency | combined bits | verdict |
|---|---:|---:|---:|---|
| 原始 10 ms tick | 25 | 10.098 ms | 32/32 | FAIL（空闲轮询） |
| 仅取消 tick | 1 | 300 ms watchdog | 1/32 | FAIL（无主动唤醒） |
| 发布后主动通知 | 1 | 0.441 ms | 32/32 | PASS |

正式安装后包的复测得到 `zero_idle=1`、显式 10 ms tick `25`、十次触发 P95
`0.074 ms`、组合、并发和满通知通道均 `32/32`，初始化失败回退也通过。

## 适用边界与查重

该知识适用于正常事件交付，不讨论强制线程取消。E1078 解决 OHOS/musl 缺少
`pthread_cancel` 时的协作式线程退出；两者可能都使用 fd 或有限等待，但根因、
生命周期和测试预言机不同。

空闲返回次数只是在没有业务 I/O/其他 timer 的受控实验中衡量 scheduler 行为，
不是系统级能耗结论。
