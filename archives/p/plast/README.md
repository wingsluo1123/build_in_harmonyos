# PLAST

## 简介

PLAST（Parallel Local Sequence Alignment Search Tool）是一个 bank-to-bank（库对库）的
序列相似性搜索工具，思路与 BLAST 相近但面向「两个序列集合互相比对」的场景。
多线程、内存占用小，支持五种算法：

| 算法 | 说明 |
|------|------|
| `plastp` | 蛋白 vs 蛋白 |
| `tplastn` | 翻译核酸 vs 蛋白 |
| `plastx` | 翻译核酸 vs 翻译核酸 |
| `tplastx` | 翻译核酸 vs 翻译核酸（另一套种子模型） |
| `plastn` | 核酸 vs 核酸 |

上游以 C++11 静态库 + 自带命令行工具的形式发布，另有可选的 JNI 绑定供 Java 侧调用。

## OHOS 适配

- **x86 SIMD → SIMDe**：上游 README 明确要求 “Intel/AMD 64bit processor providing SSE2+
  instructions set”，但 `_mm_*` 内建只出现在 3 个翻译单元
  （`SmallGapHitIteratorSSE8.cpp`、`UngapHitIteratorSSE8.cpp`、`UngapHitIteratorSSE16.cpp`）。
  改用 `#define SIMDE_ENABLE_NATIVE_ALIASES` + `#include <simde/x86/sse3.h>` 后，
  同一份 kernel 在 aarch64 上编译为 NEON，**语义不变**。
  不采用「运行期切到标量迭代器」（`-factory-hit-ungap UngapHitIterator`）是因为两者判定逻辑
  并不等价：SSE 版本会额外用 `_alignmentResult->doesExist()` 过滤已存在的比对。
- **平台宏（E092）**：PLAST 的线程/时间/文件/mmap 文件/内存全部实现由自定义宏 `__LINUX__` 选择，
  而该宏只在 `CMAKE_SYSTEM_NAME MATCHES "Linux"` 分支注入。OHOS 下 conan 把它映射为
  `HarmonyOS`，配方按 E092 覆盖为 `Linux`，否则 `DefaultFactory` 的五个工厂指针不会初始化。
- **JNI 可选**：`find_package(JNI REQUIRED)` + `file(GLOB_RECURSE)` 使 JDK 缺失时整库无法配置。
  配方改为可选：无 JDK 时排除 `src/launcher/jni`；将来有 JDK 会自动恢复编译。
- **`-msse3` 条件化**：仅在 x86 目标传递。
- **`/tmp` 只读（E002）**：`SystemCommand` 的临时文件与上游单元测试的临时文件都改用 `TMPDIR`。
- **aarch64 `char` 无符号**：暴露两处上游真实缺陷——
  `fgetc` 的 EOF 哨兵失效导致文件读循环死转；用 `char` 返回 -1 变 255 被当作数组下标，
  导致反向阅读框结果错误并在大库上段错误。两者均已修复。
- **C++17**：OHOS profile 固定 `cppstd=17`，`register` 存储类说明符已被移除，遗留源码需删除。

## 依赖

| 依赖 | 用途 | 是否必需 |
|------|------|----------|
| `simde/0.8.2` | 三个 SSE kernel 的跨架构实现（header-only） | 是 |
| `cppunit/1.15.1` | 上游 `PlastLibraryTest` 单元测试框架 | 仅构建/测试期 |
| JDK | JNI/Java 绑定 | 否（OHOS 上缺省不构建） |

内置 PCRE 8.31 随源码一起编译，无外部依赖。

## 功能验证

```bash
# 1) 单包构建（真机 aarch64）
cd archives/p/plast/2.3.2
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing

# 2) 命令行工具
PlastCmd -h
PlastCmd -p plastp -i query.fa -d bank.fa -o out.txt -e 1e-5 -a 2
cat out.txt      # qry  sub  100.00  76  0  0  6  81  1  76  1e-42  151.4

# 3) 建库工具
makeplastdb -d bank.fa && ls -l bank.fa.info
```

## 已知限制

- **JNI/Java 绑定未纳入本轮**：OHOS 生态无 JDK 配方，`src/launcher/jni` 不参与构建；
  C++ 静态库、`PlastCmd`、`makeplastdb` 功能完整。
- **8 个上游单元测试 skip**：仅因 release 归档未附带其 `test/db` 语料（上游从已失效的
  `plast.gforge.inria.fr` 下载完整语料），非平台限制；补齐语料后可恢复执行。
- `PLAST_BUILD_OS` 宏按 E092 映射显示为 `Linux`，`PlastCmd -h` 的 “OS: Linux” 属预期行为。
- 包内包含上游 `install()` 一并安装的 `test/db` 与 `PlastLibraryTest`，包体积偏大（上游行为，未裁剪）。

## 参考

- 官网 / 用户手册：https://plast.inria.fr/
- 源码仓库：https://github.com/PLAST-software/plast-library
- 适配详情：`2.3.2/notes.md`
- 真机验证证据：`2.3.2/reports/device-verification.md`
- 积分赛事 PR 正文：`2.3.2/reports/pr-body.md`
