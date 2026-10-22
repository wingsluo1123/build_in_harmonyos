# sra-sdk

NCBI SRA Toolkit and SDK — 用于访问 INSDC Sequence Read Archive 的工具包与开发库。

## 功能概述

- **数据下载**：`prefetch`（SRA/云存储数据预取）、`srapath`
- **格式转换**：`fasterq-dump`、`fastq-dump`、`sam-dump`、`abi-dump`、`illumina-dump`
- **校验与信息**：`vdb-validate`、`vdb-dump`、`vdb-config`、`sra-stat`、`sra-info`
- **检索与比较**：`sra-search`、`sra-pileup`、`align-info`、`ref-variation`
- **SDK 库**：VDB 存储引擎（`libncbi-vdb`/`libncbi-wvdb`）与 NGS C/C++ 接口（`libncbi-ngs`、`libncbi-ngs-c++`）

## OHOS 适配

- 采用 CMake 交叉编译，`CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`，
  产物为 OHOS AArch64 ELF（编译器默认 triple `aarch64-unknown-linux-ohos`）。
- 上游发行需要 sra-tools 与 ncbi-vdb 两棵源码树，配方同时获取并构建。
- 平台修复：Bison 3.8 错误回调冲突、musl 缺失 `pthread_cancel`（协作式取消）、
  libxml2 2.15 宏移除、HMDFS 符号链接降级打包。详见版本级 `notes.md`。
- 已知限制：本机策略拒绝从应用数据目录 `dlopen` 任意 `.so`，Python 绑定需把
  `libncbi-ngs.so` 安装到应用 bundle 原生库目录；C/C++ 推荐静态链接。

## 依赖关系

- 编译依赖：无外部 Conan 依赖；zlib/bzip2/zstd 由 ncbi-vdb 内置源码编译。libxml2 为上游可选项（仅 kxml/XML loader 使用），默认关闭。
- 运行依赖：标准 OHOS libc/libc++；工具均为自包含静态链接。

## 参考资料

- 上游仓库：https://github.com/ncbi/sra-tools
- VDB 库：https://github.com/ncbi/ncbi-vdb
- 下载页：https://github.com/ncbi/sra-tools/wiki/01.-Downloading-SRA-Toolkit
