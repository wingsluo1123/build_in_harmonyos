# E14723 — 纯 Python 依赖未声明 `run=True`，被 conan 标 BINARY_SKIP

## 错误特征

两种表现，一静一动：

1. **构建期（静默）** —— `conan create` / `conan install` 图日志出现：

   ```
   Skipped binaries
       pyserial/3.5, six/1.17.0
   ```
   或 `BINARY_SKIP` 标记。节点没有 `package_folder`，`conanrun.sh` 里也没有它的 `PYTHONPATH`。

2. **运行期（显性）** —— 消费者 `source conanrun.sh` 后：

   ```
   ModuleNotFoundError: No module named 'serial'
   ModuleNotFoundError: No module named 'six'
   ```

## 触发条件

- 构建系统: Conan 2（任意，与 C/C++ 无关）
- 阶段: packaging（`requirements()` 声明期埋雷，testing/runtime 才暴露）
- 前提: 依赖包的 `package_type` 是 `python-require`（纯 Python 库/应用），
  且本包**没有**在 `self.requires()` 上显式写 `run=True`

## 根因分析

Conan 2 的 `process_package_type()` 对 `python-require` 依赖把 `run` 默认置为 `False`。
`run=False` → `Requirement.files` 为 `False` → `graph_binaries._skip_binaries()`
把该节点标 `BINARY_SKIP` → 节点**不落 `package_folder`**、不进 runenv。

后果是双重的：消费者拿不到 `PYTHONPATH`，而本包若 `package_type = "application"`
（`headers/libs` 下游强制为 `False`），`run` 就成了唯一能把依赖留在图里的 trait。

理论依据见 `knowledge/operations/ohos-adaptation-patterns.md`（Conan 2 纯 Python 打包）。
仓库内同族正例（即本适配自身）：`archives/t/tinyprog/1.0.23/conanfile.py` 的
`requirements()` 对 `pyserial`/`six` 均带 `run=True`，并由
`test_package/test_tinyprog.py::test_05_dependency_wiring` 断言二者来自 conan
依赖节点（`__file__` 不在包内）——即本条的机械化回归。

## 解决方案

### 推荐方案

对每个纯 Python 运行时依赖显式加 `run=True`：

```python
self.requires("pyserial/3.5", run=True)
self.requires("six/1.17.0", run=True)
```

验证（图日志里 `Skipped binaries` 段应消失）：

```bash
conan create <recipe> -pr:h=ci/conan/profiles/ohos-aarch64 \
                      -pr:b=ci/conan/profiles/ohos-aarch64 2>&1 | grep -E "Skipped|BINARY_SKIP"
```

### 回退方案

不改依赖配方时，可在本包 `package_info()` 里把依赖的 site-packages
显式 `append_path` 进 `runenv_info` / `buildenv_info` 的 `PYTHONPATH`。
治标不治本（依赖节点仍被 Skip，`conan install --requires` 的外部消费者仍会踩），
仅在无法改动依赖侧时使用。

### 禁止做法

- ❌ 只写裸 `self.requires("pyserial/3.5")` —— 默认 `run=False`，BINARY_SKIP 静默发生，
  直到 CI 的 L1/`test_package` 或用户运行期才炸，浪费整轮 CI。
- ❌ 在 `package_info()` 里只 `print` PYTHONPATH 而不 `append_path` —— 打印不会改变消费者环境。

## 验证

`tinyprog` 1.0.23 实测（HarmonyOS PC / aarch64 / Python 3.12）：

```bash
# ① 构建期：Skipped binaries 段应为空
conan create archives/t/tinyprog/1.0.23 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd --build=missing

# ② 运行期：消费者视角（test_package 已内建同名断言）
conan test archives/t/tinyprog/1.0.23/test_package tinyprog/1.0.23 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
```

`test_package/test_tinyprog.py` 的 `test_05_dependency_wiring` 对
`serial` / `six` 从 conan 依赖包解析（而非 pip 平铺副本）做断言，
即本条的机械化回归。

## 关联条目

- 相似: E14724（纯 Python 依赖 site-packages 布局不统一：`lib/pythonX.Y/site-packages`
  与 `lib/python/site-packages` 并存，探测时不能只认一种）
- 参考: `archives/t/tinyprog/1.0.23/conanfile.py` 的 `requirements()` 与
  `test_package/test_tinyprog.py::test_05_dependency_wiring`（本条机械化回归）
