# mailfront 2.12 路径 B 三臂证据

## 结论

mailfront 的 UCSPI STARTTLS 插件在当前进程内把标准输入输出替换为 TLS 端点。上游在切换成功后只清空输入缓冲并设置 `tls_state`，没有撤销 SMTP 事务游标、EHLO 身份、认证副本和由认证派生的 relay 授权。因此 TLS 握手成功后，客户端仍可继承明文阶段的 `MAIL/RCPT`、已认证或可中继状态。

正确修复不是扩展普通 `handle_reset()`：该入口也用于正常 `RSET`、新 `MAIL` 和邮件完成路径，若让它清除认证会破坏同一认证会话连续投递邮件。STARTTLS 需要独立的安全边界 reset，并且必须在描述符切换成功与读取下一条命令之间完成；任一步失败均关闭当前会话。

## 环境与共同条件

- 目标：HarmonyOS PC aarch64，HongMeng Kernel 1.12.0。
- 源码：官方 `mailfront-2.12.tar.gz`，SHA256 `a3e3eb2e180a3dfab95f98c3ec65e4add9fb8c14a66987eebdcf02c5f80dca6d`。
- 三臂使用相同 clang、Conan 依赖、OpenSSL 证书、UCSPI TLS 桥、CVM 模块和正式 `starttls_matrix.py`。
- TLS 桥只实现外部 UCSPI 描述符契约；SMTP 状态、认证、授权、模块派发和队列写入均由安装后的真实 mailfront 与动态模块完成。
- 探针记录升级前后的 PID 并断言相同，排除“TLS 后重启进程自然清空状态”的替代解释。

## 三臂定义

| 臂 | 唯一语义差异 | 事务状态 | 认证/授权 | EHLO/协议身份 | 结果 |
|---|---|---|---|---|---|
| A | 上游原样：只替换 FD、清输入缓冲并设置 `tls_state` | 残留 | 残留 | 残留 | 稳定复现缺陷 |
| B | 伪修复：TLS 后只调用普通 `handle_reset()` | 残留 | 残留 | 残留 | 后端/插件 reset 已执行，但协议局部事务与安全状态仍跨边界 |
| C | 独立 `handle_security_reset()`，并调用协议安全 reset | 清除 | 清除 | 清除 | 正确修复 |

Arm B 的完整精确差异位于 `reports/repro/transaction-only-reset.patch`。它只增加普通事务 reset，不包含任何待测正确实现。
该 reset 仅清理后端和插件事务数据，不负责 `protocol-smtp.c` 的
`saw_mail/saw_rcpt`；因此 Arm B 对 TLS 后 `DATA` 仍返回 `354`，不得把它表述为
“邮件事务已清除”。

## 公共生产路径测试

正式探针运行以下 6 个互相独立的场景：

1. `MAIL + RCPT → STARTTLS → DATA`：正确臂必须以 `503` 拒绝没有新事务的 `DATA`。
2. `AUTH → STARTTLS → 新 EHLO → AUTH`：正确臂必须允许重新认证；脆弱臂返回 already authenticated。
3. `AUTH → STARTTLS → 新 EHLO → MAIL + 外部 RCPT`：正确臂必须撤销 relay 权限并以 `550` 拒绝外部收件人。
4. `EHLO pre-tls.example → STARTTLS → queuedir`：正确臂写入的 Received 行不得含旧域名或旧 ESMTP 身份。
5. 普通邮件完成后投递第二封：认证和 relay 权限必须继续有效，证明没有错误扩展普通事务 reset。
6. `STARTTLS` 后跟明文流水线命令：升级后拒绝残留明文，随后新 TLS 命令仍可工作。

三臂均使用探针的 `--starttls-only` 模式，只执行六个共同的 STARTTLS 场景：Arm C 的 76 项外部可观察断言全部通过，Arm A/B 的 74 项缺陷复现断言全部通过。随后对 Arm A/B 强制使用正确行为预言机，二者均在第一个事务场景稳定失败：STARTTLS 后 `DATA` 返回 `354` 而不是 `503`。正式 `conan create` 不使用该开关，另加一个与三臂主张无关的 queuedir 碰撞场景，因此最终消费者总数为 7 场景、87 项断言。

目标端摘要：

```text
STARTTLS matrix: 6 scenarios, 74 assertions PASS (original)
STARTTLS matrix: 6 scenarios, 74 assertions PASS (transaction-only)
STARTTLS matrix: 6 scenarios, 76 assertions PASS (fixed)
original with fixed oracle: AssertionError: DATA
transaction-only with fixed oracle: AssertionError: DATA
```

## 可执行复现

三臂均从同一份已应用构建兼容补丁的源码构建。Arm A 不应用 `0003`、`0004`、`0006`、`0007`；Arm B 在 Arm A 上只应用仓库内反例补丁；Arm C 应用正式九个补丁。三臂完成签名后均使用同一命令，只改变 `--expect`：

```bash
python3 test_package/starttls_matrix.py \
  --mailfront "$ARM/bin/mailfront" \
  --modules "$ARM/lib/mailfront" \
  --auth-module "$SIGNED_CVM_MODULE" \
  --openssl "$OPENSSL" \
  --starttls-only \
  --expect original

python3 test_package/starttls_matrix.py \
  --mailfront "$ARM/bin/mailfront" \
  --modules "$ARM/lib/mailfront" \
  --auth-module "$SIGNED_CVM_MODULE" \
  --openssl "$OPENSSL" \
  --starttls-only \
  --expect transaction-only

python3 test_package/starttls_matrix.py \
  --mailfront "$ARM/bin/mailfront" \
  --modules "$ARM/lib/mailfront" \
  --auth-module "$SIGNED_CVM_MODULE" \
  --openssl "$OPENSSL" \
  --starttls-only \
  --expect fixed
```

撤销检验使用 Arm A/B 重跑第三条 `--expect fixed` 命令，必须非零退出。该探针没有内建 mailfront 的状态逻辑，只通过正式 SMTP 响应、真实 queuedir 文件和进程身份观察生产实现。

## 证据绑定

```text
正式三臂探针                 8fa6121091b8ad16f7a4e62e715120f827ccbc32fd7a4fedf8cc83ec525222cb
Arm B 精确反例补丁           68c39b0e44101f45ac82d23baee62af03b4a9eba075d317aa2bbdc4cdf3dde18
Arm A 主程序                 c6429952c13ad9665ca9fc8d03259cb3c3318f96e73b9ae35f3a57b55269cd13
Arm A STARTTLS 插件          639a949fe98d7a07aef8674b592a16dd847389a2207c01cfcdcd33a36f9dee6a
Arm A 输出                   b459517a5b3c0a1d435490c3467fd1849abe491e2ad8fab63326a130ec4a5ba9
Arm B 主程序                 c6429952c13ad9665ca9fc8d03259cb3c3318f96e73b9ae35f3a57b55269cd13
Arm B STARTTLS 插件          1d6b6106482790c28579ef3ab710190bf615d2244618d066481dc26fb4eed2da
Arm B 输出                   f439115d9aa1937d87af21ae7edb1519cf21441226f6f2cc6c7c48f3daf51358
Arm C 主程序                 3538628c8fc3a4e8738d7993c6caec58eb120b8b454ff7554d878e5742da3fcc
Arm C STARTTLS 插件          cdecf72f2152cea2f3d9c6592db89376db878fc8921805b8aa9a4c2dc015eeee
撤销检验失败输出             5d44a112e5efd64e0773943c4b419972067cb373abcc2499f53f84a0b6ab3f14
最终 W3 原始输出             9a57b0b9e32fe2e36b43ebd7e23b5b1a51dc12ddced03fbd29f94a46272f2861
```

实验 ELF 和包含个人临时路径的原始日志不提交；正式探针、反例补丁、共同条件、观察预言机和哈希随 PR 提交，审核者可从官方源码重建。

## 协议依据、查重与边界

RFC 3207 第 4 节要求客户端与服务器在 TLS 握手后丢弃握手前获得的知识，并把连接视为新建。这里的新增机制不是普通 TLS 握手或输入缓冲清理，而是“原地传输升级 + 跨命令 session 状态”之间的安全边界契约。

- `E429`（uMurmur）处理 TLS ready 转换后应用发送队列没有调度，症状是首帧滞留；本条处理握手成功后旧事务、身份和授权仍有效，症状是越权或协议状态继承。
- 普通 `RSET`/事务 reset 只清邮件事务，不能代替安全边界 reset；反之也不能把清身份的安全语义施加于每次普通事务 reset。
- 若实现通过销毁并重新启动整个会话进程完成升级，旧进程状态天然消失，本机制不适用。
- 本知识不额外要求服务端强制“TLS 后必须先 EHLO”；测试主动发送新 EHLO，只验证旧 EHLO 不得继续生效。
- UCSPI 桥采用“发送不完整即终止”的 fail-closed 策略，不经过待测 session reset，不属于本知识触发条件。
