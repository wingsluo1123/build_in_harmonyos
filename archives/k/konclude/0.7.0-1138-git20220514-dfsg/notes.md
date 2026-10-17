# konclude 0.7.0-1138-git20220514-dfsg 适配笔记

> 上游：konclude/Konclude — OWL 2 DL（SROIQV(D)）高并发 tableau 推理器
> 源码 commit：`056334ad728429308991e135500d129b8c652490`（2022-05-14）
> 许可证：LGPL-3.0（树内 `LGPL-3.0.txt`，`Readme.md` 第 12 行）
> 机器：HarmonyOS PC（HUAWEI MateBook Pro），aarch64，HongMeng Kernel 1.12.0。
> 机型标识按系统参数实录（两者为同机不同层级，勿只引其一）：
> `param get const.product.model` = **HAD-W32**（产品型号）、
> `param get const.cust.devmodel` = **HAD-W24**（客户设备型号）；
> 版本 `const.comp.hl.product_base_version` = HAD-LGRP3-CHN 6.1.0.117(SP68)，
> `const.comp.product_version` = Product-HAD 206.1.0(0000)。
> 原生构建（build = host = OHOS/aarch64），clang 15.0.4，Conan 2.29.1（OHOS 适配版）

## 1. 源码身份与任务版本的对应（R47 / R39 证据）

| 项 | 值 | 证据 |
|---|---|---|
| 上游仓库 | `github.com/konclude/Konclude` | 官方 README / derivo 产品页 |
| 上游 tag | `v0.7.0-1138` → commit `0002e80635403960a7df5d93bd0e8f994d4952d0` | GitHub tags API |
| **任务源码 commit** | `056334ad728429308991e135500d129b8c652490`（2022-05-14T13:10:56Z，message「fixed brackets」） | GitHub commits API `until=2022-05-15` 首条；与 Debian changelog 三条条目逐条吻合 |
| 任务版本 | `0.7.0-1138-git20220514-dfsg` | 分支 `feat/konclude-0.7.0-1138-git20220514-dfsg`；PF9 实现要求分支 == `feat/<pkg>-<版本目录名>`（`scripts/ohc/preflight.py:588-594`） |
| Debian 对应版本 | `0.7.0+1138+git20220514~dfsg-1` | Debian tracker changelog（`+`/`~` 按本仓库惯例写作 `-`） |
| 归档 sha256 | `79293c3c2cce797a1c333b8ca4fc2be0a579eaa78b69d1ed547fd25d5cc371ce` | 两个独立镜像通道分别下载后 `cmp` 判定 IDENTICAL |

**`dfsg` 后缀的含义（不是我们要重打包）**：上游树内自带第三方预编译二进制——
`External/librdf/Linux/x64/lib/release/{librdf,libraptor2,librasqal,libxml2}.a`、
`External/jemalloc/Linux/x64/lib/release/libjemalloc.a`、
`External/hoard/Windows/x64/lib/Release/libhoard.lib`，以及 48 个 `.dll` /
36 个 `.lib` / 49 个 `.pdb`。Debian 的 `~dfsg` 正是剥离这些件。本任务按 R39/PF7
**不使用** Debian 重打包源，直接取上游官方 GitHub 归档。

## 2. 语言预检（R47，工具输出 exit 0）

```
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight konclude 0.7.0-1138-git20220514-dfsg \
    --src <BUILD_SRC_DIR> --lang cpp --project-dir <WORKTREE_ROOT>
→ ✅ 语言匹配: task=cpp, detected=cpp
```

| 证据 | 实测 |
|---|---|
| 主体语言 | `Source/` 下 **2580** 个 `.cpp`（425,441 行）+ **2653** 个 `.h/.hpp`（295,370 行），`.c` **0** |
| 构建系统 | qmake：`Konclude.pro` / `KoncludeWithoutRedland.pro` / `KoncludeLIB.pro` + `Konclude.pri`（378 KB 源清单） |
| 其它语言 | 仅 2 个辅助 shell 脚本（`UnixGitBuildScript.sh` 20 字节空壳）+ Windows `.bat`；无 Go/Rust/Python 主体 |

注：工具输出的 `language_evidence.build_system` 字段填的是 `autotools`
（`--guess` 按 URL/文件名推断，`.pro` 不在识别表内），与实际 qmake 不符；
语言判定结论（cpp）不受影响。已作为知识候选记录。

## 3. 依赖预检（W0 / W0b / R35 / R36）

`Source/` 全树检索 `mprotect` / `mmap(` / `prctl` / `epoll` / `eventfd` / `inotify` /
`syscall(` / `/proc/` / `/sys/` / `setjmp` / `ucontext` / `dlopen` / `sched_setaffinity`
→ **零命中**；平台抽象层是 Qt5（`QThread` / `QtConcurrent` / `QTcpServer`）。

| 依赖 | 实测命令 | 结果 |
|---|---|---|
| `qt5-qtbase/5.15.2.2` | `conan download … -r=ohpcd` | exit=0 |
| `dbus/1.14.10` | 同上 | exit=0 |
| `zlib/1.3.1` | 同上 | exit=0 |
| `expat/2.8.2` | 同上 | exit=0 |
| `raptor2/2.0.15` | `conan install --requires=… -r=ohpcd` | `Unable to find … in remotes` |
| `rasqal/0.9.33` | 同上 | `Unable to find … in remotes` |

`qt5-qtbase` 制品内含构建所需全部件：`bin/qmake`（QMake 3.1 / Qt 5.15.2）、`bin/moc`、
`bin/rcc`、`mkspecs/`（含 `modules-inst/`）、`lib/libQt5{Core,Xml,Network,Concurrent}.so`、
`include/Qt{Core,Xml,Network,Concurrent}`、`lib/Qt5*.pc`、`lib/cmake/Qt5*`。

## 4. 功能边界（**实测**，不推测）

`KoncludeWithoutRedland.pro` 不定义 `KONCLUDE_REDLAND_INTEGRATION`。逐项实测结论：

| 能力 | 实测 | 判定 |
|---|---|---|
| OWL 2 XML / Functional-Style 解析 | `lubm-univ-bench.owl.xml` → 45 类/44 条子类边/15,338 B | ✅ |
| classification / consistency / satisfiability / realization | 见本文档 §7.2（C1–C13） | ✅ |
| OWLlink（文件 + HTTP server） | C3–C7、C11、消费者用例 02 | ✅ |
| SPARQL（OWL/XML 本体） | `roberts-…sparql` 查询 → `Determined 331 answers` | ✅（内置简易解析器，不经 Redland） |
| RDF 非 XML 序列化（Turtle 等） | `classification -i Tests/lubm-univ-bench-data-1.ttl` → **静默空知识库**（2 类/0 边/896 B），rc=0 | ❌ 需 raptor2 |
| SPARQL over `.ttl` 数据 | `sparqlfile -s Tests/lubm-…sparql` → **结果集为空** | ❌ 受 Turtle 边界阻断 |
| Rasqal 复杂查询 / 外部三元组 DSN | 该路径未编译 | ❌ |

**修正记录**：探索初期曾按“WithoutRedland ⇒ SPARQL 全部不可用”记录，实测证伪
（`sparqlfile`/`sparqlserver` 均可用，仅数据前置为 Turtle 时结果为空），已按实测更正。
依赖缺失的准确表述：`raptor2`/`rasqal` 在仓库与制品仓均不存在，上游树内仅有 x86_64
预编译 `.a`；按 R36 属独立依赖任务，不在本 PR 内捎带。

## 5. 构建过程（探索阶段，实测）

```bash
# 1) 源码（官方 GitHub 归档，本机 github.com 直连受限，经镜像取回后与本机缓存包哈希交叉校验一致）
#    sha256 79293c3c…（两通道 cmp IDENTICAL）
# 2) init-build 建立上下文（预置 tarball 复用，避免重复下载）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build konclude 0.7.0-1138-git20220514-dfsg \
    --url="https://github.com/konclude/Konclude/archive/056334ad…tar.gz"
# 3) 语言预检（R47）
# 4) 修正 qt5-qtbase 可重定位性（bin/qt.conf + mkspecs/{modules,modules-inst}/*.pri → 包目录，
#    与 archives/q/qt5-qtdeclarative/5.15.2 的既有做法一致）
# 5) qmake + make（在源码目录内，原生 OHOS 构建）
qmake -qtconf <qtbase>/bin/qt.conf -spec linux-clang \
      QMAKE_CXX=clang++ QMAKE_LINK=clang++ KoncludeWithoutRedland.pro
make -j8 QMAKE_STRIP=
```

| 项 | 实测值 |
|---|---|
| 编译单元 | 2535 个目标；首次全量 `make -j8` 约 45 分钟（本机 load ≈ 23，8 核） |
| 编译告警处理 | 上游 `.pro` 自带 `CONFIG += warn_off`（`-w`），未人为追加任何编译参数 |
| 产物 | `Release/Konclude`，19,839,616 B，ELF64 LSB arm64，musl（`ld-musl-aarch64.so.1`），未 strip |
| `DT_NEEDED` | `libQt5Gui/Xml/Network/Concurrent/Core.so.5`、`libGLESv2.so`、`libc++_shared.so`、`libc.so` |
| 运行验证 | 见本文档 §7（14 次文档化调用执行 / PASS 13 / 未通过 1；2/2 消费者端到端 PASS） |
| 已知环境提示 | `make` 报 `jobserver mkfifo: … Operation not permitted`（HMDFS 上 FIFO 受限）→ 退化为有限并行，**不影响结果**，未做绕过 |

## 6. 源码修改（1 个补丁，平台无关 bugfix）

`patches/0001-null-guard-evaluation-order.patch` —— 修改
`Source/Reasoner/Kernel/Algorithm/CCalculationTableauCompletionTaskHandleAlgorithm.cpp:16106`：
把上游作者自己写的空值守卫 `|| !atmostConcept->getOperandList()` 从调用**之后**提到**之前**。
原写法因短路求值必然先执行 `hasIdenticalConceptOperands(NULL, …)`，在基数限制无显式 operand
列表时 NULL 解引用（`Tests/roberts-family-full-D.owl.xml` 分类/实现稳定 SIGSEGV，3/3 复现）。
完整证据链（FaultLogger / 寄存器 / 符号化 / 反汇编 / 修复前后实测）见本文档 §9.3
（`reports/test-report.md` §4 为等价的本地工作副本，按 review-memory §19 不入库）。

- 不含任何平台宏（无 `__OHOS__`），非空路径布尔语义逐字不变（纯 `||` 操作数互换）。
- 未修改其它任何上游源码文件；`Tests/`、`Configs/` 一个字节未动。
- 上游在该文件上的最后提交（`d2f12a916`，2022-05-14T12:22）早于本快照，此后未再触及，
  即该缺陷在上游未修复 —— 属上游缺陷，不是 OHOS 适配 hack。

### 补丁生成方式说明（R3 / R14）

`refresh-patch --auto` 已**先行执行**，失败并删除了它自己生成的补丁（原始输出原文）：

```
  ℹ️ refresh-patch --auto konclude 0.7.0-1138-git20220514-dfsg
  ℹ️   扫描变更（基于编辑追踪器）...
  ✅   变更文件 (1):
  ✅     ✏️ Source/Reasoner/Kernel/Algorithm/CCalculationTableauCompletionTaskHandleAlgorithm.cpp
  ℹ️   追踪到 1 个文件变更:
  ⚠️   ⚠️ 0001-Source-Reasoner-Kernel-Algorithm-CCalculationTableauCompletionTaskHandleAlgorithm.cpp.patch: dry-run 失败
  ℹ️   无有效新补丁，保留现有
```

（该失败在三次 `finish` 运行中均逐字复现，非偶发。）

```
⚠️ 0001-Source-Reasoner-Kernel-Algorithm-CCalculationTableauCompletionTaskHandleAlgorithm.cpp.patch: dry-run 失败
```

复现与归因：该文件是 **CRLF 行尾**（27676 个 CRLF / 4 个 LF）；`refresh_patch._diff_files`
用 `read_text()`（通用换行）读入，diff 的上下文行因此丢掉了 CR，`patch --dry-run` 必然
`Hunk 1 FAILED`（把整份补丁改成 CRLF 反而触发 toybox 的 `Removing DOS newlines`，同样失败；
只有 GNU `diff` 的原始输出——结构行 LF、内容行带 CR——能通过 dry-run，rc=0）。

因此按 **R14「脚本失败=手动模式入口」**改用 CR 保真的机械 diff 生成（`diff -U10`，上下文宽度
与工具一致，内容不是手写）：补丁应用后与探索目录 `.work` 逐字节一致，
sha256 `3a72fbff8b34394753f5e2d716441d6ebdefcd26dff42b5f247ff0d18a53bd86`。
仓库 400 个既有补丁中**含 CR 的为 0 个**，说明这是尚未收录的新模式（已备知识草稿与反馈）。

## 7. 验证结果（R51 与规则 12 的入库证据）

> 本节的表格是**随 PR 入库的证据承载处**：按 `.gitcode/review-memory.md` §19，
> `test-report`/`*.log` 属 PR 禁入文件，`reports/*.md` 亦被仓根 `.gitignore` 的 `reports/`
> 规则排除，因此逐条读数在此内联（`reports/test-report.md`、`reports/w3-local-ci.log`
> 为本地工作副本，不入库）。

### 7.1 上游测试清点（R51 第一步：清点）

| 清点项 | 实测 | 证据命令 |
|---|---|---|
| ctest / CMake 测试注册 | **0** | `grep -rn "enable_testing\|add_test(" .` → 0 命中；树内无 CMakeLists.txt |
| `make check` 目标 | **0** | 树内无 Makefile / configure；构建系统仅 qmake（3 个 `.pro` + `Konclude.pri`） |
| pytest / 其他框架 | **0** | 无 `tests/` 脚本目录、无 `*.py` 测试 |
| 上游数据集 | 12 个文件 | `ls Tests/`（8 个 OWL/OWLlink XML + 3 个 `.sparql` + 1 个 `.ttl`） |
| 文档化调用 | 13 个唯一 / 14 次执行 | `Readme.md` 9 行 + `./Konclude -h` 示例 9 行，去重后 13 |

**结论**：上游**无任何注册到自动化测试框架的用例**（注册数 0，非"未找到"）。

### 7.2 上游文档化调用实际执行（R51 第二步：运行，14 次全跑）

| # | 来源 | 调用（省略公共前缀 `./Konclude`） | rc | 判定特征 | 结论 |
|---|---|---|---|---|---|
| C1 | Readme L36 | `classification -w 2 -i Tests/roberts-family-full-D.owl.xml -o …` | 0 | 写出 23,957 B OWL/XML 直接层次 | PASS |
| C2 | Readme L37 | `satisfiability -i Tests/roberts-family-full-D.owl.xml -x …#Aunt` | 0 | `answered with 'Yes'` / `is satisfiable.` | PASS |
| C3 | Readme L52 | `owllinkfile -i Tests/galen-classify-request.xml -o …` | 0 | 470,339 B OWLlink 响应 | PASS |
| C4 | Readme L53 | `owllinkfile -i Tests/roberts-family-full-D-classify-realize-request.xml -o …` | 0 | classify+realize 响应 | PASS |
| C5 | Readme L54 | `owllinkfile -c Configs/default-config.xml -i Tests/1b-satisfiability-request.xml -o …` | 0 | `<BooleanResponse result="false"/>` | PASS |
| C6 | `-h` | `owllinkfile -i Tests/test-request.xml -o …` | 0 | 响应含 `<OK/>` | PASS |
| C7 | `-h` | `owllinkfile -c Configs/default-config.xml -i Tests/test-request.xml -o …` | 0 | 同上（带配置） | PASS |
| C8 | `-h` | `satisfiability -i Tests/galen.owl.xml -x http://ex.test/galen#ExternalIliacVein` | 0 | `is satisfiable.` | PASS |
| C9 | `-h` | `classification -w AUTO -i Tests/roberts-family-full-D.owl.xml -o …` | 0 | 写出层次文件 | PASS |
| C10 | `-h` | `realization -w AUTO -i Tests/roberts-family-full-D.owl.xml -o …` | 0 | 1,161,397 B 实现结果 | PASS |
| C11 | Readme L82 / `-h` | `owllinkserver -w 2 -c Configs/default-config.xml -p 18099` + HTTP POST | 0 | `HTTP 200` + `BooleanResponse`；服务端 `HTTP request successfully processed` | PASS |
| C12 | Readme L101 | `sparqlfile -s Tests/roberts-family-full-sparql-existential-variables-query-test.sparql -i Tests/roberts-family-full-D.owl.xml` | 0 | `Determined 331 answers for complex ABox query` | PASS |
| C13 | Readme L99 / `-h` | `sparqlserver -p 18098 -c Configs/querying-config.xml` | 服务 | `Listening on port '18098'` | PASS |
| C14 | Readme L100 | `sparqlfile -s Tests/lubm-univ-bench-sparql-load-and-query-test.sparql -o … -c Configs/querying-config.xml` | 0 | **结果集为空**（`<!-- end of part 1 -->`，无 `<solution>`） | **未通过**（依赖边界） |

统计：**执行 14/14，业务 PASS 13，未通过 1**（通过率 13/14 = 92.9%）。C14 未通过的原因是
其数据前置为 Turtle（`.ttl`），属依赖边界，已如实计入未通过，**未包装成豁免**。

### 7.3 消费者端到端用例（规则 12）

| 用例 ID | 场景 | 输入 | 预期业务输出 | 实测 |
|---|---|---|---|---|
| **CONSUMER-E2E-01** | 推理流水线：classification → satisfiability → consistency | `test_package/fixtures/family-reasoning.owl.xml`（Man=Person⊓Male、Father=Man⊓∃hasChild.Person、Male⊥Female、Contradiction=Male⊓Female）、`fixtures/inconsistent-family.owl.xml` | ①`Father ⊑ Man`（仅由定义推出）；②层次传递闭包含 `Father ⊑ Person`；③`Contradiction ≡ owl:Nothing`（由不相交性推出）；④负向对照 `Woman ⊑ Man` **不成立**；⑤`#Father`=`Yes`、`#Contradiction`=`No`；⑥重叠断言库 inconsistent、一致库 consistent | **PASS 10/10 断言** |
| **CONSUMER-E2E-02** | OWLlink 服务端（TCP loopback） | `fixtures/owllink-satisfiability-request.xml`（自包含 KB + `IsClassSatisfiable(#Contradiction)`） | ①HTTP 200；②响应为 OWLlink `ResponseMessage` 且含 `<OK/>`；③`BooleanResponse result="false"` | **PASS 6/6 断言** |

合计：**2 个完整消费者端到端用例，2 PASS / 0 FAIL，16/16 断言**。用例驱动的是
`conan create` **安装后的** `bin/Konclude`（`self.dependencies[tested_reference_str].package_folder`），
不使用源码树产物；CONSUMER-E2E-01 断言的全部是**蕴含事实**并含负向对照，
CONSUMER-E2E-02 的判定不由单个布尔值承担：请求夹具内的 `<ExpectedResult>` 与真实答案同值，
故该用例的不可伪造性来自**组合断言**——HTTP 200、响应为 OWLlink `ResponseMessage` 且含 `<OK/>`、
安装后二进制自身输出的 `HTTP request successfully processed` 服务端日志行，
以及 CONSUMER-E2E-01 的正向蕴含断言与负向对照；单纯回显请求的退化服务无法同时满足这些条件。

### 7.4 W3 与门禁结论（实测回填）

- **G2（conan-verify，干净 `conan create`）**：PASS（G1/G2/G3 全过，`配方验证通过`，
  含 test_package 消费者用例），可标记 `published`；本包因未 upload 取 `built`。
- **W3（`ci/conan/build_and_test.sh`，范围 = 本任务真实 PR 变更集）**：
  ```
  JC_RESULT=pass                       # Junk Files: 0，涉及软件数 1（合规）
  L0_RESULT=pass: all checks passed
  L1_RESULT=pass: upstream tests + test_package executed
  L2_RESULT=pass: Konclude --version OK
  L4_RESULT=pass: patches clean
  L5_RESULT=pass: bin/ has content
  L1e 破坏性反向验证: [sabotage] bin/ moved away ->
      [ok] Negative test confirmed — test genuinely depends on konclude
  cases executed: 2/2  assertions: 16/16 passed, 0 failed  elapsed 1.5s
  ━━━ Build Summary ━━━  Total: 1  Success: 1  Failed: 0  Pass rate: 100.0%
  ```
  即**消费者端到端用例是在 W3 的干净 `conan create` 内真实执行的**（不是只在探索目录跑过），
  且 L1e 破坏性反向验证证明该测试确实依赖被测包。
- **W3 回执**：版本目录 `.ci-result.json`（该文件被仓根 `.gitignore` 忽略，不入 PR）
  记录 `exit_code: 0`、`integrity_hash: 89eda5b1f189c5f5`、
  `log_sha256: c7bee1148bd6b1aee3b122eed410f23ecaddb51665bbb79a2bd61419730dcd5f`，
  由工具生成、未手改（该轮对应最终配方，即含 code-style 方法序修正与证据指针修正的版本）。
- **上游测试修改**：**未修改任何上游测试或数据集**（上游无测试用例文件；`Tests/`、`Configs/` 未改一字节）。
- **豁免**：无。C14 为依赖边界导致的未通过，非豁免。
- **源 URL 还原**：W3/G2 期间工具会临时把 `conandata.yml` 的官方 URL 改写为镜像/`file://` 预下载形式
  （`pre-download: conandata.yml 已还原为官方 URL` 仅还原到改写前一层）；本轮结束后已按备份逐行
  还原为**官方单值 URL** 并校验与原始内容 `diff` 为空，残留 `.orig`/`.ghfast-bak` 已删除。

## 8. 注意事项

- 本包为 **application** 类型（`bin/Konclude`），按 R38 在软件级目录提供了 `commands.json`；
  尚未发布，`binary` 字段为 `false`。
- 运行时需要 Qt5 共享库：Conan `conanrun` 环境（`LD_LIBRARY_PATH`）提供；产物 RUNPATH
  由 qmake 写入 Qt 包路径。
- `Configs/*.xml` 随包安装到 `res/konclude/Configs/`，因为上游文档化调用以
  `-c Configs/default-config.xml` 形式引用配置。

## 9. 提交政策、口径与门禁处置（如实留痕）

### 9.1 `-dfsg` 后缀的语义

包版本 `0.7.0-1138-git20220514-dfsg` 中的 `-dfsg` **只是与 Debian/Ubuntu 源码版本
`0.7.0+1138+git20220514~dfsg` 对齐的版本映射标签**（`+`/`~` 按本仓库既有惯例写作 `-`，
且 PF9 要求分支名与版本目录名一致）。本包取的是**上游官方归档**（`github.com/konclude/Konclude`
的 commit 归档），**没有**做 Debian 的 dfsg 剥离——树内 x86_64 预编译件（`External/**`）依然存在，
只是不参与 aarch64 构建。请勿据此误读为"包内已无预编译件"。

### 9.2 上游版本号与产物自报 revision

上游 `revision-git.h`（归档内既存文件）自报
`KONCLUDE_VERSION_GIT_REVISION_NUMBER 1138` / `KONCLUDE_VERSION_GIT_TAG_NAME_STRING "v0.7.0"` /
`KONCLUDE_VERSION_GIT_REVISION_HASH_STRING "500e11d9"`。因此 `Konclude -h` 打印
`Version v0.7.0-1138 - 500e11d9`。这是**上游在 tag v0.7.0-1138 时代的既存内容**，
与本任务实际取源的 commit `056334ad…`（tag 之后的开发快照）不同，属上游归档自身状态，
非本适配引入；已在此说明以免评审对照源码 commit 时产生疑问。

### 9.3 上游快照 SIGSEGV 的完整证据链（对应补丁 0001）

| 环节 | 证据 |
|---|---|
| 现象 | `Tests/roberts-family-full-D.owl.xml`（SROIQ）的 `classification`/`realization` 稳定 SIGSEGV（**3/3 复现**）；`consistency`/galen/lubm/自建小本体正常 |
| 系统故障日志 | `cppcrash-com.huawei.hmos.hishell-…-20261016183217819.log`（`-w 2`）与 `…183234721.log`（`-w 1`）：`Reason:Signal:SIGSEGV(SEGV_MAPERR)@0x0000000000000010`；`Fault thread info: Tid:…, Name:QThread` |
| 寄存器 | `x0:0 x1:0 x2:0x665dd520d0 x3:0x665dd520d0` → 第一实参为 NULL、第二实参非空 |
| 符号化 | `llvm-addr2line`：`#00 hasIdenticalConceptOperands` ← `#01 applyATLEASTRule` ← `tableauRuleProcessing` ← `handleTask` ← `CTaskProcessorThreadBase::processingLoop` |
| 反汇编 | `llvm-objdump -d`：`0x6d8f00: ldr x9,[x9,#16]`（内联的 `getCount()` 链表遍历）→ 以 `x1=0` 为基址读出地址 `0x10`，与故障地址一致 |
| 源码 | `CCalculationTableauCompletionTaskHandleAlgorithm.cpp:16106`：空值守卫 `\|\| !atmostConcept->getOperandList()` 写在 `hasIdenticalConceptOperands()` 调用**之后**，短路求值使其永远晚一步 |
| 修复 | 仅把作者原有的同一守卫提前（纯 `\|\|` 操作数互换，非空路径布尔结果逐字不变） |
| 修复后 | 同一命令 rc=0，882 ms 完成，输出 23,957 B 有效层次；C1/C9/C10 全部 PASS |
| 上游状态 | 该文件最后一次上游提交为 `d2f12a916`（2022-05-14T12:22），早于本快照 commit（13:10），此后上游未再触及 → 缺陷在上游未修复 |

### 9.4 W3 本地 CI 门禁的范围问题与处置（如实记录）

`ci/scripts/junk_check.sh` 的检查范围按优先级选择：① `pr.diff`（PR diff 模式，远端 CI 的
`checkout-pr` 即用此模式）② `git diff origin/main...HEAD`（incremental）③ 回退 `git ls-files`（full）。
本任务在 **commit 授权前**工作：分支无提交 → `origin/main...HEAD` 为空 → 回退 **full 模式**
（46,386 个文件），于是把**他人包目录**里既存的 6 个 `.staging-verified`
（kcachegrind/libbfio/libdazzle/oscpack/reflex/thc）判为 JC1/JC5 违规，并把 2,940 个包判为
JC6"多软件"违规——与本任务变更无关。另外本机 `origin` 是滞后 fork，使增量口径亦不可用。

处置：按该脚本自身支持的 `JUNK_PR_DIFF`（PR diff 模式）入口，提供**本任务真实 PR 变更集**后重跑。
（口径说明：该次复核范围为 **16 个文件**——即终态 PR 变更集 14 个文件，外加当时一并列入的
`reports/pr-body.md`、`reports/test-report.md` 两份本地证据。二者按 `review-memory §19`
与仓根 `.gitignore` 的 `reports/` 规则**不入库**，故**终态 PR 变更集为 14 个文件**，见 §9.5。）
实测该模式下 `Junk Files: 0`、`涉及软件数: 1（合规）`、`JC_RESULT=pass`。
这与远端 CI 的 prdiff 模式同口径（CI 由 checkout-pr 提供 `pr.diff`），属**纠正检查范围**，
未关闭或绕过任何检查项；本任务变更中确实不存在运行时状态文件、二进制、压缩包或隐藏文件。

**结论**：本包 W3 在"以真实 PR 变更集为范围"的前提下通过；不在该前提下运行时，JC 的
full 回退会产生上述假阳性。该项已如实留痕于本节（可复核的一切读数均已内联于 §7.4；
`reports/w3-local-ci.log` 为本地工作副本，按 `review-memory §19` 与仓根 `.gitignore` 的
`reports/` 规则不入库）。

### 9.5 finish 就绪检查与 ARCHIVE-SPEC v3.0 的冲突（如实记录，未按旧口径补文件）

`finish` 末尾的就绪预检报出 `2 项未就绪` 与 `1 个一致性问题`（`失败步骤: step5b, step7, step8`），
具体为要求存在 `packaging/` 目录与 `.staging-verified` 空文件：

```
❌ packaging/       — 需创建 packaging/ 目录并打包
❌ .staging-verified — 需创建 .staging-verified 空文件
```

而现行 `knowledge/ARCHIVE-SPEC.md`（v3.0）已把二者列为**废弃**：`packaging/` 由 Conan 体系替代
（"packaging/ 废弃"、`packaging/*.tar.gz` 删除），`.staging-verified` 亦标注"废弃：由 conan_verify 替代"。
同时 `ci/scripts/junk_check.sh` 的 JC 门禁与 `review-memory` 也把打包产物/中间标记视为禁入物。
因此**未创建这两个文件**——以现行规范与门禁为准，陈旧的就绪检查不能反过来要求制造会被 JC 拦截的产物。
本包的真实就绪证据是：干净 `conan create`（G2 PASS）+ W3 五门禁全 PASS + `.ci-result.json`（exit_code 0）。

另外 `finish` 建议的提交命令是 `git add archives/ knowledge/drafts/`；本任务的 PR 变更集为
**14 个文件**（`archives/k/konclude/**` 中除 `reports/*.md` 外的全部正式文件）。
`reports/pr-body.md` 与 `reports/test-report.md` 按 `review-memory §19`（`test-report` 为 PR 禁入件）
与仓根 `.gitignore` 的 `reports/` 规则**不入库**，其关键读数已内联到本文件 §7 与
`test_package/MANIFEST.yml`。
---

**编译结束**: 2026-10-16 22:56
**最终状态**: built
