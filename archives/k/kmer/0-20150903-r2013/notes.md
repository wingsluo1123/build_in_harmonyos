# kmer 0-20150903-r2013 适配笔记

## 编译环境
- 构建系统: 自研非递归 GNU make（Makefile + Make.rules + Make.include + configure.sh）
- 编译日期: 2026-10-11
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）、clang++
- 状态: built

## 版本说明
- 上游: http://kmer.sourceforge.net/ （Celera Genomics / JCVI，GPL-2.0-or-later），版本 `0-20150903-r2013`（2013 年 trunk 快照）
- 源码: `https://deb.debian.org/debian/pool/main/k/kmer/kmer_0~20150903+r2013.orig.tar.gz`
  sha256 `8fd9c289244e69e38bb7709f3523d39edf1c2ced2cbcc687fcf00ecfca78ea47`
- 版本号沿用赛事清单（首次适配，R37）

## 编译步骤
```bash
# 配方内部（build()）：
#   tools.build:compiler_executables 提供 clang/clang++
CC=<clang> CXX=<clang++> PYTHON=/nonexistent-python bash ./configure.sh OHOS-arm64
make -j1
make -j1 install          # 安装到 OHOS-arm64/{bin,include,lib}

conan create archives/k/kmer/0-20150903-r2013 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure.sh` 无法为 HarmonyOS 生成配置，Linux 分支还带 `-m64` | 该脚本按 `uname` 选择平台块，HarmonyOS 不在其中；Linux 块硬编码 x86 的 `-m64` | 补丁 0001 新增 `OHOS-arm64` 目标块（去掉 `-m64`，加 `-fcommon`），配方显式执行 `./configure.sh OHOS-arm64` |
| 2 | 全仓出现 `error: invalid suffix on literal; C++11 requires a space between literal and identifier` | 2013 年代码把 printf 格式宏直接粘在字符串字面量后（`"count: "uint64FMT" mers"`），clang++ 的 C++11 词法把它当作字面量后缀 | 补丁 0002（`libutil/util.h` 7 处宏定义）+ 0003（173 个翻译单元、1986 处调用点）在右引号与宏名之间补空格；宏展开后再拼接，格式串逐字节不变（知识条目 `DRAFT-cohomcalg-0.32-cpp11-literal-concat`） |
| 3 | `make` 报 `No targets specified and no makefile found` / `.d` 依赖规则报 `can't execute <src>.C` | 手写 `Make.compilers` 时缺少 `CXXDEP`/`.O`/`CLD` 等公共定义（它们由 `configure.sh` 追加写入）；HMDFS 上 `getcwd()` 失效（E114/E386） | 一律让 `configure.sh` 生成 `Make.compilers`；`build()` 预置 `PWD` |
| 4 | 可选组件 ATAC/A2Amapper 需要 Python 开发环境 | 其探测用 Python 2 的 `distutils`，在 OHOS/Python 3 上不可用 | 传 `PYTHON=/nonexistent-python`，沿用上游 `configure.sh` 既有的 `WITHOUT_ATAC` 分支（与上游在无 Python 机器上的行为一致） |
| 5 | 上游 `*/test/` 下的 29 个用例从来不被执行（评审实测 N=25） | 这些目录**没有 `Make.include`**，非递归 make 不 include 它们；也没有 `check` 目标、测试驱动与期望输出 | `build()` 内主动编译并运行全部 29 个（`SCRATCH-*` 日志留证）：**17 通过 / 2 运行失败 / 10 编译失败**；门禁用例仍为 `test_package` 6 条 |

## 源码修改
- `patches/0001-configure-add-ohos-arm64-target.patch` — 新增 OHOS-arm64 平台块（19 行）
- `patches/0002-util-h-pri-macro-spacing.patch` — `libutil/util.h` 格式宏定义补空格（7 处）
- `patches/0003-cxx11-literal-macro-spacing.patch` — 调用点字面量/宏补空格（173 个文件、1986 处，机械替换，无语义变化）

## 依赖版本
- 无第三方依赖（仅标准 C/C++ 库、`-pthread -lm`）

## 验证结果
```bash
conan create archives/k/kmer/0-20150903-r2013 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# CREATE_RC=0；包 kmer/0-20150903-r2013#94a2d392b9639f3d4c3ada747e135ed0（134 个文件、11 MB）

# 消费者用例（链接安装后的静态库，调用公开 C API）
CHECK-OK: md5_string("abc") matches the RFC 1321 test vector
CHECK-OK: md5_string("") matches the RFC 1321 empty-string vector
CHECK-OK: reverseString() reverses a sequence in place
CHECK-OK: reverseComplementSequence() complements and reverses a DNA sequence
CHECK-OK: reverseComplementSequence() leaves a palindromic k-mer unchanged
CHECK-OK: uint64MAX/uint32MAX cover the full width of their types
KMER_CONSUMER_CHECKS=6 FAILURES=0
KMER_CONSUMER_OK

# 上游用例实测（build() 内自动编译+运行全部 */test/ 用例，日志内为 SCRATCH-* 行）
SCRATCH-SUMMARY total=29 pass=17 run_fail=2 compile_fail=10
# 其中文件名含 test 的 25 个：15 通过 / 1 运行失败（需 meryl 内部数据库）/ 9 编译失败（引用同一 tarball 内已不存在的 API）

# 上游测试清点（build() 内执行，日志留证）
grep -rn 'check_PROGRAMS|^TESTS|^check:' Makefile Make.rules Make.include   → 无输出
ls -d libutil/test libkmer/test meryl/test sim4db/test                     → 仅有开发者草稿目录
```

## 交付物
| 目录/文件 | 说明 |
|-----------|------|
| `bin/` | 58 个可执行文件与 Perl 脚本（meryl、leaff、sim4db、snapper2、tapper、seagen、sim4dbutils/* ...） |
| `lib/*.a` | 9 个静态库：libkmer、libmeryl、libmerylguts、libseq、libbio、libsim4、libutil、libkaz、libmt19937ar |
| `include/` | 58 个头文件（util.h、bio.h、alphabet.h、kmer.H、positionDB.H ...） |
| `licenses/` | 上游 README（含 GPL-2.0-or-later 声明） |

## 注意事项
- 上游自 2015 年后已停止发布（kmer.sourceforge.net 已归档），代码保持 2013 年快照原样，仅做可编译性与可移植性修补。
- 消费者若要用 C 驱动链接这些静态库，需要自行补 C++ 运行库（库内有 C++ 目标文件）；本包的 `test_package` 用 clang++ 驱动链接。
- ATAC/A2Amapper 子组件未构建（需要 Python 2 开发环境），`bin/` 中不含 atac-driver/seatac 工具。
