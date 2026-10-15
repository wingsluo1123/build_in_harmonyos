# biopython 1.88 适配笔记

## 编译环境
- **类型**: Python + **13 个 C 扩展**（实测 `pyproject.toml` 的
  `[[tool.setuptools.ext-modules]]`；sdist 内自带 `.c` 源，**无需 Cython**）
- **编译日期**: 2026-09-30
- **目标**: HarmonyOS PC（OHOS aarch64 / Python 3.12.9）

## 为什么需要这个包
`biopython` 是 **qcat 的硬依赖**（qcat 的 `install_requires` =
`biopython` / `parasail` / `six` / `pyyaml`）。qcat 是 Nanopore 测序数据
demultiplexing 工具，其 barcode 解析依赖 biopython 的 SeqIO。

## 依赖声明（重要）
上游 `pyproject.toml` 的 `[project] dependencies` 只有一个：
```
numpy
```
`numpy/2.5.2` **已在 ohpcd 制品仓**（另有 1.26.4）。

## 包结构
```
Bio/          ← 主包（含 13 个已编译 .so）
BioSQL/       ← BioSQL 适配层
Scripts/      ← 上游命令行脚本
Tests/        ← 上游测试（215 个 unittest 文件）
```

## 13 个 C 扩展（实测清单）
| 扩展模块 | 源文件 |
|---|---|
| `Bio.Align._aligncore` | `Bio/Align/_aligncore.c` |
| `Bio.Align._alignmentcounts` | `Bio/Align/_alignmentcounts.c` |
| `Bio.Align._codonaligner` | `Bio/Align/_codonaligner.c` |
| `Bio.Align._pairwisealigner` | `Bio/Align/_pairwisealigner.c` |
| `Bio.Align.substitution_matrices._arraycore` | `Bio/Align/substitution_matrices/_arraycore.c` |
| `Bio.cpairwise2` | `Bio/cpairwise2module.c` |
| `Bio.Nexus.cnexus` | `Bio/Nexus/cnexus.c` |
| `Bio.motifs._pwm` | `Bio/motifs/_pwm.c` |
| `Bio.Cluster._cluster` | `Bio/Cluster/cluster.c` + `clustermodule.c`（带 `-DCLUSTER_USE_PYTHON_MEMORY`） |
| `Bio.PDB.ccealign` | `Bio/PDB/ccealignmodule.c` |
| `Bio.PDB.kdtrees` | `Bio/PDB/kdtrees.c` |
| `Bio.PDB._bcif_helper` | `Bio/PDB/bcifhelpermodule.c` |
| `Bio.SeqIO._twoBitIO` | `Bio/SeqIO/_twoBitIO.c` |

## 编译步骤（conan create 全流程）

### 1. 源码获取（source()）
```yaml
url: https://files.pythonhosted.org/packages/f6/a0/cf657d076ec56a5f9e5c29a560c1f97b8eb6ae6608dc8bc95b4e2437f129/biopython-1.88.tar.gz
sha256: 9aaa31c0bda4d059f7b2ee00bfdb5cbb73ade3057aa4b737a7cc0187091d071a
size: 19858058  (19.9 MB)
```
实测下载并校验 sha256 一致。

### 2. 构建（build() 前半）
```bash
python3 setup.py build_ext --inplace
```
实测成功编译 **13/13 个 .so**，编译后 `import Bio` / `Bio.Align` /
`Bio.Cluster` / `Bio.PDB` 均正常（HMDFS 上可 dlopen，**未触发**签名问题）。

> ⚠️ 上游 `setup.py` 仅 19 行（纯 `setup()` 调用），配置全部在
> `pyproject.toml`；执行时会打印 DeprecationWarning（上游已弃用
> `setup.py` 调用），**不影响构建**。

### 3. 上游测试（build() 后半——R51 实测回填）
上游用自带的 `Tests/run_tests.py`（PyUnit/unittest 风格，215 个测试文件）：
```bash
cd Tests && python3 -u run_tests.py --offline
```
`--offline` 跳过需联网的用例（本环境无外网）。

> ⚠️ **`run_tests.py` 会挂死在 `test_BioSQL_sqlite3`**（实测：进程 SLEEP，
> 停滞 >2 分钟无输出，复现两次）。BioSQL 组需数据库配置（`biosql.ini`），
> sqlite3 路径虽可连接但**测试结构在本环境挂住**。故实测时**排除 6 个
> BioSQL 用例文件**：`test_BioSQL_MySQLdb(_online)` /
> `test_BioSQL_mysql_connector(_online)` / `test_BioSQL_psycopg2(_online)` /
> `test_BioSQL_sqlite3`。

**实测最终结果（2026-09-30，OHOS aarch64 / Python 3.12.9）**：
```
Ran 201 tests in 157.394 seconds
DONE_RC=0
```
**175 passed / 26 skipped / 0 failed / 0 errors**（175 + 26 = 201，自洽）。

- **0 失败、0 错误** —— `DONE_RC=0`。
- 26 例 skipped 全部为**上游环境条件**：需联网（Entrez/ExifTool）、缺 SQL
  驱动、缺外部二进制等，**非我方排除**。
- 13 个 C 扩展全部编译成功，且 HMDFS 上**正常 dlopen**
  （实测 `import Bio` / `Bio.Align` / `Bio.Cluster` / `Bio.PDB` 均通过，
  **未触发**代码签名问题）。

> 计数口径说明：`171` 与 `26` 相加不等于 201 是因为上游多行输出的用例
> （如 `test_NCBIXML` 先打印 expat 跟踪再单独一行 `ok`）不会在同一行出现
> `... ok`。故**以 `Ran 201` 与 skipped 数反推** passed = 201 − 26 = 175。

## 注意事项
1. **sdist 自带 `.c` 源**（14 个），无需 Cython —— 与 Cython 包不同。
2. **必须**在 `PYTHONPATH` 中包含 numpy 的 site-packages（biopython
   运行期 `import numpy`）。
3. 上游 `Bio/__init__.py` 在源码树内导入时会警告
   "importing Biopython from inside the source tree"——属正常提示。
4. BioSQL 组测试需数据库配置且**在本环境挂死**，逐条归因，**未加入允许清单**。
5. `Tests/` 不在交付产物内（仅用于构建期测试），仅交付 `Bio/` / `BioSQL/` / `Scripts/`。

## 判据采集补正：27 个「判据不足」的 doctest 站点（2026-10-14）

前几轮 CI 的 marker 一直是 `doctest_kinds: cascade=108, mismatch=0, other-error=0,
unknown=27`，而这 27 个 `unknown` 是归因硬门禁的**唯一**卡点（`unknown_n == 0`
不成立 → 23 例失败保持硬失败、构建中断）。当时的样本只写 `站点 -> unknown`，
日志里没有块内原文，无法判断这是「采集缺陷」还是「真实的第二种失败形态」，
故先只补采集（提交 `bd56375f80`），让样本带上 `raised=`、块行数与**块尾 6 行**。

**下一轮 CI 的原文给出了答案**：27 个站点的块尾全部是同一条

```text
Bio.MissingPythonDependencyError: Please install NumPy if you want to use Bio.Align.
```

由 `Bio/Align/__init__.py:31` 抛出，即**环境里没有可用的 NumPy**（见「注意事项 2」：
numpy 本就是外部要求）。它们此前被判 unknown，是因为异常名是**限定名**
（`Bio.MissingPythonDependencyError`），而原正则 `\w*(?:Error|Exception)\s*:` 的
`\w` 不吃点号 → 这类行一条都匹配不上，直方图只显示 `<unnamed>`。

据此按证据改判定：

- 异常行正则与取类型的正则**同时**放宽到 `[\w.]*`——只改一处会在 `None.group(1)`
  上抛 `AttributeError`；
- 族判定改取**末段**比较，并把 `MissingPythonDependencyError` 与
  `NameError` / `ImportError` / `ModuleNotFoundError` / `AttributeError` 同归
  **cascade**：它是 biopython 自己定义的「某个可选依赖不在」异常，与「模块/名字
  不可用」同族，且不是断言或值不符，故不能算 `other-error`；
- 归因理由串改为**同时**覆盖两种机理（E212 无法 dlopen 用户可写路径下的 .so +
  无可用 NumPy），不再只写 E212。

**反向对照**（夹具用本轮带回的**真实**块尾，而非自造）：`unknown=0`；NumPy 缺依赖
与 NameError 同判 cascade；另行构造的 `Expected:/Got:` 块**仍判 mismatch**——
即这次改动不会把真正的值不符洗白，这是改动是否可接受的关键。
