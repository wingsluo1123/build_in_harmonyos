# pftools

> PROSITE 广义 profile 构建与搜索工具集（SIB Swiss Institute of Bioinformatics）

## 简介

pftools 是 PROSITE 数据库配套的广义 profile（generalized profile）工具集，由三部分组成：

- **pftoolsV3**（C，现行主版本）：`pfsearchV3` / `pfscanV3` / `pfcalibrateV3` / `pfindex` /
  `pfdump` / `pfpam` / `pfemit` / `pfsplit`，负责 profile 搜索、扫描、校准与索引。
- **pftools release 2.3**（Fortran 77，1990 年代遗留版）：`gtop` / `htop` / `ptoh` / `ptof` /
  `pfw` / `2ft` / `6ft` / `psa2msa` / `pfscan` / `pfsearch` / `pfmake` / `pfscale`。
- **Perl 辅助脚本**：`ps_scan.pl` / `compare_2_profiles.pl` / `split_profile_file.pl` /
  `sort_fasta.pl` / `scramble_fasta.pl` / `fasta_to_fastq.pl` / `make_iupac_cmp.pl`。

上游仓库：<https://github.com/sib-swiss/pftools3>（tag `v3.2.12`）。

## OHOS 适配要点

**pftoolsV3 的 C 对齐内核是 x86 SIMD 专用**，这是本库适配的核心难点：

1. `src/C/include/pfProfile.h:17` 无条件 `#include <emmintrin.h>`，且
   `TransposeHeuristic` / `xali1` / `xalip` / `xalit` 四族内核只存在 x86
   SSE2/SSE4.1 实现（`src/C/sse2`、`src/C/sse41`，共 9 个文件约 4.6k 行），
   **全树没有标量或 NEON 回退**。aarch64 下 clang 对这两个头直接
   `#error "This header is only meant to be used on x86 and x64 architecture"`。
2. 适配引入 `src/C/simd/` 垫片（`conanfile.py` 在 `source()` 中生成 4 个重定向头并拉取
   [sse2neon](https://github.com/DLTcollab/sse2neon) v1.9.1，MIT 许可的 SSE→NEON 转译层），
   顶层 `CMakeLists.txt` 仅在非 x86 架构下把该目录加入 include 路径。
3. 内核中的 x86 内联汇编改写为等价 intrinsic；`utils/system.c` 的
   `cpuid`/`xgetbv`/`bsrq` 探测增加非 x86 分支（aarch64 直接声明 `MM_SSE2|MM_SSE41`）。
4. `USE_AFFINITY=OFF`（上游 `INSTALL` 记载的官方构型）：OHOS 的 musl 不定义
   `__USE_GNU`，而 `system.c` 在 `USE_AFFINITY` 下会 `#error "GNU EXTENSION not activated"`。
5. Fortran 组件由 `tool_requires flang-ohos/20.1.0` 提供（OHOS 无 gfortran）；
   另需处理 flang 不支持的 `-std=legacy`、缺失的 crt/运行时，以及 Fortran 源码里的
   `Status='SCRATCH'`（`/tmp` 只读）与 `FDATE`（flang 未实现）。
6. `-ffp-contract=off`：AArch64 默认启用 FMA 收缩，会使 `pfsearchV3` 打印的分数与
   x86 参考值差 1 ULP（上游 `tests/examples/test_V3.out` 逐字节比对）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| pcre2 | 10.47 | 默认构型 `USE_PCRE2=ON` 强制链接 `pfsearchV3` / `pfscanV3` / `pfdump` |
| libfile-slurp-perl | 9999.32 | Perl 脚本运行期依赖（`use File::Slurp;`），通过 `PERL5LIB` 暴露 |
| flang-ohos | 20.1.0 | 构建期 `tool_requires`，编译 pftools release 2.3 的 Fortran 77 组件 |

运行时只需要 libc（Fortran 运行时静态链接进二进制）。

## 功能验证

```bash
# profile 搜索（随包安装的示例数据）
pfsearchV3 -f $PREFIX/share/examples/sh2.prf $PREFIX/share/examples/sh3.seq
# profile 扫描
pfscanV3 -f $PREFIX/share/examples/sh3.prf $PREFIX/share/examples/sh3.seq
# PROSITE 扫描脚本（需 File::Slurp）
perl -c $PREFIX/bin/ps_scan.pl
```

上游测试套件（CTest，6 个用例）在 OHOS/aarch64 实测 **6/6 通过**，
其中 `test_V3_output.sh` 与上游参考输出**逐字节一致**（1959 行）。

## 参考

- 官网/源码：<https://github.com/sib-swiss/pftools3>
- sse2neon（SSE→NEON 转译层）：<https://github.com/DLTcollab/sse2neon>
