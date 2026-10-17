# OpenSSL 3.x SECLEVEL 过滤 TLS1.0/1.1 的可协商性判定与适配

## 场景

libest 1.0.0 适配 HarmonyOS PC（aarch64，clang 15，openssl/3.5.6.1）。上游版本语义
测试（US894/US901）用 `SSL_CTX_set_min/max_proto_version` 固定 TLS1.0/1.1 做负向/正向
断言，运行时报 `no protocols available`，曾一度被误判为"客户端构建能力限制"。

## 症状

```
SSL routines:tls_setup_handshake:no protocols available (0A0000BF)
Test: TLS 1.1 ... FAILED   us901.c:328 rv > 0
```

- `openssl version -a` 的 `options:` 行是 `bn(64,64)`，**不含** `no-tls1`/`no-tls1_1`
  → 编译期并未禁用 TLS1.0/1.1
- `SSL_CTX_set_min_proto_version/max(TLS1_1)` 返回 1（设置成功），但仍报
  `no protocols available`
- 现象与"编译期禁用旧版本"完全同形，仅凭症状无法区分

## 根因

OpenSSL 3.x 默认安全级别 `SECLEVEL=2`（`SSL_CTX_get_security_level()` 实测为 2）。
该级别按安全强度过滤 TLS1.0/1.1 的 SHA-1/MD5 系套件：客户端若只设 min/max 协议版本
而不调低安全级别，握手在协商前即报 `no protocols available`。服务端若保持默认
SECLEVEL 同样拒绝 TLS1.1。

## 对照实验（可协商性判定）

```c
SSL_CTX_set_security_level(ctx, 0);
SSL_CTX_set_cipher_list(ctx, "DEFAULT@SECLEVEL=0");
```

- 实验证明：`SECLEVEL=0` + 显式 cipher list 后 TLS1.1/TLS1.0 可协商
- 结论：**可协商 → 属测试环境适配，必须修通**，不得放宽 `us901.c:328 rv > 0`

## 修复（测试客户端 + 服务端两侧）

客户端（测试用例内，补丁 0043/0056）：

```c
SSL_CTX_set_security_level(ssl_ctx, 0);
SSL_CTX_set_cipher_list(ssl_ctx, "DEFAULT@SECLEVEL=0");
```

服务端（`est_server_http.c set_ssl_option`，补丁 0014）：

```c
SSL_CTX_set_min_proto_version(ssl_ctx, TLS1_1_VERSION);
SSL_CTX_set_max_proto_version(ssl_ctx, TLS1_2_VERSION);
SSL_CTX_set_security_level(ssl_ctx, 0);
SSL_CTX_set_cipher_list(ssl_ctx, "DEFAULT@SECLEVEL=0");
SSL_CTX_set_options(ssl_ctx, SSL_OP_NO_SSLv2 | SSL_OP_NO_SSLv3 | SSL_OP_NO_TLSv1);
```

修复后实测：US901 23/23（含 TLS1.1 正向通过、SSL3.0/TLS1.0 Fail 负向断言成立）、
US894 27/27，两入口各连续两次 exit 0。

## 验证

```bash
openssl version -a | grep 'options:'   # 无 no-tls1/no-tls1_1 -> 编译期未禁用
# 两侧 security level 实测 + DEFAULT@SECLEVEL=0 对照实验 + 修复后版本语义全过
```

## 适用边界 / 反例 / 限制

- 适用：所有在 OpenSSL 3.x 下固定 TLS1.0/1.1 做协商测试或版本语义断言的老库
- 反例：仅凭 `s_client -tls1_1` 报 "no protocols available" 就判"构建能力限制"是错的
  （libest r10 误判案例）；不得放宽负向断言（SSL3/TLS1.0 必须仍被拒绝）
- 限制：降低 SECLEVEL 有安全隐患，仅限测试上下文；若对照实验证明仍不可协商，
  才按结构性阻塞举证并待分析端裁决

## 关联

- 相似：E162
- 引用补丁：`patches/0014-src-est-est_server_http.c.patch`、
  `patches/0043-test-UT-US894-us894.c.patch`、`patches/0056-test-UT-US901-us901.c.patch`
