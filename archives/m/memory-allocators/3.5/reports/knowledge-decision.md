# knowledge_decision: reuse_existing（路径 A）— R03

- task_id: memory-allocators-3.5-r03-ci-jobserver-fifo-j1-and-p2p3-closure-pc3-41-20261015T075519Z
- 快照: /storage/Users/currentUser/tianyi/build_in_harmonyos/.knowledge-snapshots/memory-allocators-3.5-r03-ci-jobserver-fifo-j1-and-p2p3-closure-pc3-41-20261015T075519Z
  (remote https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git, ref main,
   HEAD b544378a4ea82b4959135eebb21f5e509eeebf91, sparse: knowledge, 只读审计见 .AUDIT.json)
- 复用说明: R02 快照 HEAD(e272de0a) 与当前 main HEAD(b544378a) 不一致，按规程重建 R03 快照
- 扫描范围: knowledge/graph/E*.kv(547 条) + knowledge/doc/E*.md + knowledge/drafts/*.{md,kv} + 根 DRAFT-* 配对

## 候选 1: Release(NDEBUG) 下 assert 失效（Review P2/P3 闭合）
- 等价命中: E259「Conan Release 的 -DNDEBUG 让 assert 不求值」
  - error_signature/root_cause/rec_approach 逐字段适用（R02 已命中，本轮交付态测试仍沿用
    NDEBUG 免疫 CHECK 宏机制，21 校验点，Release 实测 21 checks/0 failures/rc=0）
- 结论: reuse_existing → 路径 A，不创建草稿

## 候选 2: CI jobserver mkfifo / fork 失败（-j20 首错）
- 快照检索: E491(swftools autotools HMDFS)/E528(libunwind autotools TMPDIR 闭包) 均非等价
  （error_signature 为 subs1.awk/PATH 闭包类，非 GNU make jobserver fifo）；E057/E074/E248/
  E292/E345 均为 autotools/patch 类不适用
- 判定: GNU make jobserver 依赖 mkfifo 而目标文件系统拒绝（Operation not permitted），
  属平台/基础设施限制；按规程基础设施故障永不走路径 B（path_a_no_knowledge 等价），
  本轮仅以配方 -j1 做最小可逆规避（任务明确"配方变更仅限 -j1"），不创建草稿

## 候选 3: r01/r02 沿用的 E092（CMake 不识别 HarmonyOS 平台）
- 本轮配方未引入新平台问题，E092 仍适用，保留继承

## 结论
- knowledge_decision: reuse_existing（E259 等价命中 + E092 继承），路径 A
- 不创建 knowledge/drafts/DRAFT-memory-allocators-3.5-* 草稿
- 无 knowledge_pair_audit 配对需求（路径 A）
