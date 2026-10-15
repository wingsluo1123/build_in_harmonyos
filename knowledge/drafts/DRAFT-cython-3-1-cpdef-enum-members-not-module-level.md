# 编译器换代把破坏推到 import 期：平台只有一份 Cython 时，具名 cpdef enum 的成员导出必须自己补

> 草稿 ID：`DRAFT-cython-3-1-cpdef-enum-members-not-module-level`
> 来源任务：scikit-learn 1.6.1 HarmonyOS PC（OHOS aarch64）适配，`archives/s/scikit-learn/1.6.1/`
> 来源 PR：`feat/scikit-learn-1.6.1`
> 归档证据：`patches/0002-ohos-cython31-cpdef-enum-member-exports.patch`、`notes.md`「Cython 3.3 具名 cpdef enum 成员导出变更」、`reports/test-report.md` §2.2/§3、`test_package/MANIFEST.yml::upstream_tests[sklearn/utils/tests]`

## 适用场景

用 Conan 交叉编译任何含 `.pyx` 的 Python 扩展包，而平台的制品仓/索引里**只有一个 Cython 版本**时。
此时「编译器换代」不是一个可选项，配方必须接受仓里那一份；而换代带来的**语义变更不一定在编译期报错**，
它可能只改变生成模块的 Python 可见名字。命中的判据：源码里出现具名 `cpdef enum`（不是 `cdef enum`，
也不是匿名 enum），且有 Python 侧代码按裸名 import 它的成员。

## 现象与原因

scikit-learn 1.6.1 在本机 `conan create` 完全成功：251 个 ninja 目标、68 个扩展 `.so`、
静态通道 6 项 ELF/ABI 断言全绿。破坏点在运行期才出现，且有两处：

```console
$ python3.12 -c "from sklearn.utils._cython_blas import NoTrans"
ImportError: cannot import name 'NoTrans' from 'sklearn.utils._cython_blas' (..._cython_blas.cpython-312-aarch64-linux-ohos.so)

$ python3.12 -m pytest .../sklearn/utils/tests/test_cython_blas.py
ERROR .../sklearn/utils/tests/test_cython_blas.py
E   ImportError: cannot import name 'ColMajor' from 'sklearn.utils._cython_blas'
!! 1 error during collection !!
```

上游 `sklearn/utils/_cython_blas.pxd` 声明的是具名 `cpdef enum`：

```cython
cpdef enum BLAS_Order:
    RowMajor
    ColMajor
cpdef enum BLAS_Trans:
    NoTrans = 110
    Trans = 116
```

Cython 3.1 起（官方 CHANGES 在 3.1.0rc1/2025-05-01 明写：*Named "cpdef enums" no longer copy their
item names into the global module namespace*）只导出 enum 类 `BLAS_Order` / `BLAS_Trans`，
不再把 `RowMajor`/`ColMajor`/`NoTrans`/`Trans` 平铺到模块级。而 `sklearn/utils/tests/test_cython_blas.py`
以及任何沿用旧写法的下游代码 import 的正是裸名。本机型只有 Cython 3.3.0：

* Conan 制品仓里 3.0.x / 3.1.x / 0.29.x 均无二进制（逐个 probe 皆缺）；
* 平台 pip 索引 `pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi` 的 `cython` simple 页只列 3.3.0。

所以「降回 3.0.x」在 Conan 配方里无处落地，把补丁写进 `.pyx` 是唯一能同时保住上游测试与下游用法的做法。

三个容易把人带偏的点：

1. **它不是构建缺陷**。编译器只做了一件合法的事，`conan create` 退出码 0、产物数量正确、
   ELF 全合规，所有「看构建」的门禁都拦不住；只有 import 期才暴露。
2. **失败长得像包坏了**。`ImportError: cannot import name 'X'` 首先让人怀疑扩展缺失/命名错误/ABI 不匹配，
   而真实原因在生成端的名字表。判据是：**enum 类本身能 import 成功**，只有成员裸名失败。
3. **它会污染历史证据**。本例此前归档的上游全量计数来自另一条工具链产物
   （`_cython_blas…so` 506 176 B，裸名可用）；换到 3.3.0 后同一文件的产物是 342 400 B（裸名缺失）。
   只要编译工具链换代，旧计数就描述不了新制品——计数必须在**将要交付的那份产物**上重跑，
   否则报告里的数字是在描述另一个二进制。

## 处理方法

1. **在 `.pyx` 末尾按 Cython 官方建议显式回填成员**，值不变、语义不变，只补名字表
   （补丁 `patches/0002-ohos-cython31-cpdef-enum-member-exports.patch`，`portability`）：

   ```cython
   for _blas_enum in (BLAS_Order, BLAS_Trans):
       globals().update(
           {_blas_member.name: _blas_member for _blas_member in _blas_enum})
   del _blas_enum
   ```

   注意 `_blas_member.name` 取的是成员名，`110/116` 这类显式值由 enum 成员对象自己携带，不需要手写常量。
2. **补丁登记进 `conandata.yml`**（`patch_file`/`patch_description`/`patch_type`），描述里写清
   「Cython ≥ 3.1 不再导出具名 cpdef enum 成员」+「本机型只有 3.3.0」，评审才看得出这是平台约束而非随意改上游。
3. **加一条真实消费者断言把它钉住**：`test_package` 的运行期用例直接调 BLAS 裸名接口
   （本例 `test_sklearn.py::blas`：`dot/asum/nrm2/copy/axpy/scal/gemv/gemm` 对 float32/float64 往返）。
   只有上游套件在真机跑过才可靠的前提是 CI 拿得到运行期依赖；本例 CI 拿不到 scipy，
   所以这条必须进 `test_package` 而不是只留在离线报告里。
4. **换代后重跑上游计数**，而不是沿用旧产物数字；同时核对
   `collected == passed + failures + errors + skipped + xfailed` 恒等式。

## 验证与边界

* 生成端独立验证：同一份（未打补丁的）`_cython_blas.pyx` + 其 `.pxd` 用 Cython 3.3.0 转译
  生成 1.77 MB C 后，按上面 4 行补丁转译成功且成员名进模块字典；补丁后真机
  `from sklearn.utils._cython_blas import NoTrans` 成功。
* 端到端：`conan create`（`cython/3.3.0`）→ 静态通道 6/6、运行期 OHOS 平台通道 9/9、
  消费者用例 12/12（补丁前 `blas` 那一条是 `ImportError`，即 11/12）。
* 上游侧：补丁后在**将要交付的那份产物**上重跑 `sklearn/utils/tests`（真机 JUnit）——
  `tests=2998 / failures=0 / errors=0 / skipped=1264`，其中 `test_cython_blas.py` 的 44 条用例
  全部通过（补丁前该文件在收集阶段就报 1 个 error，一条都跑不了）。逐目录计数见
  `test_package/MANIFEST.yml::upstream_tests`。
* 边界与不推荐做法：
  * **不要**把失败的测试文件标成 `skip`/`xfail` 来「恢复绿色」——那是少报上游用例，评审直接判不合格。
  * **不要**逐个改 import 点（上游有测试与多处内部引用，下游用户代码改不到）。
  * **不要**为了迁就旧语义去 pin 一个仓里不存在的 Cython 版本；先 probe 再下结论。
  * 只有一份 Cython 且它是新版时，改 `.pyx` 是**制品级**修复，应同时向上游提 issue/PR，
    否则下个版本还要再打一次。
* 适用范围：任何「构建期工具换代 → 生成物 Python 可见名字变化」的移植问题都同形，
  具名 `cpdef enum` 只是最常见的一种（同类还有 `cpdef` 函数的签名包装、`bint`/`bool` 导出名）。

## 关系

* 相关草稿：`DRAFT-scikit-learn-1.6.1-cython-pxd-vendoring`（同一构建里 SciPy 声明文件的获取方式）、
  `DRAFT-cython-3.3.0-conan-package-missing-top-level-pymodules`（同为 Cython 3.3.0，但那是 Cython 自身
  Conan 交付物缺 `cython` 顶层模块，与本条的生成语义变更是两回事）、
  `DRAFT-static-artifact-count-pinning`（同为「构建全绿但交付物不可用」的假绿家族）。
* 适用组件：Conan 配方 `tool_requires` 选定的 Cython、任何 `.pyx` 含具名 `cpdef enum` 的扩展包、
  以及依赖这些裸名的上游测试模块与下游用户代码。
* 验证记录：以 OHPCD scikit-learn 1.6.1 对应 PR 的最新机器人 CI 与 `test_package` marker 为准。
