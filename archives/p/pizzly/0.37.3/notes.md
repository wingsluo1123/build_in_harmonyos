# pizzly 0.37.3 适配笔记

## 概述

pizzly 是 RNA-Seq 融合基因（gene fusion）检出工具：读取 kallisto（`--fusion`，0.43.1 及以上）
输出的候选融合位点，做假阳性过滤、断点级转录本组装与融合丰度定量，产出 `.json` 与
`.fusions.fasta`。上游以 SeqAn 2 实现（仓库内 vendored `seqan/`），CMake 构建，唯一外部依赖 zlib。

本包交付 `bin/pizzly` 单可执行文件（`package_type = "application"`）。

## 源码身份

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/pmelsted/pizzly |
| 上游 tag | `v0.37.3` |
| tag 对应 commit | `96368ca642ed72297ac31e99d0fd77227dd23419` |
| 源码归档（官方 tag 归档） | https://github.com/pmelsted/pizzly/archive/refs/tags/v0.37.3.tar.gz |
| SHA-256 | `adfb221ed079aa60760e44af6baa300ad0fbdc92b407f7576cc7eab72ec6b310` |
| 许可证 | BSD-2-Clause |

语言预检（R47）：`ohc-run.py lang-preflight pizzly 0.37.3 --src <src> --lang cpp` →
`detected_language=cpp`，证据 `build_system=cmake`、`manifest=CMakeLists.txt`、
`source_stats=源文件 5 个（cpp:3, python:2），主体占比 60%`。主体为 C++（`main.cpp` +
`FilterFusions.hpp` + `GeneModel.hpp` + `common.h`，共 1765 行），`scripts/*.py` 是辅助脚本，
`seqan/` 是 vendored 头文件库。

## 编译环境

- 设备：HarmonyOS PC（HAD-W32），HongMeng Kernel 1.12.0，aarch64
- 构建模式：**原生构建**，`-pr:h=ohos-aarch64 -pr:b=ohos-aarch64`（build == host == OHOS/aarch64）
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang++`），libc++
- Conan：2.29.1（OHOS 适配版）
- CMake：4.1.2，Ninja
- 构建日期：2026-10-15

## 依赖

| 依赖 | 类型 | 核查方式与结论 |
|---|---|---|
| zlib/1.3.1 | 必需（SeqAn gzip 支持） | W0：`conan download zlib/1.3.1 -r=ohpcd --only-recipe` 成功；`conan install --requires=zlib/1.3.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=never` 成功解析预编译 binary（R35：不用 `conan list` 判断 binary） |
| pthread | 系统库 | OHOS / musl 提供，上游 `target_link_libraries(pizzly pthread ...)` 直接可用 |

系统内不存在同名 zlib（`ls /lib*/libz.so*` 为空），因此 zlib 完全由 Conan 依赖链提供，
不属于 R26 的"系统同名库污染"场景。

## 实际构建命令

```bash
conan create archives/p/pizzly/0.37.3 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

配方内部：`CMakeToolchain` → `cmake.configure()` → `cmake.build()`，然后 `package()` 用
`copy()` 把构建出的 `pizzly` 装到 `<package>/bin`（**不调用** `cmake.install()`，理由见下方问题 #4）。

## 遇到的问题与解决方案

| # | 现象（真实报错） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `CMake Error at CMakeLists.txt:2 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed from CMake.` | 上游声明 `cmake_minimum_required (VERSION 3.0.0)`，CMake 4.1.2 移除了对 <3.5 的兼容 | 配方 `generate()` 设 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，保留上游声明本身不改源码（仓库通用做法） |
| 2 | `error: call to 'empty' is ambiguous`（9 处，`seqan/arg_parse/arg_parse_option.h`、`argument_parser.h`） | profile 默认 `compiler.cppstd=17` 使 libc++ 暴露 `std::empty`（C++17），与 `seqan::empty` 在 `namespace seqan` 内的非限定调用产生二义性；上游 CMakeLists 本就是把工程固定为 `-std=c++14` 的 C++14 项目（vendored SeqAn 2.2.0） | 配方 `configure()` 固定 `self.settings.compiler.cppstd = "14"`，与上游声明一致 |
| 3 | `error: use of undeclared identifier 'aio_read' / 'aio_write' / 'aio_suspend' / 'aio_return' / 'aio_error'`（`seqan/system/file_async.h`） | OHOS 的 `<aio.h>` 只提供 `struct aiocb` 与 `AIO_*`/`LIO_*` 常量，**不声明任何 `aio_*` 函数**；SeqAn 的平台探针 `#if __has_include(<aio.h>)` 只看头文件是否存在，假阳性地把 `SEQAN_ASYNC_IO` 置 1 | 配方 `generate()` 设 `SEQAN_ASYNC_IO=0`（`seqan/platform.h` 的官方能力开关，OpenBSD 等无 AIO 平台走同一分支）。pizzly 自身不使用 SeqAn 异步 IO，所以这是如实声明平台能力，不是 stub 掉功能 |
| 4 | 包体积只有 `licenses/LICENSE`，`bin/pizzly` 缺失（`cmake --install` 输出只有 `-- Install configuration: "Release"` 一行，无任何文件） | 上游 **v0.37.3 的 CMakeLists.txt 没有 `install()` 规则**（`install(TARGETS pizzly DESTINATION bin)` 是上游后续在 master 才补上的），因此 `cmake.install()` 必然产出空包 | 配方 `package()` 按仓库既有做法（bwa 等 98 个配方同款）把构建出的 `pizzly` 从 `self.build_folder` 复制到 `<package>/bin`，不再依赖 `cmake.install()` |

补充说明（探索阶段的排除项，留档以免后人重复走弯路）：早期用手工 `conan install -g CMakeDeps`
探路时，CMakeDeps 会生成 `zlib-config.cmake`（只提供小写 `zlib::zlib` 目标与小写变量，
`CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`），导致上游的 `ZLIB_INCLUDE_DIRS`/`ZLIB_LIBRARIES` 为空、
链接报 `undefined symbol: inflateInit2_`。最终配方**只使用 CMakeToolchain、不引入 CMakeDeps**，
CMakeToolchain 会为依赖注入 `CMAKE_LIBRARY_PATH`/`CMAKE_INCLUDE_PATH`，上游的
`find_package (ZLIB)` 因此走 FindZLIB 模块模式并直接命中 Conan 的 `libz.a`
（实测 configure 输出 `-- Found ZLIB: .../zlib56af09fbb4346/p/lib/libz.a (found version "1.3.1")`，
链接行为 `... main.cpp.obj -o pizzly -lpthread .../libz.a`）。**故本版本不需要任何源码补丁。**

## 源码修改

**无源码补丁**（`conandata.yml` 的 `patches: {}`）。四处适配点全部落在配方侧：

| 适配点 | 配方位置 |
|---|---|
| CMake 4.x 兼容下限 | `generate()` → `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"` |
| C++14（上游声明） | `configure()` → `self.settings.compiler.cppstd = "14"` |
| SeqAn 异步 IO 能力声明 | `generate()` → `tc.preprocessor_definitions["SEQAN_ASYNC_IO"] = "0"` |
| 上游缺 install 规则 | `package()` → `copy(self, "pizzly", src=self.build_folder, dst=<pkg>/bin)` |

未修改任何上游源码、未删除任何跨平台分支、未引入平台宏。

## 上游测试清点（R51 第一步）

**结论：上游没有自动化测试，上游测试用例数 = 0。**

清点证据（对精确源码 `pizzly-0.37.3/` 执行）：

```bash
grep -inE "enable_testing|add_test|ctest|gtest|catch|boost" CMakeLists.txt   # 无输出
grep -rlE "int main" --include=*.cpp --include=*.cc --include=*.c . | grep -v "^./seqan"
#   → 仅 ./main.cpp（不存在测试程序）
find ./test -type f
#   → .gitignore README.md Snakefile reads_1.fastq.gz reads_2.fastq.gz
#     transcripts.fasta.gz transcripts.gtf.gz
```

`test/Snakefile` 是依赖**外部 kallisto** 的 snakemake 示例流水线（`rule all` 需要
`kallisto index` / `kallisto quant`），用于人工验证 kallisto+pizzly 联动，
不注册任何可计数的自动化用例。因此：

| 口径 | 值 |
|---|---|
| 上游 CTest 注册用例 | 0 |
| 上游测试程序 | 0 |
| 上游测试框架（gtest/Catch2/Boost.Test） | 无 |
| `ctest -N` 可列出用例 | 0（无 `enable_testing()`） |

## 消费者端到端验证（规则 12）

被测对象：`conan create` 安装后的 `bin/pizzly`（`conanrun` env 下 PATH 指向 Conan cache 的
package_folder/bin），不使用源码构建目录产物，OHOS 上也不存在同名系统程序。

输入 fixtures 的来源：`fixtures/fusion.txt` 由制品仓预编译的 **kallisto/0.52.0** 对上游
`test/reads_*.fastq.gz`、`test/transcripts.fasta.gz` 执行 `quant --fusion` 真实产出
（与上游 `test/Snakefile` 的 rule index / rule kallisto_quant 参数一致）；参考 GTF/FASTA 为上游
`test/` 原样文件，因是 gzip 数据，按仓库约定以 **base64**（`fixtures/transcripts.*.gz.b64`）承载
——test_package 内不提交裸归档扩展名（先例 `archives/b/blur`、`archives/b/bozohttpd` 的
`test_package/*.b64`），`test_pizzly.sh` 在运行时 `base64 -d` 解码并校验解码后的 sha256 与上游
原件一致。逐文件 sha256 记录在 `test_package/MANIFEST.yml`。

### E2E-PIZZLY-001 — 融合基因检出主流程

```bash
pizzly -k 31 --gtf fixtures/transcripts.gtf.gz --cache <work>/cache.txt \
       --align-score 2 --insert-size 400 --fasta fixtures/transcripts.fasta.gz \
       --output <work>/output fixtures/fusion.txt
```

实测业务输出（2026-10-15，鸿蒙 PC aarch64 实机）：

```text
GTF file contains 36 genes and 289 transcripts
Number of kept records 308 out of 366
```

`output.json` 断言：`genes` 数组 9 项（9 对融合基因），含真实致癌融合 **EML4-ALK**
（paircount=4，9 条组装转录本）；全部 9 对为
EML4-ALK、CD74-ROS1、HOOK3-RET、TMPRSS2-ETV1、EWSR1-FLI1、ETV6-NTRK3、BRD4-NUTM1、
EWSR1-ATF1、AKAP9-BRAF；组装融合转录本合计 146 条。
`output.fusions.fasta` 146 条记录，与 JSON 的 `fasta_record` 集合完全一致，
且抽样记录的序列长度等于其声明的 `transcriptA`/`transcriptB` 区间跨度之和。
每个 gene 记录满足 `paircount + splitcount == len(readpairs)`，`reads` 索引均在范围内。

### E2E-PIZZLY-002 — GTF 注释缓存生成与复用

首次运行生成 `cache.txt`；二次运行命中缓存分支：

```text
Opening cached file ... loaded 36 genes and 289 transcripts
```

二次运行的 `output.json` sha256 与 `output.fusions.fasta` 与冷启动运行逐字节一致。

| 用例 ID | 场景 | 结果 |
|---|---|---|
| E2E-PIZZLY-001 | 真实 kallisto `--fusion` 输入 → 融合过滤/组装/定量 | PASS |
| E2E-PIZZLY-002 | GTF 缓存生成与复用（结果可复现） | PASS |

消费者用例统计：**2/2 通过**（上游 0 个自动化用例，不混入本计数）。

## 注意事项

- 本包 `compiler.cppstd` 固定为 `14`（上游 CMakeLists 的 `-std=c++14` 声明）。
  若下游/CI 需要 C++17 构建，须先解决 vendored SeqAn 2.2.0 的 `empty()` 二义性，
  不能仅改 profile。
- OHOS 上安装态 ELF 需自签名（`binary-sign-tool -selfSign 1`），配方 `package()` 已处理；
  签名在 `package_type = "application"` 的 `bin/pizzly` 上执行。
- `pizzly` 依赖上游 kallisto 的 `--fusion` 能力（kallisto ≥ 0.43.1）作为**运行期数据来源**，
  但 kallisto 不是本包的 Conan 依赖（用户自行准备输入数据），故未列入 `requirements()`。
---

**编译结束**: 2026-10-15 20:07
**最终状态**: built
