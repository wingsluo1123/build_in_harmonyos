# DRAFT-12683-ohos-upstream-selftest-environment-false-failures

> 草稿（DRAFT）—— 来源：jtreg 8.3+1 适配 HarmonyOS PC（PR #14710 / 任务 12683）真机验证
> 与 `.kv` 同 stem 配套；字段见 `knowledge/drafts/DRAFT-12683-ohos-upstream-selftest-environment-false-failures.kv`

## 症状

上游自带的 make 自测套件在 HarmonyOS PC 真机上出现“失败目标”，但其失败形态与
被适配库的功能无关——是环境语义差异被上游断言捕获的方式：

| # | 现象 | 真机事实 | 上游期望（Linux） |
|---|------|----------|-------------------|
| 1 | `SkippedExceptionTest.{agentvm,othervm}` 失败 | summary 断言用 GNU BRE `\+`：toybox grep 不识别，rc=1 | GNU grep 将 `\+` 视为量词，匹配成功 |
| 2 | `CleanupTests.agentvm.retain` 目录计数失败 | chmod 只读不生效，“不可删除文件”实际可删 → 复用 scratch，计数 1 != 5（5 个用例本身全 PASS） | 只读目录令文件不可删除 → jtreg 换 scratch 目录，计数 5 |
| 3 | `ProblemList` 多跑 1 例 | JVM `os.version` 含空格 → `OSNAME-REV` 排除条目失配（passed:2; excluded:4） | passed:1 |

jtreg 8.3+1 真机 `make test`（HEADLESS=1）总账：**选中 271 个目标：266 通过 / 4 失败 / 1 挂起**
（挂起项为 `ExplicitIds.othervm`，限时终止并如实记录）。`quick-test`（上游 CI 初始集）**9/9**。

## 根因与最小复现

### 1. toybox grep 不实现 GNU BRE 扩展（`\+`）

```bash
command -v grep            # /usr/bin/grep -> toybox
printf 'a b\n' | grep 'a \+b'; echo "rc=$?"     # rc=1  ← \+ 被按字面处理
printf 'a b\n' | grep -E 'a +b'; echo "rc=$?"   # 匹配  ← ERE 正常
```

上游脚本 `... | grep '^TestKnownSkippedException.java \+Passed...'` 因此**假失败**：
被匹配的 summary 内容完全符合期望（`TestKnownSkippedException.java  Passed. Skipped: ...`），
仅因量词语法不被实现。

### 2. chmod 只读语义不生效（HMDFS/SELinux）

上游 CleanupTests 预置“不可删除文件”：`file.setReadOnly(); dir.setReadOnly();`。
真机上 chmod 受限（SKILL §7 / E046），文件可被删除 → jtreg 正常清理并复用 scratch 目录，
目录计数断言（5）失败；**该组 5 个用例本身全部 PASS**（`Test results: passed: 5`）。

### 3. JVM `os.version` 含空格

`os.version = "HongMeng Kernel 1.12.0"` → ProblemList 的 `OSNAME-REV` 条目失配。
机制与完整适配模式见主条 `DRAFT-12683-ohos-jvm-platform-properties-vs-osname-rev-selectors`。

## 三分类与证据链（推荐流程）

1. **环境语义差异**（本条的 3 类）→ 不计库缺陷；每项保留：原始日志行、最小复现命令、
   对照实验（`grep -E` 复测 / 权限对照 / JVM 属性对照）。
2. **真实回归** → 修复后重跑；不得与 1 混淆。
3. **不可判定（挂起）** → 限时（如 >45 分钟无进展）记录并终止，不无限等待、不伪造结论。

统计口径（R51）：`quick-test` 在 `conan create` 的 build() 内复跑（CI 可复现、标准 Linux 环境）；
真机全量结果按三分类列出 通过/失败/挂起 并写明根因；**不改上游断言凑绿**。

## 与现有知识的边界（查重）

- `E067`（use-grep-F-or-case）：使用者自身误用带元字符的固定串，建议 `-F/case`——**不是**
  工具实现差异；本条是 toybox 未实现 GNU BRE 扩展导致**上游套件**假失败，并给出三分类流程。
- `E010`（toybox sed/expr）、`E043`（toybox ash bashism）、`E098/E188`（toybox install）、
  `DRAFT-gradle-launcher-toybox-xargs-quote-strip`（toybox xargs）：均为其它工具的 toybox
  差异；本条补 **grep** 这一缺口并上升为“上游套件环境假失败”的判定方法。
- `E046`/SKILL §7（chmod 受限）：事实层已存在；本条将其纳入“环境假失败”归因与计数口径。
- `DRAFT-12718`（kamailio，构建期 `uname -s` 分支静默失效）与 JVM 属性条（见主条）各司其职。

## 验证证据（本 PR）

- `reports/test-report.md`：271/266/4/1 总表 + 每项根因；
- `notes.md`（R51 三步法小节）：quick-test 9/9、全量目标的逐项目标级失败清单；
- 设备探针与对照实验命令（见上）。
