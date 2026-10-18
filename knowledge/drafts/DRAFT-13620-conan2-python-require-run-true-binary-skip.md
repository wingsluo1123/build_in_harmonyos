# DRAFT-13620-conan2-python-require-run-true-binary-skip: Conan 2 python-require 依赖被 BINARY_SKIP，requires 必须显式 run=True

## 现象

lddtreepax 配方 `conan create` 两次失败：交付脚本运行时 `ModuleNotFoundError: No module named 'elftools'`。
`conan graph info` 显示 pyelftools/0.33 节点 `Binary: Skipped`，package_folder=None。

## 根因

Conan 2.29 对依赖做 skip 判定（_skip_binaries）时看 files=(headers|libs|run|build)。
pyelftools 是 python-require 包：无 C 头、无 .so/.a，requires 未显式声明 `run=True` 时四个标记全空 →
判 BINARY_SKIP → package_folder=None → 其 runenv（PYTHONPATH=…/site-packages）不聚合到下游 conanrunenv.sh。

## 修复

```python
def requirements(self):
    # run=True: python-require 包无 C 头/库，Conan 2.29 _skip_binaries 会将其 BINARY_SKIP
    # （package_folder=None、runenv 不聚合），显式 run=True 修复
    self.requires("pyelftools/0.33", run=True)
```

修复后 conanrunenv.sh 正确包含 PYTHONPATH，下游 `import elftools` 成功，conan create RC=0。

## 诊断速查

1. `conan graph info <ref>`：看依赖节点 Binary 是否 Skipped、package_folder 是否 None
2. `conan install --requires=<ref> -of dir`：检查 dir/conanrunenv.sh 是否含期望的 PYTHONPATH
3. 命中即给 requires 加 `run=True`（build 期才用的加 `build=True`）

## 关联

- 任务 1783828906105（lddtreepax 1.3.9，2026-10-14），日志 _analysis/lddtreepax-1.3.9/19,20,21-*.log
