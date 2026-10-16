# ublock 1.70.0 适配笔记 (notes.md)

## 1. 身份与源码核验

| 项 | 值 |
|----|----|
| Conan 名 | `ublock` |
| 上游身份 | uBlock Origin (uBO)，`github.com/gorhill/uBlock` |
| 上游 tag | `1.70.0` |
| 上游 commit | `3703f5efb82dde5aaaaf590a3a37550fcd34160d`（GitHub API `git/refs/tags/1.70.0` 核验） |
| 源码归档 | `https://github.com/gorhill/uBlock/archive/refs/tags/1.70.0.tar.gz` |
| SHA256 | `2f5423376833e5ae441a4e52a2ff9476fa7ff15b0d819c235c5b90505937a1ba`（3961417 字节，`shasum -a 256` 实测） |
| 许可证 | GPL-3.0-or-later |

数据资产（官方 `uBlockOrigin/uAssets`，钉死 commit）：

| 名称 | commit | sha256 |
|------|--------|--------|
| uAssets main | `158c3c962dc1ea27b7d2d1a1c7de119a1f467f59` | `dbf9e6285c1be2b5524ffef79f80e9a26b64fa866f0d22512bae26e5d9a1d227` |
| uAssets prod | `71dbf1e0a268dc06893b35f9737d4789d91962bc` | `a369e7733a1ceeae56a1a7df5ea5c9ed3206f88f24f7e5f805fd5ba3a27f3c17` |

上游 `tools/pull-assets.sh` 以 `git clone --depth 1` 拉取 uAssets HEAD（不可复现）；
本配方改用官方 archive 快照并钉死 commit，由 `source()` 解压到
`dist/build/uAssets/{main,prod}`。

## 2. 语言核验（R47）

- 上游全仓 **1028 个文件**，`*.c/*.h/*.cpp/*.cc/*.hpp/*.m/*.mm` 命中 **0**。
- 文件类型分布：`.png 279`、`.js 268`、`.json 164`、`.txt 145`、`.css 46`、`.html 42`、
  `.sh 14`、`.wat 4`、`.wasm 4`、`.py 3`……
- 构建系统 `Makefile` + bash；根 `package.json` `engines.node >=22 / npm >=11`；
  无 CMakeLists / configure(.ac) / meson.build / Cargo.toml / go.mod。
- `lang-preflight` 判定 `detected=javascript`，与任务默认语言 `cpp` 不匹配
  （protocol verdict = `env_unsupported`）。经人工复核，按仓库既有 **JS/npm 范式**
  （`archives/u/uglify`、`archives/r/roblox-ts`、`archives/l/leaflet-markercluster`
  等同族先例已并入 main）继续适配，判定证据如实留档于 manifest.yaml。

## 3. 依赖核验（W0 / R35 / R36）

- W0：`bash ci/scripts/preflight_check.sh ublock/1.70.0` → `[OK] 预检通过（无依赖需要检查）`，exit 0。
- 强制第三方 C/C++ 依赖 **N = 0**（无任何需 OHOS 流水线单独提供的原生库）：
  - npm 包（根 devDependencies 的 ESLint 工具链）——仅 lint，由 npm 自动拉取；
  - git 子模块（codemirror-ubol、publish-extension）——JS，仅 MV3 构建需要，本次
    MV2（chromium/npm）构建不依赖；
  - 内嵌 vendored JS（codemirror / csstree / diff / hsluv / js-beautify /
    punycode.js / regexanalyzer / lz4 / publicsuffixlist）——源码随仓；
  - WebAssembly 制品（hntrie / biditrie / lz4-block-codec / publicsuffixlist）
    ——`.wasm` 已提交，源为 `.wat`；
  - 系统/工具链（make / bash / python3 / node / npm）。
- R35：依赖可消费性未使用 `conan list`（沿用 batch3 依赖分析报告的 `conan download`
  对照实验：zlib 正对照 exit 0、zzz-nonexistent-xyz 负对照 exit 1、目标库自身 exit 1）。
- R36：无 conan 依赖链，无需前置发布。

## 4. 构建与 OHOS 适配

上游构建目标（真实执行）：

```
make chromium   # → dist/build/uBlock0.chromium（浏览器扩展，含 uAssets 默认过滤列表）
make npm        # → dist/build/uBlock0.npm + uBlock0.npm.tgz（@gorhill/ubo-core 库）
```

鸿蒙适配要点（均有 [OHOS] 测试用例覆盖）：

1. **`settings.os in ("Linux", "OHOS")`**（R32）；OHOS `settings.yml` 为 OHOS 定义了
   无默认值的 `os.version` 子设置，`configure()` 用 `rm_safe` 移除。
2. **Node.js 必须启用 JIT（WebAssembly 可用）** —— 本库与 `archives/u/uglify`
   （`NODE_OPTIONS=--jitless`）**相反**：
   - 首次 conan create 的首个失败用例即 `WASM / WebAssembly available /
     should fulfill with true` → `ReferenceError: WebAssembly is not defined`；
   - 根因：`--jitless` 让 V8 关闭可执行内存，`typeof WebAssembly === 'undefined'`
     （实测 `node --jitless -e 'typeof WebAssembly'` → `undefined`；plain node → `object`）；
   - uBO 引擎核心依赖 WebAssembly 制品（triestore / publicsuffixlist / lz4），
     故 **不得使用 `--jitless`**；改为构建期快速探测「plain node + WebAssembly 可用」，
     不满足即 fail-fast（`build()` → `node-wasm-check.log`）。
3. **不依赖 shell 环境变量 / shebang 路径**（R33）：OHOS 上 `/bin/bash` 不存在、
   bash 位于 `/data/service/hnp/bash.org/bash_5.3/bin/bash`；配方以 `shutil.which`
   显式解析 bash/make/node/npm/python3 绝对路径注入子进程 PATH，`self.run(..., env=None)`
   避免继承 conan 的 C/C++ 环境（`LD_LIBRARY_PATH` 指向 SDK llvm/lib 会让 node 异常终止）。

## 5. 上游测试（R51 三步法）

清点：

| 入口 | 用例 | 说明 |
|------|------|------|
| 根 `package.json` `npm test` | — | `echo "Error: no test specified" && exit 1`（上游显式声明根级无测试） |
| `platform/npm/test.js` | 34 | 官方 mocha 入口：`tests/wasm.js`(2) + `tests/snfe.js`(32) |
| `platform/npm/tests/leaks.js` | 1 | 未被 test.js 收录的上游测试资产 |
| `platform/npm/tests/request-data.js` | 498302 | `--full-battery` 可选；需外部 dev 依赖 scaling-palm-tree |
| `docs/tests/*.html` | — | 浏览器手工测试页，无自动化入口 |

实测（node v24.19.0，OHOS aarch64）：

- 默认电池：**34 passing / 0 failing**（`reports/upstream-mocha-default.log`）。
- leaks.js：**1 passing / 0 failing**（`reports/upstream-leaks.log`）。
- 门禁合计：**35 passing / 0 failing / 0 skipped**。
- 全量电池（request-data）：**496584 passing / 1718 failing**（`reports/upstream-mocha-fullbattery-summary.log`）；
  期望值取自 2021 快照 `tests/data/results.json`，1718 例均为
  `should allow ... : 1 !== 0`（引擎拦截、旧快照期望放行）→ 上游 fixture 陈旧，
  非 OHOS/配方引入；上游 test.js 仅在 `--full-battery` 下启用、上游 CI 亦不执行，故不作门禁。

**注意（上游实现缺陷）**：`platform/npm/test.js` 用 `promisify(spawn)('mocha', …)`
但**不检查子进程退出码**——mocha 失败时 test.js 仍 `exit 0`。故本配方的运行器
`scripts/run_upstream_tests.sh` **直接调用 mocha** 以取得真实退出码与逐项计数。

## 6. 消费者验证（test_package）

`test_package/test.sh`：**19 passed / 0 failed / 0 skipped**（`reports/conan-create.log`）：

- 打包布局 10 条 + 内容锚点 3 条；
- [OHOS] 鸿蒙特有 **6 条**：res 双制品布局、扩展 manifest 版本 == 1.70.0、
  WebAssembly 可用（JIT；--jitless 不兼容）、engines.node >= 18、引擎 e2e、wasm 制品分发；
- 引擎端到端 1 条：`consumer/engine_flow.mjs` 真实驱动被测包 API
  （`enableWASM` + `StaticNetFilteringEngine.create` + `useLists` + `matchRequest`
  block/exception/no-match/类型限定 + `serialize`/`deserialize`），`ENGINE_FLOW=8/8`。

**消费方注意**：uBO 的 SNFE 只允许单个实例（`index.js`：`Only a single instance is
supported.`）——反序列化必须在同一实例上进行，不能再次 `create()`（首轮 conan create
即因此失败，已修正）。

## 7. 修改文件清单

限于 `archives/u/ublock/`（目标库自身），无 C/C++ 补丁（`patches/` 为空）：

- `archives/u/ublock/1.70.0/conanfile.py`（新增）
- `archives/u/ublock/1.70.0/conandata.yml`（新增）
- `archives/u/ublock/1.70.0/manifest.yaml`、`notes.md`（新增）
- `archives/u/ublock/1.70.0/scripts/run_upstream_tests.sh`（新增）
- `archives/u/ublock/1.70.0/test_package/{conanfile.py,test.sh,MANIFEST.yml,consumer/engine_flow.mjs}`（新增）
- `archives/u/ublock/{manifest.yaml,README.md,commands.json}`（软件级，新增）
- `archives/u/ublock/1.70.0/reports/*`（验证日志，新增）
---

**编译结束**: 2026-10-12 16:29
**最终状态**: built

## 8. CI 首轮失败与修复（PR #15459，E430）

**现象**（远端 CI `conan-build-test` exit 1，26.7s）：
```
make: tools/make-chromium.sh: Resource temporarily unavailable
make: *** [Makefile:27: dist/build/uBlock0.chromium] Error 127
```

**根因**：上游 `tools/make-*.sh` 的 shebang 为 `#!/usr/bin/env bash`。`make` 对无 shell
元字符的 recipe 行会**直接 exec** 该脚本，内核经 shebang 先 exec `/usr/bin/env`（OHOS 为
toybox）再 exec bash；在 OHOS/CI（AppSpawn 沙箱）下该链失败（EAGAIN → `Error 127`）。
本地开发机 `/usr/bin/env` 可执行，故本地 W3 通过、远端 CI 失败（知识库 E165/E430）。

**修复**：
1. `conanfile.py` `build()` 不再用 `make <target>`，改为**显式 `bash`** 调用上游脚本
   （`bash tools/make-chromium.sh` / `bash tools/make-npm.sh`），bash 自读脚本、不经 shebang；
2. `patches/0001-tools-explicit-bash.patch` 将 `tools/make-npm.sh` 内部两处
   `./tools/make-nodejs.sh` / `./tools/make-assets.sh` 改为显式 `bash`；
3. `scripts/run_upstream_tests.sh` 以 `node + npm-cli.js`（绝对路径）替代按名 `npm`。

**重新验证**（本地离线 `conan create`，`-nr`）：`RC=0`；补丁已 Apply；
`bash tools/make-chromium.sh` / `bash tools/make-npm.sh` 均 `Package done`；
上游 `default battery rc=0 → 34 passing`、`leaks.js rc=0 → 1 passing`、`UPSTREAM_TESTS=PASS`；
test_package `19 passed / 0 failed / 0 skipped`（`ENGINE_FLOW=8/8`）。

## 9. CI 第二轮失败与修复（E431，npm stub）

**现象**（修复 shebang 后，远端 CI 下一轮）：
```
*** Packaging assets in dist/build/uBlock0.npm/assets...
Error: Cannot find module '../lib/cli.js'
Require stack: - /data/service/hnp/node.org/node_v24.13.0/bin/npm
```

**根因**：hnp `node.org/<ver>/bin/npm` 是**残缺 stub**
（`#!/bin/env node` + `require('../lib/cli.js')(process)`，而 `<node>/lib/cli.js` 不存在；
npm 真实入口在 `<node>/lib/node_modules/npm/bin/npm-cli.js`）。上游 `make-npm.sh` 的
`npm run build` / `npm pack` 因而一执行即失败（知识库 E431）。

**修复**：
1. `conanfile.py` 新增 `_resolve_node_npm()`：在候选 node 中**探测**可用组合
   （node 支持 WebAssembly + `<node>/lib/node_modules/npm/bin/npm-cli.js --version` 可运行），
   候选顺序以 PATH 上的 node 优先（本地=cmd-pkgs、CI=hnp node.org），再回落
   harmonybrew / node.org glob / hnp bin；
2. `build()` 在 build 目录生成 `npm` **shim**（symlink → 真实 npm-cli.js）并置于 PATH 首位，
   使上游脚本内原样的 `npm ...` 可用；
3. 运行器继续用 `node + npm-cli.js`（绝对路径）。

**重新验证**（本地离线 `conan create`，`-nr`）：`RC=0`；
`tool.node` = cmd-pkgs node、`bash tools/make-chromium.sh`/`bash tools/make-npm.sh` 均
`Package done`；上游 `34 passing` + `1 passing`（`UPSTREAM_TESTS=PASS`）；
test_package `19 passed / 0 failed / 0 skipped`（`ENGINE_FLOW=8/8`）。

## 10. CI 第三轮失败与修复（fork EAGAIN）

**现象**（修复前两项后，构建 #90284 / SHA 1cda6eb6）：
```
tools/make-chromium.sh: *** uBlock0.chromium: Package done.
tools/make-npm.sh:      *** uBlock0.npm: Package done.
=== [upstream] uBlock Origin 1.70.0 : platform/npm tests ===
--- default battery (wasm+snfe) rc=1 ---
…/run_upstream_tests.sh: fork: retry: Resource temporarily unavailable
--- leaks.js rc=0 ---  1 passing
UPSTREAM_TESTS=FAIL
```

**根因**：`bash: fork: retry: Resource temporarily unavailable` = fork(2) 返回 EAGAIN，
即 **worker 进程/资源瞬时争用**（紧随其后的 leaks.js 立刻成功，说明为瞬时而非系统性）。
前两项（shebang / npm stub）此前已修好——本轮 build 两目标均 `Package done`。

**修复**：
1. `scripts/run_upstream_tests.sh` 的 `run_mocha()` 增加**有界重试**（≤3 次，退避 10/20s）：
   仅在「子进程未产出日志」或日志命中 `Resource temporarily unavailable|cannot fork|Cannot allocate memory`
   时重试，**不吞真实失败**；
2. 测试依赖安装加 `--ignore-scripts` 降低进程 churn；
3. macOS/本地无 `fork` 限制，故本地 W3 与离线 create 均不复现（又是「本地绿、远端红」类）。

**同类**（CI 首轮 #87809 的 `git-clone` 失败）为**平台侧 worker 异常**
（`FileNotFoundError: b'/system/xbin/git'`、`can't open ci/conan/cleanup.sh`，该 worker 的
HOME/PATH 布局与其它 worker 不同），与本配方无关。
