# DRAFT — conan 2 的 `self.dependencies.*.items()` 键是 `Requirement` 对象，直接 `sorted()` 必抛 `TypeError`

> 触发事件：greenlet 3.5.6（PR #10408）第 1 轮 CI。
> `conan create` 在 `build()` 遍历 build 上下文依赖时立即失败（2026-10-02 CI 实测）。

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `DRAFT-6052-libnxml-0.18.5-ci-l0o-bare-dep-name-false-positive` | 草稿 | `self.dependencies["curl"]` 的**裸依赖名**被 CI L0o 门禁正则误判为外部命令 | 同属 `self.dependencies` 的 API 语义坑，但那条的键是**字符串索引**；本条是 `items()` 的**键类型**（Requirement 对象） |

**结论：本条为真增量**（无条目覆盖「`items()` 键为 `Requirement`，不可排序」）。

## 错误特征

```
ERROR: greenlet/3.5.6: Error in build() method, line 290
        self._run_upstream_tests()
while calling '_run_upstream_tests', line 406
        for _name, _dep in sorted(self.dependencies.build.items()):
TypeError: '<' not supported between instances of 'Requirement' and 'Requirement'
```

**辨识要点**：报错文本里只有 `Requirement`，**看不出**这是「conan 依赖对象作为 dict 键」，
还是业务代码里的自定义类。且发生在 `build()` 早期，容易误判为依赖图/环境问题。

## 根因分析

conan 2 的 `UserRequirementsDict`（`conan/internal/model/dependencies.py`）以
`Requirement` 对象为内部 dict 的键：

```python
def items(self):
    return self._data.items()          # → (Requirement, ConanFileInterface) 对
```

包名要经 `require.ref.name` 取。`Requirement` **未实现 `__lt__`**，
故 `sorted(...items())` 直接崩在排序上 —— 与依赖内容无关，属于纯 API 误用。

## 推荐方案

需要确定性顺序时，先取出名字再排：

```python
_items = []
for _req, _dep in self.dependencies.build.items():
    _name = getattr(getattr(_req, "ref", None), "name", None) or str(_req)
    _items.append((_name, _dep))
for _name, _dep in sorted(_items, key=lambda kv: kv[0]):
    ...
```

**备选**：若顺序无关，直接遍历 `items()` 即可 —— conan 内部用 `OrderedDict`，本身有序。

## 禁止做法

- ❌ **不要**对 `self.dependencies.*.items()/keys()/values()` 直接 `sorted()/min()/max()`：
  键是 `Requirement`，无比较运算符。
- ❌ **不要**把 `Requirement` 当字符串比较/拼接（如 `if _name == "pytest"` 而 `_name` 实为对象）：
  比较恒为 False，**依赖筛选静默失效**，不抛异常，比第一条更难发现。

## 验证证据

- **主证据（CI）**：greenlet 3.5.6 / PR #10408 第 1 轮，上面的 traceback。
- **本地验证**：用刻意**未实现 `__lt__`** 的 stub `Requirement` 复现同一 `TypeError`；
  改为按 `require.ref.name` 排序后，依赖名全部正确取出、`python` 被跳过、缺 pytest 仍显式告警。
- **API 依据**：直接读 conan 2.29.1 源码 `conan/internal/model/dependencies.py`
  （`UserRequirementsDict.items()` 返回 `self._data.items()`，键为 `Requirement`；
  `_get()` 内部以 `require.ref.name` 取包名）。

## 查重结论

- 对 `dependencies.build.items` / `Requirement.*sorted` / `require.ref.name` 检索：
  仅命中 DRAFT-6052（字符串索引误区），**键类型误区 0 命中**。
- **盲区声明**：基于本地已合并知识（本地 main + 本分支），无法排除外部有人提交同主题草稿。
