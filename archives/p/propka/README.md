# propka

- **上游**：https://github.com/jensengroup/propka （官网 http://propka.org）
- **版本**：3.5.1
- **形态**：纯 Python（noarch）——蛋白质 pKa 经验预测（PROPKA）；顶层 `propka/` 包（24 个模块）
- **许可证**：LGPL-2.1-or-later（上游 `setup.py` 写 `license="LGPL v2.1"`，`LICENSE` 为 LGPL 2.1 全文）
- **依赖**：**零运行期依赖**（`install_requires` 为空；包内模块不 `import numpy`）

## 归档内容

```
propka/
  3.5.1/
    conandata.yml          源（官方 sdist + sha256）与测试数据来源（上游仓库 tag v3.5.1 + sha256）
    conanfile.py           配方（source → build(测试期 pytest+numpy + 上游套件) → package(propka/))
    manifest.yaml          版本级 manifest（dependencies / upstream_tests / knowledge_gained）
    notes.md               适配要点（sdist 缺测试数据的判定与处置、依赖实证判定等 5 条）
    test_package/          消费者校验（7 项，全部离线）
```

## 上游测试

sdist 自带 `tests/*.py`（11 个 `test_*.py`），但**不带测试数据**：`tests/pdb`（PDB 输入）与
`tests/results`（期望结果）未随 sdist 发布，缺了测试会直接
`FileNotFoundError: Can't find pdbs test files …`。
故配方在 `conandata.yml` 的 `test_assets` 里钉死**上游仓库 tag `v3.5.1` 归档**（sha256 固定，
含 12 个 PDB + 7 个期望结果，**仅测试用、不进产物**）；**包产物本身仍由 sdist 源码树打包**。
测试期依赖：`pytest` + `numpy`（上游 `tests_require` 声明；仓内无归档 → pip 装到
`<build>/test-deps`，**不进产物**）。

实测：**49 passed**。

## 消费者校验

`test_package/check_propka.py` **7 项，全部离线**：产物齐备 / 关键文件齐备（8 个实测模块名，
含 `hybrid36.py`，**无 `protein.py`**）/ 真实 `import propka` / `__version__ == '3.5.1'` /
**真实离线功能 `hybrid36.decode('A0000') == 100000`** / 子模块面（`molecular_container`、
`atom`、`group`、`run`、`hybrid36` 可导入）/ 证据。实测 `checks=7 fails=0` / `RESULT: PASS`。
