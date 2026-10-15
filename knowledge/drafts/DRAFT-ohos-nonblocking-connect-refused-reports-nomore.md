# DRAFT-ohos-nonblocking-connect-refused-reports-nomore

> Contributor: isc-dhcp-4.4.3-p1 | Status: Draft | Updated: 2026-10-14
> Source: isc-dhcp 4.4.3-p1 HarmonyOS PC 适配（PR #15730），OMAPI/dhcpctl 连接栈 + 消费者负向测试
> 领域: 网络编程 / 错误码语义 / 测试断言 / OHOS 移植

## 背景

OHOS（aarch64、musl libc）上把「非阻塞 connect → select/poll 事件循环 → 独立等待层」三段架构的
C/C++ 网络库做移植与验证时，一个反复消耗调试时间的问题：**对关闭端口发起的连接，拒绝确实发生了
（套接字层可见 ECONNREFUSED），但库的等待层返回给调用者的错误码却是 "no more"（ISC_R_NOMORE）**。
识别这一语义漂移前，口径容易走两个极端——按"预期 CONNREFUSED"判会假失败；放宽成"非成功即可"
又会把根本不合法的负例（如地址解析都没过）也判过，形成假通过。

本条目来自 isc-dhcp 4.4.3-p1 适配（OMAPI 管理接口，`dhcpctl_connect` → `omapi_protocol_connect`
→ OMAPI dispatch 循环），但结论不绑定该库：任何同类三段架构都会遇到同一表达。

## 错误签名

- 消费者输出：`reported: no more`（isc-dhcp 测试实例）
- 包内工具交叉复现：`dhcpctl_connect: no more`（omshell 连本机关闭端口）
- 等价形式：`ISC_R_NOMORE`（结果码文本 "no more"）、libisc 风格 `NOMORE`
- 易混淆注意：**不是** `host unknown`/`HOSTUNKNOWN`（那是解析期早错，见「触发条件」反例）

## 根因

对 127.0.0.1 的关闭端口，事件链实际完整走完：

1. **非阻塞 connect()** → 返回 `EINPROGRESS`（设备实测 errno=115），连接未立即可判定；
2. **事件循环 select 可写** → 套接字进入可写集合；
3. **getsockopt(SO_ERROR)** → 取回 `ECONNREFUSED`（设备实测 errno=111）——**拒绝在此已确凿到达套接字层**；
4. **连接内部层**（OMAPI `connect_internal`）→ 把 SO_ERROR 转成连接类错误码（`ISC_R_CONNREFUSED`）
   并执行断开清理（拆除已注册的 IO）；
5. **dispatch/等待层** → 时序上先于 waiter 观察到 IO 状态集合清空，`omapi_dispatch` 返回
   `ISC_R_NOMORE`——该码的字面语义是「没有更多可等待的 IO」，在此语境=「拒绝已被事件循环消费」；
6. **等待层如实上报** → `dhcpctl_connect` 返回 NOMORE。**不是解析失败、不是"未连接"、不是资源耗尽**。

关键认知：错误码在这一架构里有"两跳"——套接字层 → 连接层 → 等待层。**套接字层的细码
（CONNREFUSED）可能在第二跳被事件循环消费掉**，等待层只能报告它自己观察到的状态。这是
POSIX 异步 connect 语义与库内状态机实现（非 OHOS 特有 bug）的交互结果，但在 OHOS 的
调度/时序下稳定复现。

## 触发条件

- 目标端口处于**关闭**状态（`connect` 被 RST 拒绝）的负向测试或错误处理路径；
- 库为「非阻塞 connect + select/poll 事件循环 + 独立等待层」三段架构；
- 想用「错误码 == ECONNREFUSED」判定"拒绝已发生"的任何断言/分支。

**反例（必须与 NOMORE 区分）**：主机字符串不合法（如数字地址带尾点 `127.0.0.1.`）时，
`getaddrinfo` 按主机名解析失败 → `HOSTUNKNOWN`。此时连接**从未发起**，与 NOMORE 是本质不同的
两种结局。若断言写成 `!= SUCCESS`，这种"从未连接"的错例会静默通过（实测实踩，见下）。

## 修复方案

**测试/断言层（推荐）**：负向断言按「套接字层拒绝及其事件循环表达」白名单判定——
`{CONNREFUSED, NETUNREACH, NOMORE}`（isc-dhcp 实例为 `{ISC_R_CONNREFUSED, ISC_R_NETUNREACH, ISC_R_NOMORE}`），
并对名字解析类早错（HOSTUNKNOWN 等）**明确拒绝**——它们表明连接根本没到达套接字层。

**诊断层（fallback）**：若等待层码无法区分场景，降一层自证——独立探针程序直接断言
`connect()==EINPROGRESS && getsockopt(SO_ERROR)==ECONNREFUSED`（见「验证」），再单独断言
库调用"非成功"。两层证据分开表述：套接字层证明拒绝到达，库层证明调用方未误判成功。

**禁止**：
- `ret != SUCCESS` 式无限宽断言——任何早错（句柄校验/对象分配/解析失败）都满足，无法证明
  连接路径真的执行过（实测实踩：尾点地址时日志报 host unknown，测试却判过）；
- 在任何地址/主机名位置使用带尾点的"IP 字面量"（如 `"127.0.0.1."`）——不属于合法数字地址，
  会被当主机名解析。

## 验证

设备实测（HarmonyOS PC aarch64）：

```
# 探针：非阻塞 connect 到 127.0.0.1 的关闭端口
connect() = -1, errno = EINPROGRESS (115)
select(write) → writable
getsockopt(SO_ERROR) = ECONNREFUSED (111)

# 同环境包内工具对同一端口交叉复现
$ omshell 127.0.0.1 1
dhcpctl_connect: no more
```

两条证据的结论一致：拒绝到达套接字层（SO_ERROR 有细码），而上层等待器观察到的是 NOMORE。
isc-dhcp 的消费者测试据此把断言改为白名单 `{CONNREFUSED, NETUNREACH, NOMORE}` 后，真实
拒绝路径稳定通过、且解析期假通过被堵死（全量日志随 PR #15730 归档）。

## 边界

- NOMORE 只应在**已确认事件循环接管了连接生命周期**的架构下被接受。裸 socket 代码里出现
  NOMORE 不适用本条——那里应直接看 SO_ERROR。
- 白名单只接受"拒绝/不可达"类码；把超时或其它错误码并入白名单会重新引入假通过风险。
