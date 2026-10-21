# LIVE555 2025.05.24 路径 B 三臂证据

## 唯一知识主张

允许外部线程发布事件的阻塞式事件循环中，atomic flag 只发布状态，不能中断
`select()` 等阻塞等待。正确实现必须先发布 pending 状态，再通过进入等待集的
非阻塞就绪通道通知。通知合并或 `EAGAIN` 只有在通道保持可读、pending 状态仍
可枚举，并且每次分派后对剩余 pending 主动重臂时才安全。

## 固定输入与判定器

三臂均取自 SHA256 为
`e6185902c4bfe9235067a0bc80ec9a5f8a95956d9d07525ce169f3f9753afb0a`
的同一发行源码，使用同一 Clang 15、C++20、HarmonyOS PC AArch64 目标、消费者
源码、输入、watchdog 和正确行为预言机。消费者源码 SHA256 为
`12df88f19f2192e8c0591d9fc03750edaaf0256b74c87bfcb0d45435d1aecf8a`。

共同场景：受控空闲 250 ms；十次由同步屏障后延迟 20 ms 的外部线程触发，使用
单调时钟记录延迟并以 300 ms watchdog 截止；单次组合全部 32 个 trigger bit；
四个生产线程并发发布 32 个不同 trigger。成功条件固定为：空闲返回不超过 3，
最大触发延迟小于 80 ms，组合与并发场景均处理 32/32。

三臂是分别构建的三个制品，不是同一个二进制：

1. A 原始：保持默认 10 ms tick 和原始 `triggerEvent()`。
2. B 错误修复：只把默认粒度改为 0，不增加等待集唤醒通道。
3. C 正确修复：应用仓内主动唤醒补丁；补丁 SHA256 为
   `54f9e7ba885efccc2ed2bc5ad0ff236d84abb50aa068d78740820c5671f965ee`。

探针现随 PR 位于 `test_package/three_arm_probe.cpp`；错误修复的精确补丁位于
`test_package/wrong-disable-tick.patch`，其 SHA256 为
`3f1628a9a236a2094ca5a47fb454dd8ebcf6f97dbaafc02e23ebfeaf23a29e4c`。在三个由同一配方生成 `config.ohos` 并
分别执行 `make -j4` 的源码树中，使用完全相同的链接和执行命令：

```sh
$CXX -std=c++20 -I$ARM/BasicUsageEnvironment/include \
  -I$ARM/UsageEnvironment/include -I$ARM/groupsock/include \
  test_package/three_arm_probe.cpp \
  $ARM/BasicUsageEnvironment/libBasicUsageEnvironment.a \
  $ARM/UsageEnvironment/libUsageEnvironment.a \
  $ARM/groupsock/libgroupsock.a -pthread -o $ARM/three-arm-probe
$ARM/three-arm-probe  # A：原始树，退出 1
$ARM/three-arm-probe  # B：应用 wrong-disable-tick.patch，退出 1
$ARM/three-arm-probe  # C：应用正式补丁，退出 0
```

三个 `$ARM` 均从固定源码 SHA 解包；B 只应用仓内错误补丁，C 只应用仓内正式补丁。
三条执行命令及所有输入完全相同；探针以 `pselect()` 包装器观察 public 无参数
factory 内部的 `select()` 返回次数，不修改被测库。stdout 即下表关键输出，成功
判据由探针源码固定。

## 真机结果

设备：HUAWEI MateBook Pro HAD-W32，HarmonyOS / HongMeng Kernel 1.12.0，
aarch64。三个制品依次运行同一探针：

| 臂 | idle steps | P50 ms | P95 ms | max ms | combined | concurrent | 正确预言机 |
|---|---:|---:|---:|---:|---:|---:|---|
| A 原始 | 25 | 10.045 | 10.098 | 10.098 | 32 | 32 | FAIL（空闲轮询） |
| B 仅取消 tick | 1 | 300.000 | 300.000 | 300.000 | 1 | 1 | FAIL（只能由 watchdog 唤醒） |
| C 主动唤醒 | 1 | 0.127 | 0.441 | 0.441 | 32 | 32 | PASS |

因此原始实现、固定错误修复均被同一正确行为预言机稳定拒绝，正确修复同时满足
低空闲返回与有界通知延迟。撤销“状态发布后写入就绪通道”会退回 B 臂结果；只
保留通知而撤销按新置位 bit 计数，则组合 bitmask 无法完成 32/32。

正式安装后消费者进一步执行八项断言，覆盖 public default、满通道合并/重臂与
初始化失败回退；其源码 SHA256 为
`dfd029100668da8eed0ab06cfe37bc85d7c18bfee5b8bb5ab362fde6b3421c61`，最终补丁真机
重建后的结果为
`zero_idle=1 explicit_tick=25 latency_p95_ms=0.074 verdict=PASS`。

## 范围与限制

- `SingleStep()` 返回次数是受控 scheduler 指标，不等同于整个操作系统的 CPU
  唤醒次数或能耗测量。
- 满通道用例通过受保护的 scheduler 测试 seam 预填通知通道，再使用合法 public
  API 单次发布组合 32-bit trigger；消费者在 `send()` 系统调用边界记录实际
  `EAGAIN`，直接验证合并后扫描与重臂，不把
  重复同一 public trigger 冒充业务场景。
- 生命周期遵守上游约束：生产线程停止并 join 后才销毁 scheduler；不把关闭后
  继续调用 `triggerEvent()` 的未定义用法纳入主张。
- E1078 的 pthread 协作退出机制与本项目部分使用相似原语，但它不覆盖正常事件
  交付中状态发布与阻塞等待通知的配对规则。
