# vcf-split

## 简介

vcf-split 将多样本（combined-sample）VCF 流拆分为单样本 VCF 文件。它以单次扫描输入的方式同时生成成千上万个单样本输出文件，因此适用于超大规模队列数据（例如 TOPMed 单条染色体含 137,977 个样本）——逐个样本抽取或让大量并行读者读取同一文件都不现实。

上游仓库：<https://github.com/auerlab/vcf-split>

## OHOS 适配

- 上游使用自带的 Makefile 模板构建单个命令行程序 `vcf-split`，产物安装到 `bin/`。
- 依赖 `biolibc/0.2.7` 和 `libxtend/0.2.1`，二者均已适配并发布到制品仓。
- 上游 `Makefile.depend` 硬编码了 `../local/include/...` 依赖路径（其同级目录开发工作流所致），源码包在 Conan 隔离构建目录下无法满足，补丁 `0001-Makefile.depend.patch` 将依赖行收敛为源码文件本身；依赖的 include/lib 位置由配方注入。
- 上游 `version.sh` 在构建期通过 `git describe` 推导版本号，而源码包不含 `.git`；配方显式传入 `VERSION` 宏，取值 `0.1.5-10`（即上游 `git describe` 的 `0.1.5-10-g0f2fd0a` 去掉提交号）。
- OHOS 下 `strlcpy`/`strlcat` 由 `libxtend` 的 `cpp_info.defines` 映射到 `xt_strlcpy`/`xt_strlcat`，无需额外处理。
- OHOS 可执行文件在 `build()` 与 `package()` 阶段使用 `binary-sign-tool` 签名。
- 仅 1 个补丁且不含任何平台宏；`vcf-split.c` 在 OHOS/aarch64 + clang 15 上零改动编译通过。

## 依赖

- biolibc/0.2.7
- libxtend/0.2.1

## 功能验证

- 构建期执行上游 `Test/test.sh` 中可无人值守的断言部分：运行两次拆分（全字段 + `--fields chrom,pos,ref,alt,format` 限定字段），并与上游登记的 22 个期望 fixture 逐一 `diff` 比对。
- `test_package` 从安装后的包中运行 `vcf-split --version`，并用包内 `share/vcf-split/Test` 的 fixture 重放上述拆分，验证消费端可用性。
