# DRAFT-ohos-conan-python-require-cannot-depend-shared-library — 带 C 扩展的 Python 包不能声明 python-require，否则其 shared-library 依赖被拒

> Contributor: AtomCode/oh-executor | Status: **DRAFT** / Updated: 2026-09-30 / Severity: 3 (blocking)
> Source: biopython 1.88 HarmonyOS PC adaptation（PR 分支 `feat/biopython-1.88`）；
> 同形先例 cffi 2.1.1（`feat/cffi-2.1.1`，libffi 为 static-library）
> 对应：`knowledge/drafts/DRAFT-ohos-conan-python-require-cannot-depend-shared-library.kv`

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-ohos-python-require-no-host-so` | 已在 main（draft） | python-require 包**不导出宿主 .so**（打包/运行期视角） | 本条在其**上游**：`package_type` **声明本身**就是错的，依赖图根本解析不出来。失败点不同（图解析 vs 打包/运行期）、修法不同（改 `package_type` vs 改导出规则） |
| `DRAFT-multipledispatch-python-require-conan-staging` | 已在 main（draft） | python-require 包的 staging/安装布局 | 与本条的报错文本、根因（依赖类型相容性）均不同 |
| `DRAFT-ohos-conan-test-package-pythonpath-overwrite-clobbers-runenv` | 本会话新增（`feat/beniget-0.5.0`） | 消费测试脚本覆盖 PYTHONPATH | 那条是**运行期导入路径**；本条是**依赖图解析期**的类型相容性。二者常在同一个 Python 包上先后遇到，但根因与修法互不相干 |

**全库查证**：对 `cannot have a 'shared-library' dependency`、`package_type` 与
python-require 的相容性规则，在 `knowledge/graph/`、`knowledge/doc/`、`knowledge/drafts/`
中 grep —— 未命中同名方法论条目（cffi 2.1.1 只把结论写在 conanfile docstring 里，未沉淀）。

## Scope（何时用）

适配**带 C/C++ 扩展**的 Python 包，且该包**需要另一个已打包的编译型产物**时。

命中信号：

```console
ERROR: Package 'biopython/1.88' with type 'python-require' cannot have a
       'shared-library' dependency to 'numpy/2.5.2'
```

三条同时成立即命中：

| 条件 | 检查 |
|---|---|
| 包内有 C/C++ 扩展并在构建期编译 | 上游 `pyproject.toml` 的 `[[tool.setuptools.ext-modules]]`，或 `setup.py` 的 `ext_modules` |
| 扩展**真的链接**某个编译型依赖 | `nm -D <mod>.so \| grep -i <dep 符号>`（如 numpy 的 `PyArray_*`） |
| 该依赖在 ohpcd 上是 shared-library 或 static-library 制品 | 该包的 `options = {"shared": ...}` / `default_options` |

## ⭐ 核心结论：报错指向依赖，但错在**声明**

这条报错的措辞极具误导性——它读起来像「依赖有问题」，会把人引向
`requirements()`。但实际约束是 conan 的**类型相容性规则**：

> `python-require` 表示该制品是**纯 Python**（无头文件、无库、不可链接），
> 因此**不允许**依赖类型为 `shared-library` / `static-library` 的制品。

biopython 有 **13 个 C 扩展**，其中多个链接 **numpy 的 C-API**；numpy 在本仓是
`shared` 制品 → 触发该规则。

**修法：改声明，而不是改依赖**——该包确实产出可链接的编译产物，就应如实声明：

```python
class BiopythonConan(ConanFile):
    # biopython 带 13 个 C 扩展，链接 numpy 的 C-API；而 numpy 是 shared-library
    # 制品。conan 禁止 python-require 依赖带类型的库：
    #   ERROR: Package 'biopython/1.88' with type 'python-require' cannot have
    #          a 'shared-library' dependency to 'numpy/2.5.2'
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
```

**仓内先例**：`cffi/2.1.1` 因 `_cffi_backend` 链接 libffi（static-library 制品）而
采用**完全相同**的形态；`psutil` / `lxml` 同因同理。

> 判据：`package_type` 是对**制品性质**的声明，不是分类标签。一旦构建期真的产出
> `.so`，就不是纯 Python；继续写 `python-require` 是一个**假声明**，且它会连带
> 阻断所有库依赖进入依赖图。

## ★ 为什么容易误判

| 表象 | 真相 |
|---|---|
| 报错文本以 `Package '...'` 与 `dependency to 'numpy/...'` 为主 | 受约束的是**前者**（本包的类型），不是后者 |
| 报错出现在依赖图解析阶段，日志里**看不到任何编译输出** | 还没走到 `source()`/`build()`，所以「检查源码兼容性」「检查依赖是否已发布」全是误导方向 |
| 本仓绝大多数 Python 包都是 `python-require` 且工作正常 | 那些是**真·纯 Python**（无扩展）；本条命中与否只取决于「**是否链接编译型依赖**」 |

## 反例（禁止）

- ❌ **删掉 `requirements()` 里的依赖**去消除报错：扩展确实链接它，删掉只会让构建
  在后面以未解析符号失败，或产出一个「编得出、跑不起」的包。
- ❌ **保留 `python-require` 同时照常编译扩展**：假声明，会让本包及其消费者反复在
  依赖图解析上失败，且每次都被误诊为「依赖缺失」。
- ❌ 用 `self.cpp_info.bindirs/includedirs` 等去「绕开」该规则：规则约束的是
  `package_type`，与导出目录无关，绕不过去。

## 实测记录

| 包 | 依赖 | 依赖类型 | 报错 | 处置 |
|---|---|---|---|---|
| biopython 1.88 | `numpy/2.5.2` | shared-library | `... with type 'python-require' cannot have a 'shared-library' dependency to 'numpy/2.5.2'` | 改 `package_type = "library"` + shared 选项 |
| cffi 2.1.1 | `libffi/3.5.2` | static-library | 同形（`'static-library' dependency`） | 同法（先例） |

> 补充：若 numpy 在本仓是 header-only 制品，本包的 `python-require` 声明会**通过**，
> 该误分类便会潜伏到运行期才以 `ModuleNotFoundError` 形式暴露——所以不要以
> 「以前能过」作为声明正确的依据。
