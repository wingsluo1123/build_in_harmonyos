# RTP 固定首部长度不等于负载起点

> Draft: `E429-draft-1BEB`

## 错误特征

接收端从 UDP socket 得到一个完整 RTP 数据报后直接执行 `payload = packet + 12`。
固定头输入看似工作正常，但合法的 CSRC、header extension 或 padding 会出现以下两类症状：

- 首部字节被当作 MPEG-TS 数据，输出错位且下游失去 0x47 同步；
- 增加 188 字节对齐检查后，合法数据报被记录为 invalid 并直接丢弃。

这类问题不需要丢包、乱序或分片即可复现；单个本地 UDP 数据报足以触发。

## 触发条件

同时满足以下特征时应检查：

1. 应用直接读取完整 RTP/UDP 数据报，而不是消费 RTP 库已去首部的 payload；
2. 代码存在固定 `12` 或 `RTP_HDR_SZ` 的指针移动/长度扣减；
3. 下游协议依赖固定分组边界，例如 MPEG-TS 的 188 字节和 0x47 sync；
4. 输入可能合法使用 CC、X 或 P 中任一项。

RTP 第二字节最高位是 marker，不属于 payload type；PT=33 校验必须使用低 7 位。

## 根因

RTP v2 的 12 字节只是固定部分：

```text
payload_offset = 12 + 4 * CC
if X: payload_offset += 4 + 4 * extension_length_words
payload_end = datagram_length
if P: payload_end -= last_octet_padding_length
```

每一步都依赖仍在完整数据报中的字段，且必须先做截断、乘法边界与 padding 范围校验。
只处理 CC 是一个有迷惑性的局部修复：普通 CSRC 用例恢复，但 X/P 仍让上层分组检查基于
错误的起点或终点。

## 正确处理顺序

1. 使用 datagram 语义读取一次完整 UDP 包，不用 stream 式“读满固定长度”。
2. 校验最小长度、版本 2 和 `(marker_pt & 0x7f) == expected_pt`。
3. 由 CC 计算 CSRC 末端并检查是否越过数据报。
4. X 置位时，先确保扩展头 4 字节存在，再按网络字节序读取 32 位字数；先比较剩余长度，
   再做偏移加法。
5. P 置位时读取最后一个字节；拒绝零 padding 或超过当前 payload 的长度。
6. 得到最终 `[payload_offset, payload_end)` 后再验证业务上限、188 对齐与每个 TS 包的
   0x47 sync。
7. 任一检查失败时丢弃整个数据报，不能把部分 payload 送入有状态解密/重组队列。

## 三臂实证

在 HarmonyOS PC aarch64 真机上，以同一 tsdecrypt 10.0 生产路径、编译器、依赖、签名
和黑盒探针进行对照：

| 臂 | 唯一差异 | 结果 |
|---|---|---|
| A | 官方固定剥离 12 字节 | 固定头通过，两个 CSRC 的合法包失败 |
| B | 加入 V/PT/CC 与 TS 校验，但不处理 X/P | CSRC 通过，零字扩展的合法包失败 |
| C | 完整解析 CC/X/P 后验证 TS | 合法/非法矩阵 17/17 通过 |

撤销最终解析修复会回到 Arm A，同一消费者测试稳定失败。证据摘要、实验 ELF 与日志哈希
见 `archives/t/tsdecrypt/10.0/reports/path-b-evidence.md`。

## 禁止做法

- 不要只把接收缓冲从 `FRAME_SIZE+12` 扩大；更大的缓冲不会改变 payload 起点。
- 不要只处理 CC 后立即检查 188 对齐；X/P 是同级可选字段。
- 不要把 payload type 与整个第二字节直接比较；marker 会造成假拒绝。
- 不要依赖连接关闭或下一数据报补齐；RTP/UDP 的边界已经由数据报给出。
- 不要在解析扩展字数后先执行乘法/加法再检查；应以“剩余字节 / 4”为上界比较。

## 适用边界

- 若成熟 RTP 库已经提供已验证 payload，本规则下沉到该库，调用方无需重复剥头。
- 私有协议若书面约束 CC=X=P=0，可以固定 12 字节，但应在入口明确拒绝这些位，而不是
  悄然错位解释。
- 本条只处理单个 RTP 数据报内的负载边界，不覆盖序号重排、抖动缓冲、FEC、IP 分片或
  MPEG-TS 跨 RTP 包重组。

## 查重结论

对正式图谱与草稿检索 RTP、CSRC、header extension、payload type、MPEG-TS、188-byte
alignment 和 padding，未发现相同机制条目。已有流式短写、TLS 状态机、构建期 SRTP
依赖注入等条目不涉及 RTP 可变首部到上层固定分组边界的契约。
