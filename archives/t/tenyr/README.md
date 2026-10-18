# tenyr for OpenHarmony

`tenyr` is a 32-bit CPU architecture/computer system. This package ships its
host toolchain for OpenHarmony/HarmonyOS PC (aarch64):

- **tas** — the tenyr assembler
- **tld** — the tenyr linker
- **tsim** — the tenyr simulator

## Package details

- Upstream: https://github.com/kulp/tenyr
- Build system: raw GNU Makefile (no autotools/CMake)
- Target: OpenHarmony/HarmonyOS aarch64
- Build-time requirements: flex + bison (regenerate lexer/parser)
- Runtime dependencies: none

## Versions

| Version | Status |
| --- | --- |
| 0.9.9 | built |
