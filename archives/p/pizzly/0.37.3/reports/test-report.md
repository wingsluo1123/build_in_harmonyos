# pizzly 0.37.3 测试报告（HarmonyOS PC / OHOS aarch64）

- 包引用：`pizzly/0.37.3`（首次适配，状态 `built`，未发布制品）
- 上游：https://github.com/pmelsted/pizzly，tag `v0.37.3` → commit `96368ca642ed72297ac31e99d0fd77227dd23419`
- 测试环境：HarmonyOS PC（HAD-W32），HongMeng Kernel 1.12.0，aarch64；clang 15.0.4（`/data/service/hnp/bin/clang++`）+ libc++；Conan 2.29.1（OHOS 适配版）；CMake 4.1.2 + Ninja
- 构建模式：**原生构建**（`-pr:h=ohos-aarch64 -pr:b=ohos-aarch64`，build == host == OHOS/aarch64），非交叉编译
- 测试日期：2026-10-15

## 1. 上游测试清点结果（R51 第一步）

**结论：上游没有任何自动化测试，上游测试用例数 = 0。**

对精确源码 `pizzly-0.37.3/` 执行清点：

```bash
grep -inE "enable_testing|add_test|ctest|gtest|catch|boost" CMakeLists.txt
# → 无输出（无测试注册、无测试框架、无 test 目标）

grep -rlE "int main" --include=*.cpp --include=*.cc --include=*.c . | grep -v "^./seqan"
# → 仅 ./main.cpp（不存在测试程序）

find ./test -type f
# → .gitignore  README.md  Snakefile  reads_1.fastq.gz  reads_2.fastq.gz
#   transcripts.fasta.gz  transcripts.gtf.gz
```

`test/Snakefile` 是依赖**外部** kallisto 程序的 snakemake 示例流水线（`rule all` 需要
`kallisto index` / `kallisto quant --fusion`），用于人工验证 kallisto+pizzly 联动，
不注册任何可计数的自动化用例。因此：

| 清点项 | 数量 |
|---|---|
| CTest 注册用例 | 0 |
| 上游测试程序 | 0 |
| 测试框架（gtest/Catch2/Boost.Test） | 无 |
| `ctest -N` 可列出用例 | 0（无 `enable_testing()`） |
| `make check` / `ctest` 目标 | 无 |

## 2. 上游测试执行情况

上游无自动化测试套件可执行。本配方 `build()` 中**未**添加任何 `ctest` / `make check` 调用
（无对象可调用），也未以 `BUILD_TESTING=OFF` 之类方式伪造测试。

| 项 | 值 |
|---|---|
| 上游执行数 | 0 |
| 上游 PASS / FAIL / SKIP / XFAIL | 0 / 0 / 0 / 0（不适用，非"空集 100%"） |
| 上游测试用例修改 | **无**（未修改上游任何文件；`conandata.yml` 为 `patches: {}`） |

## 3. 消费者端到端测试（鸿蒙 PC 目标机实跑）

被测对象：`conan create` 安装后的 `package_folder/bin/pizzly`（`conanrun` env 的 PATH 指向
Conan cache 的 package_folder/bin），**不使用**源码构建目录产物；OHOS 上不存在同名系统程序。

执行入口：`test_package/conanfile.py` 的 `test()` → `bash test_pizzly.sh`（`env="conanrun"`）。
实测被测二进制路径：`/storage/Users/currentUser/.conan2/p/b/pizzlonepkg…/p/bin/pizzly`。

测试输入（fixtures 逐文件 sha256 见 `test_package/MANIFEST.yml`）：

| fixture | 载体 | 解码后 | 来源 |
|---|---|---|---|
| `fixtures/fusion.txt` | 199238 B，sha256 `aa1cc960…94dd` | 同左（纯文本） | 制品仓 kallisto/0.52.0 对上游 `test/reads_*.fastq.gz` 执行 `kallisto quant --fusion` 的真实输出，366 条记录（与上游 `test/Snakefile` 的 rule index / rule kallisto_quant 参数一致） |
| `fixtures/transcripts.gtf.gz.b64` | 109138 B，sha256 `ee7b4559…efb1` | 80788 B，sha256 `9a2cf33e…46ab` | 上游 tag v0.37.3 `test/transcripts.gtf.gz` 原样（Ensembl 85 子集），base64 承载 |
| `fixtures/transcripts.fasta.gz.b64` | 107261 B，sha256 `0940a098…637c` | 79399 B，sha256 `bcf11e8d…c281` | 上游 tag v0.37.3 `test/transcripts.fasta.gz` 原样，base64 承载 |

> 两个参考数据因是 gzip 压缩数据，按仓库约定以 base64 承载（test_package 内不提交裸归档
> 扩展名，先例 `archives/b/blur`、`archives/b/bozohttpd` 的 `test_package/*.b64`）。
> `test_pizzly.sh` 运行时 `base64 -d` 解码后**强制校验解码结果 sha256**，不一致即非零退出。

### 用例 E2E-PIZZLY-001 — 融合基因检出主流程

场景：kallisto 候选融合 → 假阳性过滤 → 断点级转录本组装 → 融合丰度定量。

```bash
pizzly -k 31 \
  --gtf   "$WORK/data/transcripts.gtf.gz" \
  --cache "$WORK/case1/cache.txt" \
  --align-score 2 --insert-size 400 \
  --fasta "$WORK/data/transcripts.fasta.gz" \
  --output "$WORK/case1/output" \
  "$FIXTURES/fusion.txt"
```

实测输出（退出码 0）：

```text
GTF file contains 36 genes and 289 transcripts
Number of kept records 308 out of 366
```

业务结果断言（全部通过）：

| 断言 | 期望 | 实测 |
|---|---|---|
| stderr 基因/转录本数 | `GTF file contains 36 genes and 289 transcripts` | 一致 |
| 保留记录数 | `Number of kept records 308 out of 366` | 一致 |
| `output.json` 顶层键 | `["genes"]` | 一致 |
| 融合基因对数 | 9 | 9（EML4-ALK、CD74-ROS1、HOOK3-RET、TMPRSS2-ETV1、EWSR1-FLI1、ETV6-NTRK3、BRD4-NUTM1、EWSR1-ATF1、AKAP9-BRAF） |
| 真实致癌融合 EML4-ALK | 存在，`geneA.id=ENSG00000143924.18`、`geneB.id=ENSG00000171094.15`、paircount=4、9 条组装转录本 | 一致 |
| 组装融合转录本总数 | 146 | 146 |
| `output.fusions.fasta` 记录数 | 146 且与 JSON 的 `fasta_record` 集合完全一致 | 一致 |
| 抽样记录序列长度 | 等于 `transcriptA`/`transcriptB` 区间跨度之和 | 一致 |
| 每 gene 自洽 | `paircount + splitcount == len(readpairs)`，`reads` 索引均在范围内 | 一致 |

### 用例 E2E-PIZZLY-002 — GTF 注释缓存生成与复用

二次运行复用首次生成的 `cache.txt`，实测输出（退出码 0）：

```text
Opening cached file ... loaded 36 genes and 289 transcripts
Number of kept records 308 out of 366
```

| 断言 | 结果 |
|---|---|
| 首次运行生成 `cache.txt` 且非空 | 通过 |
| 二次运行命中缓存分支（`Opening cached file`） | 通过 |
| 缓存加载计数 `loaded 36 genes and 289 transcripts` | 通过 |
| 二次运行保留记录数一致（308/366） | 通过 |
| 二次运行 `output.json` 的 sha256 与冷启动**逐字节一致** | 通过 |
| 二次运行 `output.fusions.fasta` 与冷启动**逐字节一致** | 通过 |

## 4. 统计与结论

| 项 | 值 |
|---|---|
| 上游测试用例（执行 / PASS） | 0 / 0（上游无自动化套件） |
| 消费者端到端用例（执行 / PASS） | **2 / 2** |
| **鸿蒙特有测试（执行 / PASS）** | **2 / 2** |
| 断言总数 | 23 |
| 上游测试修改 | 无 |
| 上游测试豁免（SKIP/XFAIL） | 无（不存在可豁免对象） |
| 用例 ID | `E2E-PIZZLY-001`、`E2E-PIZZLY-002` |

**规则 12 结论：满足。** 存在 2 个完整消费者端到端用例（真实输入 → 调用安装后的包产物 →
完成核心功能 → 检查实际业务输出），并已在鸿蒙 PC 目标机（OHOS/aarch64 原生构建）实际运行通过。
`--version` 冒烟行仅作前置检查，已在脚本中显式标注不计入 E2E 用例数。

## 5. 证据文件

| 文件 | 内容 |
|---|---|
| `reports/conan-create.log` | 干净 `conan create` 完整日志（退出码 0，含 fixture 解码哈希与两个 E2E 用例 PASS） |
| `reports/w3-local-ci.log` | 本地 CI 模拟（W3）完整日志，含 JC1–JC6、L0a–L0q、L1a–L1e、L2/L4/L5 门禁结果与 `pizzly consumer E2E: PASS` |
| `reports/conan-verify-report.md` | conan-verify G1–G4 报告 |
| `reports/audit-result.json` | W4 独立审计结论（P0=0 / P1=0） |
| `.ci-result.json` | W3 回执（含日志 SHA256，由 finish 写入，未手改） |

## 6. 已知限制

- 本包 `compiler.cppstd` 固定为 `14`（上游 CMakeLists 声明）；若下游需要 C++17，须先解决
  vendored SeqAn 2.2.0 的 `empty()` 二义性，不能仅改 profile。
- `pizzly` 以 kallisto ≥ 0.43.1 的 `--fusion` 输出为运行期数据来源，但 kallisto 不是本包的
  Conan 依赖（用户自行准备输入数据），故未列入 `requirements()`。
- 未做 GUI/外设/媒体类验证（本包为纯命令行工具，无此类接口）。
