# DRAFT: ortp 5.x 回调 user_data 改 void*——configure 自动 AC_DEFINE 的 RTP_SIGNAL_PTR_CAST 仍是 unsigned long 老语义，clang -Wint-conversion 拒绝

> 配套条目：`DRAFT-ortp5-voidptr-user-data-api-gap.kv`（本 md 与 kv 成对）
> 状态：pending-editor-review（拟提升编号 E7xx，最终由主编确认）
> 首发实现：libosmo-abis 1.6.0 + ortp 5.2.0，PR #15242 commit `759011e516`（补丁 0004）
> 佐证：同 PR 真机 make check 4/5（trau 组全过），消费者探针 PASS

## 1. 错误特征（可机器匹配）

```
src/trau/osmo_ortp.c:400:8: error: incompatible integer to pointer conversion passing 'unsigned long' to parameter of type 'void *' [-Wint-conversion]
```

- error_signature：`incompatible integer to pointer conversion passing 'unsigned long' to parameter of type 'void \*'.*-Wint-conversion`
- **识别要点**：报错点在 `rtp_session_signal_connect(..., RTP_SIGNAL_PTR_CAST(rs))` 调用行；clang 15 对 -Wint-conversion 默认按错误处理（gcc 仅警告）；源码树里 grep 不到该宏定义——它由 configure 检测 ortp 版本后 **AC_DEFINE 写进 config.h**（真机 config.h 实证：`#define RTP_SIGNAL_PTR_CAST(arg) (unsigned long)(arg)`）。

## 2. 根因

ortp 5.x 把 `rtp_session_signal_connect` 的 user_data 参数从 `unsigned long` 改为 `void *` 并删除了配套转换宏。而 libosmo-abis 1.6.0 的 configure.ac 仍按老 ortp 语义生成 `RTP_SIGNAL_PTR_CAST(arg) (unsigned long)(arg)`——宏"凭空出现"曾误导排查（源码与 ortp 头文件里都 grep 不到），真相在 config.h。上游 libosmo-abis 2.x 才彻底完成 ortp 5 移植。

## 3. 修法

消费侧补丁把四处调用直接传指针（osmocom 上游后续版本的等价做法）：

```diff
 	rtp_session_signal_connect(rs->sess, "ssrc_changed",
 				   (RtpCallback) ortp_sig_cb_ssrc,
-				   RTP_SIGNAL_PTR_CAST(rs));
+				   rs);
```

## 4. 佐证

PR #15242 真机预构建：修前 osmo_ortp.c 四处 -Wint-conversion 红灯；补丁 0004 后 conan create 全链路 exit 0，libosmoabis/libosmotrau 双库产出，make check 4/5，消费探针（subchan_mux_init + TRAU up2down/encode/decode）真机 PASS。

## 5. 适用范围

任何用 ortp ≥5.x 编译 libosmo-abis ≤1.6.x / 其他携带 RTP_SIGNAL_PTR_CAST 老用法的 osmocom 组件（osmo-mgw/osmo-bsc 消费链）。排查口诀：宏在 config.h，不在源码也不在 ortp 头里。
