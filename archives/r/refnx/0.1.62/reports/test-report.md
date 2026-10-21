# refnx 0.1.62 测试报告

**包**: `refnx/0.1.62`  **目标平台**: HarmonyOS PC (OHOS aarch64 / musl)
**构建系统**: meson + ninja + Cython 3.3.0  **报告日期**: 2026-10-15
**被测产物**: 本配方 `conan create` 产出的 package 目录
（`lib/python3.12/site-packages/refnx/`，含 4 个已签名扩展）

---

## 一、测试摘要

### 1.1 上游官方套件（`refnx/**/tests`，7 个目录 / 6 个测试包）

| 项目 | 数值 |
|------|------|
| 收集用例 | **386** |
| 通过 | **386** |
| 失败 | 0 |
| 错误 | 0 |
| 跳过 | 0 |
| xfail / xpass | 0 / 0 |
| 通过率 | **100.00%** |
| 耗时 | 746.46 s |

> 证据：`reports/upstream-junit.xml`（本配方 `conan create` 产出的 package 目录上的正式运行）。
> 另有一次同条件的交叉复核运行（空载时）得到**完全相同**的 386 passed / 0 skipped，
> 耗时 314.01 s——计数一致，差异只在机器负载。

逐目录计数（由同一份 JUnit XML 统计，求和 = 386）：

| 目录 | 用例数 |
|------|--------|
| `refnx/reflect/tests` | 145 |
| `refnx/reflect/_app/tests`（仅 `test_graphproperties.py`） | 1 |
| `refnx/analysis/tests` | 99 |
| `refnx/reduce/tests` | 86 |
| `refnx/dataset/tests` | 24 |
| `refnx/util/tests` | 23 |
| `refnx/_lib/tests` | 8 |
| **合计** | **386** |

**排除项（1 个文件 / 4 个用例）**：`refnx/reflect/_app/tests/test_app.py`。
该文件包含 4 个 Qt GUI 测试，OHOS 平台 pip 索引与 Conan 制品仓均未发布 Qt 绑定
（`qtpy`），**收集阶段即报 1 个 error**（`ModuleNotFoundError: No module named 'qtpy'`），
结构上不可运行。证据命令：

```bash
python3 -m pytest refnx/reflect/_app/tests/test_app.py --collect-only -q -o addopts=''
# ERROR: ModuleNotFoundError: No module named 'qtpy'
```

即：**上游 390 个可收集用例中的 386 个全部执行且全部通过**，唯一未执行的是
依赖 Qt 的 4 个 GUI 用例，排除理由与证据已记入 `test_package/MANIFEST.yml`。

### 1.2 test_package（消费者视角 + 鸿蒙特有）

| 脚本 | 用例数 | 结果 |
|------|--------|------|
| `test_refnx.py`（真实消费者，公开 API） | 17 | **17 / 17 PASS** |
| `test_ohos_platform.py`（鸿蒙特有：6 静态 ELF + 3 运行期） | 9 | **9 / 9 PASS** |
| **合计（live 通道）** | **26** | **26 / 26 PASS** |

配方按通道断言用例数（`discovered != expected` 直接抛错），计数不可能被少报：

| 通道 | 触发条件 | 执行用例数 |
|------|----------|-----------|
| `live` | `import refnx.reflect`（连带 `refnx.reduce/analysis`）探测成功（本次真机即此通道） | 17 + 9 = **26** |
| `static-artifact-verification` (E212) | CI AppSpawn 沙箱拒绝 dlopen 用户路径 `.so`（Permission denied） | 6 |
| `static-artifact-verification` (deps) | 运行期依赖 scipy/pandas/orsopy 在该 worker 的 Python 中缺失 | 6 |

---

## 二、测试结论

### 2.1 总体评价

`refnx` 0.1.62 在 HarmonyOS PC (OHOS aarch64) 上**适配完整、测试全绿**：

- 上游 386 个可运行用例 **100% 通过，零 skip**（数据依赖用例也已真正执行，见 §3.3）；
- 4 个 C/C++ 扩展全部通过 OHOS 平台的 ELF/ABI/签名契约（静态验证）；
- 四个**互相独立**的数值参考互相校验：C `refcalc.c`、Cython/OpenMP 内核、
  纯 Python 内核、以及 sdist 自带的 Motofit 参考曲线，最大相对偏差 ≤ 6.7e-13；
- OpenMP 多线程结果与单线程**逐位一致**；
- 拟合、MCMC、数据集 IO、pickle/Orso 持久化等真实工作流全部可用。

### 2.2 主要问题

无阻塞问题。适配过程中遇到并已解决的平台类问题见 §四。

### 2.3 可用功能清单（本次实测覆盖）

| 模块 | 覆盖内容 | 状态 |
|------|----------|------|
| `refnx._lib._cutil` | `c_flatten` / `c_unique` vs 纯 Python 参考 | ✅ |
| `refnx.reflect` | `Structure`/`Slab`/`SLD`/`Spline`；6 种后端（`c`/`c_parratt`/`cython`/`cython_parratt`/`py_parratt`/`python`）；`abeles`/`abeles_vectorised`/`gepore` | ✅ |
| `refnx.analysis` | `Objective`（`chisqr`/`nll`/参数树）、`CurveFitter`（L-BFGS-B 拟合）、`emcee` MCMC 后验 | ✅ |
| `refnx.dataset` | `Data1D`、`ReflectDataset`、`OrsoDataset` 读写 | ✅ |
| `refnx.reduce` | 模块 import、`_cevent` 扩展（C） | ✅（数据归约需实测文件，本次未覆盖归约算法本身） |
| `refnx.util` | `ErrorProp`（纯 Python） | ✅（上游用例） |
| 持久化 | `pickle` 往返、Orso 文件往返 | ✅ |

### 2.4 已知限制

1. `refnx/reflect/_app`（Qt GUI）在 OHOS 上不可用——无 Qt 绑定，上游 4 个 GUI 用例排除。
2. `refnx.reduce` 的**数据归约算法**依赖真实中子/X 射线原始文件（`.nx.hdf`）。
   上游 `refnx/reduce/tests` 的 86 个用例已全部通过（其测试数据由 `refnx-testdata`
   归档提供，本次已通过本地镜像供给，见 §3.3），但本报告不额外声称在真实束线数据
   上的端到端验证。
3. scipy / pandas / orsopy 由平台 OHOS wheel 提供，不在 Conan 制品仓内（见 §4.1）。

---

## 三、测试详情

### 3.1 运行方式

```bash
cd <package_folder>/lib/python3.12/site-packages
python3 -m pytest refnx -q -p ohos_testdata \
  --ignore=refnx/reflect/_app/tests/test_app.py \
  --junitxml=upstream-pkg.xml
```

- **对将要交付的产物直接运行**（不是源码树、不是临时安装目录）；
- 必须在 site-packages 目录内以 `pytest refnx` 的形式运行——逐目录分派会破坏
  conftest fixture 与 `resources.files(refnx.reflect.tests)` 的资源解析；
- 解释器为制品仓 `python/3.12.9`（`EXT_SUFFIX=.cpython-312-aarch64-linux-ohos.so`），
  与构建所用解释器同一个，因此被测扩展的 ABI 标签互相对得上。

### 3.2 逐目录逐类结果（真机 JUnit）

全部 386 个用例 `failures=0 errors=0 skipped=0`，逐类计数见下表（节选，
按类名前缀分组统计与 §1.1 表一致）：

| 测试类 | 用例数 | 结果 |
|--------|--------|------|
| `refnx.reflect.tests.test_reflect.TestReflect` | 95 | ✅ |
| `refnx.analysis.tests.test_curvefitter.TestCurveFitter` | 35 | ✅ |
| `refnx.reflect.tests.test_structure.TestStructure` | 24 | ✅ |
| `refnx.reduce.tests.test_platypusnexus.TestPlatypusNexus` | 21 | ✅ |
| `refnx.analysis.tests.test_objective.TestObjective` | 20 | ✅ |
| `refnx.analysis.tests.test_parameter.TestParameter` / `TestParameters` | 15 / 10 | ✅ |
| `refnx.dataset.tests.test_dataset.TestReflectDataset` | 15 | ✅ |
| `refnx.util.tests.test_ErrorProp.TestErrorProp` | 11 | ✅ |
| `refnx.reduce.tests.test_batch_reduce.TestReduce` / `TestReductionCache` | 3 / 10 | ✅ |
| `refnx.reflect.tests.test_spline.TestSpline` | 8 | ✅ |
| 其余 26 个测试类 | 合计 89 | ✅ |
| **合计** | **386** | **✅ 0 fail / 0 error / 0 skip** |

### 3.3 跳过的测试：0 个

上游 `refnx.conftest` 通过 `pooch` 从 `github.com/refnx/refnx-testdata` 下载数据归档。
该域名在设备与 CI 沙箱内均不可达，**默认会让数据相关用例整体 skip（386 → 约 250）**。

本次适配用一个 12 行的 pytest 插件（`-p ohos_testdata`）monkeypatch
`urllib.request.urlopen`，把任何含 `refnx-testdata` 的 URL 重定向到本地镜像 zip，
使这些用例**真正执行**，因此最终 `skipped = 0`。

### 3.4 test_package 逐项结果（真机，live 通道）

**`test_refnx.py`（17 项真实消费者检查）**

| # | 检查 | 关键判据 |
|---|------|----------|
| 1 | `version` | `refnx.__version__ == "0.1.62"` |
| 2 | `compiled_extensions_loaded` | 4 个扩展的 `__file__` 均以 `.so` 结尾 |
| 3 | `cutil_vs_python_reference` | `c_flatten`/`c_unique` 与纯 Python 参考一致 |
| 4 | `abeles_matches_motofit_reference` | 对 sdist 自带 Motofit 曲线 500 个 Q 点，最大相对偏差 6.66e-13 |
| 5 | `all_reflect_backends_agree` | 6 个后端彼此一致，相对偏差 < 1e-9 |
| 6 | `abeles_c_vs_pure_python` | C `refcalc.c` vs 纯 Python，绝对偏差 1.2e-15 |
| 7 | `parratt_matches_abeles` | Parratt 递推 vs Abeles，相对偏差 6.66e-13 |
| 8 | `abeles_vectorised_equals_scalar` | 5 层堆栈上向量化 vs 标量，最大偏差 0.0 |
| 9 | `gepore_nonmagnetic_channels` | 非自旋翻转通道 vs 非极化内核 6.6e-15；自旋翻转通道 ~1.6e-29 |
| 10 | `cyreflect_openmp_threads` | `threads=0/1/4` **逐位一致**，且等于 C 内核（5.6e-16） |
| 11 | `structure_reflectivity_kernel` | `Structure.reflectivity()` 与打包内核完全一致（偏差 0.0），且匹配 Motofit |
| 12 | `spline_profile` | 均匀 Spline 复现等价 slab 栈（R 最大绝对偏差 1.3e-5），且 `0 ≤ R ≤ 1` |
| 13 | `objective_chisqr_nll` | 真值处 `chi2/npoint=0.923`；`nll == -logl`；参数树 19 个参数 |
| 14 | `curvefitter_fit` | 从 95 Å 起拟合恢复 99.991 Å（真值 100，stderr 0.011），`chi2=137.7` |
| 15 | `mcmc_posterior` | 200 walkers × 120 steps：厚度 100.029 ± 0.013 |
| 16 | `dataset_loaders` | `Data1D(dot.out)=1122` 点、`ReflectDataset(e361r)=99` 点、Orso 往返精确 |
| 17 | `pickle_roundtrip` | `Structure` pickle 往返后反射率完全一致 |

**`test_ohos_platform.py`（9 项鸿蒙特有检查）**

静态（纯 stdlib 解析 ELF，不需要 import，也不需要 readelf——E212 沙箱里两者都不可用）：

| 检查 | 内容 |
|------|------|
| `ohos_elf_aarch64` | 4/4 扩展为 ELF64 `EM_AARCH64` |
| `ohos_codesign` | 4/4 扩展带 `.codesign` 段（E077 必需） |
| `ohos_libpython_dt_needed` | 4/4 扩展声明 `DT_NEEDED libpython3.12.so*`（E004 必需） |
| `ohos_musl_not_glibc` | 4/4 只链 musl `libc.so`，且 DT_NEEDED 尾部与 meson 声明**精确匹配**（C++ 扩展含 `libc++_shared.so`，仅 `_cyreflect` 含 `libomp.so`），无 glibc/BLAS 链接 |
| `ohos_abi_tag` | 4/4 文件名后缀 == 运行解释器的 `EXT_SUFFIX` |
| `package_layout` | `site-packages/refnx` 树完整；`__init__.py` 用 `from refnx.version import version`；meson 生成的 `refnx/version.py` 中 `version = "0.1.62"`；6 个子包存在；测试数据资产存在 |

运行期（只需 numpy，故在缺 scipy 的环境也可执行）：

| 检查 | 内容 |
|------|------|
| `ohos_platform_identity` | `aarch64` + LP64 + `_cutil` 从 `.so` 加载 |
| `ohos_dlopen_and_mmap` | `_cutil` 从包目录 dlopen；hmdfs 上 `np.save`/`np.load(mmap_mode="r")` (120, 200) 数组；`c_flatten`/`c_unique` 与纯 Python 参考一致 |
| `ohos_musl_allocator_and_abi` | musl 分配器承受 500 000 元素不规则展平（与纯 Python 参考一致）与非连续视图输入 |

### 3.5 破坏性反向验证（L1e）

静态通道把产物总数钉成构建系统已知值（`EXPECTED_EXTENSIONS = 4`，
来自 meson 的 `Build targets in project: 4`）：

- 移走 1 个扩展 `.so` → 计数断言立即失败（不会出现"3/3 全绿"）；
- 上游同类教训（sklearn 1.6.1）已归档为知识草稿 `DRAFT-static-artifact-count-pinning`。

`test_package/conanfile.py` 另有两道计数硬闸：

- `discovered != expected`（按通道取 26 / 6）→ 直接 `ConanException`；
- `failed > 0` → 直接 `ConanException`。

因此"少跑用例还报绿"在结构上不可能发生。

---

## 四、关键问题分析

### 4.1 scipy / pandas / orsopy 不在 Conan 制品仓

refnx 的运行期硬依赖为 `numpy>=2.0`、`scipy`、`orsopy`（`import refnx.reduce` 另需 `pandas`）。
其中：

- **numpy** 在制品仓（`numpy/2.5.2`），直接 `requires`；
- **scipy / pandas / orsopy** 未在制品仓发布，由平台 pip 索引
  `pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi` 的 OHOS wheel 提供
  （`scipy-1.18.1-cp312-cp312-ohos_aarch64.whl`、`pandas-3.0.5-…`、`orsopy-1.2.3-py2.py3-none-any`）。

**关键结论：scipy 不是编译依赖。** refnx 的 4 个 `.pyx` 只 `cimport numpy` / `cython`，
不像 scikit-learn 那样需要 SciPy 的 `.pxd` 声明，因此构建图里只放 numpy 就够了，
无需 vendor 任何声明文件。

### 4.2 E004：musl 不把解释器符号导出给 dlopen 对象

扩展在 import 时找不到 `PyModuleDef_Init` 等符号。解法：meson native file 的
`c/cpp_link_args` 显式加 `-L<pylib> -lpython3.12`，使每个扩展自带
`DT_NEEDED libpython3.12.so.1.0`。静态通道逐扩展断言这一点。

### 4.3 E077：DevBox 的 lld 自动签名，CI 的 lld 不签

OHOS 拒绝 dlopen 未签名的 ELF。`package()` 对每个打包 `.so` 执行
`llvm-objcopy --remove-section .codesign` → `binary-sign-tool -selfSign 1 -signAlg SHA256withECDSA`
→ `chmod 755`，重复执行幂等。日志：`refnx: re-signed 4 extension modules`。

### 4.4 E428：conan env wrapper 重置 PATH，`meson install` 找不到 ninja

改用 `meson install --no-rebuild`（树刚编译完，不再需要触发 ninja 查找）。

### 4.5 OHOS 上并存两套 CPython，ABI 标签由驱动构建的解释器决定

| 解释器 | `EXT_SUFFIX` |
|---|---|
| Conan 制品仓 `python/3.12.9` | `.cpython-312-aarch64-linux-ohos.so` |
| 设备 HNP `/data/service/hnp/bin/python3` | `.cpython-312.so` |

构建与校验**必须**用同一个解释器。若校验脚本拿 PATH 上的 `python3` 做基线，
会把 4 个正确命名的扩展全部判成缺陷（假失败）。协议：先取候选解释器的 `EXT_SUFFIX`，
只有含 `-linux-ohos` 才作为基线，否则跳过并记录其真实后缀。已归档为知识草稿
`DRAFT-ohos-two-cpython-abi-tag-ext-suffix`。

### 4.6 数据依赖用例默认会整体 skip

见 §3.3。若不处理，本套件会从 386 通过变成"约 250 通过 + 约 136 skip"，
看起来仍是绿的，但覆盖度显著不可比。本报告的所有计数均来自**真正执行**的 386 个用例。

### 4.7 `ReflectDataset` 的二维数组语义（排障陷阱）

`ReflectDataset(np.c_[q, y, err])` 会把二维数组解释为"行的元组"，静默造出 3 点数据集，
症状是所有拟合的 `chi2 ≈ 1e6`，极易被误判为数值后端出错。正确写法是传元组
`ReflectDataset((q, y, err))`。这是上游 API 语义，不是平台差异。

---

## 五、测试环境

| 项 | 值 |
|---|---|
| 平台 | HarmonyOS PC，aarch64，HongMeng Kernel 1.13.0 |
| C 库 | musl（OHOS） |
| CPython | 3.12.9（`EXT_SUFFIX=.cpython-312-aarch64-linux-ohos.so`） |
| 编译器 | clang / clang++（OHOS SDK `ohos-sdk_26.0.0.18`，target `aarch64-linux-ohos`） |
| OpenMP | `Run-time dependency OpenMP found: YES 5.0` |
| numpy | 2.5.2（Conan 制品仓） |
| scipy / pandas / orsopy | 1.18.1 / 3.0.5 / 1.2.3（平台 OHOS wheel） |
| 被测对象 | 本配方 `conan create` 产出的 package 目录 |

---

## 六、结论

| 维度 | 结论 |
|------|------|
| 上游套件 | 386 / 386 通过，0 失败 / 0 错误 / **0 跳过**（唯一排除项为 4 个 Qt GUI 用例，理由与证据见 §1.1） |
| test_package | 26 / 26 通过（17 真实消费者 + 9 鸿蒙特有） |
| 平台合规 | 4 / 4 扩展满足 ELF64 aarch64 + `.codesign` + `libpython` DT_NEEDED + musl 无 glibc/BLAS 链接 + ABI 标签匹配 |
| 数值正确性 | 四路独立参考互查，最大相对偏差 6.7e-13；OpenMP 单/多线程逐位一致 |
| 适配完整性 | **✅ 通过**（`conan create` 含 test_package 阶段 rc=0） |
