# draft-13649-upstream-pytest-runner-degradation

## 问题

配方 `build()` 里跑上游 pytest 套件（R51"应测尽测"），开发机通过；到 CI worker 上整包失败：

```
pox/0.3.7: RUN: "/data/service/hnp/bin/python3" -m pytest pox/tests -q
/data/service/hnp/bin/python3: No module named pytest
ERROR: pox/0.3.7: Error in build() method ... ConanException: Error 1 while executing
```

CI worker 的系统 python3（`/data/service/hnp/bin/python3`）是精简构建，不带 pytest。
开发机带 pytest，所以本地验证永远发现不了——**这类"只在 CI 缺测试驱动器"的失败无法用
开发机复现**，必须在配方里做环境自适应。

## 修复：三级降级（保住"真实执行"）

```python
# ① 真实探测（不要用 self.run() 的返回值判断——conan2 的 self.run 不返回退出码，
#    ignore_errors=True 下永远返回 None；必须用 subprocess.run 拿 returncode）
probe = subprocess.run([python3, "-c", "import pytest"], ...)
has_pytest = probe.returncode == 0

# ② 构建本地安装：--target 落在 build 目录，绝不污染 worker 的 site-packages
self.run('"%s" -m pip install --retries 3 --timeout 60 '
         '--index-url https://pypi.tuna.tsinghua.edu.cn/simple '
         '--target "%s" pytest' % (python3, pytest_libs), ignore_errors=True)
has_pytest = os.path.isdir(pytest_libs/pytest) and os.path.isdir(pytest_libs/_pytest)
# 成功 → env.prepend_path("PYTHONPATH", pytest_libs) 后照常跑 pytest

# ③ stdlib 等价 runner：仅当上游测试"纯 assert、零 pytest 特性"时合法
#    （必须先逐行核实：无 import pytest、无 fixture、无 parametrize、无 capsys 等）
for modname, funcname in (("pox.tests.test_utils", "test_utils"),
                          ("pox.tests.test_shutils", "test_shutils")):
    getattr(importlib.import_module(modname), funcname)()
# AssertionError 自然传播、非零退出 —— 与 pytest 驱动语义一致
```

前提核实（这是 ③ 合法的唯一理由）：pox 上游两个测试模块是**纯 assert 函数**，
`grep import pytest` 为空、无 fixture/parametrize，且 `pox/tests/` 带 `__init__.py`
（可按包导入）。若上游用了 pytest 特性，③ 不成立，只能止步于 ②。

## 实测

- 开发机（有 pytest）：tier-1 生效，`conan create` 全流程 rc=0，`POX-CONSUMER-OK`
- tier-3 单测：在打好两个平台补丁的源码树上输出 `UPSTREAM-TESTS-OK`（2/2 断言函数通过）
- CI（无 pytest）：将走 tier-2（worker 已证明能从清华镜像下载文件，index 同域可达）；
  镜像也挂时 tier-3 兜底，测试仍真实执行

## 判据小结

| 现象 | 处置 |
|---|---|
| 本地通过、CI 报 `No module named pytest`（或其他测试驱动缺失） | 环境差异，不要删测试；按三级降级改造 |
| 用 `self.run(..., ignore_errors=True)` 的返回值判断成功 | **错误**——conan2 不返回退出码，用 `subprocess.run` |
| 想给 worker 全局装 pytest | 禁止；用 `pip install --target`（构建本地）+ PYTHONPATH 前插 |
| 上游测试用了 pytest 特性 | stdlib runner 不成立，止步于 tier-2，或改用 MANIFEST 豁免声明 |
| 顺带 | CI pre-download 的 `No such file or directory: 'curl'` 是 worker 缺 curl，
  与包无关；`修复建议`里出现 429 hint 不一定是真 429（关键词误匹配），要看实际下载行 |
