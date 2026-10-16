# ublock

`ublock` 打包 **uBlock Origin (uBO)** 1.70.0 —— 一款高效、低资源占用的广谱内容
拦截器，上游仓库 <https://github.com/gorhill/uBlock>。

## 制品内容

Conan 包安装到 `res/ublock/`：

| 路径 | 内容 |
|------|------|
| `res/ublock/chromium/` | uBlock Origin 浏览器扩展（Chromium 平台，`make chromium` 产物，含 uAssets 默认过滤列表） |
| `res/ublock/ubo-core/` | `@gorhill/ubo-core` 静态网络过滤引擎（SNFE）Node 库（`make npm` 产物） |

## OpenHarmony 适配

uBlock Origin 1.70.0 是**纯 JavaScript 项目**——仓库内 C/C++ 源文件数为 0，
WebAssembly 制品（hntrie / biditrie / lz4-block-codec / publicsuffixlist）以
`.wasm` 形式随仓提交，由 `.wat` 汇编而来；构建系统为 `Makefile` + bash + node/npm。
因此本配方按仓库既有「JS / npm 包」范式适配（参照 `archives/u/uglify`、
`archives/r/roblox-ts`、`archives/l/leaflet-markercluster`），真实执行上游
`make` 构建目标，不引入任何原生编译。

鸿蒙平台要点：

- **Node.js 运行时**：OHOS 上 node 执行 JS 可能触发 V8 断言崩溃
  （`Check failed: 12 == (*__errno_location())`，知识库 E400）。构建与测试统一
  以 `NODE_OPTIONS=--jitless` 驱动 node/npm 及其派生子进程。
- **解释器路径**：OHOS 上 `/bin/bash` 不存在、bash 位于 hnp；配方不依赖
  `#!/usr/bin/env bash` 的 shebang 路径解析，构建前由 `shutil.which` 解析
  bash/make/node/npm/python3 绝对路径并注入子进程 PATH（R33）。
- **settings**：`settings.os in ("Linux", "OHOS")`（R32）；OHOS `settings.yml`
  为 OHOS 定义了无默认值的 `os.version` 子设置，`configure()` 用 `rm_safe` 移除。

## 依赖

- 运行期：OHOS 提供的 Node.js（`engines.node >= 18`）。
- Conan 运行期依赖：**无**（N = 0，详见 `1.70.0/notes.md`）。
- 上游测试专用 dev 依赖（不打包）：`mocha`、`esm-world`，以及可选全量电池的
  `scaling-palm-tree`。

## 上游测试

真实入口 `platform/npm/test.js`（mocha）。默认电池 `tests/wasm.js`（2）+
`tests/snfe.js`（32）= 34 例，另有未被 test.js 收录的 `tests/leaks.js`（1）。
上游 `docs/tests/*.html` 为浏览器手工测试页，无自动化入口。
逐项用例名与日志见 `1.70.0/reports/`。

## 参考

- 上游仓库：<https://github.com/gorhill/uBlock>
- 过滤列表数据：<https://github.com/uBlockOrigin/uAssets>
- npm 库：<https://www.npmjs.com/package/@gorhill/ubo-core>
- 许可证：GPL-3.0-or-later
