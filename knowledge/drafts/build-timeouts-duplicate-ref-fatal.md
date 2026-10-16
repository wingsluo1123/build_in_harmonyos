# build_timeouts.txt 重复条目秒死（CI 配置校验 exit 1）

> Stem: `build-timeouts-duplicate-ref-fatal` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-BUILD-TIMEOUTS-DUPLICATE-REF-FATAL
- **严重度**: 2
- **类别**: ci-gate|config|conan
- **触发工具**: conan|ci
- **阶段**: configure（conan create 之前的超时配置校验）

## 错误特征

CI `conan-build-test` 步骤在 **0.3 秒** 内退出（`elapsedTime=0.318275`），构建从未开始：

```
o[step] Validating package build timeout overrides...
e[fail] Invalid build timeout config at line 184: duplicate package reference: syslog-ng/4.8.1
hprogram finished with exit code 1
h elapsedTime=0.318275
```

关键迷惑点：**报错只给行号（line 184），不给重复条目的完整清单**——不去对照文件实况就无法知道有几条、分别在哪。

## 根因分析

`ci/conan/build_and_test.sh` 在 conan create 之前对 `ci/config/build_timeouts.txt` 做严格校验：同一包名（如 `syslog-ng/4.8.1`）出现 2+ 次即 exit 1。

**为什么 diff 看不出来？** mysql-8.4 #11358 实证（CI #92185，九轮同签名）：

- 分支基线早于 main 合入 `syslog-ng/4.8.1 10800`（main@176）
- 分支自身历史里又带了 2 条 `syslog-ng/4.8.1`（行 163/171，来自更早的分支内提交）
- 远端 PR diff 显示的是 `+2/-0` **纯新增**——但 CI checkout 的是"main + diff"**合并视角**，实际文件里同名条目出现 **3 条** → 校验器秒死

**误判风险**：该签名曾被误判为"3600s 超时耦合"（因为报错行含 timeout 字样）。判别法：看 elapsedTime——**0.3 秒级 = 配置校验秒死**；真正的构建超时是 `TIMED OUT after 3600s`（elapsedTime 3600+）。

## 修复方案

以 `origin/main` 最新版**整文件重置**后仅追加目标条目（mysql-8.4 修复 commit `3581361ac0` 实证，修复后 CI #92239 全绿）：

```bash
git fetch origin main
git show origin/main:ci/config/build_timeouts.txt > ci/config/build_timeouts.txt
printf '\n# mysql-8.4: 8.4.11 服务器主件（478MB 源码全量编译+测试远超 3600s 基线）\nmysql-8.4/8.4.11 14400\n' >> ci/config/build_timeouts.txt
# 自检（输出应为空）
grep -E '^[a-zA-Z]' ci/config/build_timeouts.txt | awk '{print $1}' | sort | uniq -d
```

**不要**手动删旧基线里的行——逐行删容易漏（文件 180+ 行），重置法保证与 main 逐字节一致。

## 降级方案（fallback）

超时条目可由独立基建 PR 承载（mysql-8.4 即此形态：#12517 基建件 + #11358 配方件）。但两条纪律：

1. 基建件**未合入前**，配方 PR 必须自带条目——否则撞 3600s 默认超时（478MB 源码大件必 TIMED OUT）
2. 两件先后合入时，**后合的一件必须 rebase 去重**——否则触发本秒死机制

## 验证证据

| 项 | 证据 |
|---|---|
| 失败签名 | CI #92185 等 9 轮（2026-10-15 00:55–02:10 连续九轮同签名） |
| 修复 commit | #11358 `3581361ac0`（build_timeouts 重置 main 基线+追加 mysql-8.4 条目） |
| 修复后 | CI #92239 全绿（conan-build-test ✅，Extended build timeout for mysql-8.4/8.4.11: 14400s 生效） |
| 档位先例 | 14400 = mysql-8.4/pytorch/gcc-14；10800 = syslog-ng/alacritty/wstunnel；7200 = casacore |

## 适用范围

所有在 `ci/config/build_timeouts.txt` 加条目的 PR；高危场景：分支基线早于 main 合入同名条目、基建件+配方件并行携带同条目。
