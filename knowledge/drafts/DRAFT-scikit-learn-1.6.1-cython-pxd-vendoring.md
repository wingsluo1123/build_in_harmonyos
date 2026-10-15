# Cython 跨包 `cimport` 只需要声明文件：SciPy 不在 Conan 制品仓时的 declaration-only vendoring

> 草稿 ID：`DRAFT-scikit-learn-1.6.1-cython-pxd-vendoring`
> 来源任务：scikit-learn 1.6.1 HarmonyOS PC（OHOS aarch64）适配，`archives/s/scikit-learn/1.6.1/`
> 来源 PR：`feat/scikit-learn-1.6.1`
> 归档证据：`archives/s/scikit-learn/1.6.1/pxds/README.md`、`patches/0001-ohos-tolerate-build-time-numpy-scipy-probe.patch`、`conanfile.py::_scipy_declaration_root()`

## 适用场景

用 Cython 编译的 Python 扩展项目，其 `.pyx` 里有 `cimport` **另一个 Python 包**的声明（SciPy 的
`scipy.linalg.cython_blas` / `scipy.special.cython_special`、numpy 的 `numpy/__init__.pxd` 等），而目标平台的
Conan 制品仓没有那个包，或者构建 worker 用的解释器与目标解释器不是同一个，装不上也不该装。

典型判据：报错发生在 **configure 或 codegen 阶段**（`meson setup` 的 `run_command` fatal、ninja 里
`'scipy/special/cython_special.pxd' not found`），而不是链接或运行阶段——说明缺的是**喂给编译器的文本**，
不是可执行代码。

## 现象与原因

两个独立陷阱，同一个根因：把运行期依赖当成了构建期依赖。

1. **上游版本探测是硬失败**。`sklearn/meson.build` 用
   `run_command(py, ['-c', 'import numpy; print(numpy.__version__)'], check: true)` 探测 numpy 与 SciPy 版本。
   `check: true` 意味着构建解释器导入不到就直接 `ERROR: Command ... returned non-zero exit status 1`，
   configure 阶段终止——尽管这两个包在编译产物里一个符号都不链接。
2. **Cython 要的是 `.pxd`，不是 SciPy 本体**。`cimport scipy.linalg.cython_blas` 只需要 SciPy 发行包里那两个
   声明文件来生成 C 代码里的签名与调用桩；生成的桩在 **import 时**通过 `__Pyx_ImportFunction` 从真实 SciPy
   模块取函数指针。OHOS 侧 SciPy 未发布到 Conan 制品仓（平台 pip 索引
   `https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple` 有 `ohos_aarch64` wheel，
   1.14.1/1.17.1，满足的是**运行期** import）。

必须先把范围算清，否则容易过度 vendor 或漏 vendor。scikit-learn 1.6.1 的实际分布：

| 类别 | 源文件 | 需要的声明 |
|---|---|---|
| 直接 `cimport` SciPy | `utils/_cython_blas.pyx` | `scipy/linalg/cython_blas.pxd`（11 组 BLAS 符号对） |
| 直接 `cimport` SciPy | `tree/_criterion.pyx` | `scipy/special/cython_special.pxd`（`xlogy`） |
| 间接（经 sklearn 自有包装） | `utils/arrayfuncs.pyx`、`svm/_liblinear.pyx`、`svm/_libsvm.pyx`、`svm/_libsvm_sparse.pyx`、`cluster/_k_means_lloyd.pyx`、`linear_model/_cd_fast.pyx` | `from sklearn.utils._cython_blas cimport …`，共用上面同一批声明 |
| 只是 Python 级 `from scipy …` | `tree/_tree.pyx`、`ensemble/_gradient_boosting.pyx`、`metrics/cluster/_expected_mutual_info_fast.pyx`、`cluster/_hdbscan/_reachability.pyx` 等 | **不需要任何声明文件**，运行期 SciPy 满足 |

结论：真正 vendored 的只有 2 个 `.pxd`。`cython_lapack.pxd` 之类不需要。

## 处理方法

1. 从**与运行期同族**的 SciPy 版本逐字取出所需 `.pxd`（此处 SciPy 1.14.1 的
   `site-packages/scipy/linalg/cython_blas.pxd`、`site-packages/scipy/special/cython_special.pxd`），放进配方目录
   `pxds/scipy/…`，保持原路径结构，不改一个字节。
2. 通过 Cython 的 `--include-dir <pxd_root>` 传给编译器（配方里自写 cython 包装，因为制品仓 `bin/cython` 的
   shebang 指向构建机绝对路径，需要 `env -u PYTHONPATH -u LD_LIBRARY_PATH` 后用目标解释器调
   `Cython.Compiler.Main`）。
3. 补丁把 `sklearn/meson.build` 的两个探测改成 `check: false` + `if probe.returncode() == 0`：**能导入时仍以探测结果
   为权威判据**（版本不满足照样 `error()`），导入不到退化为 `message()`。这是 portability 补丁，不放宽任何约束。
4. 三条纪律决定这条方案是否可信：
   - **存在性硬校验**：配方 build 前逐个检查声明文件在不在，缺任一直接 `ConanException`——不允许「悄悄少编了」。
   - **真实优先**：`_scipy_declaration_root()` 先试目标解释器 `import scipy`，能导入就用它自带的 `.pxd`（零版本偏移），
     `pxds/` 只作回退。
   - **声明-only 边界**：`.pxd` 绝不进 `package()`、绝不进 site-packages、绝不写成 `requires`；配 `pxds/README.md`
     写清许可证（SciPy BSD-3-Clause）与「never compiled, never linked, never installed」。
5. 反面做法要禁止：造空 `scipy/__init__.py` stub 去骗过 `import scipy` 探测（只是把错误推到 codegen，甚至让 stub
   进产物遮蔽真实 SciPy）；把 `.pxd` 打进发布包。

## 验证与边界

- 2026-10-14 在 HarmonyOS PC aarch64（CPython 3.12.9 musl、meson 1.11.0 + ninja 1.12.1 + Cython 3.3.0，均来自
  OHPCD Conan 制品仓）实跑：`conan create` 退出码 0，`Build targets in project: 111`、`ninja [251/251]`、
  68 个扩展模块全部产出并导入可用。修复前的报错正是 ninja `[107/251]` 的
  `'scipy/special/cython_special.pxd' not found`。
- **「没变成假链接」的证明是二进制的**：`readelf --dynamic` 逐个看 68 个扩展的 `DT_NEEDED`，集合只有
  `libpython3.12.so.1.0`、`libc++_shared.so`、`libc.so`——没有任何 BLAS/special 库条目，符合 Cython 在 import 时
  解析符号的预期。测试脚本 `test_package/test_ohos_platform.py` 把这条断言固化为静态检查项。
- 运行期由真实 SciPy 满足：目标环境 numpy 2.2.1 / scipy 1.14.1 / joblib 1.4.2 / threadpoolctl 3.5.0，
  上游 34 个测试目录 37832 项用例全跑（0 failed / 0 error）。BLAS 相关的正确性另有直接证据：
  `test_sklearn.py` 对 `scipy.linalg.cython_blas` 做 float32+float64 的符号往返检查，并验证
  `randomized_svd` 与精确 `svd` 的谱误差 2.36e-07、`pairwise_distances` 与 scipy 计算一致到 1e-12。
- 边界：vendored 声明必须与运行期 SciPy 同族（签名兼容）。这条方案把「声明」与「实现」解耦，代价是若上游 SciPy
  改了某个 `cdef` 签名，偏移会推迟到 import 时才暴露（`ImportError`/符号错误）。因此务必在文档里钉住取出来源版本，
  并在配方里保留「真实 SciPy 优先」的分支，让有 SciPy 的环境自然走零偏移路径。
- 若上游代码生成阶段真的**执行**了该 Python 包的 API（不只是读声明），本方案不适用，退回把 wheel 装进构建解释器，
  但要接受运行期 numpy ABI 被拖进构建机的代价。

## 关系

- 适用组件：Cython + meson/setup.py 混合构建、且 `cimport` 外部 Python 包声明的项目（scikit-learn 及其同类）。
- 相关草稿：`DRAFT-cython-3.3.0-selfboot-pure-python-hybrid`（Cython 自身的 OHOS 打包）、
  `DRAFT-ohos-python-require-no-host-so`（纯 Python 包交付构建机 `.so` 的反面）；
  本条补的是**构建期声明依赖**这一层，与「打包后重签名」（E212 / `DRAFT-7939-gpgmepy-python-ext-selfsign-hmdfs`）正交。
- 验证记录：以 OHPCD scikit-learn 1.6.1 对应 PR 的最新机器人 CI 与 `test_package` 结果为准。
