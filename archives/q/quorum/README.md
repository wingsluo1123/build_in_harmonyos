# Quorum

Quorum 是利用质量分数和 Jellyfish k-mer 数据库纠正 DNA 测序读段的命令行工具。

保留质量数据库生成、读段纠错、配对读段合并/拆分、Perl 前端流水线和上游 adapter 数据。
原生适配用公开 C++/zlib 接口代替 GNU 标准库私有流接口；以显式 Conan traits 消费已发布混合工具/库包的真实头文件和库。Perl 前端运行依赖随包图声明，而不是借用系统模块。

依赖：Jellyfish、zlib、Perl；上游测试使用 GoogleTest。Conan 会解析其已发布制品。
真机成功不表示比赛 worker CI、审核或正式发布已完成。版本级配置与测试证据见各版本目录。

上游：[gmarcais/Quorum](https://github.com/gmarcais/Quorum)。
