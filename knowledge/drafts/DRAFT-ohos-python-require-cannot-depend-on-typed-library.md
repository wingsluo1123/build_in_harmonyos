# DRAFT-ohos-python-require-cannot-depend-on-typed-library — python-require 不能依赖带类型的库

> Contributor: 9C6E / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 3 (high)
> Prospect ID: `DRAFT-ohos-python-require-cannot-depend-on-typed-library`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E283` | 图谱 | **`library` 类型必须有 `shared` 选项**（契约本身）| E283 讲"有了 library 之后必须补 shared"这条规则；**本条讲"何时该从 `python-require` 切到 `library`"**，并给出两条错误是**同一动作的连锁后果**。实测 E283 全文不含 `python-require` / `cannot have a dependency` 判据 |
| `DRAFT-multipledispatch-python-require-conan-staging` | 草稿 | **纯 Python** 包误套 setuptools/pip 构建链（最小解释器）| 那是"纯 Python 包**不该**跑构建链"；本条是"**编译型**包**必须**依赖 python，因而**不能**用 python-require 类型"——方向相反 |

**全库查证**：对 `python-require` × `library`、`cannot have a dependency`、
`static-library` × Python 等组合关键词 grep —— 除上表两条（机制不同）外**命中 0 条**
专讲此类型切换的条目。

## Scope（何时用）

**编译型** Python 包（含 C/C++ 扩展的 Python 库）：greenlet / lxml / pillow /
cppy / numpy / astlib 等。

| 包类型 | 是否需要 `requires("python/...")` | 正确 `package_type` |
|---|---|---|
| 纯 Python（只有 `.py`）| 否 | `python-require` |
| **编译型扩展（有 `.so`）** | **是**（要 `Python.h` 与 `libpython`）| **`library` + `shared`** |

## Symptom

**第一条错误**（类型冲突）：

```console
ERROR: Package 'greenlet/3.5.6' with type 'python-require' cannot have a
       'static-library' dependency to 'libffi/3.5.2'
```

**第二条错误**（改了类型的连锁后果）：

```console
ERROR: greenlet/3.5.6: Package type is 'library', but no 'shared' option declared
```

> ⚠️ 两条错误是**同一处修改的连锁**。只修第一条、不补 `shared`，会在下一步再次
> 失败（本次实测正是如此，多跑了一轮）。

## Root Cause

Conan 2 对 `package_type` 施加强约束：`python-require` 表示"纯 Python 运行时
依赖"，**不允许**依赖任何带自身类型的库。而编译型扩展必须
`requires("python/3.12.9")`，该包会**传递带入 `libffi`（`static-library`）**——
于是 conan 在依赖解析阶段直接拒绝。

这是**类型契约冲突，不是版本问题**：换 python 版本、换 libffi 版本都无济于事。

## Recommended Solution

### 主方案（priority 1）— 类型 + shared 一次到位

```python
package_type = "library"
options = {"shared": [True, False]}
default_options = {"shared": True}
```

**两处必须同时改**（否则第二轮又失败）。理由：

- 产物本质是共享对象（`.so` 扩展模块）→ `library` + `shared=True` 语义正确；
- `requires("python/3.12.9")` 提供 `Python.h` 与 `libpython3.12.so`。

**与本仓既有先例一致**：`lxml` 6.1.1 与 `pillow` 10.4.0 均为
`package_type = "library"` + `requires("python/...")`。

**反向要求**：纯 Python 包（markupsafe / itsdangerous / pycparser）应**保持**
`python-require`，不要为"统一"改成 `library`——它们没有共享对象，
标成 `library` 反而要无谓地声明 `shared`。

### 回退方案（priority 2）— 不依赖 python 包

若希望维持 `python-require`（例如该包同时还有纯 Python 用法），可改为**不声明
python 依赖**，改用构建机解释器的头文件与 libpython（本仓 setuptools bootstrap
即此思路）。代价是绑定构建机环境、可复现性下降，且 CI Worker 与本地解释器路径
不同——**仅作兜底**。

### 禁止做法

- ❌ 只改 `package_type` 却不声明 `shared`——连锁报错，多跑一轮；
- ❌ 为编译型扩展保留 `python-require` 并同时 `requires("python/3.12")`——
  conan 层面直接拒绝，无法绕过。

## 实测证据（2026-09-16，greenlet 3.5.6 适配）

| 阶段 | 结果 |
|---|---|
| 初版（`python-require` + `requires("python/3.12.9")`）| `cannot have a 'static-library' dependency to 'libffi/3.5.2'` |
| 只改 `package_type = "library"` | `Package type is 'library', but no 'shared' option declared` |
| **补 `options`/`default_options` 后** | 依赖解析通过，继续到编译阶段 |
| 先例核对 | `lxml` 6.1.1 / `pillow` 10.4.0 均为 `library` + `requires("python/...")` |

## 测试覆盖边界

本条处理"**类型选择与必需选项**"。区分相邻情形：

- `library` 类型缺 `shared` 的**契约规则本身** → `E283`；
- 纯 Python 包误走构建链 → `DRAFT-multipledispatch-python-require-conan-staging`。

## 关联条目

- 相似：`E283`（library 的 shared 选项契约）
- 差异：E283 是"library 之后要什么"，本条是"**何时该变成 library**"
