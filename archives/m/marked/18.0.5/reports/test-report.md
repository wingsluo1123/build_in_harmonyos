# Test Report — marked 18.0.5

## Build Environment
- Node.js: v26.4.0
- npm: 11.17.0
- Build System: npm (package.json + esbuild + TypeScript)
- OS: OpenHarmony (Linux-compatible)

## Build Steps
1. `npm install` — 510 packages installed (50s)
2. `npm run build`:
   - `build:esbuild` — Bundled src/*.ts → lib/marked.esm.js + lib/marked.umd.js ✅
   - `build:types` — TypeScript compilation + dts-bundle-generator → lib/marked.d.ts ✅
   - `build:man` — marked-man → man/marked.1 ✅

## Build Artifacts
- lib/marked.esm.js (42KB) — ESM format
- lib/marked.umd.js (43KB) — UMD format
- lib/marked.d.ts (26KB) — TypeScript declarations
- lib/marked.esm.js.map, lib/marked.umd.js.map — Source maps
- bin/marked.js, bin/main.js — CLI entry points
- man/marked.1 — Man page

## Functional Tests
1. CLI test: `echo '# Hello World\n\n**test**.' | node bin/marked.js` → ✅ HTML output correct
2. ESM module test: `import { marked } from './lib/marked.esm.js'; marked.parse('# Test')` → ✅ HTML output correct
3. Staging test: Installed to TEST_PREFIX, CLI works from staging dir → ✅

## Result: PASS
All build steps and functional tests passed.
