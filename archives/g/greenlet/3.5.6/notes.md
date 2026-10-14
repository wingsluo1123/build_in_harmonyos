# greenlet 3.5.6 适配笔记

## 概述

greenlet 提供轻量级**进程内协程**（greenlet 之间显式 `switch()` 协作式切换），
是 gevent / SQLAlchemy 异步等生态的底座。

- 上游：https://greenlet.readthedocs.io/（源码 https://github.com/python-greenlet/greenlet）
- 版本：3.5.6
- 构建系统：**setuptools（编译型 C++ 扩展）**
- 许可：MIT AND PSF-2.0
- 编译日期：2026-09-16
- 状态：built

## 与同批其他 Python 包的本质区别

本批次四个包里，markupsafe / itsdangerous / pycparser 都是**纯 Python**（直接拷
目录即可），**greenlet 不是**：

| 特征 | 纯 Python 包 | greenlet |
|---|---|---|
| 交付物 | `.py` 文件 | **`_greenlet.cpython-312-aarch64-linux-ohos.so`** |
| 是否需要编译 | 否 | **是**（`src/greenlet/*.cpp` 约 20 个文件）|
| 纯 Python 回退 | 有（如 markupsafe `_native`）| **没有**——`__init__.py` 无条件 `from ._greenlet import ...` |
| 是否需要 python 依赖 | 否 | **是**（`python/3.12.9`，取 Python.h 与 libpython3.12.so）|
| 与构建机绑定 | 否 | **是**（CPython ABI + 架构）|

同仓先例：`lxml` / `pillow` / `cppy` / `astlib` 均为同类的编译型 Python 包。

## 依赖

`requires("python/3.12.9")` —— 扩展编译需要：

- `include/python3.12/Python.h` 等头文件；
- `lib/libpython3.12.so`（**链接期必需**，见下节）。

**不需要 setuptools / `setup.py`**（早期版本曾如此，已整体移除）：配方在
`build()` 内**直接调用 clang 编译**三个扩展模块，理由见下节「为什么不用 setup.py」。
conan 的 python 制品与 CI 环境**都不提供 setuptools**（实测五个候选路径全部落空，
CI #10488 即死于 `No module named 'setuptools'`），直接编译从根上消除了该依赖——
与 `archives/a/aggdraw/1.4.1` 同一做法。

## 核心问题：必须显式 `-lpython3.12`（否则链接通过但 import 失败）

**现象**：不加该标志时，**编译能成功产出 `.so`**（无论早年经 `setup.py build_ext`
还是本配方现在的直接 clang 编译），但 import 瞬间失败：

```
ImportError: Error relocating .../_greenlet.cpython-312-aarch64-linux-ohos.so:
               _Py_IsFinalizing: symbol not found
```

**根因**：`_Py_IsFinalizing` 由 `libpython3.12.so` 提供（实测
`nm -D --defined-only libpython3.12.so` 可见）。musl **不从主可执行文件导出
Python 符号**（glibc 下 `python3` 可执行文件会导出，musl 不会），因此扩展若
不显式链接 `libpython3.12.so`，运行时便找不到该符号。

**修法**（与 lxml / pillow 同一结论）：

```python
LDFLAGS="-fuse-ld=bfd -L{py_lib} -lpython3.12"
```

- `-L{py_lib} -lpython3.12`：显式链接 libpython；
- `-fuse-ld=bfd`：**用 GNU ld.bfd 做链接**（lxml / pillow 同款；OHOS SDK 默认
  lld 在此场景下未被验证，沿用既有可用组合）。

> 这是本包最容易踩的坑：**构建成功 ≠ 可用**。仅看 `build_ext` 的退出码会误判，
> 必须实际 import 一次。

## 需要代码签名（与 lxml/pillow 一致）

`package()` 内用 `binary-sign-tool sign -selfSign 1` 给产出的 `.so` 签名
（先 `llvm-objcopy --remove-section .codesign` 清理，再签）。

**订正**：初版 notes 曾写「本包实测不需要签名：未签名 `.so` 拷到另一目录后
`import greenlet` 与 `switch()` 均正常」——**该结论是错的**，成因是当时验证用的
行为不足以暴露问题（当时未跑 pytest，而 dlopen 失败只在 pytest 收集阶段显形）。
实测：构建期经 `-fuse-ld=bfd` 链接出的模块**无 `.codesign` 段**，HMDFS 拒绝
dlopen，pytest 收集即报

```
ImportError: Error loading shared library .../_greenlet...so: Permission denied
```

因此现在**三个**模块都在 `build()` 内、跑 pytest **之前**签名：
greenlet 本体 + `greenlet.tests._test_extension` + `_test_extension_cpp`
（后两个是配方在 `build()` 内额外编译的 C/C++ 测试扩展，早期由 `setup.py` 构建；
缺签会让 2 个测试文件无法收集）。
`package()` 复用同一 `_sign_extensions()` helper——conan 的 `copy` 会使签名失效，
故打包后需**重新签**。

## 上游测试：已可收集并真实运行（3 处阻塞，逐一修复）

初版结论是「上游测试不可运行」——**该结论只对了一半，且当时并未查到底**。
经逐层排查，实际有 **3 处独立阻塞**，任一未修都无法收集；现已全部修复。

### ① `tests/__init__.py:17` 裸 `import psutil`（CI 报出的那处）

模块级裸导入、无 `try/except` 守卫，而 psutil 只是**测试期可选依赖**
（greenlet 运行时依赖为无）。pytest 导入测试包时即执行该行 → **整个套件收集中断**。

> 早期 psutil **未发布到 ohpcd**，故当时连 `test_requires` 都声明不了；现已发布，
> 配方经 `build_requirements()` 以 `tool_requires` 声明它（见「测试依赖来源」一节）。

修法：`patches/0001-tests-psutil-optional.patch`——导入改为可选；缺失时
`get_process_uss()` 抛 `unittest.SkipTest`。**沿用上游既有语义**：上游本就为
「uss 不支持」写了 `except AttributeError -> SkipTest`（`tests/__init__.py:213-214`），
故这不是新造行为，也不伪造内存数据。依赖已就位时不走该分支，补丁保留为降级路径。

### ② `objgraph` 的两处裸导入（修完 ① 才暴露）

`objgraph` 同为测试期可选依赖，且有**两个**导入点：

- `tests/leakcheck.py:32`（被 `tests/__init__.py:33` 导入）
- `tests/test_cpp.py:6`

**只修第一个仍会失败**（实测：修 psutil 后收集错误转为 `objgraph`；
修完 `leakcheck.py` 后 `test_cpp.py` 继续报 `No module named 'objgraph'`）。
这是本次排查中最关键的一步——逐个修会反复失败，必须一次性扫全。

修法：`patches/0002-tests-objgraph-optional.patch`——两处导入均改为可选；
`leakcheck._growth()` 与 `test_cpp` 唯一用它的用例抛 `SkipTest`，**不伪造增长数据**。

> 排查方法：用 AST 扫描 `tests/` 全部 `.py` 的非标准库顶层导入，一次性列出
> 完整依赖面（`python3 -c` 遍历 `ast.Import`/`ast.ImportFrom`），
> 而不是「报一个修一个」。结论只有两个：`objgraph`（2 处）、`psutil`（1 处）。

### ③ 构建期扩展未签名 → HMDFS 拒绝 dlopen（改完 ①② 才暴露）

配方（早期经 `setup.py`、现在直接调用 clang）用 `-fuse-ld=bfd` 链接出的三个扩展模块**无 `.codesign` 段**，
HMDFS 拒绝加载，pytest 在收集阶段即报：

```
ImportError: Error loading shared library .../_greenlet...so: Permission denied
```

三个模块都要签：greenlet 本体 + `greenlet.tests._test_extension` +
`_test_extension_cpp`（后两个缺失会让 2 个测试文件无法收集）。

修法：`build()` 内新增 `_sign_extensions()`，在跑 pytest **之前**签名这三个模块；
`package()` 复用同一 helper（conan 的 `copy` 会使签名失效，需重新签）。

### ④ 早期阶段的过渡手段：上游自带的 env 闸 `GREENLET_SKIP_LEAKCHECKS=1`

> ⚠️ **本节记录的是已废弃的早期做法**，配方**现已不再设置**该变量（见下方说明）。
> 保留此节是为了说明"为什么最终选择引入依赖而不是绕过检查"。

修完 ①②③ 后套件可收集，但一度出现 **3 passed / 168 skipped**——原因是
`tests/__init__.py:72` 用 `wrap_refcount` 包裹了**每一个**测试方法，
而 objgraph 缺失使泄漏检查抛 `SkipTest`，于是几乎整套被跳过。
这不是有效验证（等于没跑）。

当时的两条出路：

| 方案 | 结果 |
|---|---|
| (a) 设上游的 `GREENLET_SKIP_LEAKCHECKS=1` 关掉泄漏检查（`leakcheck.py:70`；上游 manylinux 镜像用等价的 `GREENLET_MANYLINUX`）| 早期实测 **161 passed / 10 skipped / 1 failed** |
| (b) **引入 objgraph**，让 `wrap_refcount` 正常工作、泄漏检查真跑 | **最终选择** —— 见下 |

**最终采用 (b)**：`objgraph/3.6.2` 与 `psutil/7.2.2` 发布到 ohpcd 后，配方经
`build_requirements()` 以 `tool_requires` 声明它们，(a) 的 env 闸随之**移除**。
理由是 (b) 的证据强度严格更高——泄漏测量是**真实的检测路径**，而不是被绕过的一条；
且覆盖上游开关反而会削弱本可获得的覆盖率。
若依赖将来不可用，相关用例会经补丁退回 `SkipTest`，**计数会如实反映**（不掩盖）。

### ⑤ 早期残留的 1 failed：平台缺陷，已就地修复

> ⚠️ 状态：**已解决**（当前实测 0 failed）。

早期 `test_version.py::VersionTests::test_version` 报
`TypeError: can't concat str to bytes`（`os.popen` 的文本模式读取）。
**用宿主 Python 一行式即可复现**（完全不涉及 greenlet）：

```python
import os, sys; os.popen("%s -c 'print(123)'" % sys.executable).read()
# TypeError: can't concat str to bytes
```

根因是 python/3.12.9 补丁 0014（`_harmonyos_compat.py`）把 `os.popen` 包装为
subprocess 时，既传 `text=True`、又对已是文本的 `proc.stdout` 再套一层
`io.TextIOWrapper`，双重解码使 `read()` 必抛 TypeError——**平台缺陷，与 greenlet
及任何依赖无关**。

修法：配方在 pytest 前经 PYTHONPATH 注入 `sitecustomize.py` 就地纠正该包装
（**不改任何上游测试文件**；平台侧根治见 PR #10882 = python/3.12.9.1）。

### 结论

上游测试**已可收集（172 项）并真实运行：166 passed / 6 skipped / 0 failed**。
6 个 skip **全部为上游自身版本/平台闸**（free-threaded×3、3.15+×2、3.13+×1），
与本适配及依赖无关；早期那 4 个「缺依赖」skip 已随依赖引入而消除
（10 skip → 6 skip）。
修复由 2 份补丁 + 构建期签名 + 引入测试依赖（objgraph/psutil）+ `os.popen` 平台缺陷
shim 共同达成。

**该套件现为硬门禁**：若收集失败或 pytest 非 0 退出，`build()` 直接
`raise ConanException` 拒绝出包——避免此处记录的通过数在上游回归时静默失真。

## 消费者测试（test_package）

`test_package/test_greenlet.py`，9 组真实 API 断言（R34）：

| 组 | 断言 |
|---|---|
| 版本与导出 | `__version__ == "3.5.6"`；`__all__` 8 项逐一比对 |
| 编译期特性 | `GREENLET_USE_CONTEXT_VARS == 1`、`GREENLET_USE_GC == 1`、`_C_API` capsule 存在 |
| **切换顺序** | 双 greenlet ping-pong：`["a1","b1","a2","b2"]`（协作式交错的直接证据）|
| 惰性执行 | 构造 greenlet **不运行**函数，`switch()` 才跑 |
| `getcurrent()` | greenlet 内返回自身；主协程内返回 main |
| parent 与状态 | `parent is main`；执行完 `dead is True`、`bool()` 为 False |
| 异常传播 | greenlet 内未捕获异常向调用者抛出（`ValueError`）|
| `GreenletExit` | 协作终止信号：`switch()` **返回该实例**而非抛出 |
| `throw()` | 向挂起 greenlet 注入异常，可被其捕获；greenlet 对象可哈希 |

## 验证结果

```
conan create archives/g/greenlet/3.5.6 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ exit=0
```

| 项 | 实测结果 |
|---|---|
| `conan create` | **exit=0**，Package created |
| 扩展编译 | `built extension: ['_greenlet.cpython-312-aarch64-linux-ohos.so']`（546352 B）|
| 扩展签名 | `signed extension module(s): ['_greenlet...so', '_test_extension...so', '_test_extension_cpp...so']`（第 ① 阶段只签 1 个，现签 3 个）|
| **上游测试收集** | **`upstream tests collected: 172 test items`** ✓（初版为 0，收集即失败）|
| **上游 pytest** | **`166 passed, 6 skipped, 33 subtests passed in 96.73s`**（测试依赖经 `build_requirements()` 由 conan 提供；早期版本曾为 `1 failed, 161 passed, 10 skipped`）|
| **上游通过率（规范口径）** | **100%（166/166）** —— 口径 `passed/(passed+failed+errors)`，skipped 不计入分母 |
| **上游通过率（全量口径）** | **96.5%（166/172）** —— 分母为全部收集项（含 6 个 skip）|
| 6 个 skip 的原因 | **全部为上游自身版本/平台闸**（`Only free-threaded builds are affected`×3、`Test is 3.15+ only`×2、`Needs 3.13 and above`×1），与本适配及依赖无关；早期那 4 个「缺依赖」skip（`objgraph not available`×1、`psutil not available`×3）已随依赖引入而消除 |
| 早期 1 failed 的处置 | `test_version.py::VersionTests::test_version` —— `os.popen` 文本模式 `TypeError: can't concat str to bytes`，属 python/3.12.9 平台缺陷；已由配方注入的 `sitecustomize` shim 就地纠正（不改上游测试文件），本次实测 **0 failed** |
| **消费者测试通过率** | **100%（22/22）** —— 9 组断言、**22 个硬失败点**（21 条 `assert` + 1 条 `raise SystemExit` 守卫，AST 实测）全过，0 failed / 0 skipped；与 `test_package/MANIFEST.yml` 的 `assertion_count: 22` 同口径 |
| 消费者测试 | `greenlet 3.5.6 consumer API: PASS`（9 组断言全过）|

### 关键对照：修复前后（同一份代码）

| 阶段 | 现象 |
|---|---|
| 无 `-lpython3.12` | `.so` 能生成，但 import 报 `Error relocating ... _Py_IsFinalizing: symbol not found` |
| 加 `-lpython3.12` 后未签名 | import 报 `ImportError: Error loading shared library ... Permission denied`（HMDFS 拒 dlopen；`.codesign` 段数 **0**）|
| **签名后** | `.codesign` 段数 **1**，`import greenlet` + `switch()` 正常 → **PASS** |

## 注意事项

1. **必须 `-lpython3.12` + `-fuse-ld=bfd`**——否则 `.so` 能生成但 import 失败
   （`_Py_IsFinalizing: symbol not found`）；这是 musl 不导出主程序符号所致；
2. **不要只测构建退出码**——编译型扩展必须实际 import 才算验证；
3. **交付物必须含 `.so`**——`package()` 内已断言，缺失即 `ConanException`；
4. `.cpp/.hpp/.h/.c/.pyi` 不随包交付（只交付运行所需的 `.py` + `.so`）；
5. **测试依赖来源**：上游 `pyproject.toml [project.optional-dependencies].test`
   声明的 `psutil` / `objgraph` 现均已发布到 ohpcd，配方经 `build_requirements()`
   以 `tool_requires("psutil/7.2.2")` / `tool_requires("objgraph/3.6.2")` 声明，
   并从其制品取出 site-packages 前置到 `PYTHONPATH`。
   改用 conan 制品的理由是**可复现、可审计、符合 R36**（版本锁进依赖图，
   且不像 pip `--break-system-packages` 那样污染全局 site-packages）。
   > 实测澄清（勿传播相反的想当然结论）：平台镜像的
   > `psutil-7.2.2-cp312-cp312-ohos_aarch64.whl` **本身已带 `.codesign` 段**
   > （`llvm-readelf -S | grep -c codesign` = 1），可直接 import 并调用其
   > C 扩展（`psutil.Process().memory_full_info().uss` 实测有值）。
   > 即**签名不是**改用 conan 制品的理由。
   两份 `patches/000{1,2}-tests-*-optional.patch` 保留为依赖不可用时的降级路径。
