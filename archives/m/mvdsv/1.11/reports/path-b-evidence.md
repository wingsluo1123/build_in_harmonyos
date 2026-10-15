# mvdsv 1.11 路径 B 三臂证据

## 单一知识主张

在连接仍有效且接收端恢复读取的前提下，非阻塞流式发送队列仅保存短写后的剩余数据并不能保证最终送达。队列产生积压后，必须有独立于后续业务入队的写就绪事件或等价调度机制继续推进；队列清空后应立即取消写监听。

这不是“必须等写就绪才允许首次发送”。正确实现仍在入队时乐观调用 `send()`，仅在短写或 `EAGAIN/EWOULDBLOCK` 留下尾部时订阅写事件。

## 当前库的真实触发链

1. `NET_SendTCPPacket_SV()` 把长度头和载荷追加到 `svtcpstream_t.outbuffer`。
2. socket 是非阻塞的；上游只在本次入队末尾调用一次 `send()`，短写后以 `outlen` 保存尾部。
3. 上游 `NET_Sleep()` 只建立读集合，没有为 `outlen > 0` 的 TCP 流建立写集合。
4. 最后一帧之后若不再产生业务入队，即使对端恢复读取，旧尾部也不会再次触发发送。

修复把两个可复用原语放入生产 `net_tcp_queue.c`：

- `NET_TCP_FlushQueue()`：循环处理短写，`EINTR` 重试，`EAGAIN/EWOULDBLOCK` 保留尾部，其他错误返回 fatal；同一实现提供可注入发送器入口以确定性验证全部结果分支；
- `NET_TCP_AddWriteInterest()`：仅在 `length > 0` 时加入写集合并维护 `maxfd`；负 fd 和 POSIX 下 `fd >= FD_SETSIZE` 返回独立 invalid 结果，调用方 fail-closed。

生产 `net_tcp_stream.c` 再提供真实 `svtcpstream_t` 链表接线：过滤无效或待关闭连接、按 `outlen` 注册写集合，并在就绪后排空对应流。`NET_SendTCPPacket_SV()` 使用队列原语乐观发送；`NET_Sleep()` 与测试共同调用这组流链表接线函数，不维护测试替代算法。

## 同输入三臂实验

共同条件：AArch64 OHOS 可执行文件、真实非阻塞 `socketpair`、发送和接收缓冲区均压小、先用固定字节填满发送缓冲区，再提交 7000 字节确定性序列。三臂在一个测试进程内共享同一 socket 语义和判定方式。测试还通过生产排空函数的注入入口固定返回序列，独立证明 `EINTR -> 3 字节短写 -> EAGAIN -> 完整排空` 以及 fatal 保留未确认队列，不依赖内核碰巧产生特定短写长度。

| 臂 | 调度方式 | 结果 | 判定 |
|---|---|---|---|
| A 原始行为 | 入队时仅乐观发送一次；短写后没有独立调度 | 接收端排空预填数据并等待 100 ms，业务数据仍为 0 字节 | 缺陷稳定复现 |
| B 错误修复 | 不看队列长度，始终监听可写 | 空队列 128/128 次零超时轮询均立即唤醒 | 会导致空闲忙轮询 |
| C 正确修复 | 构造真实 `svtcpstream_t` 链表；调用 `NET_Sleep()` 复用的生产接线函数按需注册并排空 | 7000/7000 字节逐字节一致，清空后 0 次额外写事件 | 链表接线原语、送达、顺序与空闲性同时成立 |

目标端摘要：

```text
tcp queue arms: scripted_short_write=1 scripted_eintr=1 scripted_eagain=1 scripted_fatal=1 fd_guard=1 original_stalled=1 false_fix_wakeups=128 fixed_bytes=7000 idle_wakeups=0
```

## 可执行复现

官方 Conan 原生 OHOS profile 会在 `build()` 中执行 CTest：

```bash
conan create archives/m/mvdsv/1.11 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build='mvdsv/*'
```

也可以在已配置的目标构建目录直接执行：

```bash
ctest --test-dir build/Release -R tcp_queue_liveness --output-on-failure
```

测试源完整位于 `patches/0007-tests-tcp_queue_test.c.patch`，队列生产实现位于 `0003`、`0004`，真实流链表接线位于 `0005`、`0006`，`NET_Sleep()` 调用点位于 `0002`。七个补丁已在官方干净源码上按编号通过 `patch --dry-run --fuzz=0 -p1`，没有依赖未提交的实验代码。

回退 `NET_TCP_FlushQueue()` 会使确定性结果分支或尾部传递/顺序断言失败；把写兴趣改成无条件注册会使 128 次空闲断言失败；绕过生产流链表接线原语则无法满足真实 `svtcpstream_t` 的写集合、就绪排空、非法 fd fail-closed 与清空撤销断言。`NET_Sleep()` 中注册和排空这两个生产函数的调用点由补丁源码审查及完整 `mvdsv` 目标编译覆盖，测试不直接执行整个 `NET_Sleep()`，所以不把“仅回退调用点”虚称为自动化撤回测试。

## 查重与新颖性

- `E545-draft-1D7D` 处理的是 libnice **测试代码**把 `send=-1/EWOULDBLOCK` 错误累加为负字节数，造成测试文件重复字节；它不涉及生产发送队列的活性或写事件调度。
- `DRAFT-E654` 和 socat 草稿处理 OHOS 字符设备不报告 `POLLOUT`；本问题只针对 socket，目标端 socket 的写就绪报告正常，缺陷是应用没有在积压时注册写事件。
- uMurmur 的 TLS-ready 草稿处理握手状态转换后应用队列没有重新求值；本问题没有 TLS 状态机，机械触发条件是短写尾部只由后续入队驱动。两者的触发状态和最小修复位置不同。
- 本知识可机械扫描：非阻塞 socket；`send()` 返回值导致队列 `length/offset` 保留；发送函数只由 enqueue 路径调用；事件循环没有把 `length > 0` 映射到 `POLLOUT`/write fd set。该组合适用于自研 framed TCP、代理、日志转发和游戏服务器。

## 非适用边界

- 阻塞 socket、内核已经完整接收本次缓冲区，或外部框架保证积压队列持续收到写回调时不适用。
- 只用重试循环反复调用 `send()` 直到成功不是等价修复；在 `EAGAIN` 后会忙等。
- 不能永久订阅通常可写的 socket；否则空队列也会持续唤醒。
- 活跃业务可能靠下一次入队偶然刷新尾部，测试必须覆盖“最后一帧后不再入队”。
- QTV 握手采用发送不完整即终止连接的 fail-closed 策略，不经过待发队列，不属于本知识触发条件。

## 证据绑定

```text
CMake 平台补丁       e9a89a00487c4ff4e95a1cd3a3de1b8b949958b32a40319652eeb3d1ea733efd
NET_Sleep 接线补丁   a37a5fcb04f489a07a9e09762ce62d82a19dab2647c99a2b22cd8387ec234516
队列生产实现补丁    ae36513ba2819aaef0190799d30d12dde80c823de0ba3706f158ca837fd4414f
流链表接线实现补丁  b3a4a4fe4b9dc0191e3e8c9d24398ca6a64fd57bafa93f398db0c6aa942f4898
三臂测试补丁        887a03ee6b73cf6b19106e71fffe9b13c567df588658bb1444c187147274eaf1
签名队列测试 ELF    fbc9507df628beec655dea7e8af710ee7364ac6b697228fe2ae4bbe0ce335e46
脱敏真机输出        665c66e7145e26bba43879f7aec7b048daa3fd864281786b36dd009a3d11c61e
```

ELF 签名可能包含非确定性数据，哈希只绑定本次运行；可复现条件是官方源码、提交的七个补丁、目标工具链和上述行为关系，不要求重建出字节相同的签名 ELF。
