# Notes — elfutils 0.195

## OHOS 适配要点

### 补丁
1. **config.guess** — 添加 HarmonyOS/__OHOS__ 检测分支
2. **config.sub** — 添加 ohos-linux triplet
3. **lib/error.h** — 新建 error.h 兼容头（musl 无 error()）
4. **lib/eu-config.h** — NLS stubs when USE_NLS not defined
5. **lib/system.h** — program_invocation_short_name 和 FNM_EXTMATCH 兼容

### 构建修复 (conanfile.py build())
- `_fix_ohos_shell_script()`: 修复 configure 和 config.status 中的 OHOS 兼容问题
  - mktemp HMDFS 问题: 替换 `mktemp -d` 为 `ac_tmp=.`
  - E076 pipe 问题: `echo | sed` → `echo >tmpfile && sed <tmpfile`
  - cleanup trap 禁用: 防止 `rm -fr .`
- `CONFIG_SHELL=/bin/sh`: 避免 heredoc pipe 问题
- `GREP=/bin/grep`: 避免 harmonybrew grep PCRE2 符号错误
- `TMPDIR=~/tmp`: /tmp 只读 (E002)
- `configure || true`: 允许 config.status 失败后修复重跑

### test_package 修复
- CMakeLists.txt: 使用 `find_package(elfutils)` + `elfutils::elfutils` (CMakeDeps)
- conanfile.py: 使用 `eu-readelf` (elfutils 工具前缀 eu-)
- MANIFEST.yml: CI L0e 要求的测试声明文件

### 产物
- 3 个共享库: libelf.so, libdw.so, libasm.so
- 3 个静态库: libelf.a, libdw.a, libasm.a
- 18 个 CLI 工具 (eu- 前缀)
- 2 个 pkgconfig 文件: libelf.pc, libdw.pc
---

**编译结束**: 2026-07-04 12:00
**最终状态**: built
