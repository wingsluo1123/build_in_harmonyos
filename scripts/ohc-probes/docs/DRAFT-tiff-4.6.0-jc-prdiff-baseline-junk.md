# DRAFT-jc-prdiff-baseline-junk: W3/finish JC 门禁误拦其他库基线 junk → prdiff 模式规避

## 基本信息
- **严重度**: 3
- **类别**: CI, PR-validation, junk_check, prdiff, baseline
- **来源库**: tiff 4.6.0（libtiff）首轮适配
- **来源 PR**: 【知识库扩展】tiff 4.6.0（本 PR）
- **状态**: draft

## 错误特征
```
JC_RESULT=fail
Junk Files: 2
[FAIL] JC1: 5 个运行时状态文件被跟踪:
       archives/c/cloog/0.21.1/.build-closed
       ...
[FAIL] JC5: 5 个 archives 下未登记的隐藏文件:
JC_RESULT=fail / JC_ERRORS=2  →  W3 本地 CI 模拟失败，阻塞 finish
```

## 根因分析
`ci/scripts/junk_check.sh` 的模式选择链：
1. 存在非空 `pr.diff` → **prdiff 模式**（只审 PR 文件清单，真实 CI checkout-pr 同款）；
2. 否则 `git diff origin/main...HEAD` 非空 → **incremental 模式**；
3. 两者皆空 → **full 模式** `git ls-files` 整仓扫描。

新库 R01 分支从 origin/main 重建且尚未提交时，`git diff origin/main...HEAD` 为空
（HEAD==origin/main），此时若无 pr.diff 则回退 full 模式整仓扫描。若仓库中
origin/main 已跟踪了其他库的空状态文件（`.build-closed`/`.staging-verified`，
blob 均为 e69de29… 空文件），会被误判为当前 PR 的 junk 而阻塞 W3。

## 推荐方案
**方法**: generate-package-prdiff

在本地（与 CI checkout-pr 等价的）验证路径下，生成本包 pr.diff 走 prdiff 模式：

```bash
# 1. 确认分支基于 origin/main（合并基可审计）
git rev-parse origin/main
# 2. intent-to-add：让未跟踪的新库文件进入 diff 清单
git add -N archives/<首字母>/<库名>/
# 3. 生成只含本包路径的 pr.diff（真实 CI 同款文件清单来源）
git diff origin/main -- archives/<首字母>/<库名>/ > pr.diff
# 4. junk_check 自动检测到 pr.diff → prdiff 模式只审 PR 文件清单
bash ci/scripts/junk_check.sh $PWD          # → JC_RESULT=pass, Junk Files: 0
# 5. 命中过的其他库基线文件零修改、不提交；记录 blob SHA（git ls-tree origin/main -- <path>）
# 6. 重跑受影响的 finish/W3 门禁
python3 scripts/ohc-run.py finish <软件名> <版本> built
```

## 验证/命令
- tiff 4.6.0 实测：生成 pr.diff 前 `JC_ERRORS=2`（5 个其他库基线文件被 full 模式误拦）；
  `git add -N archives/t/tiff/ && git diff origin/main -- archives/t/tiff/ > pr.diff` 后
  `JC_RESULT=pass, Junk Files: 0`；finish W3 通过（`.ci-result.json` exit_code=0）。
- 基线文件保持 origin/main 原值（blob e69de29…），`git diff origin/main -- <本包路径>` 不含任何基线路径，
  `grep -cE 'cloog|kics|libbfio|/thc/' pr.diff` 得 0。

## 适用边界
- 适用：分支基于 origin/main 重建、PR 仅含本库路径的 R01 新库适配；仓库含"提交前已存在"的其他库基线空状态文件。
- 不适用/反例：若 junk 命中**当前库自己的**文件（如当前库意外提交了 .ci-result.json、tar.gz、.a），
  必须清理修复而不是 prdiff 规避；若本地分支落后 origin/main，先 W1 同步再生成 pr.diff。

## 查重差异（知识库扩展专用轴）
| 轴 | 结果 | 说明 |
|---|---|---|
| exact_duplicate | false | 无既有条目对应此问题面 |
| causal_duplicate | false | 与 E256（git apply 二进制补丁 CI 失败）仅领域重叠，非同因 |
| trigger_overlap | false | E256 触发于补丁应用失败；本条目触发于整仓扫描误判 |
| solution_overlap | false | E256 方案为移除二进制出 commit；本条目方案为 prdiff 清单规避 |
| combination_novelty | true | 与 ./SKILL.md 基线隔离规则组合成完整工作流（规避+隔离+恢复） |
| boundary_novelty | true | 明确"本库文件必须修、他库基线才可规避"的边界 |
| test_migration_novelty | false | 无测试迁移面 |

## 关系
- prerequisite_of: 无
- similar_to: E256（同为 CI/PR 校验类，但因果与方案不同）
- conflicts_with: 无