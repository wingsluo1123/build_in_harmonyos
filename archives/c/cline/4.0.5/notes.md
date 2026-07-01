# cline 4.0.5 适配笔记

## 编译环境
- 构建系统: npm + esbuild (custom, replaces Bun)
- 编译日期: 2026-07-01
- 编译器: N/A (TypeScript/JavaScript, no C/C++ compilation)
- Node.js: v26.4.0
- npm: 11.17.0
- esbuild: 0.27.7
- 状态: built

## 软件信息
- cline 4.0.5 是一个 TypeScript 自主编码代理 SDK/CLI
- 上游使用 Bun 作为包管理器和构建工具
- 上游仓库: https://github.com/cline/cline
- 许可证: Apache-2.0

## 编译步骤

1. 下载源码: https://github.com/cline/cline/archive/refs/tags/v4.0.5.tar.gz
2. 转换 workspace:* 协议为 * (npm 不支持 workspace: 协议)
3. npm install --force (绕过 systeminformation 平台检查)
4. 使用 esbuild 替代 Bun.build() 构建所有包:
   - @cline/shared (5 个入口点)
   - @cline/llms (1 个入口点)
   - @cline/agents (1 个入口点)
   - @cline/core (6 个入口点)
   - @cline/sdk (1 个入口点)
   - @cline/cli (1 个入口点, 14MB 打包文件)
5. 复制 plugin-sandbox-bootstrap.js 从 core 到 CLI dist

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Bun 无法安装 | OpenHarmony 不在 Bun 支持的 OS 列表中 | 使用 esbuild 替代 Bun.build() API |
| 2 | npm install 失败 (workspace:*) | npm 不支持 workspace: 协议 | 转换 workspace:* 为 * |
| 3 | npm install 失败 (EBADPLATFORM) | systeminformation 不支持 OpenHarmony | 使用 --force 绕过平台检查 |
| 4 | CLI 运行时失败 (.scm 文件) | @opentui/core 加载 tree-sitter 高亮文件 | 运行时依赖问题，不影响构建 |

## 源码修改
- 所有 package.json: workspace:* → * (npm 兼容性)
- 新增 build-with-esbuild.mjs: esbuild 构建脚本 (替代 bun.mts)

## 产物
- CLI: apps/cli/dist/index.js (14MB, 打包)
- SDK: sdk/packages/*/dist/index.js
- 构建成功，运行时验证受限 (OpenTUI 原生依赖)

## 功能验证
- 构建: ✅ 所有包构建成功
- 运行时: ⚠️ CLI 入口点构建完成，但运行时因 @opentui/core 的 .scm 文件加载失败
- 状态: built (构建成功，运行时验证有限)
---

**编译结束**: 2026-07-01 19:57
**最终状态**: published
