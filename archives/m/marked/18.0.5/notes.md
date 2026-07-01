# Compilation Notes — marked 18.0.5

## Software Overview
- **Name**: marked
- **Version**: 18.0.5
- **Description**: A markdown parser built for speed
- **Language**: JavaScript/TypeScript
- **License**: MIT
- **Homepage**: https://github.com/markedjs/marked

## Build System
- **Type**: npm (package.json + esbuild + TypeScript)
- **Build command**: `npm run build` (build:esbuild + build:types + build:man)
- **No C/C++ compilation required** — pure JavaScript library

## Build Steps

### 1. npm install
- 510 packages installed
- Required approving esbuild's postinstall script (`npm approve-scripts esbuild`)

### 2. npm run build
- `build:esbuild`: Bundles `src/marked.ts` → `lib/marked.esm.js` (ESM) + `lib/marked.umd.js` (UMD)
- `build:types`: `tsc` + `dts-bundle-generator` → `lib/marked.d.ts`
- `build:man`: `marked-man` → `man/marked.1`

### 3. Functional Tests
- CLI: `echo '# Hello' | node bin/marked.js` → correct HTML output ✅
- ESM import: `import { marked } from './lib/marked.esm.js'` → correct HTML output ✅
- Staging install: Files copied to TEST_PREFIX, CLI works from staging dir ✅

## Packaging Strategy
- JS library packaged as data files under `lib/node_modules/marked/`
- Structure follows npm/node_modules convention
- Consumers use `NODE_PATH` environment variable to locate the module
- `package_info()` sets `NODE_PATH` and `PATH` via `runenv_info`

## Conan Recipe
- **conanfile.py**: Custom recipe (not autotools/cmake)
  - `build()`: `npm install && npm run build`
  - `package()`: Copy lib/, bin/, man/, package.json to package folder
  - `package_info()`: Set NODE_PATH and PATH environment variables
- **conandata.yml**: Source URL + SHA256
- **test_package/**: Node.js import test (ESM module + version check)

## Known Issues
- GitHub direct download blocked in OHOS environment; used gh-proxy.com mirror
- esbuild postinstall script requires explicit approval with npm 11.x
---

**编译结束**: 2026-07-01 18:29
**最终状态**: published
