# E551 — Route in-dialog SUBSCRIBE refreshes and unsubscribe requests to the existing NTA dialog

## 错误特征

NUA-11.4.3 发送已建立 SIP 对话内的 re-SUBSCRIBE 后，刷新没有到达原 notifier handle，测试等待通知/最终响应直至超时。取消订阅（Expires: 0）也需要沿同一 dialog leg 分派到 notifier；正确回调处理后，服务端 `nua_i_subscribe` 事件仍报告 100（应用接管请求），客户端 `nua_r_unsubscribe` 才报告最终 SIP 200。

## 根因分析

NTA 的 `leg_find()` 路由条件显式排除了 `sip_method_subscribe`。因此带有原 Call-ID、From tag 和 To tag 的刷新请求没有匹配到现有 NTA dialog，而进入默认 leg 并由 NUA 分派为新 handle。原 notifier usage 没有收到刷新；这个回归测试的服务器回调也只保存 `nua_i_subscribe` 事件，没有为刷新请求发送最终响应。

设备日志确认移除 SUBSCRIBE 排除条件后，NUA-11.4.3 re-SUBSCRIBE 已通过。后续全量运行暴露测试侧取消订阅问题：原回调没有回答在既有 dialog 上送达的 Expires: 0 请求，或把 NUA 的请求通知事件误当成 SIP 最终响应。测试回调需明确回答该请求，等待最终 NOTIFY，并按 NUA 事件语义检查服务端事件状态 100；客户端事件仍校验最终响应 200。

## 解决方案

- 在 NTA 现有 dialog 查找中允许带 tag 的 in-dialog SUBSCRIBE 使用既有 leg。
- 在测试服务器回调中对 refresh 明确发送带 `SIPTAG_EXPIRES_STR("365")` 的 200 OK，并使用 `NUTAG_WITH(nua_current_request(nua))` 保留当前请求上下文。
- 在测试服务器回调中对取消订阅明确发送带 `SIPTAG_EXPIRES_STR("0")` 的 200 OK；区分 `nua_i_subscribe` 的请求通知状态 100 与客户端收到的 SIP 最终响应 200。
- 不在库运行时替应用自动应答 SUBSCRIBE，也不放宽 SIP dialog 校验。

## 验证

最终 HarmonyOS AArch64 W3 运行中，NUA-11.4.3 tagged refresh 与 NUA-11.4.4 unsubscribe 均通过。服务端 `nua_i_subscribe` 事件状态为 100，客户端最终 SIP 响应为 200；`check_sofia` 的 8 个 Check 项全部通过，W3 与 Conan `test_package` 完成。

## 关联实现

- `archives/s/sofia-sip/1.13.18/patches/0026-libsofia-sip-ua-nta-nta.c.patch`
