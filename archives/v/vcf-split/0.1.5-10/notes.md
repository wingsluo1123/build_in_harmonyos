# vcf-split 0.1.5-10 适配笔记

## 编译环境

- 构建系统: makefile（上游自带单文件程序 Makefile 模板，非 autotools/cmake/meson）
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4（OHOS SDK `ohos-sdk_26.0.0.18`，sysroot `aarch64-linux-ohos`）
- 目标平台: OHOS / aarch64（原生构建，非交叉编译）
- 状态: built（编译与测试全部通过，尚未上传制品仓）

## 编译步骤

1. `source()`：从 `https://codeload.github.com/auerlab/vcf-split/tar.gz/0f2fd0a` 下载并 `strip_root` 解压。
   - 上游 tag 为 `0.1.5`，本包对应 `git describe` 结果 `0.1.5-10-g0f2fd0a`，即 tag 之后第 10 个提交 `0f2fd0a`。
2. `generate()`：`VirtualBuildEnv` + 把 `TMP`/`TEMP`/`TMPDIR` 指向 `build_folder/tmp`（R10：鸿蒙 `/tmp` 只读）。
3. `build()`：
   - 先应用补丁 `patches/0001-Makefile.depend.patch`（见下"问题 1"）。
   - 从 `self.dependencies["biolibc"|"libxtend"].cpp_info` 取 `includedirs` / `libdirs` / `libs` / `defines`，拼成 `-isystem` / `-L` / `-l` 参数（R33：不裸用 `${CC}`/`${CFLAGS}`，编译器路径取自 `tools.build:compiler_executables`）。
   - `make -j1 CC=... LD=... CFLAGS=... LDFLAGS=... vcf-split`
   - OHOS 下用 `binary-sign-tool` 签名产物。
   - 运行上游 `Test/test.sh` 中可无人值守的断言部分（见"验证结果"）。
4. `package()`：安装 `bin/vcf-split`、`share/man/man1/vcf-split.1`、`licenses/LICENSE`、`share/doc/vcf-split/README.md`，以及 `share/vcf-split/Test/` 下的 `test.vcf` + 22 个 `correct-*.vcf` fixture（供 test_package 消费）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make: *** No rule to make target '../local/include/xtend/dsv.h'` | 上游随源码提交的 `Makefile.depend` 硬编码了 `../local/include/...` 依赖路径，源自其"同级目录共同安装到 `../local`"的开发工作流；Conan 构建目录下该路径不存在 | 补丁 `patches/0001-Makefile.depend.patch` 把该依赖行收敛为 `vcf-split.o: vcf-split.c vcf-split.h vcf-split-protos.h`，不再引用 `../local`；依赖的 include/lib 位置由配方在 `CFLAGS`/`LDFLAGS` 中注入 |
| 2 | `version.sh` 输出 `Unknown-version` | 上游 `version.sh` 在构建期执行 `git describe --tags`，而 Conan 从源码包构建，目录内无 `.git` | 配方显式传入 `-DVERSION='"0.1.5-10"'`，取值即上游 `git describe` 的 `0.1.5-10-g0f2fd0a` 去掉提交号 |
| 3 | 上游 `Test/test.sh` 无法无人值守执行 | 脚本 `#!/bin/sh` 却使用 bashism `local`，且内嵌交互式 `pause()`（`read junk`）等待回车；脚本开头还调用 `./cave-man-install.sh` 安装到 `../local` | 配方与 test_package 只重放其断言主体（两次拆分调用 + 22 项 `diff` 比对），交互式 `pause()` 与 `wc -l` 诊断横幅不计入自动化断言，已在 `test_package/MANIFEST.yml` 的 `not_run_upstream_tests` 中如实申报 |
| 4 | `strlcpy`/`strlcat` 在 OHOS/musl 下不可用 | bionic/musl 不提供 BSD 的 `strlcpy`/`strlcat` | 无需补丁：`libxtend/0.2.1` 的 `cpp_info.defines` 在 OHOS 下已声明 `strlcpy=xt_strlcpy`、`strlcat=xt_strlcat`，配方的 `_dependency_flags()` 会自动收集这些 `defines` |

## 源码修改

仅一处补丁，不涉及任何 C 源码改动：

- `patches/0001-Makefile.depend.patch`（`patch_type: portability`）
  - 修改对象：`Makefile.depend`（上游随源码提交的依赖文件，非生成物）
  - 修改内容：删除 `../local/include/xtend/dsv.h ../local/include/biolibc/vcf.h ../local/include/biolibc/sam.h ../local/include/biolibc/biolibc.h` 四行依赖引用，只保留 `vcf-split.c vcf-split.h vcf-split-protos.h`
  - 原因：上游该文件为其"同级目录共享 `../local`"的开发工作流写死了路径，在 Conan 隔离构建目录下这些目标不存在，`make` 直接报 `No rule to make target`。依赖的头文件位置改由配方通过 `-isystem` 注入。
  - 补丁不含任何平台宏（不违反 R8 / preflight PF5）。

`vcf-split.c` 本身在 OHOS/aarch64 + clang 15 下零改动编译通过。

关于 `sysexits.h`：`vcf-split.c` 直接 `#include <sysexits.h>`，该头文件由 OHOS SDK sysroot 提供
（`.../ohos-sdk_26.0.0.18/ohos/native/llvm/sysroot/usr/include/sysexits.h`），因此本包不需要像同族
`ad2vcf` 那样在 `generate()` 中生成兼容头。

## 依赖版本

- biolibc/0.2.7
- libxtend/0.2.1

两者均已适配并发布到 `ohpcd` 制品仓，实测 `conan install --requires=<dep> --build=never` 直接命中预编译包。

## 验证结果

构建期上游测试回放（`build()` 内）：

```bash
cd Test
../vcf-split test-all-fields- 1 11 < test.vcf
../vcf-split --fields chrom,pos,ref,alt,format test-limited-fields- 1 11 < test.vcf
for col in 1 2 3 4 5 6 7 8 9 10 11; do
    diff correct-all-fields-$col.vcf test-all-fields-$col.vcf
    diff correct-limited-fields-$col.vcf test-limited-fields-$col.vcf
done
```

上游测试清点（R51 三步法）：

- 上游测试套件为 `Test/test.sh`：2 次 `vcf-split` 调用，产出 22 个单样本 VCF，与 22 个登记期望文件比对 → **22/22 通过**。
- 未执行项（已申报，非失败）：`pause()` 交互提示与 `wc -l` 诊断横幅（不断言任何内容）；
  `Tools/run-test.sbatch`（SLURM 批处理，依赖 bcftools 与 13.7 万样本 TOPMed 数据）；
  `Bench/*`（对照 bcftools/vcftools 的性能基准，非正确性测试）。

消费者测试（`test_package`）：三个独立脚本全部从**安装后的包**出发运行，共 **78/78 项断言通过**。

1. `test_vcf_split.py`（23 项断言）—— 运行 `vcf-split --version`，并用包内 fixture 重放两次拆分、逐一比对 22 个期望文件。
2. `test_vcf_split_workflow.py`（48 项断言，**完整消费者端到端用例**）—— 在 OHOS/aarch64 上真实跑通 3 条工作流，共产出 22 个单样本 VCF：
   - **全量拆分**：11 样本 VCF → 11 个单样本文件，逐一断言每个输出恰好 1 个样本列（列名 `SAMPLE`）、10 条记录、且 CHROM/POS/REF/ALT 与多样本输入逐条一致；
   - **字段投影**：`--fields chrom,pos,ref,alt,format` 丢弃 INFO 列（断言为 `.`）且仍保留单样本列；
   - **提前终止**：`--max-calls 3` 使全部 11 个输出各恰好 3 条记录。
3. `test_ohos_binary.py`（7 项断言，**鸿蒙平台特性**）—— 纯 Python 解析 ELF（不依赖 `readelf`），断言产物为 AArch64、`ET_DYN`（PIE 可执行）、含 `.note.ohos.ident`（OHOS 标识段）、`GNU_STACK` 不可执行（NX）、含 `PT_GNU_RELRO` 且 `DT_FLAGS` 置 `DF_BIND_NOW`（完整 RELRO）、`DT_FLAGS_1` 置 `DF_1_PIE`。

> 说明：`--max-calls` 的语义（"stops after N calls"）与 `--fields` 丢弃 INFO 的行为均在写入断言前经实测确认，未凭文档推断。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/vcf-split` | 命令行程序（OHOS 已签名） |
| `share/man/man1/vcf-split.1` | 手册页 |
| `share/doc/vcf-split/README.md` | 上游 README |
| `share/vcf-split/Test/` | 上游 fixture（`test.vcf` + 22 个 `correct-*.vcf`） |
| `licenses/LICENSE` | BSD-2-Clause |

## 注意事项

- `0.1.5-10` 为上游 `git describe` 形态的版本号（tag `0.1.5` 之后第 10 个提交），并非上游 tag；
  上游 FreeBSD/NetBSD ports 对该快照归一化为 `0.1.5.10`，本包按 Conan 版本号与任务分支保持 `0.1.5-10` 形态。
- 产物安全属性由 OHOS SDK 的 clang 15 默认提供，无需显式 `-fPIE`/`-pie`：实测产物为
  `DYN (Position-Independent Executable file)`，动态段含 `BIND_NOW` 与 `PIE`，`GNU_STACK` 为 `RW`（NX）。
---

**编译结束**: 2026-10-15 01:09
**最终状态**: built（编译与测试全部通过；尚未 upload 到制品仓，按 R29 不标 published）
