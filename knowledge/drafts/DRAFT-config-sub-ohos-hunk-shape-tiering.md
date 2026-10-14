# DRAFT-config-sub-ohos-hunk-shape-tiering — config.sub ohos 补丁按脚本年代分层

> title: config.sub 年代决定 ohos 补丁形状与失败模式：2013 系响亮失败、同代目标行（118/126-129/1368）字节同一，三 hunk 添加模板可跨库逐字节复用；2018 系 rc=0 静默改写、必须替换对+os 归一化大表 hunk；先 head -3 查年代选型，终判以 config.sub 输出断言为准

## 摘要

bundled config.sub 的"年代"（版权年，`head -3` 可见）同时决定失败模式和补丁
形状。选错模板要么打不上（响亮返工），要么更危险——静默改写三元组且 rc=0
（全绿假阳性传播错误平台身份）。

## 两种失败模式

| 代际 | 代表版本 | 失败模式 | 补丁形状 |
|------|---------|---------|---------|
| 2013 系（autoconf 2.69 / automake 1.11 世代） | 2013-04-24 | 响亮失败：`Invalid configuration 'aarch64-unknown-linux-ohos'` / `unknown operating system` | 三 hunk 添加型：maybe_os 列表行、linux-ohos 子分支、os 归一化大表 |
| 2018 系 | 2018-05-05 | **静默失败**：os 归一化大表缺 `-linux-ohos*` 时被兜底 sed 改写为 `<machine>-unknown-linux-gnu-ohos`，rc=0（行级机理与 hunk 必要性分级见 DRAFT-autotools-config-sub-ohos-table-hunk-tiering） | 替换对形状（must 含大表 hunk） |

## 三例证据（同一 2013 模板跨库复用，metrics_success_count=3）

2013-04-24 版 config.sub 的三个目标行（118 / 126-129 / 1368）在下列包中逐字
一致，同一份三 hunk 添加型补丁近乎原样适用（dry-run 零偏移命中）：

- globus-callout 4.3（先例）
- globus-gsi-openssl-error 4.4
- globus-openssl-module 5.2

反例：globus-gsi-proxy-ssl 6.6 的 config.sub 为 2018-05-05，必须用替换对模板
（详见 DRAFT-autotools-config-sub-ohos-table-hunk-tiering）。

## 两条禁则

- forbid_1：只看 rc=0 认定三元组被接受——2018 系静默改写 rc=0，必须输出断言。
- forbid_2：跨代际复制模板（2013→2018）且以单一路径 dry-run 下结论——上下文
  全漂移必败；即使应用成功，缺大表 hunk 仍被静默改写。后果：响亮返工，或
  全绿假阳性传播错误身份。

## 验证收口（自包含序列，以 5.2 为例；终判是 config.sub 输出断言）

pristine 基线（预期 Invalid configuration、rc≠0）→ `head -3` 断言 2013 年代 →
dry-run + 应用三 hunk 模板 → 4 段输入原样输出、3 段输入归一为 4 段双断言。
完整命令序列见 .kv 的 verification_cmd。

## 与既有条目的关系

similar_to：E007、E072、E122、E268、DRAFT-autotools-config-sub-silent-ohos-triplet、
DRAFT-autotools-config-sub-ohos-table-hunk-tiering、
DRAFT-toybox-patch-pure-insert-hunk-unappliable、
DRAFT-mpsolve-3.2.3-config-sub-ohos-kernel-hunk-and-no-build-host-bypass、
E572-draft-BD92。

- E072：config.sub 需要改的"点位清单"（本条目补充：按年代分层的"形状"选型）
- DRAFT-autotools-config-sub-ohos-table-hunk-tiering：2018 系静默改写的行级机理与 hunk 必要性分级（机理主覆盖）
- DRAFT-toybox-patch-pure-insert-hunk-unappliable：toybox 纯插入 hunk 陷阱细节
- principles：P-PATCH-001

## 已知限制

证据来自 GCT 四库（三例 2013 系 + 一例 2018 系）；其他项目代际边界
（2014-2017 之间）未实测，套用前先 `head -3 config.sub` 确认年代并 dry-run 收口。
