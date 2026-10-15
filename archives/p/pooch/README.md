# pooch

- **上游**：https://github.com/fatiando/pooch
- **版本**：1.9.0
- **形态**：纯 Python（noarch）数据下载/缓存/校验工具库
- **运行期依赖**：`platformdirs (>=2.5.0)`、`packaging (>=20.0)`、`requests (>=2.19.0)`
  —— **三者在仓库中均已有归档**（4.3.8 / 26.3 / 2.22.0）→ 直接 `requires`

## 归档内容

```
1.9.0/
  conandata.yml            源（官方 sdist + sha256，钉死）
  conanfile.py             配方（source → build(测试期依赖 + 上游离线子集) → package）
  manifest.yaml            版本级 manifest（dependencies / upstream_tests / knowledge_gained）
  notes.md                 适配要点与依赖判定
  test_package/            消费者校验（7 项，全部离线）
```

## 上游测试

测试位于**包内** `pooch/tests/`（9 个 `.py`；**sdist 无顶层 `tests/`**）。
上游以 `@pytest.mark.network` 标记需真实外网的用例（源码内实测 38 处）
→ 按**上游自己的标记**取离线子集：`-m 'not network'`，实测
**62 passed / 13 skipped / 85 deselected**；未被标记者的失败仍会让 build 硬失败。

## 消费者校验

`test_package/check_pooch.py` **7 项，全部离线、不触网**：
产物齐备 / 关键文件 / 真实 `import pooch` / `__version__ == 1.9.0` /
真实离线 API `pooch.file_hash()` 算出正确 sha256 / 真实离线 API `pooch.create()` 构造 Pooch 且保留 registry / 证据。
