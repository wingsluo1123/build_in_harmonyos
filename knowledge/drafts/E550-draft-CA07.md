# E550 — HarmonyOS NUA 快速 100 Trying 使 CANCEL 测试错过 calling 状态

## 错误特征
在 Sofia-SIP 1.13.18 HarmonyOS AArch64 完整 Conan 检查中，`test_nua` 的 NUA-5.1.1 与 `check_sofia` 的 `with_proxy` 均收到 INVITE 408，而预期是 CANCEL 200 和 INVITE 487。同一 `check_sofia` 运行的 `without_proxy` 项通过。

## 触发条件
- 构建系统: Autotools + Conan
- 阶段: HarmonyOS AArch64 原生 NUA 集成测试
- 环境: 仅测试代理设置 `SOFIA_OHOS_TEST_PROXY_NO_WS`

## 根因分析
NTA 将下游 100 Trying 作为逐跳响应消费，并且不会把它交给测试代理的 `proxy_response()` 回调。测试代理仅等待该回调时，NUA 不能及时获知 INVITE 进入临时响应状态，排队的 CANCEL 直到事务超时才发出。应在代理成功启动 INVITE 转发后，通过原始入站 server transaction 立即生成本地 100 Trying；NUA 回调又可能先观察到 `proceeding`，所以取消逻辑还必须在 `calling` 或 `proceeding` 中最多执行一次。

## 解决方案

### 推荐方案
仅在 HarmonyOS 测试代理环境中，代理成功启动 INVITE 转发后，对原始入站 server transaction 调用 `nta_incoming_treply(irq, SIP_100_TRYING, TAG_END())`。让 CANCEL 回调在 `calling` 或 `proceeding` 状态取消，并使用一次性标志避免重复发送。两项修改都只影响测试代理与测试回调。

### 禁止做法
- ❌ 不要在下游 Via 已被移除后继续把该响应交给 `nta_incoming_mreply()`。
- ❌ 不要把 NUA-5.1.1 限定为只在 `calling` 状态发 CANCEL；线程调度可能先观察到 `proceeding`。
- ❌ 不要为了修复测试代理现象而改变生产库的 SIP 路由或放宽响应事务校验。

## 验证
```bash
HarmonyOS AArch64 Conan 全量 `make check`：核对 NUA-5.1.1 的 CANCEL 200 与 INVITE 487，并确认 `check_sofia` 的 8 个 Check 测试项全部通过；之后 Conan test-package 两个实际场景均通过。
```

## 关联条目
- 相关: HarmonyOS 原生 SIP/NUA 事务测试
