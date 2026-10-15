# DRAFT-python-ext-import-classify-by-package-own-error — 扩展 import 分类：让包自己说话，别硬编码依赖分组

> 草稿（待审核 promote）。来源：biopython 1.88（PR #14021，提交 `3dda766ba5`）。

## 症状

第一轮把 5 个 `Bio.Align.*` 扩展挪进"numpy 分支"后，CI 仍在下一处翻车：

```text
Bio.MissingPythonDependencyError: Install NumPy if you want to use Bio.motifs.
```

出在 `Bio.motifs._pwm`——**其父包** `Bio/motifs/__init__.py` 在缺 numpy 时同样 raise。

## 根因

上游把"缺依赖"实现为**包级异常**：import 子模块时父包 `__init__` 先检查依赖。
"哪些模块需要 numpy"是**开放集合**，手工分组必然漏；名单还会随上游演进持续漂移。

## 修法（classify by raised exception + 台账断言）

import 循环里按**异常本身**分类：

| 异常形态 | 归类 | 理由 |
|---|---|---|
| `MissingPythonDependencyError` / 消息含 `nstall NumPy` | `need_numpy` | 包在说"这能力需要 numpy"，与本包适配无关 |
| 消息含 `Error loading shared library` / `symbol not found` | `env_limited` | E212 族：HMDFS 拒载用户可写路径下的 .so |
| 其余异常 | **原文打印后 raise** | 真失败，不吞 |
| 成功加载 | 校验 `__file__` 以 `.so` 结尾 | 防把纯 Python 垫片计入 |

两道硬断言：

1. **台账**：`loaded + env_limited + need_numpy == len(EXTS)`——任何"消失的扩展"不许溜过；
2. **矛盾检查**：`HAVE_NUMPY` 为真却仍有模块报缺 numpy → raise（探测与包口径打架不放行）。

## 禁止做法

- ❌ `ALIGN_EXTS` / `PLAIN_EXTS` 之类的名单分组（开放集合作封闭假设，漏一个烧一轮 CI）；
- ❌ 分类器放行不明异常（真失败被吞）；
- ❌ 三类计数不对账（扩展"消失"不可见）。

## 关联

- E212 知识：平台机理与替代证据口径；本条是消费测试**分类器**的写法，把 E212 / 缺依赖 / 真失败三类分开；
- `DRAFT-E733-numpy-testdata-sandbox-pip`：numpy 供给问题，与本条分类正交。
