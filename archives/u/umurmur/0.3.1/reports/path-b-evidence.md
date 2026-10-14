# uMurmur 0.3.1 路径 B 三臂证据

## 结论

uMurmur 在接受 TCP 连接时、非阻塞 TLS 握手完成前就把服务端 `Version` 消息加入应用发送队列。上游事件循环只在已有序列化发送缓冲或 TLS 读操作阻塞于写时订阅 `POLLOUT`，握手完成后也没有重新检查应用队列。因此 TLS 握手可以成功，但遵循“等待服务端首帧后再发送认证帧”的客户端会永久等待。

正确修复不是让未完成握手的队列直接触发 `POLLOUT`，而是在 `SSLready` 从 false 转为 true 的状态转换点重新评估并排空一条应用消息。前者既没有可靠发送首帧，还会让只建立 TCP、不发送 ClientHello 的连接触发忙轮询。

## 环境与共同条件

- 目标：HarmonyOS PC aarch64，`HongMeng Kernel 1.12.0`。
- 源码：官方 `v0.3.1`，三臂仅 `src/client.c` 的队列调度方式不同。
- 编译器、依赖、TLS 证书、配置、监听地址和客户端探针完全相同。
- 使用非特权临时端口和临时证书；三臂均由正式 Conan 配方的 `package()` 完成最终 ELF 签名。
- CPU 指标读取同一目标进程 `/proc/<pid>/stat` 的第 14、15 字段，即 `utime + stime`，测量窗口为 1 秒。

## 三臂结果

| 臂 | 改动 | TLS 握手 | 服务端首个 Version | 未握手空闲 TCP 的 1 秒 CPU ticks | 结果 |
|---|---|---|---|---:|---|
| A | 上游队列处理原样 | 成功 | 超时 | 不适用 | 复现缺陷 |
| B | 直觉修复：队列非空即订阅 `POLLOUT` | 成功 | 仍超时 | 105 | 错误修复；引入忙轮询 |
| C | 仅在 TLS ready 状态转换后排空队列 | 成功 | 收到，且 payload 含 `0.3.1` | 0 | 正确修复 |

目标端原始摘要：

```text
ARM_A_PASS tls_handshake_ok_server_first_version_timeout
ARM_B_PASS still_times_out_and_busy_poll_ticks=105
ARM_C_PASS version_delivered_idle_ticks=0
THREE_ARM_PASS
```

## Arm B 精确反例

错误修复只增加一项事件订阅条件，没有改变握手或应用写回调：

```diff
-		if (c->txsize > 0 || c->readBlockedOnWrite) /* Data waiting to be sent? */
+		if (c->txsize > 0 || c->readBlockedOnWrite ||
+		    !list_empty(&c->txMsgQueue)) /* Data waiting to be sent? */
```

可直接应用的完整补丁为
`reports/repro/arm-b-always-pollout.patch`。它证明“持续监听可写”不是 ready
转换调度的等价替代：未发送 ClientHello 的 TCP socket 通常持续可写，循环不断唤醒；
原 `Client_write()` 又没有合法推进握手前应用队列的状态转换，所以首帧仍然滞留。

## 可执行复现步骤

以下命令在 HarmonyOS PC 目标端执行。构建脚本为 A/B/C 分别创建临时配方副本：A 从
`conandata.yml` 移除最终调度补丁，B 用上述精确反例替换它，C 保持正式配方；三臂均通过
`conan create --test-folder=` 从官方源码构建、安装并签名，不复用实验二进制。

```bash
REPO=/path/to/build_in_harmonyos
WORK="$(mktemp -d /data/storage/el2/base/cache/umurmur-three-arm.XXXXXX)"

python3 "$REPO/archives/u/umurmur/0.3.1/reports/repro/build-three-arms.py" \
  --recipe "$REPO/archives/u/umurmur/0.3.1" \
  --profile "$REPO/ci/conan/profiles/ohos-aarch64" \
  --output "$WORK/arms" \
  --conan "$(command -v conan)"

OPENSSL="$(command -v openssl)" \
python3 "$REPO/archives/u/umurmur/0.3.1/reports/repro/probe-three-arms.py" \
  --arm-a "$WORK/arms/umurmurd-arm-a" \
  --arm-b "$WORK/arms/umurmurd-arm-b" \
  --arm-c "$WORK/arms/umurmurd-arm-c" \
  --config "$WORK/arms/umurmur.conf"
```

探针为每一臂生成独立非特权端口和临时证书，以 `-d -c` 前台启动，完成真实 TLS
握手，并在客户端未发送应用数据时读取第一个 Mumble 帧。Arm B/C 随后各建立一个只完成
TCP 连接、不发送 ClientHello 的空闲连接。CPU ticks 的实现和判定为：

```text
ticks = (utime_after + stime_after) - (utime_before + stime_before)
Arm B >= 20
Arm C <= 10
Arm B >= Arm C + 20
```

`/proc/<pid>/stat` 在进程名右括号之后从字段 3 开始，因此脚本读取拆分后的索引 11、12，
对应规范中的字段 14、15。阈值不要求复现某个固定调度次数；它只区分一秒内持续忙轮询与
正确修复后的空闲状态。

## 产物、脚本和输出绑定

```text
Arm A ELF       80a7f7ed983ff9fde5af5555354c1cd6ca953f7eb1a916125bbe524dc45e2246
Arm B ELF       cf9d23923ada5c62e94a4919606c9d4ac61c6725f3ac401b029daefce4a28536
Arm C ELF       ae59ce1dc845f50e49d7acd2da2bd3dbcaf95d65d154e027964873ae07409923
Arm B 反例补丁  eacb7e638dd2590c421a576944ac5c895213c4c4fd3f283e0d37988b8c16920f
三臂构建脚本    c2623ed37074a211690621c843939a9caac5b6b73bd0800494599088b1538854
三臂目标端探针  4fa896e80775444b593ad8b1622139a11bb8daf627d01b77ea3fe038c9fac5eb
脱敏标准输出    d933eb83037d866ce9fe6c29d91bb6d1e076c3b5a0607d5d561be686ca6755d0
```

实验 ELF 和含临时路径的完整构建日志不提交；精确反例补丁、构建脚本和目标端探针均随
PR 提交，审核者可以从官方源码重新构建并得到同一行为关系。ELF 自签名可能包含非确定性
数据，因此哈希绑定本次运行产物，不把 ELF 字节完全相同当作复现条件。

## 完整协议回归

正确修复臂随后由正式 `test_package` 在同一真机完成：

```text
uMurmur target closure passed: config + server-first TLS Version + protobuf auth + session-bound encrypted UDP + UDP status + malformed inputs + foreground/background SIGTERM
```

回归链包括：最终安装 ELF 的 `.codesign`、配置正负例、服务端首帧、最小合法 Protobuf-C Authenticate、CryptSetup/ServerSync、使用该 TLS 会话密钥和 nonce 的 OCB 加密 UDP 往返、公共 UDP 状态查询、错误 TLS 数据、超长帧拒绝、存活检查、前台和守护模式 SIGTERM、PID 文件清理。

## 查重与适用边界

- 已有 `jamnntpd` 草稿覆盖非特权端口、临时配置和守护进程回环测试；这些测试方法不作为本知识的新意。
- 对“TLS handshake + queued application frame + ready transition + poll scheduling”组合检索未发现同机制正式条目或草稿。
- 知识引擎命中 E026 是 `TLS` 被解释成 Thread Local Storage 的假阳性，与网络 TLS 状态机无关。
- 机械触发条件是：握手前允许排队应用帧、事件掩码不观察该队列、握手完成只更新布尔状态且没有显式发送调度。缺少任一条件时不适用。
- 本结论不等价于普通 `dlopen`、签名、端口可达性或一般 TLS 握手测试。
