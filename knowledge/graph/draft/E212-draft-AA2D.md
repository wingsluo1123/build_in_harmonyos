# E212: Bun not available on OpenHarmony

> **Structure**: [graph/draft/E212-draft-AA2D.kv](E212-draft-AA2D.kv) | **Principle**: P-TOOLCHAIN-001
> **Severity**: 🟡 medium | **Category**: build-system, javascript, typescript | **Auto-fix**: ❌ manual

---

## Error Characteristics

```
npm error code EBADPLATFORM
npm error notsup Unsupported platform for bun@1.3.14: wanted {"os":"darwin,linux,android,freebsd,win32","cpu":"arm64,x64"} (current: {"os":"openharmony","cpu":"arm64"})

curl: (28) Failed to connect to github.com port 443 after 65249 ms: Couldn't connect to server
error: Failed to download bun from "https://github.com/oven-sh/bun/releases/latest/download/bun-linux-x64-baseline.zip"

TypeError [ERR_UNKNOWN_FILE_EXTENSION]: Unknown file extension ".scm" for .../node_modules/@opentui/core/assets/javascript/highlights.scm
```

## Root Cause

Bun runtime/package manager is not available on OpenHarmony:
1. `npm install -g bun` fails with EBADPLATFORM — OpenHarmony is not in Bun's supported OS list (darwin, linux, android, freebsd, win32)
2. Direct install from bun.sh fails — GitHub connectivity issues on OpenHarmony
3. Projects using `Bun.build()` API in `bun.mts` files cannot build without Bun

## Solution

Replace Bun.build() calls with esbuild.build() calls:

1. **Identify all `bun.mts` files** that use `Bun.build()` API
2. **Write a Node.js build script** (`build-with-esbuild.mjs`) that replicates each `Bun.build()` call using esbuild's `build()` API:
   - `Bun.build({ entrypoints, outdir, target, minify, packages, external })` → `esbuild.build({ entryPoints, outfile, bundle, platform, target, minify, external })`
3. **Convert `workspace:*` protocol to `*`** in all package.json files (npm doesn't support `workspace:` protocol)
4. **Use `npm install --force`** to bypass platform checks for packages like `systeminformation`
5. **Build packages in dependency order**: shared → llms → agents → core → sdk → cli

## Involved Software

- cline (4.0.5) — TypeScript autonomous coding agent SDK/CLI
- Any TypeScript project using Bun as package manager/build tool (identified by `bun.lock` or `bun.mts` files)

## Related Patterns

- [E001](E001.md) — Compiler not found (false positive when build system is npm/esbuild, not autotools)

---

*doc/E212.md · knowledge graph draft · 2026-07-01 · contributor: AA2D*
