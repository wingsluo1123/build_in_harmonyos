# E600 — 纯 Python Conan 包的传递依赖漏标 `run=True`：被 Conan 判为 "Skipped binaries"，消费端 import 崩

> 草稿态（`knowledge/drafts/E600-draft-A14E.kv`），未进正式索引；正式 E 编号待 `graph promote` 分配。
> 来源适配：`archives/s/synadm/0.49.2`（本仓库首个在配方里直接 `requires("requests/...")` 的 Python 包）。
> 同机制的既有未晋升草稿：`DRAFT-pytest-9.1.1-application-dep-skip`（application 包传递依赖被
> skip、runenv 不进消费者环境）。**本条的增量**是把结论推广到纯 Python 包：必须声明**整个导入闭包**
> 为 `run=True`，并在 `package_info()` 里遍历可见 host 依赖、兼容 flat 与
> `lib/pythonX.Y/site-packages` 两种布局后逆序 prepend `PYTHONPATH`。晋升时请与上述草稿合并去重。

## 错误特征

`conan create` 构建本身成功，**test_package 阶段**（消费者视角）整片红：

```
ModuleNotFoundError: No module named 'chardet'
  .../requests/__init__.py:21
```

`conan install` 日志里能看到一行被忽略的关键信息：

```
Skipped binaries
    certifi/2026.7.22, chardet/5.2.0, idna/3.18, urllib3/2.7.0
```

件**都在**制品仓、**都能**下载，但下游包看不到它们 → 极易误判为"依赖没发布"，进而错误地
`--status dependency_missing` 止损，或者去 vendor 本来不需要 vendor 的东西。

## 触发条件

- 构建系统：Conan 2（配方，非源码）
- 阶段：`package_info()` / 运行期 import
- 条件：被适配包是**纯 Python**，需要把依赖的 `site-packages` 组装进 `PYTHONPATH`；
  而某个 registry 依赖把自己的运行时依赖写成了不带 `run=True` 的 `self.requires(...)`
  （本项目实测：`requests/2.22.0` 对 certifi / chardet / idna / urllib3 就是这样写的）

## 根因分析

Conan 2 的依赖视图是**按 context 过滤**的：

```python
# conans/model/dependencies.py（语义）
ConanFileDependencies.host  →  requires 中 {"build": False, "test": False, "skip": False}
```

`self.requires("chardet/5.2.0")` 没有 `run=True`，在下游 host 上下文里 `skip=True`，
于是**从 `self.dependencies`（默认 host）里彻底消失**。`package_info()` 遍历依赖图拼
PYTHONPATH 时自然拿不到它 → 包产物里没有 chardet 的路径 → 消费端 `import requests` 崩。

次生坑（同一处代码必须一起处理）：

1. **布局不统一**：registry 里 Python 件的产物既有 `lib/python3.12/site-packages/<pkg>/`，
   也有顶层平铺 `<pkg>/`。硬编码任一种都会随机漏路径。
2. **发布不完整**：`requests/2.22.0`、`tabulate/0.10.0`、`certifi` 等现有配方几乎不发布
   `PYTHONPATH`（只有 `click`、`pyyaml` 发布了）。所以**下游必须自己遍历依赖拼路径**，
   不能指望上游件替你设好环境变量。

## 解决方案

### 推荐方案：`declare-import-closure-run-true-and-walk-host-deps`

第一步，把**完整导入闭包**逐项声明为直接依赖并 `run=True`（包括被 skip 的传递依赖）：

```python
def requirements(self):
    self.requires("click/8.4.2", run=True)
    self.requires("requests/2.22.0", run=True)
    self.requires("tabulate/0.10.0", run=True)
    self.requires("pyyaml/6.0.2", run=True)
    # requests 自身的导入闭包 —— 不声明就会被 prune 成 "Skipped binaries"
    self.requires("certifi/2026.7.22", run=True)
    self.requires("chardet/5.2.0", run=True)
    self.requires("idna/3.18", run=True)
    self.requires("urllib3/2.7.0", run=True)
```

第二步，`package_info()` 遍历可见 host 闭包，用**探测函数**适配两种布局，无导入根时返回
`None`（而不是注入垃圾路径）：

```python
@staticmethod
def _find_site_packages(package_folder):
    if not os.path.isdir(package_folder):
        return None
    if os.path.isdir(os.path.join(package_folder, "lib")):
        for dirpath, dirnames, _files in os.walk(package_folder):
            if "site-packages" in dirnames:
                return os.path.join(dirpath, "site-packages")
    entries = os.listdir(package_folder)
    has_module = (any(n.endswith(".py") for n in entries)
                  or any(os.path.isfile(os.path.join(package_folder, n, "__init__.py"))
                         for n in entries if os.path.isdir(os.path.join(package_folder, n))))
    return package_folder if has_module else None

def package_info(self):
    dep_sites = []
    for dep in self.dependencies.host.values():          # ← 必须 .host，不能用默认视图凑合
        folder = dep.package_folder
        if not folder or os.path.realpath(folder) == os.path.realpath(self.package_folder):
            continue                                     # 防自环（tested_reference_str 场景）
        site = self._find_site_packages(folder)
        if site:
            dep_sites.append((str(dep.ref.name), site))
    for env in (self.buildenv_info, self.runenv_info):
        for _name, site in reversed(dep_sites):
            env.prepend_path("PYTHONPATH", site)         # 逆序 → 声明顺序即优先级
        env.prepend_path("PYTHONPATH", self._site_dir())
        env.prepend_path("PATH", self._bin_dir())
```

诊断打点（值得留一行日志，下次同类问题一眼定位）：

```
synadm/0.49.2: published 8 dependency import path(s): click, requests, tabulate, pyyaml, certifi, chardet, idna, urllib3
```

### 禁止做法

- ❌ 用 `self.dependencies`（默认 host 视图）却期望拿到 `test_requires` / 未标 run 的传递依赖
  ——test 上下文另说（见 E429），skip 件同样拿不到。
- ❌ 用"库名子串"匹配 conan 包路径判断依赖是否存在：包目录是**截断名**
  （`.conan2/p/charda66bc07a7df17/p/…`），按路径匹配会假阴性。判**模块目录**是否存在。
- ❌ 凭推断认定"registry 没这个件"：必须 `conan download <ref> -r=ohpcd --only-recipe` 实证
  （R35：`conan list/search` 对 cnb.cool 不完整）。
- ❌ 为绕过可见性问题去 dummy 包顶替 / 伪造 `.ci-result.json` / 跳过 W3（R41、W3 硬规则）。

## 验证

```bash
# 1) 复现可见性缺失（修复前）
grep -A5 "Skipped binaries" ~/create.log

# 2) 修复后：消费端逐个锁定依赖来源（本项目 test_package/test_synadm.py 内已固化）
python3 - <<'PY'
import importlib, json, os
expect = {"click":"click","requests":"requests","tabulate":"tabulate","yaml":"pyyaml",
          "certifi":"certifi","chardet":"chardet","idna":"idna","urllib3":"urllib3"}
for mod, pkg in expect.items():
    f = importlib.import_module(mod).__file__
    assert pkg in f.replace("-", "_"), (mod, f)
    assert ".conan2" in f or "b/synad" not in f, f
print("all 8 deps resolved from their own package folders")
PY

# 3) 端到端：conan create 必须 rc=0 且 test_package 全绿
conan create archives/s/synadm/0.49.2 -pr=$OHC_PROJECT_DIR/ci/conan/profiles/ohos-aarch64 --build=missing
```

## 关联条目

- 相关：E429（Conan 2 `test_requires` 落在 test 上下文，遍历 host/build 取不到 —— 同一族"依赖上下文可见性"坑）
- 相关：E143（OHOS 上 Python 脚本的 shebang/解释器与库加载问题）
- 后续：E601（`.dist-info` 目录名 PEP-427 归一化；vendored 件携带测试工具写只读 `/tmp`）
