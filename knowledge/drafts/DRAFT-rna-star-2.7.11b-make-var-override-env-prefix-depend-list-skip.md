# DRAFT-rna-star-2.7.11b-make-var-override-env-prefix-depend-list-skip
> OHOS 大源码 Makefile 构建：命令行变量覆盖 target-specific 赋值致链接标志丢失时改用 env 前缀注入，并用 make -o 跳过超高 fork 的依赖生成规则

## 问题特征（真实日志片段/标记）

真机 `conan create` 在 compile 阶段先后暴露两类构建期失败。

链接期（htslib 符号未定义）：


ld.lld: error: undefined symbol: bgzf_open
ld.lld: error: undefined symbol: bgzf_close
ld.lld: error: undefined symbol: bgzf_flush
ld.lld: error: undefined symbol: bam_init1
ld.lld: error: undefined symbol: bam_aux_get


注意此时 `htslib/libhts.a` 已成功构建（`ranlib libhts.a` 通过），即归档存在但链接命令行没有引用它。

更早一轮还有编译期缺头路径的同源症状：


./cram/cram.h:53:10: fatal error: 'cram/sam_header.h' file not found
1 error generated.


依赖生成期（fork 耗尽）：


Makefile:138: Depend.list: No such file or directory
clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable
make: *** [Makefile:138: Depend.list] Error 1


`Depend.list` 阶段失败时 `.o` 编译尚未开始，属构建系统语义失败，非源码/API 不兼容。

## 根因

两个互相独立但同属 GNU Make 语义的内核：

1. **命令行变量压过 target-specific 赋值，链接/编译标志被整条丢弃。**
   GNU Make 规定命令行变量（`make VAR=value`）的优先级高于 Makefile 内任何赋值，包括 target-specific 赋值与 `+=` 追加。上游 STAR Makefile 用
   `STAR: LDFLAGS := $(LDFLAGSextra) $(LDFLAGS_shared) $(LDFLAGS)`
   把 `-Lhtslib -Bstatic -lhts -Bdynamic -lz` 并入链接；内嵌 htslib 子 Makefile 用 `CPPFLAGS += -I. -DSAMTOOLS=1` 追加头路径。配方若把 `LDFLAGS`/`CPPFLAGS` 作为 make 命令行变量传入，这两处赋值被整条忽略——链接只保留配方 LDFLAGS、缺 `-lhts`，于是 bgzf_*/bam_* 全未定义；`CPPFLAGS` 缺 `-I.`，于是 hts.o 找不到 `cram/sam_header.h`。

2. **单条 `-MM` 依赖清单规则 fork 数超高，OHOS worker 进程资源耗尽。**
   上游 `Depend.list` 规则把约 190 个源文件一次性喂给一条 `clang++ -MM`，clang 为每个输入 fork 一个 `-cc1` 子进程；OHOS worker 进程数受限，`posix_spawn` 返回 `Resource temporarily unavailable`，clang 非零退出、make 删除半写目标，随后 `include Depend.list` 报 `No such file or directory`。

## 修复方案（rec）

1. 在 `archives/r/rna-star/2.7.11b/conanfile.py` 的 `build()` 中，把 `CPPFLAGS`/`LDFLAGS` 从 make 命令行参数改为**环境变量前缀**注入：
   `CPPFLAGS="<zlib_inc>" LDFLAGS="<zlib_lib>" make -j1 -o Depend.list htslib all`。
   环境变量不参与命令行变量优先级，target-specific 赋值与子 Makefile 的 `+=` 均能正常生效。
2. 在同一 make 调用加 `-o Depend.list`，把该超高 fork 的依赖清单规则标记为“已最新”以整体跳过，避开 `posix_spawn failed: Resource temporarily unavailable`。
3. 由于 `Depend.list` 原也是内嵌 htslib 的唯一触发点，跳过它后在目标列表中显式补回 `htslib`，保证 `libhts.a` 仍在链接前构建。
4. 用官方 2.7.11b 源码本地复现：命令行变量形式精确复现 `cram/sam_header.h` 找不到；env 前缀形式下 `libhts.a` 与 STAR 均构建成功，`STAR --version` 输出 `2.7.11b`。
5. 在 `notes.md` 记录本轮根因与改动，保持工作树未提交，等待 HMBS 复跑真机预检后统一提交。

关键改动点（配方片段语义）：

python
self.run('CPPFLAGS="-I%s" LDFLAGS="-L%s" make -j1 -o Depend.list htslib all' % (...), cwd=src)


## 禁止策略

- 禁止继续用 `make LDFLAGS=... CPPFLAGS=...` 命令行变量形式传递构建标志：它会静默丢弃上游 target-specific 赋值与 `+=`，症状即 `undefined symbol: bgzf_*/bam_*` 或 `fatal error: 'cram/sam_header.h' file not found`。
- 禁止用“直接改上游 Makefile 删掉 target-specific 赋值”的粗暴做法绕过优先级问题；应优先用 env 前缀注入保留上游语义。
- 禁止在未处理 `Depend.list` 高 fork 规则的情况下反复重跑同一命令期待通过。

## 与相近条目的边界（查重）

- 既有 E678/E692/E737/12592/13532/14257 针对 `configure`/`config.status`/autotools 三元组，属配置期失败；本条是**构建期 make 变量优先级与依赖生成 fork 耗尽**，无实质重叠。
- 机械命中表与修复轮命中均为平台能力样板或 autotools 三元组/归档闭包等异因条目，没有一条描述 make 变量优先级或依赖生成 fork 耗尽，属相邻不相同。
- 本条通类内核可复用于任意 make/autotools 大源码项目：只要 Makefile 对标志做 target-specific 赋值，或依赖清单由单条 `-MM` 全量扫描生成，即适用。

## 适用判断

满足以下任一即可套用：

- 上游 Makefile 对 `LDFLAGS`/`CPPFLAGS`/`CXXFLAGS` 做 target-specific 赋值或 `+=` 追加，而配方以命令行变量注入同名变量；
- 链接报第三方静态库符号未定义（如 htslib 的 bgzf_*/bam_*），但对应 `.a` 已构建成功；
- 依赖清单规则用单条 `-MM`/`-M` 扫描全部源文件，在受限进程数的 OHOS worker 上触发 `posix_spawn failed: Resource temporarily unavailable`。

满足时优先采用 env 前缀注入 + `make -o <depend_target>` 跳过依赖生成，并显式补回被该规则带起的子目标。
