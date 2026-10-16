# E431 — OHOS：hnp `node.org` 自带 `bin/npm` 是残缺 stub（MODULE_NOT_FOUND）

## 错误特征

```
Error: Cannot find module '../lib/cli.js'
Require stack:
- /data/service/hnp/node.org/node_v24.13.0/bin/npm
    at Object.<anonymous> (/data/service/hnp/node.org/node_v24.13.0/bin/npm:2:1)
  code: 'MODULE_NOT_FOUND'
```

- 任何 `npm ...`（`npm run build` / `npm pack` / `npm install`）一执行即报此错。

## 触发条件

- 构建系统: make / npm（配方内调用 `npm`）
- 阶段: build（首次调用 `npm` 时）
- 环境: OHOS / hnp 的 node.org 安装

## 根因分析

hnp `node.org/<ver>/bin/npm` 的内容是一个**残缺 stub**：

```console
$ head -3 /data/service/hnp/node.org/node_v24.13.0/bin/npm
#!/bin/env node
require('../lib/cli.js')(process)
```

其 `require('../lib/cli.js')` 相对 `bin/` 解析到 `<node>/lib/cli.js` —— **该文件不存在**
（npm 的真实 CLI 入口在 `<node>/lib/node_modules/npm/bin/npm-cli.js`）。因此 PATH 上的
`npm` 不可用；上游 `tools/make-npm.sh`（`npm run build` / `npm pack`）随之失败。

> 注意与 E165/E430 区分：后者是 **shebang 执行**问题；本条目是 **npm 包布局**问题，
> 二者可同时出现（本例先修 shebang 才暴露 npm stub）。

## 解决方案

### 推荐方案

1. **不使用 PATH 上的 `npm`**，改为 `node` 直接执行真实入口：
   `"$node" "<node>/lib/node_modules/npm/bin/npm-cli.js" <args>`
2. 或在 build 目录生成指向真实 `npm-cli.js` 的 **`npm` shim** 并置于 PATH 首位，
   这样上游脚本里原样的 `npm ...` 也能工作。
3. 配方应**探测并解析**可用组合（node 需满足库的实际能力要求，如 uBlock Origin 需要
   支持 WebAssembly 的 node），不可想当然：

```console
$ node <node>/lib/node_modules/npm/bin/npm-cli.js --version   # 应有版本号输出
```

### 禁止做法

- ❌ 直接用 `npm`（PATH 解析到残缺 stub）。
- ❌ 因 npm 失败就判定“源码编译错误”去改源码。

## 验证

```bash
head -3 "$(dirname "$(which node)")/npm"        # 观察是否为 require('../lib/cli.js') stub
"$(which node)" "$(dirname "$(which node)")/../lib/node_modules/npm/bin/npm-cli.js" --version
```

## 关联条目

- 相关: E165（OHOS 无 /bin，shebang 路径修复）
- 相关: E430（make 直接 exec shebang 脚本失败 → 显式 bash）
- 相关: E429（依赖 WebAssembly 的 JS 库禁用 --jitless）
