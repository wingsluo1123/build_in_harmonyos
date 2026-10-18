# pizzly

pizzly 是 RNA-Seq 融合基因检出工具：读取 kallisto（`--fusion`，0.43.1 及以上）输出的候选
融合位点，做假阳性过滤、断点级转录本组装与丰度定量，输出 `.json` 与 `.fusions.fasta`。
上游以 SeqAn 2 实现，CMake 构建，唯一外部依赖 zlib。

当前适配版本：

- `0.37.3`：CMake + zlib（Conan 管理），交付 `bin/pizzly` 可执行文件。

适配要点与实测证据见 `0.37.3/notes.md`。
