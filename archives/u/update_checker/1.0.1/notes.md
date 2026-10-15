# update_checker 1.0.1 适配笔记

## 结论速览
- **类型**：纯 Python（noarch），**src 布局**（`src/update_checker/`）；**零运行期依赖**（`dependencies = []`）
- **上游测试**：sdist **不含测试** → 取上游仓库 tag `v1.0.1` 归档的 `tests/`；实测 **43 passed**（mock 网络、纯离线）
- **测试期依赖**：`aiohttp`（**仓库已有归档** `archives/a/aiohttp/3.14.3` → `test_requires`）+ `pytest`/`pytest-asyncio`（pip → `<build>/test-deps`）
- **状态**：built（本地 conan create 全绿：上游 43 passed + 消费者 9/9）

## 打包步骤
```bash
conan create archives/u/update_checker/1.0.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1) 先验证"测试能不能跑"（跑不了就放弃该库）
sdist 里**没有测试**，测试只在上游仓库：
```bash
python3 -c "import tarfile;print([n for n in tarfile.open('<sdist>').getnames() if 'test' in n.lower()])"   # → []
# 取仓库归档 tests/ 后（需 aiohttp + pytest + pytest-asyncio）：
PYTHONPATH=<repo-src>:<repo-root>:<test-deps>:<aiohttp 等依赖 site-packages> \
  TMPDIR=/data/storage/el2/base/cache python3 -m pytest tests/ -q
# → 43 passed
```

### 2) 依赖
- **运行期：零依赖**（`dependencies = []`；`async = ["aiohttp"]` 只是可选 extra）→ 不声明任何 `requires`
- **测试期**：
  - `aiohttp` → **`self.test_requires("aiohttp/3.14.3")`**（仓库已有归档；上游测试 `import aiohttp`）
  - `pytest`、`pytest-asyncio` → pip 装到 `<build>/test-deps`（**不进产物**；不能依赖宿主自带）

### 3) 被测源码的口径（**必须如实披露的差异**）
官方 sdist 的成员时间戳被归一化到 **epoch（`mtime = 0`，SOURCE_DATE_EPOCH 那套）**，而上游
`tests/test_update_checker.py::test_import__without_package_metadata` 用 `zipfile.write()`
按**源文件 mtime** 造 zip：

```
ValueError: ZIP does not support timestamps before 1980
```

该用例在 git 检出（mtime 正常）下是通过的。实测两种口径：

| 被测源码 | 结果 |
|---|---|
| sdist 抽出的 `src/`（mtime = 1970） | 42 passed / **1 failed**（即上述 zip 时间戳用例） |
| 仓库归档 tag v1.0.1 的 `src/`（同版本同源码，mtime 正常） | **43 passed** |

本配方取后者：把仓库归档的 `src/` 置于 `PYTHONPATH` 最前（sdist 的 `src/` 仍列在其后作兜底）。
**包产物本身仍由 sdist 源码树打包**，差异已在 manifest.yaml / MANIFEST.yml / PR 正文写明。
> 处置原则：不修改上游测试、不伪造文件时间戳；改为按上游"从 git 检出跑测试"的语义取同 tag 源码，
> 并把口径差异讲清楚。

## 实测结果（本地 conan create）
```
[upstream tests] 被测源码 = 仓库归档 .../upstream-tests/src（tag v1.0.1，与 sdist 同版本；因 sdist 把 mtime 归一化到 1970，上游 zip 用例会误失败）
[upstream tests] pytest rc=0
[upstream tests] 43 passed in 1.51s
[ok]   产物齐备：update_checker 模块位于 lib/python3.12/site-packages/update_checker
[ok]   模块文件齐备：__init__.py / core.py / py.typed（含 PEP 561 的 py.typed）
[ok]   import update_checker 成功（零运行期依赖）
[ok]   公开符号面齐备：__all__ 的 12 个导出全部可访问
[ok]   真实离线 API：parse_version() 归一化正确（'1.2.3' 与 '1.0.0b1' 两例）
[ok]   真实离线 API：pretty_date() 正确（now-2d → '2 days ago'，now-1h → '1 hour ago'）
[ok]   真实离线 API：standard_release('1.0.0') is True；UpdateChecker(bypass_cache=True) 构造成功
[ok]   __version__ == 'unknown'：上游 core.py 的兜底值（其版本由构建期 metadata 注入，本适配只装模块不建 dist-info）——如实报告，不臆造
[ok]   证据：update_checker 模块总字节 …；python 3.12.9
checks=9 fails=0
RESULT: PASS
```

## 踩坑记录（都可复用）
1. **`test_requires` 在 `test` 上下文**：遍历依赖图收集 site-packages 时，`self.dependencies`（默认 host）
   与 `.build` **都拿不到** test_requires，必须加 `self.dependencies.test`
   （实测：aiohttp 作 test_requires 时，只遍历 host+build 得到空集合）。
2. **别用"库名子串"匹配 conan 包路径**：包目录名是**截断名**（`.conan2/p/aioht9f1a043272ee1/p/…`
   里并没有 `aiohttp` 子串）→ 我第一版守卫就这样假阴性、把好好的依赖判成"没找到"。
   正确做法：检查**模块目录**是否存在（`os.path.isdir(os.path.join(site, "aiohttp"))`）。
3. **src 布局**：包在 `src/update_checker/` → `package()` 从 `src/update_checker` 拷，
   测试期 `PYTHONPATH` 要带 `<source>/src`。
4. **sdist 时间戳归一化会打到上游"按 mtime 造 zip"的用例**（见上）；判定方法是看 tar 成员 `mtime`
   是否为 0。
5. `/tmp` 只读 → `TMPDIR=/data/storage/el2/base/cache`。
