# STARTTLS 原地升级后必须原子撤销握手前事务、身份与授权状态

> 状态：DRAFT（路径 B 知识库扩展候选）｜来源：mailfront/2.12 HarmonyOS PC 适配｜日期：2026-10-15
> 候选编号：E550｜机器可读层：`E550-draft-4F37.kv`

## 结论

STARTTLS 成功只证明传输层已经切换，不能证明应用会话已经成为“新的安全会话”。如果服务器在当前进程和同一 session 对象内替换明文文件描述符，握手成功路径必须在读取下一条命令前，原子撤销握手前的：

- 协议事务游标；
- EHLO 名称、能力和协议身份；
- 认证身份副本；
- 由认证派生的 relay 或其他授权缓存。

只清输入缓冲、只设置 `tls_state` 或只调用普通邮件事务 reset 都不充分。正确结构是独立安全边界 reset；失败时关闭连接，不能带着半重置状态继续。

## 稳定症状与机械触发条件

典型症状是 TLS 握手完全成功，但握手后的首个应用命令观察到明文阶段状态：

```text
MAIL + RCPT -> STARTTLS -> DATA returns 354 instead of 503
AUTH -> STARTTLS -> AUTH returns already authenticated
AUTH -> STARTTLS -> external RCPT remains relay-authorized
EHLO old.example -> STARTTLS -> Received still names old.example/ESMTP
```

源码同时满足以下条件即可机械判为高风险：

1. 存在 STARTTLS 或同类传输升级命令；
2. 用 `dup2`、替换流或更新 socket 成员在原 session 内切换端点；
3. session 保存事务、协议身份、认证或授权状态；
4. 握手成功后只清字节缓冲或设置 TLS 标志，没有独立安全状态重置；
5. 下一条协议命令仍由原对象、原插件链处理。

静态初筛：

```bash
rg -n 'STARTTLS|SSLREADFD|SSLWRITEFD|dup2|tls_state|authenticated|relay|helo|reset' src .
```

## 根因

mailfront 2.12 的 UCSPI STARTTLS 路径不是 `exec` 一个全新服务器，而是在当前进程内执行：

```text
STARTTLS
  -> 回复 220
  -> 通知外部 UCSPI TLS 提供者
  -> dup2(SSLREADFD, 0), dup2(SSLWRITEFD, 1)
  -> 重新初始化输入缓冲
  -> tls_state = 1
  -> 原 session / protocol / plugin 链继续处理命令
```

字节流边界已经更新，但语义状态仍属于握手前会话。`saw_mail/saw_rcpt` 会让 TLS 后的 `DATA` 延续旧事务，`authenticated` 和 `relayclient` 会让 TLS 后继承旧身份与授权，`helo_domain` 与 `protocol.name` 会把旧端点声明带进 Received 记录。

普通 `handle_reset()` 不是答案：它为 `RSET`、新 `MAIL` 和邮件完成等普通事务服务，只清后端和插件事务数据。将认证清理塞入该入口会让用户发送第二封邮件时意外注销。

## 三臂真机实证

三臂使用同一官方源码、clang、依赖、证书、CVM 模块、UCSPI TLS 桥和目标端探针，只改变握手后的 reset。目标为 HarmonyOS PC aarch64。

| 臂 | 实现 | 事务 | 认证与 relay | EHLO/协议身份 | 结果 |
|---|---|---|---|---|---|
| A | 上游原样，只设置 `tls_state` | 残留 | 残留 | 残留 | 74 项缺陷行为断言通过 |
| B | STARTTLS 后只调用普通 `handle_reset()` | 残留 | 残留 | 残留 | 后端/插件 reset 不能清理协议局部事务与安全状态 |
| C | 独立安全边界 reset + 协议 hook | 清除 | 清除 | 清除 | 6 场景、76 项正确行为断言通过 |

三臂均完成真实 TLS 握手，并断言握手前后 PID 相同。Arm A/B 使用正确行为预言机重跑时均非零退出，首个失败为 TLS 后 `DATA` 错误进入旧事务。

完整共同条件、命令、反例补丁、哈希和测试边界位于：

- `archives/m/mailfront/2.12/reports/path-b-evidence.md`
- `archives/m/mailfront/2.12/reports/repro/transaction-only-reset.patch`
- `archives/m/mailfront/2.12/test_package/starttls_matrix.py`

## 正确修复

安全边界入口必须与普通事务 reset 分离，并按确定顺序执行：

```c
static const response *security_boundary_reset(void)
{
    response = transaction_reset_backend_and_plugins();
    if (!ok(response))
        return response;

    protocol_security_reset();      /* saw_mail, saw_rcpt, protocol identity */
    delete_session("helo_domain");
    delete_session("authenticated");
    delete_session("auth_user");
    delete_session("auth_uid");
    delete_session("auth_gid");
    delete_session("auth_realname");
    delete_session("auth_domain");
    delete_session("auth_mailbox");
    return OK;
}
```

调用位置必须满足时间关系：

```text
TLS descriptor/stream replacement succeeds
  -> security_boundary_reset succeeds
  -> publish new tls_state
  -> accept the next application command
```

任一步失败均 fail closed。若框架无法枚举所有状态，更安全的回退是销毁旧 session 并围绕 TLS 端点创建全新 session，同时确保旧回调和插件缓存不能再被引用。

## 为什么直觉修复错误

### 只清输入缓冲

这只能处理明文流水线注入，不能触及已经保存于 session、协议对象和插件中的事务与授权状态。TLS 后的命令仍会在旧语义上下文中执行。

### 只调用普通事务 reset

这只执行后端和插件事务 reset，不清理 `protocol-smtp.c` 保存的
`saw_mail/saw_rcpt`，也不清理认证、relay、EHLO 和 ESMTP 身份。因此它是类型层级就不完整的伪修复，而不是“邮件事务已修好”。

### 扩大所有普通 reset 的语义

若每次 `RSET`、新 `MAIL` 或邮件完成都清身份，合法的已认证客户端无法连续发送多封邮件。安全边界 reset 必须是独立入口，只在传输安全上下文改变时调用。

## 可执行验证

最终包由正式消费者测试运行安装后的主程序和模块：

```bash
python3 archives/m/mailfront/2.12/test_package/starttls_matrix.py \
  --mailfront "$PACKAGE/bin/mailfront" \
  --modules "$PACKAGE/lib/mailfront" \
  --auth-module "$SIGNED_CVM_MODULE" \
  --openssl "$OPENSSL" \
  --expect fixed
```

通过条件不仅是 TLS 握手成功，还必须同时满足：TLS 后无新事务时拒绝 `DATA`、可以重新认证、旧 relay 权限失效、旧 EHLO/ESMTP 身份不进入后端产物、普通事务仍保留认证，以及流水线明文被拒绝后 TLS 会话可继续。撤销核心 reset 时同一命令必须失败。

## 协议依据与适用边界

[RFC 3207 第 4 节](https://www.rfc-editor.org/rfc/rfc3207.html#section-4)要求客户端与服务器在 TLS 握手后丢弃握手前获得的知识，并把连接视为新建。本知识把该协议要求落实为可审查的状态机规则，而不是把“TLS 握手成功”当作完成条件。

适用于 SMTP、IMAP、POP3、FTP 和自定义长连接协议中的原地安全升级。以下实现不适用：

- 升级时销毁旧进程/旧 session，并以全新对象承载 TLS；
- 根本没有跨命令事务、身份或授权状态；
- 协议规范明确允许某项状态跨越安全边界，且该状态不影响身份或授权。

本知识不额外要求服务端强制 TLS 后先 EHLO；测试主动发送新 EHLO，只验证旧 EHLO 不得继续生效。

## 查重与新增差异

| 既有条目 | 重合点 | 本条新增机制 |
|---|---|---|
| `E429`（uMurmur：TLS ready 后发送队列未调度） | 都涉及非阻塞 TLS 状态转换 | E429 的症状是握手成功但首帧滞留，根因是发送调度；本条症状是握手后旧事务或授权仍有效，根因是安全语义状态没有撤销 |
| 一般 TLS/证书/签名知识 | 都需要目标端 TLS 或安全验证 | 本条不处理证书、算法或 ELF 签名，而处理同一进程传输升级前后的 session 状态契约 |
| 一般 SMTP `RSET` | 都会清邮件事务 | `RSET` 有意保留认证；STARTTLS 边界必须撤销身份和授权，不能复用相同语义 |

检索覆盖正式知识图谱、`knowledge/drafts/` 和归档报告；未发现同时描述“原地 STARTTLS + 普通事务 reset 伪修复 + 事务/身份/授权/EHLO 联合撤销 + 同 PID 三臂”的既有条目。
