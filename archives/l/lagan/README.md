# lagan

LAGAN（**L**ocal **A**lignment **G**enome **AN**alysis）是 Stanford 大学发布的
DNA 序列比对工具集，提供局部、全局与多序列比对的命令行程序。

## 功能概述

* **多序列比对**：`mlagan` —— 基于系统发生树的多序列比对
* **局部锚定比对**：`chaos`（CHAOS 锚点搜索）、`anchors`、`order`
* **全局比对**：`glocal`、`prolagan`、`lagan.pl`
* **工具集**：`utils/` 下 17 个小工具（格式转换、打分、拼接、dotplot 等）
* **perl 包装**：`lagan.pl` `slagan.pl` `slagan-mfa.pl` `rechaos.pl`
  `anal_gloc.pl` `xmfa2mfa.pl` + `Utils.pm`
* **打分矩阵**：`nucmatrix.txt`、`blosum62.txt`、`blosum62s.txt`

## OHOS 适配

* 构建系统是**普通 Makefile**（非 autotools/CMake）：顶层 `make` 递归到
  `src/`，`glocal/` 单独再 make。
* **无第三方依赖**，仅链接 `-lm`；交叉编译只用到 OHOS SDK 的 clang 15。
* 2006 年代码配上现代 clang/glibc 需要 4 个可移植性补丁（`getline` 撞名、
  C99 裸 `inline`、`std::end` 二义、`<fstream.h>`），另加 `-fcommon` 处理
  `thrtrie.h` 的 tentative definition。详见 `2.0/notes.md`。
* `src/Makefile` 硬编码 `gcc`/`g++`，因此配方显式列出各二进制目标并在 make
  命令行覆盖 `CC`/`CPP`/`CLINKER`。
* 运行期通过 `$LAGAN_DIR` 定位数据文件，配方已在 `runenv_info` 中导出该变量
  并把 `<package>/bin` 加入 `PATH`。

## 依赖关系

| 类型 | 依赖 |
| --- | --- |
| 编译依赖 | 无（OHOS SDK clang 15 + make） |
| 运行依赖 | `libc`、`libm` |
| 构建期依赖 | `$LAGAN_DIR`（由本包 runenv 提供） |

## 参考资料

* 官网：http://lagan.stanford.edu/lagan_web
* 源码归档：http://lagan.stanford.edu/lagan_web/lagan20.tar.gz
* 相关论文：Brudno et al., *LAGAN and Multi-LAGAN*, Genome Research 13(4), 2003