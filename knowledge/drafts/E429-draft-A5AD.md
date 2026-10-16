# E429 — OHOS Node.js：依赖 WebAssembly 的纯 JS 库禁用 `--jitless`

## 错误特征

- 上游 mocha 用例失败：`ReferenceError: WebAssembly is not defined`
  （uBlock Origin `platform/npm/tests/wasm.js:37`，`WebAssembly available / should fulfill with true`）。
- 观测量：`node --jitless -e 'typeof WebAssembly'` → `undefined`；plain `node` → `object`。
- 附带：上游 `platform/npm/test.js` 用 `promisify(spawn)('mocha', …)` 却不检查子进程退出码，
  mocha 失败时 `test.js` 仍 `exit 0`（易被误判为通过）。

## 触发条件

- 构建系统: make / npm（纯 JS 项目，无 C/C++）
- 阶段: build（上游测试执行）/ conan create G2

## 根因分析

OHOS 上 node 执行 JS 可能触发 V8 断言崩溃（知识库 E400），因此习惯性以
`NODE_OPTIONS=--jitless` 规避。但 `--jitless` 会让 V8 关闭可执行内存分配，
**WebAssembly 随之不可用**（`typeof WebAssembly === 'undefined'`）。
当被测 JS 库/CLI 依赖 WebAssembly 制品时（uBO 的 trie / publicsuffixlist / lz4 引擎），
`--jitless` 会让上游 wasm 用例直接 `ReferenceError`。

uBlock Origin 的 `tests/wasm.js` 正是验证 `enableWASM()` 返回值，故该失败在
首次 `conan create` 即暴露（首个失败用例）。

## 解决方案

### 推荐方案

1. **不要**对依赖 WebAssembly 的 JS 库注入 `NODE_OPTIONS=--jitless`（与
   `archives/u/uglify` 的纯 JS 场景相反）。
2. 构建期以 **plain node + `typeof WebAssembly === 'object'`** 作可用性探针，fail-fast。
3. 运行上游测试时**直接调用 mocha**（`node node_modules/.bin/mocha
   --experimental-vm-modules --no-warnings …`）以取得真实退出码，勿依赖 `test.js`。
4. 注意 uBO SNFE 为单实例，`serialize()`/`deserialize()` 必须作用于同一实例。

### 禁止做法

- ❌ 为“对齐 E400”而盲目注入 `--jitless`（会静默禁用 WebAssembly 引擎）。
- ❌ 依赖上游 `test.js` 的退出码判定测试成败（不传播 mocha 退出码）。

## 验证

```bash
node -e 'process.stdout.write(typeof WebAssembly)'   # object
node --jitless -e 'process.stdout.write(typeof WebAssembly)'  # undefined
# 修复后：上游默认电池 mocha 实测 34 passing / 0 failing；并额外跑 tests/leaks.js
```

## 关联条目

- 相关: E400（Node.js CLI on HarmonyOS: JITless/WASM capability boundary）
