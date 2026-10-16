# tsdecrypt 10.0 路径 B 三臂证据

## 核心结论

RTP 固定首部长度不等于 MPEG-TS 负载起点。接收端必须在完整 UDP 数据报上联合解析
CSRC 数量、扩展头长度与 padding，再验证 payload type、长度和每个 188 字节分组的
同步字节。只扩大缓冲区或只处理 CSRC 仍会拒绝或错位解释完全合法的数据报。

缺陷归属于 `tsdecrypt` 的应用层 RTP 组帧：上游直接固定剥离 12 字节。它不是 UDP API
缺陷，也不把截图、短写或 CAMD 协议混入同一知识主张。

## 共同实验条件

- 官方 v10.0 主源码与固定提交的两个官方子模块。
- HarmonyOS PC aarch64 真机、同一 Clang/LLD 15、同一已发布依赖和编译选项。
- 三臂均为真实 `tsdecrypt` 生产二进制，最终执行一次 ELF 签名。
- 三臂均运行同一 `test_package/test_rtp_input.py`，通过安装后 CLI 的 UDP 输入与文件输出
  观察结果；探针自身不实现 RTP 解析。
- 每个场景使用非特权临时端口，发送待测数据报后发送内容可区分的有效冲刷帧。

## 三臂结果

| 臂 | 实现 | 结果 | 关键观察 |
|---|---|---|---|
| A | 上游固定剥离 12 字节 | 失败 | 固定头与 marker 通过；首个带两个 CSRC 的合法包字节错位，`two_csrc` 稳定失败 |
| B | 解析 V/PT/CC，但忽略 X/P | 失败 | CSRC 通过；首个合法扩展包 `zero_word_extension` 被错误丢弃 |
| C | 完整解析 CC/X/P 并验证 TS 边界 | 通过 | 合法与非法矩阵 17/17 全部通过 |

实际退出码为 A=1、B=1、C=0。Arm A 失败时已得到 211876 字节错误流；Arm B 明确记录
`Invalid RTP/MPEG-TS datagram dropped`，说明“严格校验”若基于错误负载起点同样会拒绝
合法输入，而不是正确修复。

## Arm B 精确错误修复

Arm B 以最终解析器为基线，只保留固定头与 CSRC 计算，删去以下两个边界步骤：

```diff
- if (packet[0] & 0x10) {
-     extension_words = read_be16(packet + header_len + 2);
-     header_len += 4 + extension_words * 4;
- }
  payload_len = packet_len - header_len;
- if (packet[0] & 0x20)
-     payload_len -= validated_padding_len;
```

随后仍执行 188 字节对齐和 sync 检查。因此它不是“完全不校验”的稻草人，而是常见的
局部修复：解决 CSRC 后立即校验 payload，却遗漏 RTP 同一首字节中独立存在的 X/P 位。

## 可复现命令

仓库提交了可执行复现脚本 `reports/repro/build-three-arms.py` 和 Arm B 的完整精确补丁
`reports/repro/arm-b-cc-only.patch`。脚本复制正式配方：Arm A 删除 0009，Arm B 用精确
错误修复替换 0009，Arm C 保持正式配方；三臂其余源码、依赖、编译参数和签名步骤一致。
在 HarmonyOS PC 目标端运行：

```sh
python3 reports/repro/build-three-arms.py \
  --recipe . --profile ../../../../ci/conan/profiles/ohos-aarch64 \
  --output /tmp/tsdecrypt-three-arms
python3 test_package/test_rtp_input.py /tmp/tsdecrypt-three-arms/tsdecrypt-arm-a
python3 test_package/test_rtp_input.py /tmp/tsdecrypt-three-arms/tsdecrypt-arm-b
python3 test_package/test_rtp_input.py /tmp/tsdecrypt-three-arms/tsdecrypt-arm-c
```

预期退出码依次为 1（`two_csrc`）、1（`zero_word_extension`）、0（17/17）。探针由
命令行参数接收三臂 ELF，不包含或替代生产 RTP 解析逻辑。

## 证据绑定

实验 ELF 与原始日志保存在仓外，提交中只保留脱敏结论和哈希：

| 对象 | SHA256 |
|---|---|
| Arm A ELF | `9d6050088854f9a79e218fea7f805eb5f14966325f9b7fe2beb9d3982c1a6c7c` |
| Arm B ELF | `9fdc2b90c71bd3c569073977da252541216a2d3b5d47e48d5a8f3eff8c65484e` |
| Arm C ELF | `2e6e97e5a8aa12c22dd95a09283b3b3ce36d865e08f855e3fd81dbafd5395e33` |
| Arm A 原始输出 | `fd45bdc8b5c08e2f69a72acf67d41e291c1eca3f6ee530d30e4a994f93a9422c` |
| Arm B 原始输出 | `98bb888bb71accd24dedc93df34c5aefa41bf494e56ce90fea2f581384afbe38` |
| Arm C 原始输出 | `6cf60921410d8ba62e2590d0a7f9f9a0a4725c804ddd488097db08611984d276` |
| 公共黑盒探针 | `debb9ab3744c332db1cc08b36f02d1362b925b57d93dd2cffa1270de33a64336` |
| 三臂构建脚本 | `d6c9cb34e12ff3a064ca24143a518cc074897ffe809ebe679cb60aaaaf82e3bf` |
| Arm B 精确补丁 | `f39e0ef397f0adbe85c8f24dbadae6d902c8404a62834a51fe8e3f7c45e15f41` |

自签名和构建时间可能令 ELF 哈希不可重复；复现条件是三臂行为关系和逐字节预言机，
不是二进制必须逐字节相同。

## 机械规则与边界

触发特征：RTP/UDP 接收器把 `packet + 12` 直接交给固定大小分组协议，或只解析 CC 后
立即校验负载。检查顺序应为：完整数据报 → V/PT → CC → X 及扩展字数 → P 及尾部长度
→ payload 上限/188 对齐 → 每包 sync。

本结论不适用于已由 RTP 库提供去首部 payload 的调用点，也不适用于没有 X/P/CSRC 的
私有固定 12 字节协议。RTP marker 位不改变 payload type；校验 PT 时必须屏蔽 marker。
