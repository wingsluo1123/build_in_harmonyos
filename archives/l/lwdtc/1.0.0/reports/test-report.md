# lwdtc 1.0.0 测试报告（test-report）

- 库: lwdtc
- 版本: 1.0.0
- 上游: https://github.com/MaJerle/lwdtc（tag v1.0.0，commit c6bafbf89b3a05286eba78c96e6e2814b23e71b2，tarball sha256 b463ef6e…）
- 轮次: R03（赛事评审整改轮，task_id lwdtc-1.0.0-r03-invalid-log-removal-and-metadata-repair-pc2-9-20260929T041500Z）
- 报告日期: 2026-09-29
- 报告形态: R03 起按 R19 交付文件规范，以本 test-report.md 承载必要文本证据；R02 的 31 份 `.log` 证据日志已从 PR 删除并在设备侧保留引用（见附录 A/B）

## 一、测试矩阵（测试项与来源）

| 测试项 | 来源 | 入口 | 类型 |
|---|---|---|---|
| 上游 cron 表驱动向量 harness（17 条 CRON_ENTRY × 100 轮） | 上游 dev/main.c | dev/main.c main() | 上游测试 |
| failcap 篡改期望值负向实证 | 上游 dev/main.c（期望值篡改变体） | harness 变体可执行 | 上游测试（负向对照） |
| 上游示例 cron_basic | 上游 examples/ | cron_basic 可执行 | 上游示例 |
| 上游示例 cron_multi | 上游 examples/ | cron_multi 可执行 | 上游示例 |
| 上游示例 cron_dt_range | 上游 examples/ | cron_dt_range 可执行 | 上游示例 |
| 上游示例 cron_calc_range | 上游 examples/ | cron_calc_range 可执行（上游占位实现） | 上游示例 |
| 鸿蒙特有测试（OHOS 编译 + cron parse/valid/next 冒烟） | 适配侧新增（R01） | OHOS clang 编译 test_package 源码 | 鸿蒙特有 |
| test_package 消费性测试（R34） | 适配侧 conan 配方 test_package/ | test_package 可执行 | Conan L1 消费性 |

## 二、逐入口可运行性台账

### 2.1 可运行且已运行

| 入口 | 命令摘要 | cwd | 退出码 | 首条输出 | 设备侧日志（占位）+ SHA-256 |
|---|---|---|---|---|---|
| 上游向量 harness（17 向量 × 100 轮，TZ=UTC-2） | 运行 harness 可执行 | 上游源码根目录 | 0 | Total tick: 337（Test failed 0 次） | `<设备侧绝对路径>/r02_upstream_harness_run_utcminus2.log` — 83113a467c579607a8badf184130c88356ed413a2faf3661000925ed1e108a53 |
| harness failcap 负向变体 | 运行 failcap 变体 | 上游源码根目录 | 255 | Test failed: cron: \* \* \* \* \* \* \*, exp: 2023-08-28_23:09:59, got: 2023-08-28_23:09:51 | `<设备侧绝对路径>/r02_upstream_harness_failcap_run.log` — d1d1ceb205f2fd30e6ba439f7455fe48518d2ed6123d62940d8c31c7e9f9f1d3 |
| 示例 cron_basic | 受控运行（≥60s 后 SIGINT） | 示例源码根目录 | 130（SIGINT 受控终止） | Executing×27 | `<设备侧绝对路径>/r02_example_cron_basic_run.log` — 0ed94d9b29d01a706ec38ff44b2e7980f5eb8373b1bf9bff13446b4fe411e900 |
| 示例 cron_multi | 受控运行（≥60s 后 SIGINT） | 示例源码根目录 | 130（SIGINT 受控终止） | CRONs parsed | `<设备侧绝对路径>/r02_example_cron_multi_run.log` — f5121c874ac773a0b57ac16fc45993610aa90b702d4eda1d7b05710b929a32c2 |
| 示例 cron_dt_range | 受控运行（≥60s 后 SIGINT） | 示例源码根目录 | 130（SIGINT 受控终止） | NOT within×53 | `<设备侧绝对路径>/r02_example_cron_dt_range_run.log` — 31f1a498d0195e2d3974743e41344e6a66a5d80455467f141d5efa888e2ee60e |
| 示例 cron_calc_range | 直接运行（上游占位实现） | 示例源码根目录 | 1 | 占位输出（如实记录，不计通过） | `<设备侧绝对路径>/r02_example_cron_calc_range_run.log` — 694843ecf983a637a86e7efcd880c30fdcb70ccf95e60edb803e81cf5fe04bc2 |
| 鸿蒙特有测试 | OHOS clang 编译 + 运行冒烟 | 适配 worktree | 0 | lwdtc test_package: PASS (parse + valid + next) | `<设备侧绝对路径>/r02_harmonyos_specific_test_reverify_run.log` — 0edf99c37ff0b6125a72450b7cabf7706850317f7f3185926f015b74da4764c3 |
| test_package（R03 修复后重跑） | conan create 内嵌 test_package 运行 | conan 构建目录 | 0 | lwdtc test_package: PASS (parse + valid + next) | 见附录 C（R03 证据日志登记） |

### 2.2 可运行但本轮（R03）未运行

- 无。R03 为评审整改轮：删除无效 `.log` 交付文件并保留引用，未新增/重跑上游入口；R02 已真实执行的上游入口与鸿蒙特有测试结论保持成立（见 §三 口径与少报核验）。

### 2.3 不可运行

- 无。上游 4 个示例中 3 个为无限循环（受控 ≥60s + SIGINT，exit 130 属受控终止而非断言失败），1 个（cron_calc_range）为上游占位实现（真实 rc=1，如实记录、不计通过）；均已在 R02 实际运行并留有设备侧日志引用。

## 三、通过/失败/跳过统计及其口径

| 统计项 | 结果 | 口径 |
|---|---|---|
| 上游向量 harness | 17/17 向量 × 100 轮全过（Test failed 0 次，Total tick: 337，自然退出 rc=0） | R02 实测；TZ=UTC-2 为 harness 隐式时区前提，未改期望值、未裁剪向量 |
| failcap 负向对照 | 非恒绿实证：篡改期望值后 rc=255 + Test failed | 负向对照组，证明 harness 非恒绿、非占位 |
| 上游示例 | 3 个无限示例受控 ≥60s + SIGINT（exit 130，非断言失败）；1 个占位示例真实 rc=1 | 如实记录；占位不计通过 |
| 鸿蒙特有测试 | PASS（1 项：OHOS 编译 + parse/valid/next 冒烟） | R01 新增、R02 复跑 PASS、R03 重跑 PASS（硬门禁，最终计数 ≥1、exit_code 0） |
| test_package | 4/4 断言通过（parse、valid(30s)、valid(31s) 不匹配、next 严格晚于 now） | R34 消费性验证；R03 修复 P3（未初始化读）后重跑通过，断言强度未降低、未删除检查点 |
| 少报核验 | 实测上游入口 21 = 17 向量 + 4 示例；适配后实际执行 22 = 上游 21 + 鸿蒙新增 1 | R02 已核验并记录；R03 不改变该结论 |

统计口径：以实际执行结果为准；完整 stdout/stderr 以内嵌摘要 + 设备侧日志绝对路径（占位）+ SHA-256 追溯；R02 的 21/22 份证据日志 sha256 已由分析端逐文件对拍一致，R03 不重做、不回退。

## 四、实际执行的命令与退出码

- R02 已真实执行（命令 + cwd + 退出码见附录 A 逐项表，原始输出见设备侧日志引用，本文件不重复全文）。
- R03 实际执行：本报告 §五 所列整改 + 附录 C 证据日志登记的真实命令（删除 31 个 `.log`、test-report.md 生成、conandata.yml 官方源恢复、test.c P3 修复、conan create/forward gate/JC5-prdiff 复验、鸿蒙特有测试重跑）。

## 五、R03 变更说明

1. R19 整改：删除 `archives/l/lwdtc/1.0.0/reports/` 下 31 个已提交 `.log` 交付文件（R02 证据日志），删除后 `git ls-files` 该目录 `.log` 归零；R02 测试证据以本 test-report.md + 设备侧日志引用保留，未降低测试范围、数量与结论。
2. R39 整改：`conandata.yml` `sources.url` 恢复官方单一 URL `https://github.com/MaJerle/lwdtc/archive/refs/tags/v1.0.0.tar.gz`，删除手写 gh-proxy 镜像前缀；`sha256` 逐字符保持 `b463ef6eb9ee3d1b98e2bad43bc3099f9f9e64d1024042d976ff96b68c2bd4b5` 不变；镜像 fallback 交由 CI 自动注入。
3. P3 整改：`test_package/test.c` 将 `next <= now` 断言移入 `lwdtc_cron_next` 成功分支（else-if），失败路径不再读取未初始化的 `next`；断言强度未降低、无平台宏、未删除任何检查点。
4. PR 交付态修正：head 以实际 `a075229c…` 为准；PR 文件列表按更新后实测全量列出。
5. 未触碰上游源码（dev/main.c、examples/**、lwdtc/src/** 零改动）；未触碰共享框架、其他库、基线文件；未登记 JC5 白名单；issue_action: none。

## 附录 A：R02 实测命令与退出码（引用登记）

命令与退出码取自 R02 各证据日志包装头与运行日志，R02 报告已与分析端对拍一致。

| # | 入口/门禁 | 命令 | cwd | 退出码 | 设备侧日志（占位） | SHA-256 |
|---|-----------|------|-----|--------|---------------------|---------|
| 1 | 上游向量 harness 运行 | TZ=UTC-2 运行 harness 可执行 | 上游源码根 | 0 | `<设备侧绝对路径>/r02_upstream_harness_run_utcminus2.log` | 83113a467c579607a8badf184130c88356ed413a2faf3661000925ed1e108a53 |
| 2 | harness failcap | 运行 failcap 变体 | 上游源码根 | 255 | `<设备侧绝对路径>/r02_upstream_harness_failcap_run.log` | d1d1ceb205f2fd30e6ba439f7455fe48518d2ed6123d62940d8c31c7e9f9f1d3 |
| 3 | 示例 cron_basic | 受控运行 ≥60s + SIGINT | 示例根 | 130 | `<设备侧绝对路径>/r02_example_cron_basic_run.log` | 0ed94d9b29d01a706ec38ff44b2e7980f5eb8373b1bf9bff13446b4fe411e900 |
| 4 | 示例 cron_multi | 受控运行 ≥60s + SIGINT | 示例根 | 130 | `<设备侧绝对路径>/r02_example_cron_multi_run.log` | f5121c874ac773a0b57ac16fc45993610aa90b702d4eda1d7b05710b929a32c2 |
| 5 | 示例 cron_dt_range | 受控运行 ≥60s + SIGINT | 示例根 | 130 | `<设备侧绝对路径>/r02_example_cron_dt_range_run.log` | 31f1a498d0195e2d3974743e41344e6a66a5d80455467f141d5efa888e2ee60e |
| 6 | 示例 cron_calc_range | 直接运行（上游占位） | 示例根 | 1 | `<设备侧绝对路径>/r02_example_cron_calc_range_run.log` | 694843ecf983a637a86e7efcd880c30fdcb70ccf95e60edb803e81cf5fe04bc2 |
| 7 | 鸿蒙特有测试（R02 复跑） | OHOS clang 编译 + 运行 | 适配 worktree | 0 | `<设备侧绝对路径>/r02_harmonyos_specific_test_reverify_run.log` | 0edf99c37ff0b6125a72450b7cabf7706850317f7f3185926f015b74da4764c3 |
| 8 | conan create（G0–G4） | conan-verify lwdtc 1.0.0（含 conan create G2） | 仓库根 | 0 | `<设备侧绝对路径>/r02_evidence_conan_create.log` | 5d063e794c89cd8e245efc948506d751492ce87a63024fe24587f495d37310a7 |

## 附录 B：R02 31 份证据日志 SHA-256 清单（已从 PR 删除，设备侧保留引用）

| 日志 | SHA-256 |
|---|---|
| r02_evidence_atomicity.log | 1b2b53b0c9b5310cb2ebf909eb6a939ef2b9e1fd1eb30010578c9778aaa88cea |
| r02_evidence_baseline_restore.log | 539baf48f961532f9f3e1084145fa28a3a8340cfb0f6e013f1ade8aa57a8011a |
| r02_evidence_conan_create.log | 5d063e794c89cd8e245efc948506d751492ce87a63024fe24587f495d37310a7 |
| r02_evidence_delivered_state.log | 13db1e27ad4a418fe22996e5c1b791b09e49d17a87404a5b83c19d8f20ef9562 |
| r02_evidence_examples_run.log | 15c13603cfcbbff7b378aae33c382c96e97e698fecc2e8552f572208873d0a9b |
| r02_evidence_forward_gate_recheck.log | 317aad674cc535ef1836d99aec4adf528a8c1b09df537843486fb3426e5172f1 |
| r02_evidence_harness_run_raw.log | ce361b71eea119d1273c810b7607fdf32e9448c600397d13940f908c472b575f |
| r02_evidence_jc5_prdiff.log | 1bb950f391099392d2b7308181689899183d6511553993562a8188adb6b69756 |
| r02_evidence_knowledge_lookup.log | 0d721c5907f7253cf38d49e571993a6225a706437c92ab00105f278fcb9f0764 |
| r02_evidence_pr_body_rewrite.log | 43317252a15069bcb9151c7264a22aa95c5d339de1d9e3babee7a544b62ca714 |
| r02_evidence_pr_body_template.log | e055f9c1221c5d666a2919796198f509bc743b2ddfee8552c1ef59fdd82f302d |
| r02_evidence_pr_update_readback.log | d234ce44599e07e9b661f872da08d0d577c4b3903ec77a41f5d5bf9d3a37e727 |
| r02_evidence_preflight.log | e36dea7acb5be2453bee23a34182fe97f2d1f8fbd4e0e257354427d23569c7c4 |
| r02_evidence_test_package_scope.log | c2a7f1e88756009d9358d234d6bc3e4a0b2f257058dfb25e9151aefa659c8a2e |
| r02_evidence_upstream_entry_inventory.log | ee12d6de013927992c23ab7ccfb62724341d8362cd6c373a5dd7f52daad5df93 |
| r02_evidence_windows_host_header.log | 5009e8fe4718a1ffb08af25dc710a1ac73b7b7e74415ea40a6eab7bcd90df032 |
| r02_evidence_worktree_reuse.log | cd1a8160c807147535f4bd4242668835bd078dc38416a6489556f01eb1e8a3ec |
| r02_example_cron_basic_build.log | 50fd20b4c6a7561f57737003b6d00053149a9ed0026ad578757dba15fa73dc8c |
| r02_example_cron_basic_run.log | 0ed94d9b29d01a706ec38ff44b2e7980f5eb8373b1bf9bff13446b4fe411e900 |
| r02_example_cron_calc_range_build.log | ab5b40e7365cc2486bf967b8927078f5680e8f5ffbf8f11ecd7a3cc10afc27cf |
| r02_example_cron_calc_range_run.log | 694843ecf983a637a86e7efcd880c30fdcb70ccf95e60edb803e81cf5fe04bc2 |
| r02_example_cron_dt_range_build.log | 6aa1bcd65664c518b5daa5983c475f0aef772ebb9d564ac9d194bca0be7aaa03 |
| r02_example_cron_dt_range_run.log | 31f1a498d0195e2d3974743e41344e6a66a5d80455467f141d5efa888e2ee60e |
| r02_example_cron_multi_build.log | 51e1cbc08494df309b0df16100ba75a07131f3cc509d34baeae7fa8fb0a1b2d1 |
| r02_example_cron_multi_run.log | f5121c874ac773a0b57ac16fc45993610aa90b702d4eda1d7b05710b929a32c2 |
| r02_harmonyos_specific_test_reverify_build.log | ec1343fc3666328c2a094f858211ae2978126483f202943c66e7fc9394ca9e86 |
| r02_harmonyos_specific_test_reverify_run.log | 0edf99c37ff0b6125a72450b7cabf7706850317f7f3185926f015b74da4764c3 |
| r02_upstream_harness_build.log | 693d68e83d84339727c639ad02647cceccf9acd058b07d6b9d2f914edac9e9aa |
| r02_upstream_harness_failcap_build.log | 6fa17a362ec8cd38c700f0106570c8a6915cc6f3e75f3360a538c254c0bc0ae7 |
| r02_upstream_harness_failcap_run.log | d1d1ceb205f2fd30e6ba439f7455fe48518d2ed6123d62940d8c31c7e9f9f1d3 |
| r02_upstream_harness_run_utcminus2.log | 83113a467c579607a8badf184130c88356ed413a2faf3661000925ed1e108a53 |

## 附录 C：R03 证据日志登记（不入库，设备侧保留）

R03 本轮新产生的证据日志一律不提交入库，仅登记设备侧绝对路径（占位）+ SHA-256；R03 各门禁证据日志随回报 `evidence_log_records` 与 `evidence` 登记。

（占位说明：本交付文件保持可移植，设备侧绝对路径以 `<设备侧绝对路径>` 占位；具体路径与 SHA-256 在回报与 PR 正文中引用。）
