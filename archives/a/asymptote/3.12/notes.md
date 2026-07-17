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
- Optional dependencies (`ffmpeg`/`gsl`/`opengl`) are disabled via
  `--disable-*` to avoid OHOS platform missing-library build failures.
- `package_info`: `cpp_info.libs = []` (executable, not a linkable library);
  `bindirs = ["bin"]` exposes the installed `asy` binary.
- No patches are bundled in this base recipe (`patches: {}`).

## OHOS Adaptation
A full HarmonyOS (aarch64) build of asymptote relies on platform availability
of its core C++ runtime and the Boehm GC. Key adaptations:

1. `config.guess` / `config.sub`: pass `--build=aarch64-unknown-linux-gnu`
   explicitly to bypass OHOS system type detection failures (autotools
   projects 惯例).
2. `--disable-ffmpeg` / `--disable-gsl` / `--disable-opengl`: 关闭鸿蒙平台
   缺失的可选依赖, 仅保留核心 asy 编译器功能.
3. `config_options`: OHOS 平台删除 `shared` 选项 (asymptote 为可执行工具).

## Dependencies
- Core runtime: libc, libstdc++ (clang/clang++)
- Optional (disabled on OHOS): ffmpeg, gsl, opengl/freeglut

## Verification
The test_package is a Conan L1 smoke test verifying the `asymptote` package is
consumable. Because `asy --version` requires a working TeX installation at
runtime, the test uses a minimal consumer program that links against the
package's environment to verify the install layout.

---

**编译结束**: 2026-07-17
**最终状态**: built
