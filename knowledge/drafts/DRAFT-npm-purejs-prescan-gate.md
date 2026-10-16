# E-草稿详解：纯 Node.js/npm 包 prescan 前置识别（G0 自动拦截）

> 配对文件：`knowledge/drafts/DRAFT-npm-purejs-prescan-gate.kv`
> 状态：DRAFT（路径 B 提名，待评审委员会审核，协作者不得自行 promote）

## 1. 背景与发现过程

适配 **imageoptim-cli 3.1.9**（npm 包，上游 `JamieMason/ImageOptim-CLI`）时，W0/W0b 选型阶段拉取源码即发现：

| 证据项 | 实测值 |
|---|---|
| 构建系统 | npm/yarn（`tsconfig.json` + `yarn.lock`），无 Makefile/CMake/configure |
| manifest | `package.json`：`engines: node>=18`、`bin: dist/imageoptim`、依赖全为 JS 包（chalk/commander/globby 等） |
| 源码统计 | `src/` 全 TypeScript；`osascript/` 为 macOS AppleScript；**C/C++ 源文件 0 个** |
| lang-preflight | exit 2，`detected_language: nodejs`，按 R47 终止适配 |

本次因人工走了 R47 预检而及时止损。但复盘发现**机制缺口**：

## 2. 一类问题（非单库 workaround）

**所有以 npm 包形态发布的纯 JavaScript 项目（含 TypeScript CLI）误入 C/C++ conan 适配管线。**

- R47 `lang-preflight` 是"AI 自觉调用"的软约束，协议 v0.8 附录 D 冻结后仍有 **9 例违规**（SKILL v12.15 反馈 0831 P1），根因"旧版部署/跳过调用"；
- build 14 步管线中唯一**无条件执行**的静态扫描点是 Step 2.5 G0 预扫描（prescan），但其规则集（24 条静态规则 + 知识库动态派生规则）**没有 nodejs 语言主体识别规则**；
- 后果：漏掉预检的 npm 包会一路走到 conan create 才失败，浪费整轮构建预算与 CI 额度。

## 3. 知识贡献内容

1. **prescan_pattern 字段**（核心增量）：条目合入正式库后，按 v12.5 动态派生机制，PreScanner 自动派生 `PSCAN-KB-<id>` 规则——**知识库增长即扫描能力增长**，G0 在 conan 配方生成前即给出 `env_unsupported` 信号；
2. **判定口径**（与 lang_detect 对齐且防假阳性）：`package.json` 含 `bin`/`engines` 键 **且** C/C++ 源文件计数为 0 → nodejs 主体。叠加"零 C/C++ 源文件"条件，避免复刻 `DRAFT-libok-0.6.5` 记录的 clib/npm 双生态 C 库假阳性；
3. **止损衔接**：命中后指引走 R47 既有终态通道（`env_unsupported` + `detected_language: nodejs`，平台 lang_hold 挂起等生态），不新造流程；
4. **边界声明**：native addon（binding.gyp/napi-rs）不算、辅助构建脚本不算、C 库附带 package.json 发布脚本不算。

## 4. 不重复性声明（与既有知识的关系）

| 既有条目 | 覆盖点 | 本条目差异 |
|---|---|---|
| `DRAFT-npm-purejs-conan-packaging-pattern` | 判定 nodejs **之后**如何打包（W0-W4 决策树） | 本条目管**前置自动识别**（漏判/假阴性侧），且以 prescan_pattern 机制化 |
| `DRAFT-libok-0.6.5-langpreflight-clib-packagejson-misdetect` | lang_detect **误判 C 库为 nodejs**（假阳性） | 本条目管**漏判 npm 包**（假阴性），并复用其边界规则做防误伤 |
| E400 | Node.js 运行时能力矩阵（bun/jitless） | 本条目在选型期 prescan 层，与其运行期知识互补 |

## 5. 验证证据

- imageoptim-cli 3.1.9 端到端：lang-preflight exit 2，`detected_language=nodejs`，语言证据三项齐全（build_system=npm / manifest=package.json engines+bin / source_stats=nodejs 主体 100%）；
- 满足本 pattern 的包与 `lang_detect` 三级判定的 manifest 分支结论一致（叠加零 C/C++ 条件后假阳性受控）；
- prescan_pattern 动态派生机制已在 E013/E019/E037 上实证（v12.5）。

## 5.1 鸿蒙PC 本机消费者用例（端到端复跑，2026-10-15）

在本机（HarmonyOS PC aarch64 真机）重新下载上游官方 tag 3.1.9 源码，端到端复跑本条目覆盖的完整链路：

| 用例 | 执行内容 | 实测结果 |
|---|---|---|
| 消费者用例① | 官方源码下载（codeload tag 3.1.9，61238 字节）→ `ohc-run.py lang-preflight imageoptim-cli 3.1.9 --src <源码>` 全流程 | exit 2，`detected_language: nodejs`，语言证据三项齐全（build_system=npm / manifest=package.json 含 main/scripts/engines/bin / source_stats=nodejs 主体 100%），并经 `result` 命令落 `env_unsupported` 终态 ✅ |
| 消费者用例② | 以本条目 `prescan_pattern` 正则对 3.1.9 真实 `package.json` 执行 G0 派生规则语义验证 | 正例命中（`"engines": {"node"...`）✅；负例（clib 双生态 C 库 package.json，仅 scripts 无 bin/engines node）不命中，防假阳性边界有效 ✅ |

两用例覆盖「源码进入 → 自动识别 → 信号输出 → 终态上报」完整消费者链路，非纯断言。

## 6. 采纳后预期效果

- npm 包误入管线的最坏代价从"conan create 整轮失败"降为"G0 秒级拦截"；
- R47 违规（跳过 lang-preflight）由"文档约束"升级为"管线机械兑底"；
- 与 R47 形成"手动预检（AI）+ 自动预扫（G0）"双保险。

## 7. 上游测试用例清点证据（PR #15826 rule4/rule8 审阅意见澄清，2026-10-16 实测）

审阅意见按上游**默认分支 HEAD** 统计出「17 个测试文件 / 149 个测试函数」，但本任务适配对象是 **tag 3.1.9**。上游在 3.1.9 之后将项目**整体重写为 Rust**，两版代码库完全不同，测试统计必须锚定被适配的 tag。实测证据：

### 7.1 tag 3.1.9（本 PR 适配对象，TypeScript）

```bash
# 源码：https://codeload.github.com/JamieMason/ImageOptim-CLI/tar.gz/refs/tags/3.1.9
find . -iname '*test*' -o -iname '*spec*'        # → 0 个文件
type d \( -name test -o -name tests -o -name __tests__ \)  # → 0 个目录
find . -name '*.rs' | wc -l                       # → 0（无任何 Rust 源码）
find . -name '*.ts' | wc -l                       # → 19（src/ 全 TypeScript）
python3 -c "import json;print(list(json.load(open('package.json'))['scripts'].keys()))"
# → ['build','build:bin','build:ts','format','format:eslint','format:imports',
#    'format:prettier','lint','postbuild','prebuild','prepack']  # 无 test script
grep -E 'jest|mocha|vitest|ava|tap' package.json  # → 无任何测试框架依赖
```

结论：**tag 3.1.9 上游测试用例数为 0**（无测试文件、无测试目录、无 test script、无测试框架 devDependencies），PR 正文申报 0 如实。

### 7.2 上游 HEAD（审阅者统计口径，2026-08-02 重写后的 Rust 版）

```bash
# https://api.github.com/repos/JamieMason/ImageOptim-CLI/git/trees/HEAD?recursive=1
grep -c '_test.rs'    # → src/*_test.rs 17 个（+tests/*.rs 6 个，共 23 个测试文件）
```

审阅意见的「17 个测试文件 / 149 个 #[test]」与该 Rust 重写版吻合，属**版本错位**：该代码库不是本 PR 适配的 3.1.9，且 Rust 工具链在 CI 能力矩阵中为 ❌（W0b/R47 口径，与 TypeScript 版同为 env_unsupported）。本 PR 为知识库扩展（无 conan 包产物），无论按哪个版本口径，均不产生 test_package 补全义务。
