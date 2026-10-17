# 持久字节流一次正数短读不是完整应用消息：按协议边界跨读取周期组帧

> 状态：DRAFT（路径 B 知识库扩展候选）｜来源：lxi-tools/2.8 HarmonyOS PC 适配｜日期：2026-10-14
> 候选编号：E429｜机器可读层：`E429-draft-58E6.kv`

## 结论

持久字节流上的一次正数 `read/recv/receive` 返回，只表示当前获得了一批字节，不表示一个应用消息已经完整。客户端必须从应用协议取得完成条件：文本等待终止符；长度前缀消息等待完整头部和声明 payload；所有读取共享一个单调时钟总截止时间。

把正数短读当完整响应会静默截断；改成读到 EOF 又会在 keep-alive 连接上超时。二者都把 transport 状态错当成 application framing。

## 稳定症状与机械触发条件

典型症状不是崩溃，而是假成功或假超时：

```text
server sends one logical response in delayed chunks
client exits 0 after printing only the first chunk

or, after a "read until close" change:
server has sent the complete response and keeps the connection alive
client waits until timeout and exits nonzero
```

源码同时满足以下四项即可机械标为高风险：

1. 使用持久 TCP、串口或其他字节流；
2. 底层 API 允许短读并返回当前正数字节数；
3. 应用协议本身有终止符或长度字段；
4. 调用方第一次正数返回后立即打印/解析/成功退出，或循环到 EOF 才完成。

可先扫描：

```bash
rg -n 'recv\(|read\(|receive\(|termination|delimiter|length|EOF|close' src
```

这不是 HarmonyOS 特有的 TCP 行为；HarmonyOS PC 真机迁移使 lxi-tools 中潜伏的层次契约错误得到确定复现。知识可复用于任何长连接请求/响应客户端。

## lxi-tools 根因

liblxi 的 RAW/TCP 接收接口返回本次取得的字节批次，并不承诺一个调用覆盖完整 SCPI 响应。上游 lxi-tools 却在发送查询后只调用一次 `lxi_receive()`，然后立即打印返回字节并以成功结束。

因此目标仪器执行以下合法发送时：

```text
send "ACME,"
wait 200 ms
send "MODEL"
wait 200 ms
send "\n"
keep TCP open
```

上游会在第一批字节后输出 `ACME,` 并返回 0。这个责任属于 lxi-tools 的应用层组帧，不是 liblxi API 违反契约。

## 三臂真机实证

三臂使用同一官方 2.8 源码、Conan 依赖闭包、clang 15、公共 `lxi scpi --raw` 命令和 HarmonyOS PC AArch64 目标。私有 loopback 假仪器发送同样的三段响应，并在完整换行后继续保持连接 1.5 秒。

| 臂 | 实现 | 真机结果 |
|---|---|---|
| A 原始实现 | 一次正数 `lxi_receive()` 即完成 | 268 ms、rc=0、只输出 `ACME,` |
| B 直觉修复 | 循环读取直到连接关闭 | 完整响应已发送仍等到 1696 ms 超时，rc=1 |
| C 正确修复 | 按文本换行或 definite-length 声明组帧，共享总截止时间 | 655 ms、rc=0、输出 `ACME,MODEL\n`，对端尚未关闭 |

原始输出：

```text
arm-a-original: stdout_hex=41434d452c returncode=0
arm-b-wait-for-close: stdout_hex= returncode=1 stderr=Error: Timeout
arm-c-protocol-framing: stdout_hex=41434d452c4d4f44454c0a returncode=0
```

共同条件、精确反例差异、探针与原始日志 SHA256 见 `archives/l/lxi-tools/2.8/reports/path-b-evidence.md`。

## 正确修复

实现一个增量组帧状态机，而不是围绕单次读取猜测完成：

```c
deadline = monotonic_now() + total_timeout;
while (!frame_complete(buffer)) {
    remaining = deadline - monotonic_now();
    if (remaining <= 0)
        return TIMEOUT;
    n = receive(buffer + used, capacity - used, remaining);
    if (n <= 0)
        return TRUNCATED_OR_IO_ERROR;
    used += n;
}
return exact_frame_length;
```

SCPI RAW 的两种完成规则：

- 文本响应：扫描配置终止符，本项目为换行；
- IEEE 488.2 definite-length block：先取得 `#` 和十进制位数 `n`，再等待 `n` 位长度字段，验证位数、累积运算安全、最大容量和声明上限，最后等待精确 payload 字节数。payload 可含 NUL 和换行。

完整帧到达即返回，不能等待连接关闭。每次读取必须使用同一总截止时间的剩余预算；若为每个新分片重置完整超时，攻击者可用慢速字节流无限延长操作。

## 为什么直觉修复错误

### 正数短读即完成

TCP 不保留应用写入边界。调度、网络分段、代理或底层“当前排空”策略都能在应用帧中间产生正常短读。返回码 0 和部分可打印文本构成危险的假绿。

### 固定 sleep 后再读

固定延迟无法证明响应完整：短则仍截断，长则无谓降低每次请求性能，环境变化后仍会失败。

### 一直读到 EOF

SCPI RAW 仪器通常保持连接供后续命令复用。EOF 是连接生命周期事件，不是每个响应的消息边界。本次 Arm B 在完整响应已到达后仍等到超时。

### 每个分片重置超时

这不是统一总截止时间；只要对端在每个局部超时前发送一个字节，操作就可无限延长。

## 可执行验证

构建正式包并执行安装制品消费者：

```bash
python3 archives/l/lxi-tools/2.8/test_package/test_lxi_tools.py "$PACKAGE_FOLDER"
```

回归必须同时覆盖：

- 文本终止符被拆分；
- `#`、位数字段、长度字段和 payload 分别拆分；
- payload 含 NUL；
- 完整帧后连接继续保持；
- 非数字头/长度字段、`#0`、声明超限、提前 EOF 与总超时；
- 输出原始字节和退出码。

最终消费者输出：

```text
lxi-tools consumer scenarios: 14/14 PASS
```

回退核心组帧补丁后，拆分文本场景会稳定得到前缀假成功；把完成条件改成 EOF，则持久连接场景稳定超时。

## 独立普适性佐证

PyVISA 官方资源文档将终止字符作为消息完成条件，并说明读取会重复执行并拼接分块；pyvisa-py 的 TCP/IP 实现也独立维护 termination character、读取计数和 end indicator。它们佐证的是同一上层契约，不表示这些项目存在 lxi-tools 的具体缺陷：

- `https://github.com/pyvisa/pyvisa/blob/main/docs/source/introduction/resources.rst`
- `https://github.com/pyvisa/pyvisa-py/blob/main/pyvisa_py/tcpip.py`

## 适用与不适用边界

适用于 line protocol、SCPI RAW 和自定义长度前缀协议等持久字节流客户端。

不适用于：

- VXI-11 RPC、datagram 或框架已经提供完整消息语义的 API；
- 明确定义“连接关闭就是消息结束”的短连接协议；
- HiSLIP、WebSocket 等具有其他帧规则的协议，它们必须按自己的边界解析；
- `#0` 不定长块：需要带外结束条件或连接关闭，本项目在持久 RAW 模式明确拒绝；
- 非换行文本协议：终止符应由协议/配置给出，不能硬套换行；
- pipelining：当前 CLI 是单请求命令，不宣称缓存完整帧后的额外字节。

## 查重与新增差异

| 既有 stem/条目 | 重合点 | 本条新增机制 |
|---|---|---|
| `E545-draft-1D7D`（PseudoTCP 测试累计 `EWOULDBLOCK`） | 都涉及非阻塞 socket 和字节数 | E545 是测试代码把 `send=-1` 计入长度并重复输入；本条是正式接收路径把正数短读当应用帧完成 |

检索范围覆盖正式图谱、`knowledge/drafts/`、归档笔记和现有网络事件循环案例；未发现同时描述“持久字节流一次正数短读假成功 + 等 EOF 伪修复超时 + 按终止符/声明长度跨读取周期组帧 + 单调总截止时间”的既有知识。
