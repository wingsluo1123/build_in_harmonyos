# mailfront 2.12 测试报告

> 测试日期：2026-10-15
> 目标环境：HarmonyOS PC aarch64，HongMeng Kernel 1.12.0
> 构建环境：clang 15，Conan 2，OHOS 6.0 profile

## 测试摘要

| 类别 | 总数 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|---:|
| 上游 `run_compare_test` 展开实例 | 128 | 128 | 0 | 0 |
| 新增端到端场景 | 7 | 7 | 0 | 0 |
| 新增外部可观察断言 | 87 | 87 | 0 | 0 |
| 队列原子不覆盖语义场景 | 1 | 1 | 0 | 0 |

上游共有 73 个命名测试组、128 个展开实例；最终构建实际运行 `sh tests.sh -v`，输出 `128 tests executed, 0 failures`。新增测试严格不少于上游实测，并另含 HarmonyOS 目标端专项验证。

## 最终结果

- 干净 `conan create`：构建、上游 128/128、消费者 7 场景/87 断言均通过。
- 最终包：10 个程序、19 个动态模块、3 个公共头文件。
- `mailfront`：ELF64 AArch64 OHOS；恰有一个 `.codesign`；动态依赖仅 `libc.so`；没有 `RPATH/RUNPATH`。
- 所有打包程序和动态模块均检查单一 `.codesign`、无 Conan package 路径和无构建目录泄漏。
- 消费者程序能够包含并使用安装后的公共 `mailfront.h`。
- 主程序从可执行文件位置发现同包动态模块，不依赖构建期绝对路径。
- queuedir 后端在 HarmonyOS 应用数据目录通过 `renameat2(RENAME_NOREPLACE)` 完成消息原子发布；生产后端碰撞测试确认返回 `451`、仅删除本写入者临时文件，竞争者已发布内容保持不变。
- 真实 UCSPI TLS 描述符切换成功，STARTTLS 前后 mailfront PID 相同。
- 事务、认证、relay 授权、EHLO 域名和协议身份均不能跨越 TLS 安全边界。
- 普通邮件事务 reset 仍保留认证状态，可连续投递，避免把安全 reset 错用到普通流程。
- STARTTLS 后的明文流水线输入被拒绝，连接在 TLS 下仍能继续处理新命令。
- 上游 RBL 实例仍真实执行；对受外部 DNS 策略影响的 `127.0.0.2` 查询，仅接受完整的标准列入输出或完整的标准未列入输出，不跳过、不伪造结果。
- 另以不可解析测试域强制进入“未列入”分支，两个受影响实例均命中标准未列入结果，聚焦回归为 2/2、0 失败；标准已列入分支由最终 W3 的真实 Spamhaus 查询覆盖。

## HarmonyOS 目标端专项验证

1. 签名后的 AArch64 主程序与 19 个签名动态模块在目标端实际加载并执行。
2. 在同一目标进程内执行真实 UCSPI 文件描述符切换和 TLS 握手，不用重启进程掩盖旧状态。
3. HarmonyOS 应用数据文件系统不允许硬链接时，queuedir 通过 `renameat2(RENAME_NOREPLACE)` 完成不覆盖的原子发布；消费者既验证 libc 原语，也直接运行安装后生产 `queuedir` 后端的碰撞清理路径。
4. 最终包可迁移：模块发现不含构建机绝对路径，ELF 无 `RPATH/RUNPATH` 和 Conan 缓存路径。

## 路径 B 对照

上游臂和“只调用普通事务 reset”的伪修复臂均稳定保留握手前安全状态；三臂使用 `--starttls-only` 执行完全相同的六个场景，独立安全边界 reset 臂通过全部 76 项正确行为断言。正式消费者另执行 queuedir 碰撞场景，故总数为 7 场景、87 项断言。撤销核心修复后同一正确行为探针稳定非零退出。完整定义、命令、哈希和边界见 `reports/path-b-evidence.md`。

## 证据哈希

```text
正式目标端探针        8fa6121091b8ad16f7a4e62e715120f827ccbc32fd7a4fedf8cc83ec525222cb
最终 mailfront ELF    3538628c8fc3a4e8738d7993c6caec58eb120b8b454ff7554d878e5742da3fcc
最终 STARTTLS 模块    cdecf72f2152cea2f3d9c6592db89376db878fc8921805b8aa9a4c2dc015eeee
最终 queuedir 模块    023f6dc5764c7bb1da2a1d5c3955da258df851f6cbf700acadba970ada37ba0f
最终 W3 原始日志      a2d44221f3e9d4764b49dfeedbbca7084e243e05db9822b7091ad86eb113af67
RBL 未列入聚焦日志    d2834a5db5e687bdbc971d9e77af7be1da96ff535c255afd0f14b5d850a08919
```

原始日志保留在仓库外审计目录，不随 PR 提交；报告只保留可复核摘要与 SHA256。
