# lxi-tools 2.8 路径 B 三臂证据

## 单一知识主张

面向持久 TCP 的 RAW/SCPI 客户端不能把一次字节接收调用返回的当前批次当作完整应用响应。客户端必须依据协议边界，在一个单调时钟总截止时间内跨多个可读周期组帧：文本响应等待终止符；IEEE 488.2 definite-length block 严格解析 `#<n><length><payload>`。

liblxi 提供字节接收接口，不承诺一次调用返回完整 SCPI 消息。缺陷归属于 lxi-tools 的应用层组帧，不归因于 liblxi，也不扩展到 VXI-11 RPC、截图插件或 DNS-SD。

## 真实触发链

上游 RAW 路径向仪器发送查询后只调用一次 `lxi_receive()`，随后把该次返回的全部字节直接打印并以成功退出。TCP 分段、调度延迟或当前暂时没有更多数据，都可能使一次调用只返回响应前缀；长连接又不能依赖 EOF 表示消息结束。

机械触发条件为：

1. 持久字节流连接；
2. 应用响应有终止符或长度字段；
3. 接收函数允许返回当前已获得的正数字节数；
4. 调用方一次正数返回后立即把响应视为完成。

## 同条件三臂真机实验

三臂使用同一官方 2.8 源码、Conan 依赖闭包、clang 15、HarmonyOS PC AArch64 目标和公共命令：

```bash
lxi scpi --address 127.0.0.1 --port "$PORT" --timeout 1 --raw '*IDN?'
```

同一私有 loopback 假仪器先确认收到以换行结束的查询，再分三次发送 `ACME,`、`MODEL`、`\n`，片间延迟 200 ms；完整响应后继续保持连接 1.5 秒。三臂仅改变客户端如何判定响应完成。

| 臂 | 实现 | 目标端观测 | 判定 |
|---|---|---|---|
| A 原始实现 | 一次 `lxi_receive()` 正数返回即完成 | 268 ms、rc=0、输出 `ACME,` | 把前缀误报为完整响应 |
| B 错误修复 | 循环读取，直到对端关闭 | 1696 ms、rc=1、`Error: Timeout` | 持久连接不以 EOF 标帧，正常响应被误报超时 |
| C 正确修复 | 文本等换行；definite block 等声明长度；共享单调总截止时间 | 655 ms、rc=0、输出 `ACME,MODEL\n` | 在对端关闭前完整返回 |

探针原始摘要：

```text
{"elapsed_ms": 268, "label": "arm-a-original", "returncode": 0, "stderr": "", "stdout_hex": "41434d452c"}
{"elapsed_ms": 1696, "label": "arm-b-wait-for-close", "returncode": 1, "stderr": "Error: Timeout\nError: Failed to receive message", "stdout_hex": ""}
{"elapsed_ms": 655, "label": "arm-c-protocol-framing", "returncode": 0, "stderr": "", "stdout_hex": "41434d452c4d4f44454c0a"}
```

## 错误修复与正确修复

Arm B 将上游的一次接收改成“不断接收直到 `lxi_receive()` 返回非正数”。该做法对短连接看似有效，但把 transport EOF 当作协议边界；仪器正常保持连接时必然等到超时，并丢弃已经收到的完整数据。

Arm C 的生产修复：

- 文本从开头扫描换行，只有终止符到达才完成；
- `#<n><length>` 每个字段均可跨接收周期拆分；
- 使用受限 `size_t` 运算，先验证十进制累积安全且声明长度不超过 5 MiB 容量；
- 完成长度为“头部 + payload”，payload 可含 NUL 和换行；
- 所有接收调用使用同一 `CLOCK_MONOTONIC` 截止时间的剩余预算，不为每个分片重置完整超时；
- `#0` 在持久 RAW 连接没有可判定边界，明确以非零退出拒绝。

## 可执行复现

完成正式包后运行仓内消费者测试：

```bash
python3 archives/l/lxi-tools/2.8/test_package/test_lxi_tools.py "$PACKAGE_FOLDER"
```

三臂探针和 Arm B 精确差异保存在仓外审计目录，避免把实验二进制、缓存路径或原始日志放入 PR。复现步骤为：从官方源码分别构建原始 `scpi.c`、应用 Arm B 差异、应用正式 `0006-src-scpi.c.patch`，签名目标 ELF 后，在同一目标端依次运行探针。

证据绑定：

```text
三臂探针源码       1cbac2554901e73c11e2ffb19377679ad302aa9112d1e84e899fdedb89618f95  lxi-tools-2.8-path-b-probe.py
Arm B 精确差异      0731679feb7073651cae5dc373b4824332cde6d59d91a15b46edac81286e8756  lxi-tools-2.8-arm-b-wait-for-close.patch
三臂原始输出       c155a0797d3641672a7f5bb9e8cbe30b228015b0f1b195f1735218a7d310be92  lxi-tools-2.8-path-b-arms.log
Arm A 目标 ELF     8b21fac2b42e3f3612dcda91431aa269aaea3a0e5907dd414d4655c887c2f13f
Arm B 目标 ELF     4dff7c6f3e3a12b1e5444e28737188bc15489a2405124ecb606967c1e137f165
Arm C 目标 ELF     f1103dd7881d5cbf04acff14a82afdced16a5347ff1674977474f3f8331ffce4
```

签名可能包含非确定性数据，ELF 哈希仅绑定本次实验；可复现条件是官方源码、精确反例差异、正式补丁与行为预言机。

## 独立普适性佐证

该契约不是为 lxi-tools 单独发明。PyVISA 官方资源文档明确把终止字符作为消息结束条件，并说明读取会重复执行并拼接分块；pyvisa-py 的 TCP/IP 实现也把 termination character、读取计数和 end indicator 作为独立完成条件。它们是相同“字节流读取必须由上层协议边界决定完成”的独立实现佐证，不声称这些项目存在同一缺陷：

- `https://github.com/pyvisa/pyvisa/blob/main/docs/source/introduction/resources.rst`
- `https://github.com/pyvisa/pyvisa-py/blob/main/pyvisa_py/tcpip.py`

## 非适用边界

- VXI-11 RPC 自带消息语义，不由本条 RAW/TCP 组帧规则替代。
- HiSLIP、WebSocket 等其他协议必须使用各自帧边界。
- `#0` 不定长块需要带外结束条件或连接关闭；本实现针对持久 RAW 连接选择显式拒绝。
- 若文本协议使用非换行终止符，应把该终止符作为配置输入，不能硬套换行。
- 当前 `lxi scpi` 是单请求命令；本修复不宣称为 pipelining 缓存帧后额外字节。

## 查重与新增差异

- `E545-draft-1D7D` 是测试代码错误累加 `send=-1/EWOULDBLOCK`，导致长度负数和字节重复；本条是正式客户端在接收端把正数短读当完整应用消息。
- 非阻塞发送队列活性条目研究短写尾部缺少 `POLLOUT` 推进；本条不涉及发送队列，研究接收字节批次与应用帧边界的层次差异。
- TLS-ready 队列条目研究握手状态转换后漏调度；本条没有 TLS 状态转换。
- 既有 loader、签名与一般超时条目不提供“终止符/声明长度 + 单一总截止时间”的应用组帧契约。

检索正式图谱、知识草稿、归档笔记和网络事件循环案例后，未发现同时描述“持久字节流一次正数短读假成功 + 等 EOF 伪修复超时 + 按文本/definite block 边界跨读取周期组帧”的既有知识。
