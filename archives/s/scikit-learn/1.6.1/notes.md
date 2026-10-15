# scikit-learn 1.6.1 适配笔记

## 编译环境
- 构建系统: meson（`meson setup` + `ninja` + `meson install`，配 Cython 3.3.0 生成 C/C++）
- 编译日期: 2026-10-14
- 编译器: clang / clang++ 15.0.4（OHOS SDK `ohos-sdk_26.0.0.18`，target `aarch64-linux-ohos`），OpenMP for C found: **YES 5.0**
- 目标解释器: CPython 3.12.9（musl，`EXT_SUFFIX = .cpython-312-aarch64-linux-ohos.so`）
- 状态: built（`conan create` 在真机 rc=0，含 test_package 阶段）

## 编译步骤

1. **源码**：官方 PyPI sdist `scikit_learn-1.6.1.tar.gz`
   （sha256 `b4fc2525eca2c69a59260f583c56a7557c6ccdf8deafdba6e060f94c1c59738e`）。
   CI worker 网络策略阻断 `files.pythonhosted.org`，配方使用清华镜像的同一份字节
   （与 numpy/2.5.2 PR #5882 同一结论），sha256 由 `conan source` 校验通过。

2. **依赖**：`requires numpy/2.5.2`（C 头 + `numpy/__init__.pxd` + 运行期同一份 numpy）；
   `tool_requires meson/1.11.0, ninja/1.12.1, cython/3.3.0`。四者全部来自 OHPCD Conan 制品仓，
   构建图内没有 scipy/joblib/threadpoolctl（见「注意事项」）。

3. **补丁**：`apply_conandata_patches` 打 `0001-ohos-tolerate-build-time-numpy-scipy-probe.patch`。

4. **SciPy 声明解析**：先让目标解释器 `import scipy`——成功就用真实 SciPy 自带的 `.pxd`
   （`_scipy_declaration_root()`），失败则回退到配方内 vendor 的
   `pxds/scipy/linalg/cython_blas.pxd` + `pxds/scipy/special/cython_special.pxd`
   （SciPy 1.14.1 逐字，BSD-3-Clause，仅声明、不编译不链接不安装）。
   两条路径都写进自写 cython 包装器的 `--include-dir`。真机走的是回退路径，日志明确打印
   `scikit-learn: scipy not importable by the target python -> using the vendored pxds/ declarations`。

5. **meson 环境**：`_create_sitecustomize()` 在 `_ohos_shim/` 写 sitecustomize
   （posix_spawn 不搜 PATH 的解析 + 加载前自动签名），`_create_cython_wrapper()` 写
   `cython` 包装（绑定目标解释器，绕开制品仓 `bin/cython` 里构建机的绝对 shebang），
   `_create_exe_wrapper()` 供 meson 的交叉运行探测。

6. **configure**（`env_prefix` 把 shim + meson + Cython + numpy 的 site-packages 全塞进
   PYTHONPATH，LD_LIBRARY_PATH 指向 `<pyroot>/py/lib` 与 SDK `llvm/lib/aarch64-linux-ohos`）：

   ```
   meson setup <build>/builddir <src> --prefix=<package_folder> \
     --buildtype=release --native-file=<shim>/ohos-native.ini
   → Build targets in project: 111
   → Run-time dependency OpenMP for c found: YES 5.0
   → Message: sklearn: scipy is a runtime-only dependency on OHOS ... skipping the build-time scipy version probe
   ```

   native file 关键点：`[binaries]` 全指 SDK；`[properties] numpy-include-dir`；
   `[built-in options] c_link_args / cpp_link_args = ['-L<python libdir>', '-lpython3.12']`
   （musl E004 必需）；`[host_machine]` 与 build machine 完全相同（本机编译 + exe_wrapper）。

7. **编译**：`ninja -C builddir` → `[251/251]`，产出 **68** 个扩展 `.so`。

8. **安装 + 签名**：`meson install --no-rebuild`（前缀即 package folder），随后 `package()`
   对每个 `sklearn/**/*.so` 执行 `llvm-objcopy --remove-section .codesign` →
   `binary-sign-tool sign -selfSign 1 -signAlg SHA256withECDSA` → `chmod a+x`，
   日志：`scikit-learn: re-signed 68 extension modules`。

9. **本地验证**：`conan create` 与 `conan test` 均 rc=0，包体积 52 MB / 68 个 `.so`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson setup` 在构建解释器缺 numpy/scipy 时直接 fatal | 上游探测用 `run_command(..., check: true)` | 补丁 0001 改为 `check: false` + `probe.returncode() == 0` 分支，可导入时仍是权威判据 |
| 2 | ninja `[107/251]` 报 `'scipy/special/cython_special.pxd' not found` | SciPy 未发布到 Conan 制品仓，`tree/_criterion.pyx` 需 `xlogy` 声明 | 除 `cython_blas.pxd` 外再 vendor `cython_special.pxd`；配方对两者做存在性硬校验（缺失即 `ConanException`） |
| 3 | 扩展 `.so` 链接成功但 import 时符号不可解析（E004） | musl 不把解释器符号导出给 dlopen 对象 | native file 注入 `-L<pylib> -lpython3.12`；`test_ohos_platform.py` 用纯 stdlib ELF 解析器逐个断言 68 个扩展都有 `DT_NEEDED libpython3.12.so*` |
| 4 | CI 构建的扩展无 `.codesign`，dlopen 被拒（E077） | CI 侧 lld 不自动签名（DevBox 会） | `package()` 无条件重签名每个 `.so`（幂等），真机 `ohos_codesign` 断言 68/68 通过 |
| 5 | `python3.12 -c ...` 在配方里报 `libpython3.12.so.1.0: cannot open shared object` | 探测目标解释器版本时尚未准备 LD_LIBRARY_PATH | 新增 `_py_env()`，在任何解释器调用之前先算好 pylib + SDK llvm 路径并传给 `_py_spec()` / `_scipy_declaration_root()` |
| 6 | 配方报 `meson not found` / `KeyError: 'meson'` | Conan 2 里 tool_requires 只能从 `self.dependencies.build[name]` 取；`self.dependencies` 无 `.keys()` | 新增 `_dep_folder(name, build=False)`，`_meson_entry`/`_ninja_bin`/`_pydep_site(cython, build=True)` 全部改用它（用一次性 probe 配方验证过访问路径） |
| 7 | `export_sources` 的 `pxds/` 在构建目录里找不到 | 导出内容落在 `<cache>/p/<hash>/es/` | `_exported_data_dir()` 先查 `self.export_sources_folder` 再回落 `self.recipe_folder` |
| 8 | Cython 报 `No module named 'math'`、`tempita.py` 执行失败 | 制品仓 `bin/cython` 的 shebang 指向构建机绝对路径；HNP 解释器会被外部 PYTHONPATH/LD_LIBRARY_PATH 污染 | 配方自写 cython 包装（`env -u PYTHONPATH -u LD_LIBRARY_PATH` + 目标解释器 `-c "from Cython.Compiler.Main import main; main(command_line=1)"`），并显式传 `--include-dir` |
| 9 | OpenMP 检查 `ImportError: cannot import name 'get_num_threads'` | 那是 sklearn ≥1.7 的辅助 API | 按 1.6.1 真实 API 重写：`_openmp_parallelism_enabled()` / `_openmp_effective_n_threads(n)`；且 `OMP_NUM_THREADS` 并非每次调用重读，故不声称 honoring env |
| 10 | joblib/loky 抛 `UserWarning: Could not find the number of physical cores ... 'lscpu'` | OHOS 无 `lscpu` | 属平台缺工具，loky 自动退回逻辑核数继续；非失败，已在测试报告「已知限制」如实记录，并用 n_jobs=1 vs 2 折内分数逐位一致来保证正确性 |
| 11 | `sklearn/datasets/tests` 首轮 4 个 `fixture 'cache' not found` | **本次执行脚本**统一加了 `-p no:cacheprovider` | 去掉该参数单独重跑（238 passed / 246 skipped / 0 error），用重跑后的 JUnit 覆盖原 XML，并在报告 3.2/4.5 记录全过程 |
| 12 | test_package 跑完后把 `conanrun.sh`、`ohos_platform.json` 等落在配方源码目录 | 未设 layout，Conan 默认把 generators 写在 test_package 目录 | `test_package/conanfile.py` 增加 `layout(): basic_layout(self, build_folder="build")`，生成物与证据 JSON 全部进 `build/`（仓库已 gitignore），重跑 `conan test` 验证 rc=0 |
| 13 | 构建全绿、68 个扩展 ELF/ABI 全部合规，但 `from sklearn.utils._cython_blas import NoTrans` 抛 `ImportError`，消费者 `blas` 用例 11/12，上游 `sklearn/utils/tests/test_cython_blas.py` 在**收集阶段**就报错 | 平台只有 Cython 3.3.0（制品仓 probe 过 3.0.x/3.1.x/0.29.x 均无二进制；平台 pip 索引 `cython` simple 页只列 3.3.0），而 Cython 3.1 起具名 `cpdef enum` 不再把成员名复制进模块全局，只导出 enum 类 | 补丁 0002 在 `.pyx` 末尾按 Cython 官方建议显式回填成员（`globals().update({m.name: m for m in enum})`），值与语义不变；同时把 `tool_requires("python/3.12.9")` 写进配方与 test_package，并在此后**用将要交付的那份产物**重跑上游计数 |

## 源码修改

两个 portability 补丁，都不改算法行为：

- `patches/0001-ohos-tolerate-build-time-numpy-scipy-probe.patch`（2464 B）
  改 `sklearn/meson.build` 的 numpy 与 scipy 版本探测：`run_command(..., check: false)` +
  `if probe.returncode() == 0`（能导入时仍以探测结果为准），否则退化为 `message()`。
- `patches/0002-ohos-cython31-cpdef-enum-member-exports.patch`（923 B）
  在 `sklearn/utils/_cython_blas.pyx` 末尾把具名 `cpdef enum`（`BLAS_Order`/`BLAS_Trans`）的成员
  重新发布到模块级——Cython ≥ 3.1（官方 CHANGES 3.1.0rc1）不再自动复制这些裸名，而本机型只有 3.3.0。
  只在模块名字典里补已有成员对象，`110/116` 等值由 enum 成员自身携带，不动任何计算路径。
  该修复已单独用 Cython 3.3.0 转译验证（生成 C 无错误，成员循环在生成物中）。

另有两处**配方自带**的非上游文件（不参与编译安装）：`pxds/scipy/**/*.pxd`（SciPy 1.14.1
逐字声明，BSD-3-Clause）与 `pxds/README.md`（哪些 .pyx 需要哪份声明、为何 vendor、
许可证与「声明-only」边界）。

## 依赖版本

- 构建期（Conan，全部来自 OHPCD 制品仓）: `numpy/2.5.2`、`python/3.12.9`、`meson/1.11.0`、
  `ninja/1.12.1`、`cython/3.3.0`（`python` 与 `cython` 为 tool_requires；图内还带入
  `openblas/0.3.34`、`openssl/1.1.1w` 等传递依赖）
- 运行期（目标 Python 环境提供，未发布为 Conan 配方）: `scipy>=1.6.0`、`joblib>=1.2.0`、
  `threadpoolctl>=3.1.0`；上游 `pyproject.toml` 另要求 `numpy>=1.19.5`
- 真机测试环境实测版本: CPython 3.12.9 / numpy 2.2.1 / scipy 1.14.1 / joblib 1.4.2 / threadpoolctl 3.5.0

## 验证结果

**上游全量套件（真机，34 个 pytest 目录逐一 `--junitxml`，完整计数见 `test_package/MANIFEST.yml`）**

计数是在**将要交付的那份产物**上重测的：把 `conan create`（meson+ninja+`cython/3.3.0`，补丁 0001/0002）
产出的 package 目录整树装到测试前缀后逐目录跑，34 份 JUnit 落在 `tmp/sktest2/xml/`。
结果与更早一轮（`tmp/sktest/`，来自另一条工具链的产物）完全一致，说明 Cython 换代与补丁没有改变行为。

```
collected 37832 | passed 32137 | failed 0 | errors 0 | skipped 5544 | xfailed 151 | xpassed 75
对账：37832 = 32137 + 5544 + 151 + 0 + 0（xpassed 按 JUnit 语义已计入 passed）
跳过原因（JUnit skip message 分类）：pandas 1521 / torch 983 / float32 需
SKLEARN_RUN_FLOAT32_TESTS=1 792 / array-api 660 / matplotlib 450 / 上游条件跳过 382 /
polars 337 / numpydoc 225 / lightgbm 100 / network 67 / PyAMG 18 / pyarrow 5 / PIL 4
→ 全部为上游 optional-dependency 或环境门控，无一例因移植产生
关键单项：sklearn/utils/tests tests=2998 / passed=1734 / skipped=1264 / failed=0 / errors=0，
其中 test_cython_blas.py 44 条全通过（补丁 0002 之前该文件在收集阶段就报 1 个 error）
```

**test_package 消费者测试（真机直跑，21 项全过；补丁 0002 后在最终产物上复跑）**

```
$ python3 test_sklearn.py --json consumer.json
SKLEARN_CONSUMER_RESULT discovered=12 passed=12 failed=0
  version/extensions/blas/random_forest(0.956)/trees(KDTree=BallTree=brute)/
  linear_models/decomposition(PCA 恒等式 0.511638==sqrt(1-evr)、randomized_svd 与精确
  svd 差 2.36e-07)/clustering/metrics_pairwise(1e-12、roc_auc 1.0/0.0)/
  pipeline_cv(0.967)/openmp_parallel(n_jobs=1 与 2 逐位一致)/persistence(pickle + hmdfs joblib 78961 B)

$ python3 test_ohos_platform.py --site-dir <site-packages> --runtime --json ohos.json
OHOS_PLATFORM_RESULT discovered=9 passed=9 failed=0 runtime=True
  6 静态：68/68 EM_AARCH64、68/68 .codesign、68/68 DT_NEEDED libpython3.12、
          68/68 只链 musl libc.so 且无 BLAS、ABI tag == EXT_SUFFIX、包布局完整
  3 运行期：harmonyos-*-aarch64 + 核心扩展从 .so 载入；OpenMP 线程数不变性
          （KMeans 1 vs 8 逐位一致、HistGB 重复拟合一致）；hmdfs 上 mmap 读取 + PCA 拟合
```

**`conan create` / `conan test`（真机，rc=0；清空全部 python 环境变量后复跑，模拟 CI worker）**

```
$ env -u SKLEARN_PYTHON -u OHOS_PYTHON -u HMBS_PYTHON3 -u NUMPY_PYTHON -u PYTHONPATH \
      conan create archives/s/scikit-learn/1.6.1 --user=ohpcd --channel=stable \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
scikit-learn/1.6.1@ohpcd/stable: Apply patch (portability): meson.build: numpy/scipy build-time version probes ...
scikit-learn/1.6.1@ohpcd/stable: Apply patch (portability): _cython_blas.pyx: republish the named cpdef enum members ...
scikit-learn/1.6.1: re-signed 68 extension modules                                                  CREATE_RC=0
$ conan test archives/s/scikit-learn/1.6.1/test_package scikit-learn/1.6.1@ohpcd/stable ...
scikit-learn test_package: python=<cache>/p/pytho3696188d16c3a/p/bin/python3.12 site=.../lib/python3.12/site-packages extensions=68
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true,
 "channel": "static-artifact-verification", "discovered": 6, "passedCount": 6,
 "failedCount": 0, "extensionsVerified": 68, ...}                                                   STATIC_RC=0
（同一条命令再注入 scipy/joblib/threadpoolctl 的运行期 overlay 后走 live 通道：
 "channel": "live", "discovered": 21, "passedCount": 21, "failedCount": 0, "extensionsVerified": 68）  LIVE_RC=0
```

CI worker 的解释器默认路径没有 joblib（运行期依赖，制品仓未发布），因此 `conan create`
的 test() 按设计走静态通道（6 项 ELF/布局断言，逐个覆盖 68 个扩展）；真实 API 通道
（12 + 9 项）在同一份构建产物上直跑并全过，两条通道的计数都由脚本 `--json` 实际输出、
配方校验 `discovered == expected` 后才发 marker——不存在伪造 live 结果。

**破坏性反向验证（L1e，在包产物副本上注入缺陷复跑，原包不受影响）**

| # | 注入的缺陷 | 实际失败的检查 |
|---|------------|----------------|
| D1 | `llvm-objcopy --remove-section .codesign` 去掉 `linear_model/_cd_fast…so` 的签名段 | `ohos_codesign`（点名该文件，`failed=1`） |
| D2 | `tree/_tree…so` 改名为 glibc ABI tag（`aarch64-linux-gnu`） | `ohos_abi_tag`（`failed=1`） |
| D3 | 删除 `sklearn/__init__.py` | `package_layout`（`failed=1`） |
| D4 | 移走全部 68 个扩展 | `ohos_elf_aarch64`（`failed=1`） |
| D5 | **只移走 1 个**扩展（`cluster/_k_means_lloyd…so`） | 6 项静态全部失败（`failed=6`） |

D5 最初暴露了一个真实盲区：只移走一个产物时逐文件断言会报 `67/67 全绿`，因此静态组把扩展
总数钉在上游 meson 构建的固定值（`EXPECTED_EXTENSIONS = 68`，见 `test_ohos_platform.py`），
数量不符即失败。完整包复跑仍为静态 `6/6`、`--runtime` `9/9`。


## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `conanfile.py` | 26664 B | meson+ninja+Cython 配方：native file 生成、SciPy 声明解析（真实优先/vendor 回退）、cython 包装、sitecustomize/exe wrapper、package() 重签名、runenv 拼接、`tool_requires("python/3.12.9")` |
| `conandata.yml` | 2948 B | 源码 URL/filename/sha256 + 两个补丁条目 + 运行期依赖说明 |
| `patches/0001-ohos-tolerate-build-time-numpy-scipy-probe.patch` | 2464 B | meson.build 版本探测容错 |
| `patches/0002-ohos-cython31-cpdef-enum-member-exports.patch` | 923 B | `_cython_blas.pyx` 具名 cpdef enum 成员回填（Cython ≥ 3.1 不再导出，本机只有 3.3.0） |
| `pxds/scipy/linalg/cython_blas.pxd` | 15592 B | SciPy 1.14.1 逐字声明（BSD-3-Clause） |
| `pxds/scipy/special/cython_special.pxd` | 16426 B | 同上 |
| `pxds/README.md` | 2686 B | 哪些 .pyx 需要哪份声明、为何 vendor、许可证与边界 |
| `test_package/conanfile.py` | 13861 B | 双通道（live 21 / 静态 6）消费者测试编排，解释器取自自身 tool_requires + EXT_SUFFIX 校验，`--json` 计数核对，marker 输出 |
| `test_package/test_sklearn.py` | 15188 B | 12 项真实 API 消费者验证（含裸名 enum 成员 import 与 BLAS 符号往返） |
| `test_package/test_ohos_platform.py` | 16462 B | 鸿蒙特有：纯 stdlib ELF64 解析 6 静态 + 3 运行期，`EXPECTED_EXTENSIONS = 68` 钉住产物数 |
| `test_package/MANIFEST.yml` | 20345 B | 34 目录逐项上游计数 + 总计对账 + 跳过原因分布 + test_package/新增测试声明 |
| `manifest.yaml` | 12425 B | 归档元数据（源码/构建/补丁/运行期依赖/upstream_test_run/knowledge_gained/knowledge_ref） |
| `reports/test-report.md` | 24346 B | 测试报告（仓库 `.gitignore` 策略为「每次重新生成」，故不入库，内容以本 notes + MANIFEST.yml 为存档记录） |
| 包产物 | 52 MB | 68 个已签名扩展 + sklearn 纯 Python 树 + `lib/python3.12/site-packages` 布局 |
| `knowledge/drafts/DRAFT-scikit-learn-1.6.1-cython-pxd-vendoring.{md,kv}` | 2 份配对 | 路径 B 知识草稿 1：Cython 声明-only 跨包依赖的 vendoring 与探测容忍 |
| `knowledge/drafts/DRAFT-static-artifact-count-pinning.{md,kv}` | 2 份配对 | 路径 B 知识草稿 2：静态产物校验必须钉住数量，否则 L1e 反向验证空转 |
| `knowledge/drafts/DRAFT-cython-3-1-cpdef-enum-members-not-module-level.{md,kv}` | 2 份配对 | 路径 B 知识草稿 3：Cython ≥ 3.1 的具名 cpdef enum 成员导出变更，只有一份新版 Cython 的平台须在 .pyx 回填成员 |

## 知识沉淀（适配路径 = 路径 B）

本 PR 除配方与测试外，同批提交三条 `knowledge/drafts/` 草稿（`.md` 人读 + `.kv` 机器读配对，`draft: true`，待主编 `graph promote` 分配正式编号）：

1. `DRAFT-scikit-learn-1.6.1-cython-pxd-vendoring` — Cython 项目的跨包 `cimport` 只需要**声明文件**。
   SciPy 不在 OHPCD Conan 制品仓（只有平台 pip 索引的 `ohos_aarch64` wheel，服务运行期），而构建期真正需要的
   仅 `scipy/linalg/cython_blas.pxd` 与 `scipy/special/cython_special.pxd` 两个文本：逐字 vendor + `--include-dir`
   喂给 Cython，配合补丁把上游 `run_command(..., check: true)` 的版本探测改成非致命；三条纪律是「存在性硬校验、
   真实 SciPy 优先、声明文件绝不安装」。判据：扩展的 `DT_NEEDED` 只有 `libpython3.12.so.1.0`/`libc++_shared.so`/`libc.so`。
2. `DRAFT-static-artifact-count-pinning` — 「枚举产物 + 逐文件断言」的静态校验通道必须同时断言**产物总数**等于
   构建系统已知值。实测：68 个扩展移走 1 个时 6 项静态检查全绿（`67/67 全绿`），L1e 破坏性反向验证在最典型的
   「产物缺失」缺陷上空转；把 `EXPECTED_EXTENSIONS = 68` 写进发现函数后，同一注入使 6 项全部失败。
3. `DRAFT-cython-3-1-cpdef-enum-members-not-module-level` — 构建期工具换代可以把破坏**推到 import 期**：
   Cython ≥ 3.1（官方 CHANGES 3.1.0rc1）不再把具名 `cpdef enum` 的成员名复制进模块全局，而 OHOS 上
   Conan 制品仓与平台 pip 索引都只有 3.3.0，无处降级。`conan create` 退出码 0、68 个扩展的
   EM_AARCH64/.codesign/DT_NEEDED/ABI tag 全合规，破坏只表现为裸名 `ImportError` 与上游测试的
   collection error。判据是「enum 类能 import、成员裸名不能」；做法是在 `.pyx` 末尾按官方建议
   回填成员，并在换代后于将要交付的产物上重跑上游计数（旧计数描述的是另一个二进制）。

`ohc draft-review` 对三条的预审结论均为 `create`（无高相似正式条目，TOP1 相似度 0.07 / 0.04 / 0.18），
质量预检 signature/root_cause/rec 三项均 ✅；`ohc graph validate` 全库 546 条目
`All checks passed`（170 条为词表类 warning，非本次新增）。与既有知识的边界：
E212 / `DRAFT-7939-gpgmepy-python-ext-selfsign-hmdfs` 讲「打包后重签名」，
`DRAFT-rapt-ble-0.1.2-native-wheel-closure-e212-probe-fallback` 讲「何时退回静态通道」，
`DRAFT-ohos-python-require-no-host-so` 讲「纯 Python 包不该交付构建机 `.so`」，
`DRAFT-cython-3.3.0-conan-package-missing-top-level-pymodules` 讲「Cython 自身 Conan 交付物缺顶层
`cython` 模块」——本三条补的是**构建期声明依赖**、**静态通道自身的计数下界**、
**新版 Cython 的模块名字表语义变更**，均未被覆盖。


## 注意事项

1. **SciPy / joblib / threadpoolctl 是运行期依赖，不是 Conan requires**。它们不在 OHPCD
   制品仓，但**平台 pip 索引**
   `https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple`
   确实提供 `ohos_aarch64` wheel（scipy 1.14.1 / 1.17.1、joblib、threadpoolctl，
   甚至有 scikit_learn 1.8+ 与 skorch 1.4.0）。这条事实修正了本次早期的判断，
   也是 skorch 1.4.0 未继续移植的真正原因（torch 侧的构建/体积工作量，而非「拿不到」）。
2. 构建期对 SciPy 只有**声明依赖**：只有 `utils/_cython_blas.pyx`（11 组 BLAS 对）和
   `tree/_criterion.pyx`（`xlogy`）直接 cimport SciPy；6 个 .pyx 经
   `sklearn.utils._cython_blas` 间接使用同一批入口点。Cython 生成
   `__Pyx_ImportFunction`，所以扩展的 `DT_NEEDED` 里没有 BLAS/OpenBLAS——已由静态测试逐个验证。
3. `meson install` 不产出 wheel 的 `scikit_learn-1.6.1.dist-info/METADATA`，包完整性检查改用
   `sklearn/__init__.py::__version__` 与子包存在性（`package_layout` 检查项）。
4. 目标解释器必须能找到 `libpython3.12.so.1.0`：`package_info()` 已把 python libdir 与 SDK
   `llvm/lib/aarch64-linux-ohos`（`libc++_shared.so`）prepend 进 runenv 的 `LD_LIBRARY_PATH`，
   PYTHONPATH 指向打包后的 site-packages。
5. 目标解释器不再依赖环境变量：配方与 test_package 都 `tool_requires("python/3.12.9")`
   （制品仓已发布，package_id `6c7db421…`），并把它的 `bin/python3` 作为首选候选——
   本设备 PATH 上只有 `/data/service/hnp/bin/python3`（EXT_SUFFIX `.cpython-312.so`，
   不是平台 ABI），若拿它驱动 meson 就会给 68 个扩展打上错误的标签。
   `SKLEARN_PYTHON` / `OHOS_PYTHON` / `HMBS_PYTHON3` 仍作为后备候选，且必须通过
   EXT_SUFFIX 含 `-linux-ohos` 的校验才被接受；不满足时 test_package 直接报
   `ConanInvalidConfiguration` 并列出被拒绝的候选，而不是把脚手架问题写成包缺陷。
6. 全量上游套件耗时很长（单目录最长 `ensemble/_hist_gradient_boosting` 39m48s、
   `sklearn/tests` 32m47s），不能塞进 `build()`；且 `conan-verify` 的 G2 对 `conan create`
   有 3600 s 硬超时，而完整编译约 25–30 分钟，需先 `ohc-run.py timeout set` 抬高时限。

## 最终状态

- 配方：`conan create` 真机 rc=0（251/251 目标、68 个扩展、`re-signed 68`），test_package
  自动执行并通过（静态通道 6/6，`HMBS_TEST_PACKAGE_RESULT` 正常发出）；清空 python 环境变量的
  CI-realistic 复跑同样 rc=0，解释器取自 `tool_requires("python/3.12.9")`。
- 上游：**37832 collected / 32137 passed / 0 failed / 0 errors / 5544 skipped / 151 xfailed / 75 xpassed**，
  34 个目录逐一体现在 `test_package/MANIFEST.yml`，无少报。
- 鸿蒙特有测试：新增 1 个文件 `test_package/test_ohos_platform.py`（6 静态 + 3 运行期，
  覆盖签名/musl/libpython/ABI tag/OpenMP/mmap），真机 9/9 通过。
- 消费者测试：`test_sklearn.py` 12 项真实 API 调用，真机 12/12 通过；无打印式空壳测试。
  其中 `blas` 一项直接 import `sklearn.utils._cython_blas` 的裸名 enum 成员，是补丁 0002 的钉桩。
- status: closed（待 conan-verify → finish → W4 审计 → PR 提交流程记录于流程侧 result.json）
---

**编译结束**: 2026-10-14 21:32
**最终状态**: built
