# rna-star 2.7.11b 适配笔记

## 编译环境
- 构建系统: makefile（source/ 下 GNU Makefile，无 configure、无 install 目标）
- 编译日期: 2026-10-12
- 编译器: clang++ / clang（hnp 工具链，clang 15，libc++）
- 目标: HarmonyOS PC aarch64
- 状态: built

## 编译步骤

```bash
CPPFLAGS="<zlib -I>" make -j1 all \
  SHELL=<hnp bash> \
  CC=<clang> CXX=<clang++> \
  CXXFLAGS="-O3 -std=c++17 -stdlib=libc++ -fopenmp -static-openmp -Wall \
             -D'COMPILATION_TIME_PLACE="harmonyos"' -D'GIT_BRANCH_COMMIT_DIFF="none"'" \
  CFLAGS="-O3" \
  LDFLAGS="<stdlib> <zlib -L>" \
  CXXFLAGS_SIMD=
```

先由 build() 用 Python 预生成 `parametersDefault.xxd`（vim-xxd 契约），再执行 make。
产物为 `source/STAR`，package() 拷入 `bin/` 并做 ELF 自签。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS `/usr/bin/xxd` 是 toybox，`xxd -i` 只输出裸 hex 体，缺 `unsigned char parametersDefault[]` 声明与 `parametersDefault_len` 变量 | 上游 `parametersDefault.xxd: xxd -i parametersDefault` 依赖 vim-xxd 的输出契约；STAR.cpp / Parameters.cpp 都 `#include "parametersDefault.xxd"` 并引用这两个符号；toybox 输出导致编译 undefined。metaeuk 同款坑 | build() 预生成符合 vim-xxd 契约的 `parametersDefault.xxd`（先于 make 落盘且 mtime 比 parametersDefault 新，make 视其最新不再触发玩具 xxd 规则） |
| 2 | `-std=c++11` 在 OHOS 上编译失败（nullptr_t / __abi_tag__ / constexpr 错误） | E130：OHOS 自定义 libc++-ohos 头要求 C++17 最低 | 命令行传 `-std=c++17`（.o 规则用裸 `$(CXXFLAGS)`，覆盖上游 `?=-pipe -Wall -Wextra`；STAR 目标与 opal 规则 `-std=c++17` 均最后出现胜出） |
| 3 | `register` 存储类在 C++17 被移除，SuffixArrayFuns.cpp 7 处 `register <type> var` 硬错误 | 上游 C++11 代码 | 补丁 `0001-remove-register-keyword-cxx17.patch` 移除全部 `register`（纯 portability，无平台宏） |
| 4 | 链接动态 libomp 后 CLI 启动报 `Error loading shared library libomp.so` | clang 交叉编译默认把 RUNPATH 写宿主 resource dir，OHOS 镜像不含 libomp.so；spaced 同款坑 | 链接给 `-fopenmp -static-openmp` 让 libomp 静态并入，生成自包含二进制 |
| 5 | `-mavx2` 在 aarch64 上直接报 unknown target | 上游 `CXXFLAGS_SIMD ?= -mavx2` 是 x86 专属 | 命令行传 `CXXFLAGS_SIMD=` 清空；opal 用 simde_avx2.h（SIMDe）在 aarch64 软件兜底，无需改 SIMDe 代码 |
| 6 | 可执行 ELF 需 `.codesign` 段，否则 OHOS 内核拒绝执行（Operation not permitted） | E077/E082：OHOS 要求 ELF 带有效签名 | package() 用 binary-sign-tool 自签（先 llvm-objcopy 移除旧签名再 sign），工具缺失则跳过（preflight worker 缺件场景容错） |
| 7 | 内嵌 htslib 静态构建需要 zlib.h 与 `-lz` | source/htslib 多个 .c 文件 include zlib.h，Makefile 链接 `-lz` | 声明 conan 依赖 zlib/1.3.1.1，注入 zlib include/lib 到 CPPFLAGS/LDFLAGS |
| 8 | 真机预检 apply_conandata_patches 报 `Failed to apply patch: .../patches/0001-remove-register-keyword-cxx17.patch` | 补丁路径写的是 `a/SuffixArrayFuns.cpp` / `b/SuffixArrayFuns.cpp`，但源码根目录（source_folder，strip_root 后即 STAR-2.7.11b 根）下没有该文件——`SuffixArrayFuns.cpp` 实际位于 `source/SuffixArrayFuns.cpp`；Conan `apply_conandata_patches` 以 `-p1` 从 source_folder 应用全部补丁，找不到目标文件即失败 | 把补丁内所有文件路径前缀改为 `a/source/SuffixArrayFuns.cpp` / `b/source/SuffixArrayFuns.cpp`，与源码树相对位置一致；`patch -p1 --dry-run` 在源码根验证干净应用，真实打补丁后确认 7 处 `register` 全部移除 |
| 9 | 真机预检 `_gen_parameters_default_xxd` 报 `OSError: parametersDefault not found at .../s/parametersDefault` | STAR 上游把 all 可构建源码（Makefile / *.cpp / parametersDefault / htslib）放仓库 `source/` 子目录；配方把所有 build/打包路径都指向 `self.source_folder` 根（缺 `source/` 前缀），故找不到参数文件、make 也找不到 Makefile | 新增 `_star_src_dir()` 返回 `<source_folder>/source`；parametersDefault 生成（读写）、`make` 的 `cwd`、`package()` 拷 STAR 全部改用该子目录；LICENSE/README 仍在 source_folder 根，保留不动 |
| 10 | 真机/本地编译 `.o` 阶段报 `COMPILATION_TIME_PLACE was not declared` / `GIT_BRANCH_COMMIT_DIFF was not declared` | 上游 Makefile 把这两个信息宏放 `CXXFLAGS_common`，只在链接目标（STAR）应用；`.o` 编译规则是裸 `$(CXXFLAGS)` 从不带 `CXXFLAGS_common`，故 STAR.cpp / Parameters.cpp 在 `.o` 阶段未声明这两个宏（与 `-std`/`-fopenmp` 无关，任何平台都会命中） | 在配方 `CXXFLAGS` 里补 `-D'COMPILATION_TIME_PLACE="harmonyos"'` 与 `-D'GIT_BRANCH_COMMIT_DIFF="none"'`（纯信息输出，固定值即可）；本地 `make -j1 STAR` 全量构建通过并产出可运行 STAR（--version 输出 2.7.11b） |
| 11 | htslib 子构建报 `cram/cram.h:53: fatal error: 'cram/sam_header.h' file not found` | STAR 顶层 make 以 `$(MAKE) -C htslib lib-static` 递归构建内嵌 htslib，其 Makefile 用 `CPPFLAGS += -I. -DSAMTOOLS=1` 补自己的头路径；但此前配方把 zlib 的 `CPPFLAGS=<zlib_inc>` 作为 make **命令行变量**传入，GNU Make 会忽略子 makefile 对命令行变量的 `+=`，导致 htslib 编译缺 `-I.`，`#include "cram/sam_header.h"` 找不到头，与 -std/-fopenmp 无关 | 改为 `CPPFLAGS="<zlib_inc>" make ...` 的 **env 前缀**形式（环境变量，非 make 命令行变量），子 makefile 的 `+=` 正常叠加，得到 `<zlib_inc> -I. -DSAMTOOLS=1`；本地复现（命令行变量形式报同样错误、env 形式 libhts.a 构建通过）并全量 make 产出可运行 STAR（--version 输出 2.7.11b） |
| 12 | 真机预检 `.o` 编译报 `use of undeclared identifier 'harmonyos'`（`#define COMPILATION_TIME_PLACE harmonyos`，引号被剥） | 第 10 行用 `CXXFLAGS="-D'COMPILATION_TIME_PLACE=\"harmonyos\"'"` 传字符串宏；该值是 make **命令行变量**，值里含单/双引号，经外层 self.run 命令串与 make→shell 的引号层层嵌套后，真机 bash 把内层双引号剥掉，clang 实际收到 `-DCOMPILATION_TIME_PLACE=harmonyos`（裸标识符），源码当字符串字面量引用即报 undeclared。本地手敲因引号逐层手动转义恰好成立，真机走完整链则破坏 | 弃用 `-D'NAME="value"'` 字符串宏，改为 build() 预生成 force-include 头 `.hmbs_compilation_info.h`（`#define COMPILATION_TIME_PLACE "harmonyos"` / `GIT_BRANCH_COMMIT_DIFF "none"`），用 `-include <abs path>` 注入 CXXFLAGS；绝对路径无空格无引号，经 make→bash 传递不会丢内容 |
| 13 | 真机预检 `SharedMemory.o` 编译报 `error: unknown type name 'key_t'`（SharedMemory.h:142/160/161 与 SharedMemory.cpp:22） | `key_t` 是 POSIX 类型，定义于 `<sys/types.h>`；上游 `SharedMemory.h` 类声明直接用 `key_t` 但自身只 include `<string>/<semaphore.h>/<unistd.h>/<exception>/<iostream>`，`SharedMemory.cpp` 又是在 `#include "SharedMemory.h"` **之后**才 include `<sys/types.h>`。glibc 靠头文件传递包含把 `key_t` 带进来；OHOS（musl 系 libc）不做传递包含，故头文件非自包含、`key_t` 未声明（librope `ssize_t` 同款平台头文件传递性差异） | 新增补丁 0002：在 `SharedMemory.h` 的 include 区顶部显式加 `#include <sys/types.h>`（纯 POSIX 头、无平台宏，符合 R8 补丁规范；librope DRAFT 同款最小补丁法） |
| 14 | 真机预检 `apply_conandata_patches` 报 `Failed to apply patch: .../0002-...patch: source file is different - b'source/SharedMemory.h', actual: b''` | 补丁 0002 首个版本的 hunk 头 `@@ -7,6` 与源码真实行号不符（实际 `#ifndef` 在第 5 行、`#define` 在第 6 行，且其后有**两个**空行；我误按 7/8 行 + 单个空行写上下文）。GNU patch 能按 offset -2 自动偏移套用，但 Conan 的 `apply_conandata_patches` 用纯 Python `patch` 库、默认不做偏移匹配，上下文对不上即报 `source file is different`/`actual: b''` 而失败 | 用 `diff -u` 对官方源码生成精确 hunk（`@@ -6,6 +6,7 @@`），补丁在 GNU patch 与 Python `patch` 库（Conan 同款）上都以 offset 0 干净应用；教训：手写补丁必须保证 hunk 行号与源码逐行一致、无 offset，兼容 Conan 严格校验 |
| 15 | 真机预检链接阶段报大量未定义：`bgzf_flush` / `bam_init1` / `bam_aux_get` / `bgzf_dopen` 等（`ld.lld: error: undefined symbol ...`），全是 htslib 符号；`ranlib libhts.a` 明明成功 | 上游 Makefile 靠 **target-specific 赋值**把 htslib 并入链接：`STAR: LDFLAGS := $(LDFLAGSextra) $(LDFLAGS_shared) $(LDFLAGS)`，其中 `LDFLAGS_shared := -pthread -Lhtslib -Bstatic -lhts -Bdynamic -lz`。但本配方此前把 `LDFLAGS=<stdlib> -L<zlib>` 作为 **make 命令行变量**传入；GNU Make 规定「target-specific 变量值不覆盖命令行变量」，整条 target-specific 赋值被丢弃，链接只剩配方 LDFLAGS、缺 `-Lhtslib -lhts`，从而 htslib/BAM 符号全未定义。本地复现：命令行变量传 LDFLAGS 时链接行只有 `... -L<zlib>`、报同样未定义；env 前缀传 LDFLAGS 时链接行变为 `... -pthread -Lhtslib -Bstatic -lhts -Bdynamic -lz -L<zlib>` 正常 | 配方 build() 把 `LDFLAGS="..."` 从 make 命令行参数改为 **env 前缀**（`CPPFLAGS="..." LDFLAGS="..." make ...`），与 CPPFLAGS 同款；env 值可被 target-specific 赋值正常覆盖，链接保留 `LDFLAGS_shared` 又追加 zlib `-L`/`-stdlib=libc++`。已本地复现两种传法的链接命令差异 |
| 16 | 真机预检判定 incomplete：`缺少 test_package 真实用例计数和机器测试证据` | 真机 conan create 的 test_package 段能真实运行 `test_rna_star.sh` 并打印 `PASS: STAR --version...`、`PASS: STAR --help...`、`ALL TESTS PASSED`，但**脚本从不输出 hmbs 要求的 `HMBS_TEST_PACKAGE_RESULT={...}` 单行机器证据标记**（缺 discovered/passedCount 计数），被 hmbs 判定 incomplete 拒绝放行。上游 no_tests 也缺 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",...}` 复发标记 | 重构 `test_rna_star.sh`：显式 `TOTAL=2` / `PASSED` 计数变量（仅在 grep 匹配真实输出时 `PASSED+=1`，非对 stdout 字符串数数），任一用例失败调用 `fail_test()` 打印 `passed:false` 标记并 exit 1，全部通过后在末尾打印单行独立 JSON `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test_rna_star.sh","discovered":2,"passedCount":2}`；`test_package/conanfile.py` 的真实 test() 运行后再用 `json.dumps` 复发行 `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","discovered":0,...}`（reason 引用 MANIFEST.yml 审计结论） |
| 17 | CI #88193 编译失败：`Makefile:138: Depend.list: No such file or directory` / `make: *** [Makefile:137: Depend.list] Error 1`，日志中该规则内出现 160 行 `clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable` | 上游 Makefile 的头文件依赖规则把全部 ~190 个源文件一次性喂给单条 `$(CXX) $(CXXFLAGS_common) -MM $^ >> Depend.list`（规则行 `Depend.list: $(SOURCES) parametersDefault.xxd htslib`）。clang 多输入时对每个源文件 fork 一个 `-cc1` 子进程；真机 worker 进程/内存受限，成批 `posix_spawn` 返回 EAGAIN，clang 报错退出 → 规则失败 → make 删除半成品 Depend.list → 紧接着 `include Depend.list` 找不到文件即 `Error 1`。**不是源码/API 兼容问题**（.o 尚未开始编译），也非 htslib 错误（日志显示 `ranlib libhts.a` 已成功） | Depend.list 仅服务增量重编译，全新构建不需要它。`make` 命令改为 `make -j1 -o Depend.list htslib all`：`-o Depend.list` 让 make 把该目标视为「已最新、禁止重建」，GNU make 对缺失但可重建的 include 文件在有 `-o` 时静默跳过、不报错，从而绕开这条高 fork 规则；因 Depend.list 同时是 htslib 的唯一触发点（`Depend.list: ... htslib`），跳过它后 htslib 不会自动构建、链接会缺 `-lhts`，故显式追加 `htslib` 目标先建 libhts.a。本地对官方 2.7.11b Makefile 复现：缺失 Depend.list 时 `make -o Depend.list htslib all` 干净通过并产出可运行 STAR（--version=2.7.11b），`-MM` 规则完全未触发 |
| 18 | CI #91281 编译失败：`/system/bin/sh: .../conanbuildenv-release-armv8.sh[13]: can't fork - try again`，随后 `Error in build() method, line 228 self.run(...)`；同一构建日志里 CI 自身脚本也报 `knowledge_check.sh: fork: retry: Resource temporarily unavailable` | conan 默认（`tools.env:deactivation_mode` 未设）在聚合环境脚本 `conanbuildenv-<id>.sh` 顶部生成一段 **source 时立即执行** 的反激活前导块：`for v in LD_LIBRARY_PATH PATH SHELL CONFIG_SHELL; do value=$(printenv $v) ...; done`。该块仅为生成配方从不使用的 `deactivate_*.sh`，却要在 `. conanbuildenv-*.sh` 时对每个变量 fork 一次 `printenv` 与命令替换子 shell；真机 worker 进程资源紧张，mksh 执行到循环末尾（脚本第 13 行 `done`）即返回 EAGAIN。**失败发生在 conan 环境脚本激活阶段，早于 make 任何一次编译**（第 17 轮的 `-o Depend.list` 只消除了 make 内 `-MM` 规则的 fork，管不到 conan 自身的 env 前导块）；日志同批出现 CI 脚本 fork 报错，属 fork 压力而非源码不兼容 | 在配方新增 `generate()`：`self.conf.define("tools.env:deactivation_mode", "function")`，把前导块改为只**定义**一个反激活函数（source 时不执行、零 fork），仍完整导出 `LD_LIBRARY_PATH/PATH/SHELL/CONFIG_SHELL`（lld 依赖 LD_LIBRARY_PATH 找 libxml2.so.16，故不能用 `env=None` 跳过整个 env 文件）。`generate()` 在 conan 自动生成 VirtualBuildEnv 之前运行，conf 生效。本地同源 conan 2.29.1 `conan create` 复现：默认形态脚本第 2-13 行含 `printenv`；改后脚本改为 `deactivate_...() { ... }` 函数、`printenv` 计数为 0，`self.run(env="conanbuild")` 正常执行 |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| `patches/0001-remove-register-keyword-cxx17.patch` | 移除 SuffixArrayFuns.cpp 中 7 处 C++17 已移除的 `register` 存储类关键字 |
| `patches/0002-add-sys-types-h-for-key_t.patch` | SharedMemory.h 顶部显式 `#include <sys/types.h>`，使 `key_t` 在头文件内自包含（OHOS musl 无 glibc 式传递包含） |

（`parametersDefault.xxd` 为 build() 生成物，不落在 patches/。）

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.1.1 | 内嵌 htslib 静态构建需要 zlib.h + `-lz` |

## 源码下载
- conandata.yml 的 source url 改为有序列表：`gh-proxy.com` 镜像优先，官方 `github.com` 保留末尾作回退（与 ci/conan/build_and_test.sh 的 get_mirrors GitHub 映射一致）。
- sha256 校验不变（各镜像提供同一归档）。

## 验证结果

- 上游测试套件：不存在（STAR 无正式测试；upstream_test_total=0，见 test_package/MANIFEST.yml 审计）。
- test_package 消费测试（真实执行编译产物）：
  - `STAR --version` → exit 0，输出 `2.7.11b`
  - `STAR --help` → exit 0，输出 `STAR version=2.7.11b`

```bash
STAR --version   # 2.7.11b
STAR --help | head   # STAR version=2.7.11b ...
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/STAR` | RNA-seq 剪接比对可执行文件（静态链入 htslib/libomp，动态链 zlib） |
| `licenses/LICENSE*` / `README*` | 上游许可证与说明 |

## 注意事项

- 默认构建的共享内存路径（SharedMemory.cpp）使用 SysV shm，仅在 `--genomeDir`/`--readFilesIn` 实际比对运行阶段走；本次消费测试仅做 `--version`/`--help` 冒烟，不触发该路径。完整比对工作流属运行时行为，不在 CI 冒烟范围内。
- STAR `--version` 无独立分支，是由 Parameters::inputParameters 在扫描命令行参数时命中 `--version` 打印并 exit 0；L2 冒烟门禁 `STAR --version` 可过（无需依赖 `--help` 兜底，但 `--help` 同样 exit 0 可作备选）。
