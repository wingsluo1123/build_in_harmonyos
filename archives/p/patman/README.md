# patman

PatMaN（Pattern Matching in Nucleotide databases）把一组短模式（FASTA）与一个或多个核酸数据库（FASTA）做近似匹配，
允许指定数量的错配和缺口，输出制表符分隔的命中表（库序列名、模式名、起止位置、链、编辑距离）。

```sh
patman -e 1 -D genome.fa -P patterns.fa -o hits.tsv
```

## 源码来源

Debian 的 `patman_1.2.2+dfsg.orig.tar.xz`（官方 Debian 归档，已核对 sha256）。上游主页 <https://bioinf.eva.mpg.de/patman/>，许可证 GPL-2.0-or-later。

## HarmonyOS PC 适配

- 单个补丁 `0001-Makefile.patch`：`g++` 改为 `$(CXX)`，删除 `-march=k8`，版本串 `1.2` 改为 `1.2.2`。
- 依赖 `popt/1.16`；产物 `bin/patman`、`share/man/man1/patman.1`。
- 上游无自动化测试，`test_package` 提供消费者用例：运行打包出的 `patman`，用编译出的 `check_hits` 解析并比对命中表。
