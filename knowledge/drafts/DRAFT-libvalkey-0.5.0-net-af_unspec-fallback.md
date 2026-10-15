# libvalkey 0.5.0 — 双族 getaddrinfo 回退覆盖白名单 errstr（#66 NXDOMAIN 修复）

> 知识草稿（路径 B，R02）。配对 KV: `DRAFT-libvalkey-0.5.0-net-af_unspec-fallback.kv`

## 问题

上游 `tests/client_test.c` 第 #66 用例 `Returns error when host cannot be resolved`
在鸿蒙 PC 真机（aarch64）上 FAILED：域名 `nonexistent.example.com` 确实不可解析
（`getaddrinfo` AF_INET 返回 EAI_NONAME），但库 `valkeyConnect` 的
`c->errstr` 是 `System error`（EAI_SYSTEM 文案），不在上游硬编码的 10 条
白名单内，逐字比对失败。

## 根因

`src/net.c` 的 DNS 解析在失败后按**单族**回退：先 `AF_INET`（失败，
rv=-2 EAI_NONAME "Name does not resolve"，白名单内），再改 `AF_INET6`
重试（rv=-11 EAI_SYSTEM，"System error"，白名单外），并以**最后一次**
`gai_strerror(rv)` 写入 errstr。

设备实测（最小复现）：

| 探测 | 结果 |
|------|------|
| `getaddrinfo(AF_INET, nonexistent.example.com)` | rv=-2，`Name does not resolve`（白名单内 ✓） |
| `getaddrinfo(AF_INET6, ...)`（any flags） | rv=-11，`System error`（EAI_SYSTEM，errno=22 EINVAL，白名单外 ✗） |
| `getaddrinfo(AF_UNSPEC, ...)` | rv=-2，`Name does not resolve`（白名单内 ✓） |
| DNS 服务器 AAAA 查询（114.114.114.114/8.8.8.8） | 正常应答（rcode=0 ancount=0） |

即平台 musl resolver 的 **AF_INET6 主机名解析路径在系统级失败**（无全局
IPv6、errno=EINVAL），即使 DNS 服务器对 AAAA 查询回应正常；AF_UNSPEC
单次查询则返回语义正确的白名单文案。

## 修复

将回退从「换另一单族」改为 **AF_UNSPEC 单次回退**（一次查询同时尝试
A/AAAA）：

```c
rv = getaddrinfo(c->tcp.host, _port, &hints, &servinfo);
if (rv != 0 && hints.ai_family != AF_UNSPEC) {
    hints.ai_family = AF_UNSPEC;
    rv = getaddrinfo(c->tcp.host, _port, &hints, &servinfo);
}
if (rv != 0) {
    valkeySetError(c, VALKEY_ERR_OTHER, gai_strerror(rv));
    return VALKEY_ERR;
}
```

以 `patches/0001-src-net.c.patch` 固化进配方（conandata.yml 登记，sha256
`cb567a31...`）。

## 验证

- 修复后 `./tests/client_test -h 127.0.0.1 -p 56379 -s <sock>`：**#66 PASSED**，
  112 PASSED / 0 FAILED / 3 SKIPPED（UNIX socket 段因 HMDFS 拒绝 AF_UNIX bind 跳过），
  `ALL TESTS PASSED`，exit 0。日志 SHA256 `ac14753a...`。
- 鸿蒙特有测试 `harmonyos_specific_test.c`：exit 0，0 failures（TCP PING→PONG +
  AF_UNIX 受限行为优雅返回）。日志 SHA256 `f9028d77...`。

## 适用边界

适用于所有使用 getaddrinfo 双族回退（先单族、失败换另一族）的 C/C++ 客户端库
（libvalkey、hiredis 及其衍生），在平台某地址族解析路径系统级失败（EAI_SYSTEM）
的场景。纯 IPv4/AF_UNSPEC 单次查询不受影响。

## 反例与限制

- 不得通过修改上游测试、删减白名单比对、跳过用例或伪造 exit 0 使其通过。
- 环境层（提供全局 IPv6/改 resolv.conf）在本真机不可行（resolv.conf 只读、无
  全局 IPv6）；修补丁方案不依赖外网环境，CI 可复现。

## 证据

- `nxdomain_probe.c` / `probe8.c`：真机 getaddrinfo 各族返回值与 gai_strerror 原值
- `client_test_server_backed_r02.log`：修复后 #66 PASSED 与全量统计
- `harmonyos_specific_test.log`：设备运行通过
- 现有知识等价检索：无等价命中（DRAFT-6050 libnxml dead-domain 为数据源替代，
  与本问题「库双族回退 errstr 覆盖」不同类）