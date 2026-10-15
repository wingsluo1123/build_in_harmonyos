# 非阻塞发送队列保留短写尾部仍不足以保证活性：积压队列需要按需写就绪推进

> 状态：DRAFT（路径 B 知识库扩展候选）｜来源：mvdsv/1.11 HarmonyOS PC 适配｜日期：2026-10-14
> 候选编号：E549｜机器可读层：`E549-draft-6F91.kv`

## 结论

在连接持续有效且接收端恢复读取的前提下，非阻塞 `send()` 短写后仅保存尾部，不等于尾部最终会被发送。若发送器只由后续业务入队调用，最后一帧的剩余数据可能永久滞留。队列积压后必须通过独立于后续入队的写就绪事件或等价调度继续推进；清空后立即取消监听。

首次入队仍可乐观发送。只有短写或 `EAGAIN/EWOULDBLOCK` 留下尾部时才监听写就绪。直接循环重试会忙等；永久监听通常可写的 socket 则会让空队列忙轮询。

## 稳定症状与机械触发条件

运行时表现通常没有崩溃或明确错误日志，而是：

```text
connection remains established
pending/queued byte count stays greater than zero
peer resumes reading, but the final frame never completes
```

源码同时满足以下四项即可机械标为高风险：

1. socket 设为非阻塞；
2. `send()` 的短写或 `EAGAIN` 路径保存 buffer offset/length；
3. 同一发送函数只从 enqueue/业务生产路径调用；
4. `select/poll/epoll` 没有在 pending length 非零时注册写事件。

可先扫描：

```bash
rg -n 'O_NONBLOCK|EAGAIN|EWOULDBLOCK|send\(|outlen|pending|POLLOUT|EPOLLOUT|FD_SET' src
```

这不是 HarmonyOS 特有的 TCP 语义；问题在 HarmonyOS PC 移植的目标端背压回归中得到实际复现。可复用价值是为任何自研非阻塞流式发送队列建立“数据所有权 + 活性驱动”双重契约。

## mvdsv 根因

上游 `NET_SendTCPPacket_SV()` 将长度头和载荷加入 `svtcpstream_t.outbuffer`，然后只尝试一次 `send()`。短写时它正确移动未发送尾部并更新 `outlen`，遇到 `EAGAIN` 也保留队列；但 `NET_Sleep()` 只监听标准输入和 UDP 可读事件，没有 TCP 写集合。

因此：

```text
enqueue final frame
  -> optimistic send hits EAGAIN
  -> outlen remains positive
  -> no later business enqueue
  -> NET_Sleep never observes TCP writability
  -> peer drains receive buffer, but tail has no execution path
```

队列保存解决了数据所有权，却没有解决“谁在何时再次执行发送器”的活性问题。

## 三臂真机实证

测试直接编译生产 `net_tcp_queue.c` 与 `net_tcp_stream.c`。可注入发送器先固定制造 `EINTR -> 3 字节短写 -> EAGAIN -> 完整排空` 和 fatal；随后构造真实 `svtcpstream_t` 链表，使用真实非阻塞 `socketpair`，压小收发缓冲区并先填满发送端，再提交 7000 字节确定性序列。正式 `NET_Sleep()` 与测试共同调用流链表写集合注册和就绪排空函数；测试直接执行这两个生产函数，但不虚称执行整个 `NET_Sleep()`。

| 臂 | 实现 | 结果 |
|---|---|---|
| A 原始调度 | 乐观发送一次，保存尾部，不再制造调度事件 | 接收端恢复后等待 100 ms，业务数据仍为 0 字节 |
| B 直觉修复 | 不看队列长度，始终注册写 fd | 空队列 128/128 次零超时轮询立即唤醒 |
| C 正确修复 | 通过真实流链表生产接线按 pending length 注册写 fd；就绪后排空对应流 | 7000 字节无丢失、重复或重排；清空后 0 次额外唤醒 |

HarmonyOS PC aarch64 输出：

```text
tcp queue arms: scripted_short_write=1 scripted_eintr=1 scripted_eagain=1 scripted_fatal=1 fd_guard=1 original_stalled=1 false_fix_wakeups=128 fixed_bytes=7000 idle_wakeups=0
```

完整共同条件、补丁哈希、真机哈希和证据边界见 `archives/m/mvdsv/1.11/reports/path-b-evidence.md`。

## 正确修复

把队列排空和写事件注册分别收敛成可复用原语：

```c
flush_result flush_queue(int fd, unsigned char *buf, size_t *pending)
{
    while (*pending != 0) {
        ssize_t n = send(fd, buf, *pending, 0);
        if (n > 0) { consume_prefix(buf, pending, n); continue; }
        if (n < 0 && errno == EINTR) continue;
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) return PENDING;
        return FATAL;
    }
    return DRAINED;
}
```

- enqueue 后立即乐观调用一次；
- 返回 `PENDING` 时，让事件循环仅为该非空队列注册写事件；
- 写就绪回调再次调用同一排空函数；
- 返回 `DRAINED` 后取消写监听；
- fatal 错误关闭连接，不把失败数据伪装成已送达。

若事件框架不直接暴露写掩码，可在短写后投递一个可去重的 one-shot writer，但仍须等待真实写就绪，不能在 `EAGAIN` 后裸循环。

## 为什么两种直觉修复错误

### 仅依赖下一次 enqueue

活跃流量可能偶然刷新旧尾部，使常规压力测试看似正常；最后一帧后没有新业务时才稳定暴露。因而测试必须暂停新的生产者，再让接收端恢复。

### 永久监听可写

TCP socket 在空队列时通常也是可写的。水平触发的 `select/poll/epoll` 会持续立即返回；本次反例 128 次探测全部唤醒。队列长度必须参与事件掩码计算。

## 可执行验证

在原生 HarmonyOS 构建环境执行正式配方：

```bash
conan create archives/m/mvdsv/1.11 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build='mvdsv/*'
```

或在构建目录单独运行：

```bash
ctest --test-dir build/Release -R tcp_queue_liveness --output-on-failure
```

七个补丁均可按顺序在官方源码上以 `patch --dry-run --fuzz=0 -p1` 应用。生产排空函数回退会使确定性结果分支或字节完整性断言失败；让写兴趣忽略队列长度会使 Arm B 空闲断言稳定失败；绕过流链表生产接线原语会使 Arm C 的注册、非法 fd fail-closed、排空或清空撤销断言失败。`NET_Sleep()` 中的调用点由源码审查与完整服务器目标编译覆盖，现有 CTest 不声称仅回退该调用点也会失败。

## 适用与不适用边界

适用于自研 framed TCP、代理、日志转发、游戏服务器或其他保存短写尾部的非阻塞流式发送器。

不适用于：

- 阻塞 socket；
- 框架已保证 pending queue 对应 one-shot/level-triggered write callback；
- 已完整交给内核、pending length 为零的数据；
- 字符设备不报告 `POLLOUT` 的平台差异；
- TLS 握手 ready 转换前的分层应用队列；
- mvdsv QTV 握手采用发送不完整即终止连接的 fail-closed 策略，不经过待发队列。

## 查重与新增差异

| 既有 stem/条目 | 重合点 | 本条新增机制 |
|---|---|---|
| `E545-draft-1D7D` | 都出现 `EWOULDBLOCK` 和字节计数 | E545 是测试代码把 `-1` 计入长度并重复输入字节；本条是生产队列保存尾部后没有活性驱动 |
| `E429-draft-4084` | 都涉及应用发送队列与写事件 | E429 的机械触发点是 TLS `ready: false -> true`；本条没有 TLS，触发点是一般 TCP 短写/背压后的最终尾部 |
| `DRAFT-E654-ohos-chardev-pollout-select-hang` | 都观察写就绪 | E654 是字符设备永不报告 `POLLOUT`；本条 socket 正常报告可写，缺陷是应用没有按积压状态注册事件 |

检索范围覆盖正式图谱、`knowledge/drafts/`、归档笔记和现有网络事件循环草稿；未发现同时描述“短写尾部已保存 + 发送只由后续入队驱动 + 最后一帧活性丢失 + 无条件写监听忙轮询反例”的既有条目。
