# SortMeRNA

SortMeRNA 是一个局部序列比对工具，用于宏转录组/总 RNA 数据中 rRNA reads 的过滤、比对与聚类（C++17，CMake 构建）。

## 功能概述

- fasta/fastq（含 .gz）reads 对一个或多个 rRNA 参考库的比对过滤
- SAM / BLAST（pairwise 与 tabular）/ FASTA / FASTQ / OTU map 等多种输出
- burst-trie 索引（可分段构建）+ RocksDB KVDB 存储中间结果
- 支持 Illumina / Ion Torrent / PacBio 数据，双端 reads

## OHOS 适配

- 依赖 `rocksdb7/7.9.2`（替代上游 setup.py 固定拉取的 RocksDB v7.10.2；上游 CMake 对 RocksDB 无版本约束，API 兼容）
- 依赖 `zlib/1.3.1.1`（与 rocksdb7 对齐）、`concurrentqueue/1.0.5`（单头文件无锁队列）
- 补丁 0001：保留 RocksDB::rocksdb 完整传递依赖（上游脚本默认 RocksDB 静态库只依赖 zlib+Threads，会丢弃 conan rocksdb7 的 snappy/lz4/zstd/bzip2/gflags）
- 产物为命令行可执行文件 `bin/sortmerna`，OHOS 下 package() 阶段执行自签名
- 已知限制：上游完整测试套件中 54 个场景依赖未随仓分发的外部大体积 reads 数据，另有 16 个场景需 12–77MB 参考库/reads，均未纳入 test_package；详见版本级 notes.md

## 依赖关系

- 编译/链接依赖：rocksdb7、zlib、concurrentqueue（间接：snappy、lz4、zstd、bzip2、gflags）
- 运行依赖：无外部数据依赖（自带 data/ 示例）

## 参考资料

- 上游仓库: https://github.com/sortmerna/sortmerna
- 用户手册: docs/manual4.0.rst（上游源码树内）
