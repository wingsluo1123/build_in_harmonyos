# update_checker

- **上游**：https://github.com/bboe/update_checker
- **版本**：1.0.1
- **形态**：纯 Python（noarch）——PyPI/GitHub 版本更新检测；**零运行期依赖**（`dependencies = []`）
- **布局**：**src 布局**（`src/update_checker/`，含 `py.typed`）

## 归档内容

```
update_checker/
  1.0.1/
    conandata.yml          源（官方 sdist + sha256）与测试资产（tag v1.0.1 仓库归档 + sha256）
    conanfile.py           配方（source → build(测试期依赖 + 上游套件) → package(src/update_checker)）
    manifest.yaml          版本级 manifest（含被测源码口径的如实披露）
    notes.md               适配要点（test_requires 上下文、包路径截断名、sdist 时间戳等 5 条）
    test_package/          消费者校验（9 项，全部离线）
```

## 上游测试

**官方 sdist 不含测试**（只打 `src/update_checker`）→ 配方在 `conandata.yml` 的 `test_assets`
里钉死上游仓库 tag **v1.0.1** 归档作为测试来源（sha256 固定，仅测试用、不进产物）。
测试用 mock 替换网络，纯离线可跑：**43 passed**。

测试期依赖：`aiohttp`（**仓库已有归档** `archives/a/aiohttp/3.14.3` → `self.test_requires`；
上游测试 `import aiohttp`）+ `pytest`、`pytest-asyncio`（仓库无归档 → pip 装到
`<build>/test-deps`，不进产物）。

> ⚠️ **被测源码口径（已披露）**：官方 sdist 的成员时间戳被归一化到 epoch（`mtime = 0`），
> 上游 `test_import__without_package_metadata` 用 `zipfile.write()` 按源文件 mtime 造 zip →
> `ValueError: ZIP does not support timestamps before 1980`。故本配方把**仓库归档（同 tag、同源码）**
> 的 `src/` 置于 PYTHONPATH 最前：sdist 源码 42 passed / 1 failed，仓库归档源码 **43 passed**；
> **包产物仍由 sdist 源码树打包**。

## 消费者校验

`test_package/check_update_checker.py` **9 项，全部离线、不触网**：产物齐备 / 模块文件齐备
（含 `py.typed`）/ 真实 `import update_checker` / 公开符号面（`__all__` 12 个导出）/
真实 API `parse_version()`（两例）/ 真实 API `pretty_date()`（两例）/
真实 API `standard_release()` + `UpdateChecker()` 构造 / `__version__`（上游兜底 `'unknown'`，如实报告）/
证据。实测 `checks=9 fails=0` / `RESULT: PASS`。
（其联网能力 `query_pypi`/`update_check` 需真实外网与缓存目录，消费者校验只覆盖离线可实证部分。）
