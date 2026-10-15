# OHOS/musl 缺 netdb 可重入族，且设备无 `/etc/protocols`、`/etc/services`

> 草稿（DRAFT）——配套结构化条目：`knowledge/drafts/oarc-dsc-2.16.1-netdb-reentrant-gap.kv`
> 样例库：`archives/o/oarc-dsc/2.16.1/`（四件套在 `knowledge-extension/`）

## 基本信息

| 项 | 值 |
|---|---|
| 主题 | 平台 libc 不提供 netdb 可重入查询族 + 根文件系统缺协议/服务数据库 |
| 首次记录 | oarc-dsc 2.16.1 适配（2026-10-11） |
| 触发阶段 | 链接期（`undefined symbol`）与运行期（名字退化为数字标签） |
| 严重度 | 2（能编过、但结果错——比直接编译失败更隐蔽） |
| 类别 | portability / libc / runtime |

## 问题形态

两条并列的缺口，**同一处代码同时踩中**：

1. **链接期**：OHOS（musl 系）sysroot 的 `<netdb.h>` 只声明非重入版
   `getprotobyname/getprotobynumber/getservbyname/getservbyport`，**不含 `_r` 族**。
   源码若写 `getprotobynumber_r(N, &p, buf, sizeof(buf), &pp)`：
   - 编译期：C99 起隐式声明只是告警 → 悄悄过去；
   - 链接期：libc 里没有该符号 → `undefined symbol: getprotobynumber_r`。
2. **运行期**：目标根文件系统**没有 `/etc/protocols` 也没有 `/etc/services`**。
   于是把调用改成非重入版之后，目标机上照样返回 NULL；按名字输出的维度
   （例：DSC 的 IPProto 维度 `val="udp"`）会退化成数字标签 `p17`。

> **只做「`_r` → 非 `_r`」替换 = 编得过、结果错**：gold 比对会以「名字对不上」的形式
> 失败，而且不会指向 netdb —— 这是本条目最主要的价值。

## 处理策略（样例库实证）

- **能力探测放源码侧、判据不靠平台宏**：补丁里按「哪些 libc 确实提供 `_r` 族」
  （glibc / Apple / Android / FreeBSD）条件编译，其余一律走「非重入 + 内置表」；
  补丁内**不含 `__OHOS__` 等平台宏**（R8）。
- **内置 IANA 协议号回退表**：实测 20 项常用协议号（`0 ip`、`1 icmp`、`2 igmp`、`4 ipencap`、
  `6 tcp`、`8 egp`、`17 udp`、`41 ipv6`、`43 ipv6-route`、`44 ipv6-frag`、`47 gre`、`50 esp`、
  `51 ah`、`58 ipv6-icmp`、`59 ipv6-nonxt`、`60 ipv6-opts`、`89 ospf`、`103 pim`、`112 vrrp`、
  `132 sctp`）（复验命令：`grep -oE '\{ *[0-9]+,' patches/0002-ip-proto-no-reentrant-lookup.patch | wc -l`
  → 20）。原表述为「26 项」，经 W4 独立审计逐行清点修正为实测值（`0 ip`、`1 icmp`、`6 tcp`、`17 udp`、
  `58 ipv6-icmp`、`132 sctp` …）。libc 查得到就用 libc，查不到用表，
  表也没有才退化为 `p<N>`。
- **服务名同理**：`/etc/services` 缺失时按端口号输出数字，或自备回退表。
- **验证必须先看链接期、再看运行期**：只跑一次完整构建看不出运行期退化
  （gold 失败信息不指向 netdb）。

## 适用库范围

- 任何在鸿蒙 PC 上交叉编译、调用 `get*by*_r` 的 C/C++ 代码；
- 任何运行期按名字解析协议号/服务号的功能：统计监控（DSC、dnsstat 类）、
  端口服务名标注、协议名展示、用 `/etc/services` 做白名单的组件。

**已知先例（均未覆盖本条目）**：`socat` 有 `getprotobynumber_r()` 变体探测、
`wxWidgets/0001-probe-getservbyname-r-signature.patch` 探测 `getservbyname_r` 签名
——它们解决的是「`_r` 族存在但签名不同」，**不解决本平台「`_r` 族根本不存在」**；
`alpine-baselayout` 提供 `/etc/protocols`+`/etc/services` 属另行补数据，
本平台没有对应兜底包，且交叉编译产物无法假定目标机存在该文件。

## 验证与判据

干净环境两阶段（脚本：`archives/o/oarc-dsc/2.16.1/knowledge-extension/reproduce.sh`）：

| 阶段 | 期望 |
|---|---|
| A：只打前置补丁 0001（`u_char`，既有知识 E113），不打本主题补丁 | 编译 rc=0（仅隐式声明告警）、**链接 rc=1**，日志含 `undefined symbol: getprotobynumber_r` |
| B：再打本主题补丁 0002 | 编译/链接 rc=0，运行输出 **`17=udp`**（且不得出现 `17=p17`） |

本轮 oarc-dsc 2.16.1 实测：A 阶段链接失败并命中该符号 1 次；B 阶段输出
`17=udp` 1 次、`17=p17` 0 次（`REPRO_EXIT=0`）；完整 `conan create` EXIT=0，
上游 `make check` 18 项 14 PASS / 4 FAIL（失败项与本主题无关：dnstap 未构建、
平台无 passwd/group 库）。
