# tabixpp

tabixpp 是 tabix 索引器的 C++ 封装，用于读写 bgzf 压缩、tabix 索引的基因组数据文件（VCF/BED/GFF）。

## OHOS 适配

- **构建入口**：仓库根 raw `Makefile`（`make all` 产出 `tabix++`、`libtabix.a`、`libtabix.so.1`；`make test` 为上游测试）。
- **依赖外置**：发布 tarball 不含 htslib 子模块内容，配方依赖 `htslib/1.24-r0` 并以 `INCLUDES/LIBPATH` 覆盖传入，`HTS_HEADERS/HTS_LIB` 置空。
- **链接修正**：去掉 htslib 已禁用的 `-lcurl -lbz2`，补静态 `libhts.a` 所需的 `-ldeflate`（见 `1.1.2/patches/`）。
- **测试**：上游 `make test`（单集成用例）+ test_package 现场制作 VCF 夹具驱动 Tabix API（8 断言）。

## 版本

- `1.1.2`：首次适配（`tabixpp/1.1.2`）

## 参考

- 上游仓库：https://github.com/vcflib/tabixpp
- 依赖：https://github.com/samtools/htslib
