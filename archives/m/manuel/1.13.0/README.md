# manuel 1.13.0

Manuel 是 Apache-2.0 纯 Python 文档测试库。本候选固定 PyPI sdist
`5d63120de8fa6d927780b69ae28aa3e9d1669b10af3d32785f3fba11a5be885a`，
保留原测试和文档输入；补丁仅修改 `src/manuel/__init__.py` 的两个相关边界位置。

`Document.find_regions()` 按字符匹配起止标记，`claim_region()` 按整行划分。
结束正则仅匹配 `END block` 的 `END` 前缀时，原行尾扫描不执行，
登记该区域后会静默丢失 ` block`。修复扫描上界，并保留已经吃掉换行的
结束正则边界，避免继续吞入下一行。完整文本重组一致性和未变原 suite 验证这两种情况。

目标配方使用已固定的 OHOS Python 3.12.9；setuptools 84.0.0 从固定纯 wheel
用于构建并随包保留声明的运行依赖。zope.testing 6.2 仅用于原测试，不引入其 extras，
不随最终运行包安装。各输入 URL/SHA256 在 `conandata.yml`。

在目标 Conan 原生环境运行：

```sh
conan create archives/m/manuel/1.13.0 --build=manuel/*
```

实际 host/build profile 和制品源由唯一 H1 采用当前已验证配置；这里不假定 profile 名称。
可用 `MANUEL_SOURCE_ARCHIVE` 和 `MANUEL_WHEEL_INPUT` 指向同摘要原件进行离线源读取。
配方中先执行完整 `python -m unittest manuel.tests.test_suite`、6个新增回归，
再构建 wheel；`test_package` 实际从新 Conan 包导入并执行1个完整消费者。


## H1-002 actual target result (2026-10-14)

OHOS6.0 armv8 / Clang15 libc++ cppstd17 Release / published Python3.12.9.
Conan2.29.1 create/build/package/test_package and original suite passed: 63/63
unittest groups, 273/273 original doctest examples, 6/6 added boundary regressions,
and one delivered-package extraction/claim/reassembly consumer with 5 assertions.
The actual consumer imports Manuel from the new Conan package. Package core SHA256
remains dc3ae247600365d4f3a1a5444a5d9697feb9f78670bdd94271153c7c38fb9ca3.
Original corpus, tests and doc1/2/3.ex are byte-identical in that package.

Actual local package: `manuel/1.13.0#34a5a794c5652c2f1f91305ae7246710:da39a3ee5e6b4b0d3255bfef95601890afd80709#fe7c7c66491dc64079a3c9046deaf2cc`. No manual upload/publication is claimed.
W3 G0 knowledge integrity, KC, JC, L0/L1/L4/L5 passed (JC_ERRORS=0); L2 skipped
because this pure Python package has no bin directory. This W3 G0 differs from the
legacy H1-001 clean-build ./configure check, whose rc127 and finish rc1 remain FAIL.
H1-001 patch export and CLI metadata failures also remain in their original record.
The three official W3 source pre-download warnings remain; the recipe used the
fixed hash-checked source and pure wheels supplied by the original H1.

This publication preparation changes only result documentation/manifest metadata.
Recipe, conandata, patch, observer, regressions, test_package and original corpus
are unchanged from tested002. No software or W3 rerun. Independent W4, actual
AtomCode full-range review, Issue/PR association, official PR CI and effective
submission remain pending; local W3 success does not establish those states.
