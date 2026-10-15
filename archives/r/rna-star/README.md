# rna-star (STAR)

## 简介

STAR（Spliced Transcripts Alignment to a Reference）是 RNA-seq 剪接比对工具，将高通量测序 reads 比对到参考基因组并生成剪接位点信息。C++ 编写，`source/` 下以纯 GNU Makefile 构建，产物为单个命令行可执行文件 `STAR`。

- 上游仓库: https://github.com/alexdobin/STAR
- License: GPL-3.0-or-later
- 构建系统: Makefile（无 configure、无 install 目标）

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 2.7.11b | built | 2026-10-12 |

## 依赖

- **zlib/1.3.1.1**（conan 依赖）：内嵌 htslib 子目录（lib-static 静态链进 STAR）需要 zlib.h 与 `-lz`。
- 内嵌 htslib / opal（SIMDe 可移植 SIMD）均随上游源码打包，无需外部下载。

## 编译说明

```bash
conan create archives/r/rna-star/2.7.11b \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

构建时 build() 会先预生成 `parametersDefault.xxd`（规避 OHOS toybox xxd），随后 `make -j1 all`（命令行钉死 CXXFLAGS/CXXFLAGS_SIMD 等），package() 拷入 `bin/STAR` 并做 ELF 自签。

## HarmonyOS 平台适配

- 上游 Makefile 硬编码 `CXX ?= g++`；编译/链接 flag 由 make 命令行钉死（R33 取 conan conf 的 CXX/CC）
- E130：OHOS libc++-ohos 头要求 C++17 最低，传递 `-std=c++17`；`register` 存储类在 C++17 移除，经补丁 0001 从 SuffixArrayFuns.cpp 移除
- 链接 `-fopenmp -static-openmp` 让 libomp 静态并入，规避 clang 默认 RUNPATH 写宿主 resource dir 导致 CLI 启动 `libomp.so` 加载失败
- `CXXFLAGS_SIMD=` 清空 x86 专属 `-mavx2`（aarch64 上用 SIMDe 软件兜底）
- 可执行 ELF 需 binary-sign-tool 自签（E077/E082），否则 OHOS 内核拒绝执行

## 运行说明

```bash
STAR --version          # 2.7.11b
STAR --help             # 打印全部参数与 STAR version=2.7.11b
STAR --runMode genomeGenerate --genomeDir <idx> --genomeFastaFiles <ref.fa>
STAR --genomeDir <idx> --readFilesIn R1.fq R2.fq
```
