# megadepth 1.2.0 适配笔记（OHOS PC / aarch64 真机）

## 编译环境
- 构建系统: cmake（配方自带 CMakeLists.txt，CMakeDeps 消费 Conan 依赖）
- 编译日期: 2026-10-13
- 编译器: /data/service/hnp/bin/clang（OHOS SDK llvm 15），libc++
- 状态: built（本机 conan create 通过，未 upload）
- 平台: HarmonyOS aarch64（原生构建，非交叉编译）
- 语言预检: cpp（构建系统 cmake；`CMakeLists.txt project(megadepth)`；c↔cpp 兼容族）

## 依赖
| 包 | 版本 | 来源 | 说明 |
|----|------|------|------|
| htslib | 1.24-r0 | ohpcd | 静态库仅 libhts.a；以 `--disable-bz2 --disable-libcurl --disable-plugins --disable-ref-cache --with-libdeflate` 构建 |
| libbigwig | 0.4.9 | ohpcd | 静态 libBigWig.a，头文件在 include/libbigwig/，传播 `NOCURL` 宏 |
| zlib | 1.3.1 | ohpcd | 静态 libz.a |
| libdeflate | 1.25 | ohpcd | htslib 传递依赖，**共享库**（见问题 #2） |
| xz | 5.6.2 | ohpcd | htslib 传递依赖，未进入最终 DT_NEEDED |

## 编译步骤

```bash
# 与 CI 同源的本地验证（W3）
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

构建流程由配方驱动，无手工步骤：
`source()` 取官方 tag 归档 → 复制配方自带 CMakeLists.txt → 应用 conandata 补丁
→ `generate()` 产出 CMakeDeps/CMakeToolchain/VirtualRunEnv
→ `build()` cmake configure+build → 上游测试 `bash tests/test.sh static`
→ `package()` 安装 bin/megadepth + licenses → test_package（消费者视角 9 条断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无规范名 `CMakeLists.txt` | 上游只提供 `CMakeLists.txt.ci/.static/.statlib/.windows`，构建脚本用 `ln -fs CMakeLists.txt.ci CMakeLists.txt` 取别名，且硬编码 `-L${CMAKE_SOURCE_DIR}/htslib` 等 vendored 子模块目录 | 配方自带 `CMakeLists.txt`（export_sources 导出，source() 拷入源码根），改用 CMakeDeps 目标 `htslib::htslib` / `libbigwig::libbigwig` / `zlib::zlib` 消费 Conan 依赖；不改动上游任何源码文件 |
| 2 | 产物 `DT_NEEDED libdeflate.so.0`，直接执行报 `Error loading shared library` | htslib 静态库 `--with-libdeflate`，其传递依赖 `libdeflate/1.25` 以共享库分发；且该配方 `build()` 硬编码 `-DLIBDEFLATE_BUILD_SHARED_LIB=ON`，`shared=False` 不改变产物 → 无法静态化 | 不擅改已发布依赖（PR 原子性）；按仓库既有约定（E298/libharu）在 `generate()` 中加 `VirtualRunEnv`，`build()` 内上游测试以 `env="conanrun"` 注入 `LD_LIBRARY_PATH`；test_package 同样走 `conanrun` |
| 3 | 首次写 `self.run(..., env={...})` 报 `env argument ... should be a list` | Conan 2 的 `run(env=)` 只接受环境脚本名或 `"NAME=VALUE"` 列表 | 改走 `VirtualRunEnv` + `env="conanrun"`（问题 #2 的同一处修正） |
| 4 | `CMake Error: Target "megadepth" links to ZLIB::ZLIB but the target was not found` | Conan 的 zlib 包未设置 `cmake_file_name`，CMakeDeps 生成 `zlib-config.cmake`，目标是 `zlib::zlib`，不是 CMake 内置 FindZLIB 的 `ZLIB::ZLIB` | `find_package(zlib REQUIRED)` + 链接 `zlib::zlib` |
| 5 | 上游测试 `Error 127` / `Error 1` 早退 | 127 = 产物缺 `libdeflate.so.0`（同 #2）；1 = CRAM 用例断言失败（见 #6） | #2 修 LD_LIBRARY_PATH；#6 由补丁 0002 解决 |
| 6 | CRAM 用例失败：`Failed to open reference file '/data7/hbb_megadepth/./test.fa'`，`Slice decode failure`，Read 0 records | 上游 `test.cram` 头部的参考序列指向作者机器绝对路径，仓库未附带任何 FASTA；上游 CI 靠 htslib 内置 curl 从 ENA 在线回取参考，而本平台 `htslib/1.24-r0` 以 `--disable-libcurl` 发布；该用例带 `--alts`，megadepth 据此请求 `SAM_SEQ` 全量解码，CRAM 全量解码必须取参考序列 | 补丁 0002 去掉该用例的 `--alts`：megadepth 于是走 `CRAM_OPT_REQUIRED_FIELDS`（QNAME/FLAG/RNAME/POS/MAPQ/CIGAR/RNEXT/PNEXT）参考无关解码路径，实读 96 条记录；用例的两条断言（`coverage.tsv` 逐行 diff、`window.tsv` 求和 diff）与本补丁前**输出完全一致**（已实测比对）。未删除任何用例、未改动任何期望文件 |
| 7 | 上游测试 `tests/test.sh:95` 有一处未加 `static` 守卫的远程 HTTP 取数 | 上游为联网 CI 设计；本平台 htslib/libbigwig 均无远程读取能力 | 补丁 0001 用完全等价的本地 fixture（`tests/test_noprefix.bam` + `--add-chr-prefix human`，与 static 分支首例输入一致）替换该 URL，断言与期望文件不变 |
| 8 | `tests/` 内含相对符号链接（`test.bam -> test_noprefix.bam`） | 直接 `copy(self, "*", ...)` 不保证保留链接，引用 `tests/test.bam` 的用例会失效 | `_run_upstream_tests()` 用 `shutil.copytree(..., symlinks=True)` 复制 fixture 到构建目录副本，不改动源码目录 |
| 9 | **CI `checkout-pr` 失败**：`error: missing binary patch data for 'archives/m/megadepth/1.2.0/test_package/fixtures/test_noprefix.bam'` / `binary patch does not apply` / `patch: Unknown option 'fuzz=3'` | 平台 `checkout-pr` 用 `curl https://atomgit.com/.../pull/N.diff` 取 PR diff 后 `git apply`；该端点对二进制文件只给 "Binary files differ" 占位，不携带 `GIT binary patch` 数据，因此**只要 PR 里含二进制文件，整个 diff 都无法应用**（第二道 `patch -p1 --fuzz=3` 因设备 patch 不认 `fuzz=` 选项也失败）。我最初把上游 `.bam`/`.bai` 二进制 fixture 放进了 `test_package/fixtures/` | 换成上游**纯文本** `tests/test.sam`（megadepth 的 `get_file_format_extension()` 把 `.sam` 归入 BAM 族、`sam_open()` 自动识别 SAM），并移除 `.bam`/`.bai`；实测 `annotation.tsv` / `unique.tsv` / `alts.tsv` 三条断言与替换前**逐行完全一致**。归档内现无任何二进制文件 |

## 源码修改

补丁仅作用于上游测试脚本 `tests/test.sh`，**不改动任何上游 C++ 源码**（`megadepth.cpp` 原样编译）：

| 补丁 | 修改对象 | 内容 |
|------|---------|------|
| `0001-tests-remote-bam-to-local-fixture.patch` | `tests/test.sh` 第 95 行 | 远程 HTTP `test.bam` → 等价本地 fixture |
| `0002-tests-cram-reference-free-decode.patch` | `tests/test.sh` 第 12 行（static 分支） | CRAM 用例去掉 `--alts`（走参考无关解码） |

aarch64 无需架构补丁：`megadepth.cpp` 的 AVX512/AVX2/SSE2 分支全部由
`__AVX512F__`/`__AVX2__`/`__SSE2__` 守卫，x86 头文件 `x86intrin.h` 亦然；
aarch64 上这些分支整体编译剔除（`nper`/`nsimd` 只在守卫内声明），
每个 SIMD 段后都有标量尾循环 `for(; i < ninc; ++i)` 兜底。

## 验证结果

```bash
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
...
megadepth/1.2.0: RUN: bash tests/test.sh static     # 上游测试（层 1）
...
======== Testing the package ========
megadepth/1.2.0 (test package): Running test()
[test] 结果: PASS=9 FAIL=0
[test] ALL PASSED
EXIT=0
```

- 上游测试：19/19 次 megadepth 调用执行，30/30 条断言通过（0 条 diff 差异）
- 消费者测试：9/9 通过
- 产物：`bin/megadepth`，`readelf -d` 仅 `libdeflate.so.0`（依赖仓共享库）、`libc++_shared.so`、`libc.so`
- 完整日志：`reports/conan-create.log`（含上游 tests/test.sh 全部输出）、
  `reports/w3-local-ci.log`（L0-L5 门禁）、`reports/conan-verify-report.md`（G0-G4）。
  注：`reports/` 被仓库 `.gitignore` 忽略，属本机留档，不随 PR 提交。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 主配方（application 类型） |
| `CMakeLists.txt` | 配方自带的等价 CMake 构建文件（export_sources） |
| `conandata.yml` | 官方源码 URL + SHA256 + 补丁清单 |
| `patches/0001-*.patch`、`patches/0002-*.patch` | 上游测试脚本适配补丁 |
| `test_package/` | 消费者测试（conanfile.py + test_megadepth.sh + 6 个上游 fixture + MANIFEST.yml） |
| 软件级 `commands.json` | R38：本包产物含可执行文件（bin/megadepth），声明 hicmd 命令 |
| 软件级 `README.md` | 软件简介与鸿蒙适配说明 |

## 注意事项

- **`--alts` 与 CRAM 参考序列**：在本平台（htslib 无 curl）对 CRAM 输入使用
  `--alts` 会因无法回取参考序列而解码失败；对 BAM 输入无此限制。
- **运行时依赖**：产物需 `libdeflate.so.0` 可见（Conan 依赖链，`conanrun` 环境脚本
  已注入 `LD_LIBRARY_PATH`）。`libdeflate/1.25` 无法静态化（见问题 #2）。
- **上游参考序列**：`tests/test.cram` 头部记录的是作者机器路径
  `/data7/hbb_megadepth/./test.fa`，上游仓库不含该文件；如需对 CRAM 全量解码，
  需自行提供 hg19 参考并 `--fasta` 指定。
---

**编译结束**: 2026-10-13 22:37
**最终状态**: built
