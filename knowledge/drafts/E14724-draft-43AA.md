# E14724 — 纯 Python 依赖的 site-packages 布局不统一

## 错误特征

构建/测试期静默出现依赖不可见，运行期才炸：

```
ModuleNotFoundError: No module named 'serial'
```

或 `package_info()` 里对无 `package_folder` 的依赖取属性时：

```
TypeError: expected str, bytes or os.PathLike object, not NoneType
```

`conanrun.sh` / `conanbuild.sh` 里对应的 `PYTHONPATH` 段落中，该依赖目录**根本没有出现**。

## 触发条件

- 构建系统: Conan 2（任意）
- 阶段: packaging（`package_info()` 拼 PYTHONPATH 时）
- 前提: 本包用一个**固定路径**去猜依赖的 site-packages 位置，而依赖的 payload
  布局与假设不符

## 根因分析

本仓库的纯 Python 配方由多个来源/时期生成，payload 目录至少存在三种布局：

| 布局 | 实例 |
|------|------|
| `lib/pythonX.Y/site-packages` | `packaging` 风格配方 |
| `lib/python/site-packages`（不带版本号） | `pyserial/3.5`、`six/1.17.0`（实测） |
| flat（模块直接躺在包根） | `tinyprog` 自身（本适配实测） |

`package_info()` 里若只写死其中一种（例如只认 `lib/pythonX.Y/site-packages`），
另一种布局的依赖就探测失败 → 返回空 → `PYTHONPATH` 少一段 → 消费者 import 失败。

三重加剧因素：

1. **无构建期报错** —— 探测失败只是"少 append 一个路径"，构建照样绿；CI 的 L1/`test_package` 才暴露。
2. **`run` 与 `build` 两个环境是分开的** —— 只写 `runenv_info` 的依赖（`six/1.17.0` 实测无 buildenv），构建期消费者看不到，必须两边都 append。
3. **`self.dependencies` 可能含无 `package_folder` 的条目** —— 直接 `dep.package_folder` 取用会抛 `NoneType`。

## 解决方案

### 推荐方案

写一个探测器，按顺序返回首个存在的目录，并对每个依赖逐个调用：

```python
def _dep_site(self, dep):
    folder = dep.package_folder
    if not folder:
        return None
    for candidate in (
        os.path.join(folder, "lib", self._py_tag(), "site-packages"),
        os.path.join(folder, "lib", "python", "site-packages"),
    ):
        if os.path.isdir(candidate):
            return candidate
    if os.path.isdir(folder):
        return folder
    return None
```

探测到后 **runenv 与 buildenv 同时** `append_path`。

### 回退方案

无法确定依赖布局时，把依赖包根目录本身加进 `PYTHONPATH`（flat 兜底），
但这对 `lib/` 子目录布局无效，只能救 flat 类依赖。

### 禁止做法

- ❌ 硬编码 `os.path.join(folder, "lib/python/site-packages")` 一种路径。
- ❌ 只写 `runenv_info` 不写 `buildenv_info` —— 依赖只发布 runenv 时构建期消费者看不见。
- ❌ 不做 `if not folder: return None` 空值保护 —— 图上存在未解析节点的场景会抛 `NoneType`。

## 验证

`tinyprog` 1.0.23 的 `package_info()` 采用上述探测器，对
`pyserial/3.5` 与 `six/1.17.0` 逐个探测；消费者视角断言见
`test_package/test_tinyprog.py::test_05_dependency_wiring`：

```bash
conan test archives/t/tinyprog/1.0.23/test_package tinyprog/1.0.23 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
```

实测：`Ran 12 tests ... OK`（`serial`/`six` 均从 conan 依赖包解析成功）。

## 关联条目

- 相似: E14723（同一族的"依赖不可见"根因——那条是 `run=True` 缺失导致节点被 Skip，
  本条是节点在但路径没拼对；两条常同时出现，修一条不代表另一条已修）
