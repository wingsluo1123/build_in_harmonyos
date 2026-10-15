# megadepth

megadepth 是一个用于从 BAM/CRAM 比对文件与 BigWig 覆盖度文件中快速计算
覆盖度、AUC（曲线下面积）、剪接位点（junctions）等汇总统计的命令行工具，
由 Christopher Wilks 开发，服务于 RNA-seq 覆盖度分析的常见流水线。

## 简介

megadepth 用单次流式扫描完成以往需要 mosdepth + bwtool + wiggletools 等多个
工具串联才能得到的统计量，输出可直接用于下游注释与 AUC 求和。它既接受
BAM/CRAM/SAM 比对输入，也接受 bigWig 输入（含多 BigWig 并行汇总），
并支持按 BED 注释区间、按固定窗口长度两种聚合方式。

## 主要特性

- BAM/CRAM/SAM 与 BigWig/BigBed 双输入路径
- 覆盖度统计与 AUC 计算（按注释区间或固定窗口长度）
- 唯一比对/多重比对区分（`--min-unique-qual`）、soft-clip、polyA、链方向等过滤选项
- 剪接位点（junctions）与长读长支持（`--long-reads`）
- 片段长度分布（`--frag-dist`）、read 起止位置、alt 等位统计
- `--op sum|mean|min|max` 多种区间聚合算子
- 多线程计算（`--threads`）

## 鸿蒙适配说明

- 构建系统：CMake。上游只提供 `CMakeLists.txt.ci/.static/.statlib/.windows`
  四个变体并以 `ln -fs` 取规范名，且硬编码 vendored 子模块目录；配方自带等价的
  `CMakeLists.txt`（`export_sources` 导出），改用 CMakeDeps 目标消费依赖，
  **不改动任何上游 C++ 源码**。
- 依赖：`htslib/1.24-r0`、`libbigwig/0.4.9`、`zlib/1.3.1`（均取自 ohpcd 制品仓），
  传递依赖 `libdeflate/1.25`、`xz/5.6.2`。
- aarch64 无需架构补丁：上游的 AVX512/AVX2/SSE2 与 `x86intrin.h` 均由
  `__AVX512F__`/`__AVX2__`/`__SSE2__` 守卫，aarch64 上整体编译剔除并走标量尾循环。
- 上游测试 `tests/test.sh` 以 `static` 模式完整运行（19 次调用 / 30 条断言），
  对上游脚本有两处最小改动（见 `1.2.0/notes.md` 与 `1.2.0/patches/`）：
  1. 一处未加 `static` 守卫的远程 HTTP 取数 → 等价的本地 fixture；
  2. CRAM 用例去掉 `--alts` → 走 htslib 参考无关解码路径（断言与期望输出不变）。
- **不要在 PR 中提交二进制文件**：平台 `checkout-pr` 用 `curl .../pull/<N>.diff` + `git apply`
  应用 PR 变更，该 diff 端点对二进制文件不携带 `GIT binary patch` 数据，会导致整个 diff
  无法应用而 CI 直接失败（本包曾因 `test_package/fixtures/` 内的 `.bam`/`.bai` 踩中）。
  故测试 fixture 一律使用纯文本：这里改用上游 `tests/test.sam`（megadepth 把 `.sam` 归入
  BAM 族且 `sam_open()` 自动识别），输出与 `.bam` 完全等价。

## 上游地址

- 仓库：https://github.com/ChristopherWilks/megadepth
- 许可：MIT
- 版本：1.2.0
