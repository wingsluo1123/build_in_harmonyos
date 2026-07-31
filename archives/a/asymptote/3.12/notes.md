# Adaptation Notes - asymptote 3.12

## Overview
Asymptote is a powerful descriptive vector graphics language for technical
drawing, providing a natural coordinate-based framework. Labels and equations
are typeset by LaTeX, producing high-quality PostScript/PDF output.

- Official source: https://asymptote.sourceforge.io/
- GitHub mirror: https://github.com/vectorgraphics/asymptote
- Product: `asy` executable (vector graphics compiler — no linkable library)
- Build system: autotools (configure + make)
- 类型: 【积分赛】(矢量图形语言/工具)

## Source
The canonical source tarball is the official SourceForge release:
`https://sourceforge.net/projects/asymptote/files/3.12/asymptote-3.12.src.tgz/download`

- sha256: `eaec1e97463ef213a393c388d466a73478b0818f9403c962b91240659c9b8f1b`
- size: 28607113 bytes
- tar_format: tar.gz

## Conan Recipe (3.12)
- Conan 2.x autotools recipe (`conan.tools.gnu.Autotools` / `AutotoolsToolchain`).
- `config_options`: on OHOS the `shared` option is removed (asymptote is a
  standalone executable, never a shared library).
- `generate`: `--build=aarch64-unknown-linux-gnu` is appended for OHOS
  config.guess detection (autotools 项目惯例).
- Optional components (`ffmpeg`/`gc`/`gsl`/`gl`/`vulkan`/`lsp`) are disabled only on
  OHOS to avoid missing-library build failures on that platform.
- `package_info`: `cpp_info.libs = []` (executable, not a linkable library);
  `bindirs = ["bin"]` exposes the installed `asy` binary.
- The recipe builds in the copied source directory because Asymptote's main
  Makefile is not safe for an out-of-source build (`Makefile.in` is expected
  beside the generated Makefile).
- `make --jobserver-style=pipe -j4` keeps the build within the CI timeout
  without using the FIFO jobserver, which is unavailable on OHOS.
- `001-config-status-readable-temp.patch` changes Autoconf's temporary
  directory umask from `077` to `022`, matching the repository's established
  HMDFS workaround so `config.status` can consume its generated files.

## OHOS Adaptation
A full HarmonyOS (aarch64) build of asymptote relies on platform availability
of its core C++ runtime and the Boehm GC. Key adaptations:

1. `config.guess` / `config.sub`: pass `--build=aarch64-unknown-linux-gnu`
   explicitly to bypass OHOS system type detection failures (autotools
   projects ??).
2. `--disable-ffmpeg` / `--disable-gc` / `--disable-gsl` /
   `--disable-gl` / `--disable-vulkan` / `--disable-lsp`: ?????????????????, ????? asy
   ?????. In particular, the bundled Boehm GC starts a nested Autotools
   configure that cannot create its probe files on the OHOS worker.
3. `config_options`: OHOS ???? `shared` ?? (asymptote ??????).
4. `config.status`: create its temporary directory with HMDFS-compatible mode;
   `umask 077` causes `subs1.awk: Permission denied` on the OHOS worker.
5. Build in-source and use make's pipe jobserver: out-of-source make cannot
   find `Makefile.in`, while the default FIFO jobserver is unavailable on OHOS.

## Dependencies
- Core runtime: libc, libstdc++ (clang/clang++)
- Optional (disabled on OHOS): Boehm GC, ffmpeg, gsl, gl/freeglut, Vulkan, LSP


## Verification
The test_package is a Conan L1 smoke test for the packaged `asy` executable.
It builds and runs a consumer that executes `asy --version` through Conan's
run environment, accepts only exit status 0, and requires output identifying
Asymptote 3.12. Missing artifacts, loader failures, crashes, or unrelated
output fail the test.

Upstream ships a much larger suite: 12 functional test categories plus error
tests and C++ unit tests. This Conan package does not run that suite in CI, so
the adapted verification is a single 1/1 smoke test (100%) with roughly 5%
functional coverage against the upstream surface.

---

**编译结束**: 2026-07-17
**最终状态**: built

---

## Vulkan 编译修复记录

**问题**: configure 检测不到 vulkan.hpp 时, Makefile 仍会编译
thirdparty_impl/vk-mem-allocator_impl (vma_cxx.cc), 导致
`fatal error: vulkan/vulkan.hpp file not found`.

**修复**: OHOS 平台 configure 增加 `--disable-vulkan` 参数。
configure.ac 中该参数会令 VMA_IMPL_FILES 为空, Makefile 不再编译
vk-mem-allocator_impl。同步使用 `--disable-gl`/`--disable-lsp`
替代无效的 `--disable-opengl`。

**验证**: CI 在 aarch64-unknown-linux-ohos 上重新构建通过后确认。
