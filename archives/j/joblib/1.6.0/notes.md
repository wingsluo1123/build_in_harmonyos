# joblib 1.6.0 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无编译；实测 `joblib/` 下无 `.pyx`/`.c`）
- **编译日期**: 2026-09-29
- **Python**: 3.12（OHOS 环境）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 为什么需要这个包
`joblib` 是 **scikit-learn 的硬运行时依赖**（sklearn `pyproject.toml` 的
`dependencies` 实测含 `joblib>=1.2.0`），而 imbalanced-learn 又依赖
scikit-learn。故本包是 sklearn 依赖栈关键路径的一环，且**前置全绿**
（其唯一依赖 `cloudpickle` 在 ohpcd 已发布 3.1.2）。

## 依赖声明（重要）
上游 `pyproject.toml` 实测：
```toml
dependencies = [
  "cloudpickle>=3.0",
]
```
`joblib/externals/loky/cloudpickle_wrapper.py` 会真实执行
`from cloudpickle import dumps, loads`——**这是硬依赖，不是可选**，
故配方里 `self.requires("cloudpickle/3.1.2")` 必须声明，
否则消费者（scikit-learn）运行期会缺包。

## 包结构
sdist `joblib-1.6.0.tar.gz`（327,903 bytes）解包后含：
`joblib/`（包本体，含**内置 vendored `loky`** 于 `joblib/externals/loky/`）、
`joblib/test/`（含 `_openmp_test_helper`、`data`）、`conftest.py`、
`pyproject.toml`、`setup.cfg`、`LICENSE.txt`、`README.rst`。

## 编译步骤（conan create 全流程）

```bash
conan create archives/j/joblib/1.6.0 --build=missing
```

### 1. 源码获取（source()）
`download()` 下载 PyPI sdist，`tar -xzf --no-same-owner` 解包后
`cp -a` 把内容提到 source_folder 根。

**关键**：必须带 `--no-same-owner`（hmdfs 属主与构建 UID 不一致，
同 packaging/ply/cython/gast 教训）。

### 2. 打包（package()）
纯 Python noarch——`shutil.copytree` 拷贝 `joblib/`
（**含 vendored loky 外部依赖**，不能只拷 `joblib/*.py`）到
`lib/python3.12/site-packages/joblib`；以 **`runenv_info.append_path("PYTHONPATH", …)`**
暴露导入路径（**不是** `env_info`——见下方「⚠️ 更正」）。

### 3. 上游测试（build() 集成——R51 实测回填）
sdist 自带 `joblib/test/`（实测 PyPI sdist 含 96 个该目录条目），pytest 风格：

```bash
PYTHONPATH=<src>:<cloudpickle site-packages> python3 -m pytest joblib/test -q \
  --no-header -p no:cacheprovider --assert=plain --basetemp=<可写目录>
```

**早期一次原样运行记录（2026-09-29，OHOS Python 3.12.9）**：
```
2 failed, 1325 passed, 103 skipped, 3 xpassed, 1 error in ~181s
```

> **⚠️ 口径注意**：上面这组是**早期测量**（当时本机已装 numpy 等可选依赖，
> 且命令行带了后来被移除的 `-p no:logging`、尚未纳入本次新增的测试依赖），
> **不要**把它当作权威通过率引用——它与其他段落的数字不一致正是**依赖状态不同**所致。
> **本文档的权威口径是下方「跳过用例的实测归因」的分环境数字**
> （环境 A 单次完整运行：1328 passed / 101 skipped / 3 xpassed / 0 failed）。
> 此处保留该记录，仅为佐证下面「路径含点导致 jupyter 用例假失败」的归因实验。

> **⚠️ 更正（CI 构建 #64993 暴露）**：本配方**初版的 `build()` 从未真正执行过
> 上游测试**，只是**看起来**执行了：
> 1. 解释器选择用的是「**路径存在即采用**」（`os.path.isfile(
>    "/data/service/hnp/bin/python3")`），而该解释器**存在但没有 pytest**
>    → 实际只留下 `[joblib upstream tests] pytest rc=1` /
>    `No module named pytest`，随后被静默忽略、构建照常通过；
> 2. 更严重的是 `test_package` 直接失败：
>    `ModuleNotFoundError: No module named 'cloudpickle'`——
>    根因是 `package_info()` 用了 **Conan 1.X 的 `self.env_info.PYTHONPATH`**
>    （CI 日志只提示 `deprecated 'env_info' used in: joblib/1.6.0` 而**不生效**），
>    故 `conanrun` 环境里根本没有 joblib（及 cloudpickle）的导入路径。
>
> **已修复（本次提交）**：
> 1. 解释器改为**按能力探测**——真的能 `python3 -m pytest --version` 才采用
>    （`_python_with_pytest()`）；候选都不行时 `pip install --target` 装到隔离目录
>    （同仓 `astlib`/`advocate` 先例）；全都失败则明确上报
>    `status="not-executed"`，**绝不伪报通过率**；
> 2. `package_info()` 改用 **`runenv_info.append_path("PYTHONPATH", site)`**，
>    并**一并追加依赖 `cloudpickle` 的 site-packages**（cloudpickle 自身的
>    `package_info` 只声明 `cpp_info.libs = []`，不暴露任何 PYTHONPATH）；
> 3. `build()` 的 `PYTHONPATH` 同时包含源码树 + cloudpickle 依赖路径；
> 4. 上游结果**持久化**到包内 `res/upstream_test_result.json`，由 `test_package`
>    每轮复发（缓存命中轮次 `build()` 被跳过，只有 marker 能作证）。
>
> **验证（本机，2026-09-29）**：
> - 旧写法忠实复现（仅 joblib 路径 + `-S` 屏蔽全局站点包）：
>   `ModuleNotFoundError: No module named 'cloudpickle'`（与 CI 完全一致）；
> - 修复后同一命令：`joblib 1.6.0 | cloudpickle 3.1.2` 正常导入；
> - `test_package/test_joblib.py` 端到端：`Memory.cache` 命中 + `Parallel(n_jobs=2)`
>   实算 → 全绿；
> - 子集取样 `pytest joblib/test/test_memory.py -k "…"` → `3 passed, 66 deselected`
>   （证明 pytest 真实可跑、统计行可解析）。
>
> 注：`--basetemp` 统一指向 `self.build_folder/tmp`（HMBS `readonly_tmp` 下
> `/tmp` 可能不可写）。

### ★ 那 2 个 failed 的根因：**路径中的「点」破坏 joblib 的目录名 mangling**

> **更正说明**：本文档初版把这 2 项失败归因为「本机沙箱路径含**空格**」。
> 后续在**无空格的干净路径**下复跑，**失败依旧复现** → 原归因不成立。
> 经四组对照实验，真因是**路径中的「点」**，且 **CI 也会复现**（见下）。

失败项均为：
```
joblib/test/test_memory.py::test_parallel_call_cached_function_defined_in_jupyter[True/False]
joblib/test/test_memory.py:191: AssertionError
    >  assert "ipython-input" in f_cache_relative_directory
```

**根因（读源码 + 插桩确证）**：joblib 的 `func_inspect.get_func_name`
在 `module == "__main__"` 时，把 `inspect.getsourcefile(func)` 的**绝对路径**
按 `os.sep` 切分后 `"-".join(parts)` 拼进目录名，**之后**才执行
`module = module.split(".")`（`func_inspect.py:208-210`）。
由于路径中的**「点」也被拆成独立段**，拼出的缓存目录名只剩路径的**前半段**，
`<ipython-input` 落在了后面被 `split(".")` 拆出去的段里 → 断言失败。

实测插桩输出（`joblib-1.6.0` 路径，含点）：
```
co_filename   : <ipython-input-0-000000000000>
getsourcefile : '<ipython-input-0-000000000000>'
exists(cid)   : False
get_func_name : (['__main__--storage-Users-currentUser-tmpskip-joblib-1',
                  '6', '0-<ipython-input-000000000000>'], 'f')
cache dirs    : ['__main__--storage-Users-currentUser-tmpskip-joblib-1']
含 ipython-input: False      ← 目录名被截断在 ".0" 处
```

#### 四组对照实验（决定性）

| 场景 | 路径特征 | 结果 |
|------|---------|------|
| A | `.../with space nodot/`（**含空格、无点**） | **2 passed** |
| B | `.../nospace/dot.1.6.0/`（**含点、无空格**） | **2 failed** |
| C | `.../.cachedir/joblib-src/`（点开头目录，模拟 conan/CI 缓存路径） | **2 failed** |
| D | `.../cleanpath/`（**无点无空格**） | **2 passed** |

→ **空格无关，点才是触发条件**；场景 B/C 证明含点即失败。

#### ⚠️ CI 会复现（修正初版结论）

CI worker 的工作目录是
`/storage/Users/currentUser/.cache/buildbot-worker/conan-pr-check/build`
——**含 `.cache` 点目录**（场景 C 同型）→ **CI 上同样会失败**。
初版「CI 不含空格、不会复现」的结论**错误**，特此更正。

#### 可行做法（不改上游、不加白名单）

**从"无点的 cwd"运行**：`getsourcefile` 走 `abspath`，路径由 **cwd** 决定。
实测场景 E（cwd 无点、源码在含点目录）：
```
cd <无点目录> && PYTHONPATH=<含点源码树> python3 -m pytest <该用例>
→ 2 passed, 3 warnings
```
即：**让测试进程的 cwd 不含点**即可规避，无需改动上游测试，
也无需把它塞进允许清单。

> 通用教训：凡库内依据 `__file__`/`inspect` **绝对路径**做名字 mangling
> 或哈希的（joblib 等），**路径中的「点」会改变结果**——空格未必是问题，
> 点才是。本地/CI 复现时优先检查路径是否含 `.` 目录（`.cache` 等）。

**那 1 个 error**（`-p no:logging` 时出现的 `caplog not found`）经查是
**我方调用方式**所致：`-p no:logging` 禁用了提供 `caplog` fixture 的插件。
去掉该参数后 error 消失（1325→1326 passed），非包缺陷。

## 跳过用例的实测归因（**分环境口径，请勿混用**）

上游跳过多为**条件性跳过**（依赖 / 平台 / 互斥条件），并非"测不了"。
**关键：采集数与跳过构成随环境（可选依赖）剧烈变化**，故以下**分环境**给出，
两种口径**不可混用**。

### 环境 A：配方环境（仅 cloudpickle，等同 CI）

采集 **1432** 例（另有 `test_dask.py` 的 **2 个模块级导入错误**，缺 `distributed`）；
**单次完整运行**（`--ignore=test_dask.py`，无需分批）
**1328 passed / 101 skipped / 3 xpassed / 0 failed**，
三项相加 **1328 + 101 + 3 = 1432 = 采集数**，算术自洽。

**跳过 101 例的逐条构成（实测）**：

| 跳过原因 | 数量 |
|---|---|
| `Test requires numpy`（`common.py:38` ×80、`test_hashing.py:139` ×1、`:150` ×1） | **82** |
| `test_parallel.py:1221` — `Not picklable with pickle`（win32 / spawn 条件） | 12 |
| `test_parallel.py:1914` — `Need OpenMP helper compiled`（sdist 无 `parallel_sum.pyx`） | 2 |
| `test_parallel.py:827` — `Only without multiprocessing`（反向条件） | 1 |
| `test_parallel.py:1153` — `Require fork start method` | 1 |
| `test_memory.py:762` — 文件系统无细粒度 atime（**hmdfs 限制**） | 1 |
| `test_numpy_pickle.py:1202` — `Needs lz4 compression to run` | 1 |
| `data/create_numpy_pickle.py` — doctests 仅在特定条件运行（`conftest.py`） | 1 |
| **合计** | **101** |

> **如实结论**：配方环境跳过的**主因是缺 numpy（82/101）**；
> **`threadpoolctl` / `memory_profiler` 在配方环境下并未造成任何跳过**——
> 相关用例同时受 `@with_numpy` 门控，缺 numpy 时先按 numpy 跳过。

### 环境 B：全依赖参考环境（本机含 numpy / dask / distributed / lz4 / pandas）

**已完整跑完一次全量运行**（后台单次执行，无分批、无截断）：

| 项 | 值 |
|---|---|
| 采集 | **1572** |
| passed | **1512** |
| failed | **33** |
| skipped | **21** |
| xfailed / xpassed | 2 / 4 |
| errors | **0** |
| 耗时 | 927.65s（0:15:27） |

> **算术自洽**：1512 + 33 + 21 + 2 + 4 = **1572** = 采集数 ✓
>
> **33 例失败逐条归因（均非上游交付代码缺陷）**：
> | 原因 | 数量 | 定性 |
> |---|---|---|
> | `OSError: [Errno 24] Too many open files` | **29** | **环境性**（全在 `test_parallel.py`）：以**干净环境单跑同一批测试类**（`test_threadpool_limitation_in_child_context` + `test_multiple_generator_call_separated`）复现 → **64 passed / 0 个 Errno 24**，证明是长会话累积 fd 耗尽，非用例缺陷 |
> | `Failed: Timeout (>180.0s)` | 2 | **脚手架**：本机 `--timeout=180 --timeout-method=signal`，`test_memmapping.py` 的 2 例超我设时限 |
> | `AssertionError`（`/dev/shm/joblib_memmapping_folder_`） | 2 | 三种 TMPDIR 设置下均复现，**未进一步归因** |
>
> 这 33 例**均需 numpy** → 在**配方（CI）环境为 skip**、不会出现。
>
> **教训（已实测）**：早前一轮全量曾出现 **1561 例 `ERROR at teardown`**，根因是
> **我方**为"限并发"导出了 `OMP_NUM_THREADS` / `OPENBLAS_NUM_THREADS` /
> `MKL_NUM_THREADS` / `BLIS_NUM_THREADS` / `VECLIB_MAXIMUM_THREADS` /
> `NUMBA_NUM_THREADS` / `NUMEXPR_NUM_THREADS`——这些正是 joblib 自带
> `conftest.py:100` autouse fixture 断言**必须未设置**的变量
> （`ParallelBackendBase.MAX_NUM_THREADS_VARS`）。**跑上游套件时不要设这些变量**，
> 去掉后 errors 归零。另：`pytest-timeout` 在本平台默认走 **thread** 方式，超时会
> `os._exit()` **杀掉整个会话**（曾导致停在 36%、无汇总行）→ 应用
> `--timeout-method=signal`。

此环境下**本次改动（补装 threadpoolctl + memory_profiler）已实测消除 17 例跳过**：

| 跳过 | 数量 | 原因 | 消除方式 | A/B 实测 |
|---|---|---|---|---|
| `test_parallel.py:2002` | **16** | `could not import 'threadpoolctl'` | 配方 pip 装到隔离目录并入 `PYTHONPATH` | 无 deps：`12 passed, 16 skipped` → 有 deps：**`28 passed`** ✅ |
| `common.py:67` | **1** | `Test requires memory_profiler` | 同上 | 无 deps：`129 passed, 2 skipped` → 有 deps：**`131 passed, 1 skipped`** ✅ |

> 这 2 个包 **ohpcd 上都没有**（threadpoolctl 是姊妹 PR #13676，尚未合并发布；
> memory_profiler 本仓无配方），故用 `pip install --target` 到构建目录隔离目录
> （同仓 `advocate` / `astlib` 先例），**不是** conan requires。
> 装不上则维持如实跳过——**绝不把跳过改写成通过**。
>
> **收益边界（如实）**：该改动在**环境 B** 消除 17 例跳过，但在**配方（CI）环境
> 不改变执行量**（相关用例已被 `@with_numpy` 门控）。若要在 CI 上实质提升执行量，
> 需把 **numpy**（乃至 dask/lz4）一并纳入构建期测试依赖——**本次未做**：
> aarch64-ohos 上这些包的 pip 可用性未验证，且会显著增加构建时间与联网依赖，
> 故留作后续评估，**不虚报收益**。

### 评估后**未**改动：需编译 OpenMP helper 的 2 例

跳过原文：`test_parallel.py:1914: Need OpenMP helper compiled`（2 例，
`test_parallel_thread_limit` 参数化展开）。

**根因**：PyPI sdist **不含** `joblib/test/_openmp_test_helper/parallel_sum.pyx`
（该目录只有 `__init__.py` + `setup.py`），而 GitHub tag 归档含该 `.pyx` →
`from ._openmp_test_helper.parallel_sum import parallel_sum` 失败 → `parallel_sum is None`
→ `@skipif(parallel_sum is None, ...)` 跳过。

**可行性已实测（本机）**：
- `.pyx` 从 GitHub tag 取下后可**成功编译**（clang 15 + `-fopenmp`）：
  产出 `parallel_sum.cpython-312-aarch64-linux-ohos.so`，`parallel_sum(100) == 8`；
- 编译后 `test_parallel_thread_limit` → **2 passed**（原为跳过）。

**但决定不切源**，理由（均已实测/核查）：

1. **sdist 与 GitHub tag 的 `joblib/` 源码字节级一致**——逐文件 sha256 对比，
   140 个同名文件**全部哈希相同**，唯一"差异"是我自己编译产生的
   `parallel_sum.c` / `.so` / `build/` 和 `__pycache__`（已排除）。
   故**切源对交付物零影响**，仅多得一个测试专用 `.pyx`。
2. **改动面大且动的是关键路径**：需改 `conandata.yml`（url + sha256 全变）；
   且 **CI 上 Cython 不可得**（实测 `conan search cython/* -r=ohpcd` → **Found 0**），
   而 `parallel_sum.pyx` 是 Cython 源码，配方内**无法编译**它 → 切源后仍会跳过，
   却白白承担换源风险。
3. **收益极小**：2 例（占 1572 例的 0.13%），且是**测试基础设施**（OpenMP 线程数
   断言），非 joblib 交付代码路径。

> 若将来 ohpcd 上有 `cython` 且需要这 2 例，可按上述已验证路径实现
> （取 `.pyx` → cythonize → `build_ext`）。

### 无法跑（**反向条件**，装了反而跳过）—— 4 例

上游刻意测"**未安装**某依赖时的行为"，装了依赖就跳过：

| 跳过 | 源码条件 |
|---|---|
| `test_parallel.py:1931` ×2 | `@skipif(distributed is not None, reason="This test requires dask")` |
| `test_parallel.py:827` ×1 | `@skipif(mp is not None, reason="Only without multiprocessing")` |
| `test_numpy_pickle.py:1226` ×1 | `Needs lz4 not being installed to run` |

要执行它们需要**另建一个不带 dask/lz4 的环境**，与主环境互斥——非本配方可及。

### 真·平台受限 —— 15 例

| 跳过 | 数量 | 原因 |
|---|---|---|
| `test_parallel.py:1221` | 12 | `Not picklable with pickle`（`win32` 或 `multiprocessing/spawn` + 非 `SQUARE_MAIN`） |
| `test_parallel.py:1153` | 1 | `Require fork start method`（启动方式差异） |
| `test_memory.py:762` | 1 | 文件系统不支持细粒度 atime（**hmdfs 限制**） |
| `test_memmapping.py:165` | 1 | `PermissionError only easily triggerable on Windows` |

### 汇总

| 阶段 | skipped |
|---|---|
| 原始（无 threadpoolctl / memory_profiler） | **38** |
| 装 threadpoolctl + memory_profiler（本次改动） | **21** |
| 若再切源编译 OpenMP helper（评估后未做） | 19（预估） |
| 理论上限（须多套互斥依赖环境） | **15** |

> 口径说明：**两个环境都已完整跑完**——
> 环境 A（配方/CI，仅 cloudpickle）采集 1432，**1328 passed / 101 skipped / 3 xpassed / 0 failed**；
> 环境 B（全依赖参考，本机）采集 **1572**，**1512 passed / 33 failed / 21 skipped / 2 xfailed / 4 xpassed / 0 errors**（927.65s）。
> 两者均算术自洽。构建期 marker 的计数反映的是配方环境实跑。
>
> ⚠️ 环境 B 的 **33 例失败**均需 numpy（故**配方/CI 环境为 skip、不会出现**）：
> 29 例 `OSError: [Errno 24] Too many open files`（长会话 fd 耗尽，**环境性**——
> 干净环境单跑同一批测试类为 `64 passed / 0 个 Errno 24`）、
> 2 例本机 `--timeout=180` 超时（**脚手架**）、
> 2 例 `/dev/shm` 路径断言（三种 TMPDIR 设置下均复现，**未进一步归因**）。

## 注意事项
1. 纯 Python 包不需要 `commands.json`（R38：库包误加反而会被拦）。
2. 上游构建后端 `setuptools>=77.0.3`——**无需为它建 Conan 包**，
   走「直接拷贝模块到 site-packages」路线（同 packaging 先例）。
3. **必须整体拷贝 `joblib/ externals/`**（vendored loky），
   否则并行执行（`Parallel`）会在运行期缺 `loky` 而失败。
4. 跑上游测试时，**cwd 与源码路径都尽量不含「点」**；若无法避免，
   让 cwd 无点即可（见上「可行做法」）。
5. 不要用 `-p no:logging`——它会禁用 `caplog` fixture，造成假 error。
