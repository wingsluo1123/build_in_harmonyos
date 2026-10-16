# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_4d700818.md`

---

## 背景

- **软件名称**: ublock
- **版本**: 1.70.0
- **构建日期**: 2026-10-12
- **构建系统**: make（Makefile + bash + node/npm；纯 JS，C/C++ 源文件 0）
- **上游仓库**: https://github.com/gorhill/uBlock （uBlock Origin，tag 1.70.0 / commit 3703f5ef）
- **适配路径**: 路径 A（基础适配，无补丁；JS/npm 范式）
- **补丁数量**: 0
- **编译依赖**:
无（N = 0，无第三方 C/C++ 依赖）
- **最终状态**: 成功（本地门禁全绿；按用户要求停在 commit/push/PR 前）

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 部分 | `init-build` 直连 github.com 超时失败（exit 3）；改由 conan-verify 的镜像注入路径完成 source 下载（官方 URL + ghfast 镜像） |
| build | 编译构建 | 成功 | `make chromium` + `make npm`（构建系统: make） |
| conan-verify | 配方验证 | 通过 | G1/G2/G3/G4 + L2/L4/L5 全 PASS；test_package 19/19 |
| finish | 归档收尾 | 完成 | W3 本地 CI 通过（L0-L5）；W2 原子性通过；`.ci-result.json` 已生成 |
| submit | PR提交+AI检视+CI | 未执行 | 按用户指令停在远端写操作前（AI Review: —） |

### 失败与问题

1. **`init-build` github.com 直连超时**（exit 3）→ 由框架 CI/W3 的镜像回退解决（conandata 保持官方 URL）。
2. **首个 conan create 失败用例** `WebAssembly is not defined`：根因是沿用 `NODE_OPTIONS=--jitless`（E400 的常规规避手段），而 `--jitless` 会禁用 WebAssembly；uBO 引擎强依赖 wasm → 移除 `--jitless`，改以「plain node + WebAssembly 可用」探测。
3. **`spawn mocha ENOENT` / `Cannot find package 'esm-world'`**：上游测试依赖未声明/未在 PATH；运行器显式安装并直接调用 mocha。
4. **`Only a single instance is supported.`**：uBO SNFE 单实例，消费用例误二次 `create()` → 改为同实例 `deserialize()`。
5. **W3 JC 门禁首次失败（full 模式）**：本地 `main` 落后 `origin/main`，`origin/main...HEAD` 为空 → 回退整仓 `git ls-files` 扫描，命中**其他库/历史**的 `.staging-verified` 等残留（cloog/kics/libbfio/oscpack/reflex/thc）；以 CI 同源 `pr.diff`（prdiff 模式）复跑即通过（14 文件 0 垃圾）。

### 知识图谱使用情况

- **引用知识条目**: E400（Node.js CLI on HarmonyOS: JITless/WASM capability boundary）
- **新增知识草稿**: 1 条（`E429-draft-A5AD`：依赖 WebAssembly 的纯 JS 库禁用 `--jitless`；npm test.js 不传播 mocha 退出码）
- **引擎命中情况**: 草稿目录 3034 条
- **测试统计**: 上游默认电池+leaks 35/35 通过；全量电池 496584/498302（1718 上游陈旧 fixture，非门禁）；test_package 19/19
- **未覆盖的错误模式**: E400 已覆盖 `--jitless`↔WASM 边界；本次补充「JS 库 must-JIT（wasm）」与「上游 test.js 退出码不传播」两点（E429）

### AI 检视结果

- **检视阶段到达**: —（未提交 PR）
- **变更摘要评估**: 未执行（按要求停在远端写操作前）
- **检视意见数量**: 未执行
- **检视意见处理**: 未执行

### CI 结果

- **本地 CI 模拟 (W3)**: 通过（L0 pass / L1 pass / L2 skip(no bin) / L4 pass / L5 pass；Pass rate 100%）
- **远程 CI (PR 校验)**: 未执行（未提交 PR）
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 1（首次 finish 因 W3 JC full 模式误拦既有垃圾）
- **重试次数**: 4（github 下载、mocha 依赖、jitless→WASM、SNFE 单实例）
- **关键瓶颈**: ①本机 github.com 直连不可达，依赖镜像；②每次 `conan create` 全量重跑（下载 uAssets + 构建 + 安装测试依赖 + mocha）；③本地 main 落后 origin/main 导致 junk_check 回退整仓扫描
- **耗时较长的步骤**: `conan create`（含 `make chromium`+`make npm`+mocha）与 uAssets 下载

---

## 建议

### SKILL 设计改进

1. **junk_check 的 full 模式不应把「仓库既有历史残留」算作本次门禁失败**：本地无 `origin/main` 或本地 main 落后时回退整仓扫描，会命中其他库已提交的 `.staging-verified`/`.build-closed` 等，导致 W3 假失败。建议 full 模式仅对「本次新增/变更」判定，或对历史已跟踪残留降级为警告。
2. **`finish` Step 10 与 Step 6 的就绪口径不一致**：Step 6 已接受「conanfile.py（v3.0）或 legacy packaging/」，但 Step 10 仍硬性要求非空 `packaging/`；建议 Step 10 对齐 v3.0（conanfile.py 存在即视为打包就绪）。
3. **JS/npm 类库的 `--jitless` 默认注入应更谨慎**：E400 的规避手段并非万能（会禁用 WebAssembly）；建议在预扫描/预分析阶段对「含 .wasm 或 wasm 相关依赖」的包提示「禁用 `--jitless`」。

### 模板改进

1. `conanfile-headeronly.py.tmpl` 的「脚本工具/数据资源」变体可补充「JS 库（无 CLI）」子形态（本包=扩展资产 + Node 库，无 bin），减少手工裁剪。
2. test_package 模板建议内置「node 探测（含 WebAssembly 能力）+ [OHOS] 用例」骨架，JS 类库可直接套用。
3. MANIFEST.yml 模板的 `upstream_test_in_build` / `count` 字段建议支持「多套件分列」以表达「默认电池 + 可选全量电池」两类统计。

### 自动化补全

1. `finish`/W3 失败时若能自动识别「full 模式误拦历史残留」并给出 `JUNK_PR_DIFF` 的生成指引，可省去人工排查。
2. `conan create` 的 source 下载可复用本地已下载归档（sha256 命中即跳过网络），降低重复构建耗时。
3. 上游测试依赖（mocha/esm-world/外部 GitHub dev 包）建议由运行器统一声明，自动注入并缓存。

### 知识图谱覆盖

1. 新增 E429（`--jitless` 与 WebAssembly 互斥；npm `test.js` 不传播 mocha 退出码；SNFE 单实例）——已以草稿 `E429-draft-A5AD` 记录。
2. 建议补充「纯 JS / 浏览器扩展类库的 conan 适配范式」条目（资产包 resdirs + Node 消费者测试），与既有 uglify / roblox-ts / leaflet-markercluster 经验互链。

---

## 作者

- **姓名**: lyl_ling
- **邮箱**: lan_ling_wang@noreply.gitcode.com
- **Agent ID**: A4DC
- **生成时间**: 2026-10-12 16:34:39
- **PR 编号**: —（未提交）
- **Git Commit**: ff1dce4f96
