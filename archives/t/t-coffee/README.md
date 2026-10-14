# t-coffee

## 简介

T-COFFEE（**T**ree-based **C**onsistency **O**bjective **F**unction for
**E**valuation of alignments）是西班牙 CRG Barcelona（Cedric Notredame 组）的
经典渐进式**多序列比对**（MSA, multiple sequence alignment）程序。它先用文库
（library）里的成对比对做一致性扩展，再用引导树做渐进式合并，是目前被引用
最多的比对工具之一，也是 Expresso / 3D-Coffee / M-Coffee / R-Coffee / PSI-Coffee
等一整族工具的公共引擎。

- 唯一版本（本包）：`13.45.0.484626413.41.0.28bdc39`（上游发布号 `13.45.0.4846264`）
- 官方来源：<https://www.tcoffee.org>
- 许可证：GPL-3.0-or-later
- 平台：HarmonyOS HongMeng Kernel / aarch64

## 关键参数

| 能力 | 说明 |
|------|------|
| 比对对象 | 蛋白 / DNA / RNA 序列；通过 3D-Coffee 还可引入 PDB 结构模板 |
| 输出格式 | `-output clustalw|fasta|gcg|phylip|srampage|razf|bootstrap|summary` |
| 库导出 | `-lib_only -in <序列文件>`：只算成对文库（对 Expresso 等上层工具有用） |
| 线程 | `-n_core <n>`：本包构建为单进程，`-n_core 1` 最稳 |
| 快速树 | `-quicktree` 输出引导树而不做比对 |
| 矩阵 | `-matrix default`，残基矩阵编译在 `matrices.h` 里，运行期不需要外部矩阵文件 |
| 运行期缓存 | `HOME_4_TCOFFEE` / `DIR_4_TCOFFEE` 指定 T-Coffee 自建 `tco/` `mcoffee/` `methods/` `plugins/` 的位置（默认 `$HOME/.t_coffee`） |

**本包不包含** `TMalign`（同目录里的 Fortran 程序，需要 gfortran，OHOS NDK 不提供），
因此 Expresso / 3D-Coffee 等依赖 TMalign 的上层模式不在本包范围内。

## 版本号说明

平台任务池给的 `13.45.0.484626413.41.0.28bdc39` 是把上游发布号
`13.45.0.4846264` 与 Debian 源码包版本
`13.45.0.4846264+really13.41.0.28bdc39`（去掉 `+really` 与 `+dfsg-1`）首尾相接
得到的串，二者指向同一份代码。配方里的源码 URL / sha256 / 版本目录 / 分支名
一律用任务池给定的串，源码本身取自上游官方归档
`T-COFFEE_distribution_Version_13.45.0.4846264.tar.gz`。

## 构建状态

- `13.45.0.484626413.41.0.28bdc39` — built (2026-10-04)
- 构建系统：makefile（上游 `t_coffee_source/makefile`，23 行，无 configure）
- 补丁：1 个（`portability`，补齐 30 处 non-void 函数落空返回，见版本级 manifest）
- 依赖：无（只链接 libc，libm 在 OHOS 已并入 libc.so）
