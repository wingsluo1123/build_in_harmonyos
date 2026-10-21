# LIVE555 2025.05.24 测试报告

## 构建与依赖

- HarmonyOS PC / aarch64 / Clang 15 / Release / C++20。
- `openssl/3.5.8.1` 保留并由制品仓完整解析；未使用 `NO_OPENSSL`。
- 源码 SHA256：`e6185902c4bfe9235067a0bc80ec9a5f8a95956d9d07525ce169f3f9753afb0a`。
- 正式 `conan create` 成功，产物为四个静态库、181 个 `.hh`、一个 `.h` 和两份
  license。

## 上游测试与程序清点

- 注册自动测试：0；上游没有 `make check`、单元测试注册表或自动测试框架。
- 34 个默认 `testProgs` + 三个服务器 = 37 个自包含程序目标，真机全部构建。
- 一个可选 GSM 骨架已清点，但上游发行包缺少用户应提供的
  `testGSMEncoder.cpp/createNewGSMAudioSource()`，不属于适用的自包含目标。
- 程序构建不计为测试通过；媒体输入、外部网络、长期服务和人工交互型程序也未
  虚报为自动执行用例。

## 适配后消费者测试

安装后 Conan 消费者直接链接 `live::live`，执行一个 HarmonyOS PC 端到端场景，
其中八项行为断言全部通过：

1. 无参数 public factory 在受控空闲 250 ms 内不产生 10 ms 周期 `select()`。
2. 显式零 granularity 在受控空闲 250 ms 内无 10 ms 周期轮询。
3. 显式正 granularity 保持兼容的周期 tick 语义。
4. 外部线程触发可立即唤醒阻塞的 `select()`，十次 P95 小于 80 ms。
5. 单次组合 32-bit `EventTriggerId` 处理 32/32。
6. 四个生产线程发布 32 个不同 trigger，处理 32/32。
7. 预先填满非阻塞通知通道并确认发布命中 `EAGAIN` 后，合并通知仍通过 pending 扫描和重臂处理 32/32。
8. 以 `RLIMIT_NOFILE=3` 确定性令通道初始化失败后，选择 10 ms tick 回退并保持活性。

真机输出：

```text
[ok] public default selects active wakeup with no periodic tick
[ok] explicit zero granularity avoids periodic idle polling
[ok] explicit positive granularity retains polling semantics
[ok] cross-thread trigger wakes select with bounded latency
[ok] one combined 32-bit trigger call delivers every new bit
[ok] 32 distinct triggers from four producers are each delivered once
[ok] full notification channel coalesces and rearms pending triggers
[ok] wakeup initialization failure falls back to bounded tick
RESULT zero_idle=1 explicit_tick=25 latency_p95_ms=0.074 verdict=PASS
```

测试计数：上游 0/0；新增消费者行为测试 8/8；适配后合计 8/8。没有删除或修改
任何上游测试。三臂反事实证据见 `path-b-evidence.md`。

## 37 个程序目标的运行边界

- 13 个 multicast streamer：`testMP3Streamer`、`testMPEG1or2VideoStreamer`、
  `testMPEG1or2AudioVideoStreamer`、`testMPEG2TransportStreamer`、
  `testMPEG4VideoStreamer`、`testH264VideoStreamer`、`testH265VideoStreamer`、
  `testDVVideoStreamer`、`testWAVAudioStreamer`、`testAMRAudioStreamer`、
  `testMKVStreamer`、`testOggStreamer`、`vobStreamer`，均需要相应媒体输入并持续
  提供网络流。
- 4 个 multicast receiver：`testMP3Receiver`、`testMPEG1or2VideoReceiver`、
  `testMPEG2TransportReceiver`、`sapWatch`，均需要真实 multicast/SAP 对端。
- 2 个 multicast 组合工具：`testRelay`、`testReplicator`，需要上下游网络会话。
- 4 个 unicast 工具：`testOnDemandRTSPServer`、`testRTSPClient`、`openRTSP`、
  `playSIP`，属于长期服务或需要 RTSP/SIP 对端及媒体会话。
- 1 个 HLS 工具：`testH264VideoToHLSSegments`，需要 H.264 输入文件并持续生成分片。
- 10 个转换/索引工具：`testMPEG1or2Splitter`、
  `testMPEG1or2ProgramToTransportStream`、`testH264VideoToTransportStream`、
  `testH265VideoToTransportStream`、`MPEG2TransportStreamIndexer`、
  `testMPEG2TransportStreamTrickPlay`、`registerRTSPStream`、`testMKVSplitter`、
  `testMPEG2TransportStreamSplitter`、`mikeyParse`，分别需要格式匹配的媒体、索引、
  RTSP 服务或命令行密钥输入。
- 3 个服务器：`live555MediaServer`、`live555ProxyServer`、`live555HLSProxy`，
  均为长期运行服务且需要客户端或上游媒体源。

本 PR 只声明四库和 scheduler 知识主张的构建/运行验证；不把上述依赖外部媒体、
网络对端或长期运行的程序写成已通过的自动功能测试，也不宣称覆盖全部 RTSP、
RTP、TLS 或 SRTP 运行组合。
