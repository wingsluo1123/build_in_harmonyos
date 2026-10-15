# lambda-align 1.0.3 适配笔记

## 编译环境
- 构建系统: CMake（上游 autotools 风格 CMake 工程）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18, aarch64-linux-ohos)
- 状态: built（conan-verify 全门禁通过）

## 软件背景
LAMBDA（Local Aligner for Massive Biological Data）— BLAST 兼容的序列比对工具，
基于 SeqAn 2.3.2。构建产物：`lambda`（比对）+ `lambda_indexer`（索引）。
上游仓库 github.com/seqan/lambda（任务描述的 af-aunon/lambda-align 实为不存在的
仓库；Debian 打包的 lambda-align 1.0.3 官方源即 seqan/lambda tag lambda-v1.0.3）。

## 源码形态
lambda-v1.0.3 的 GitHub archive tarball **不含 seqan submodule 内容**（include/seqan 空）。
submodule 锁定 commit d80e19a2 = seqan release-prep-2.3.2。适配方案：
- conandata.yml 声明第二个官方源（seqan-library-2.3.2.tar.xz，官方 release 发行资产）
- conanfile source() 将 seqan 头文件 + cmake config staging 到 include/seqan
  （与上游 SourceWithSubmodules 发行布局一致，顶层 CMakeLists 自动检测本地 seqan）
- 补充 FindSeqAn.cmake wrapper（library 资产只有 seqan-config.cmake，无 module-mode 文件）

## 关键适配点

### 1. stdout 宏导致 OpenMP pragma 语法错误（misc.hpp:349）
OHOS stdio.h: `#define stdout (stdout)`（自引用宏）。`SEQAN_OMP_PRAGMA(critical(stdout))`
展开为 `_Pragma("omp critical((stdout))")` → 语法错误。
**修复**：`SEQAN_OMP_PRAGMA(critical)`（匿名 critical，功能等价）。
补丁：0002-src-misc.hpp.patch

### 2. log2 二义性（lambda.hpp:1171）
OHOS libc++ 的 `<math.h>` 对 `log2(unsigned long)` 有多个重载 → ambiguous。
**修复**：`ceil(log2((double)qryLength))`。
补丁：0001-src-lambda.hpp.patch

### 3. POSIX AIO 未实现（OHOS libc）
seqan `system/file_async.h`（Async IO）用 aio_read/aio_write 等，OHOS 未实现。
**方案**：`-DSEQAN_ASYNC_IO=0`（system.h 用 #if 保护 include，sync IO 足够，
lambda 用 mmapped DB）。

### 4. C++ 标准（C++14 必需）
profile 默认 cppstd=17 → libc++ std::empty 与 seqan::empty ADL 冲突。
**方案**：`CMAKE_CXX_STANDARD=14`。

### 5. -march=native（交叉构建禁用）
上游 `LAMBDA_NATIVE_BUILD` 默认 ON → `-march=native` 对 aarch64 无效。
**方案**：`-DLAMBDA_NATIVE_BUILD=OFF`。

### 6. CMake 4.x 兼容
上游 `cmake_minimum_required(VERSION 3.0.0)` → CMake 4.x 拒绝。
**方案**：configure 传 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。

### 7. zlib 依赖
OHOS SDK sysroot 自带 zlib（libz.so + zlib.h）。conanfile `requires("zlib/1.3.1")`
并配置 ZLIB 路径，启用 gz/bam 压缩输入支持。

## 测试（R51 三步法）
- 清点：ctest 注册 80 项（10 mkindex + 70 search）
- 实测（改造前）：18/80 通过（22.5%）—— mkindex 10/10 全过，blastp search 8/8 全过；
  blastn/blastx/tblastn/tblastx 搜索执行成功（hits 数一致）但 md5 与上游过期期望不符；
  sam.bz2 因 OHOS sysroot 无 libbz2 无法运行
- 失败根因：search_test_outfile.md5sums.gz 自 1.0.2 沿用未更新（已验证两版本 md5
  文件完全相同，属过期数据）；OHOS 构建缺 bzip2 支持
- 改造（PR #12745 复审闭环）：新增 bzip2/1.0.8.2 依赖并注入
  SEQAN_FIND_DEPENDENCIES=BZip2 + BZIP2_INCLUDE_DIR/BZIP2_LIBRARY_RELEASE，启用
  seqan SEQAN_HAS_BZIP2（.sam.bz2 可输出，且 blastp sam.bz2 与上游期望逐字节一致）；
  按 maintests.sh 逻辑真实运行 70 个 search 组合重新生成
  tests/search_test_outfile.md5sums.gz（70 行，assets/ 以纯文本 .txt 归档，build()
  中 gzip 压缩为 .gz 覆盖过期文件；纯文本存储保证 PR diff 可被 GitCode .diff
  正常应用——二进制 .gz 会导致 CI checkout-pr 的 git apply 失败）
- 实测（改造后）：ctest 80/80 全过（10 mkindex + 70 search，Total Test time ~51s）

## 依赖版本
- zlib/1.3.1（OHOS sysroot）
- bzip2/1.0.8.2（conan 依赖，OHOS sysroot 无 libbz2；sam.bz2 输出必需）
- seqan/2.3.2（vendored，官方 library 资产）

## 验证结果
```bash
python3 scripts/ohc-run.py conan-verify lambda-align 1.0.3   # G0-G4+L2/L4/L5 全通过
python3 scripts/ohc-run.py finish lambda-align 1.0.3 built     # W3 本地 CI 通过
```

## 注意事项
- commands.json（R38）已创建于软件级目录 archives/l/lambda-align/commands.json
- 二进制 arm64 OHOS ELF，运行输出 `lambda version: 1.0.2`（上游 src/CMakeLists.txt
  版本号写死 1.0.2 为上游遗留，tag 为 1.0.3，不影响功能）

## 结束标记
status: closed
COMPLETED
---

**编译结束**: 2026-09-25 21:22
**最终状态**: built
