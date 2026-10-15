# propka 3.5.1 适配笔记

## 结论速览
- **类型**：纯 Python（noarch），顶层 `propka/` 包，24 个模块；**零运行期依赖**
- **上游测试**：sdist 自带 `tests/*.py`（11 个），但**不带测试数据** → 由上游仓库 tag `v3.5.1` 归档补齐（12 PDB + 7 期望结果）；实测 **49 passed**
- **测试期依赖**：`pytest` + `numpy`（pip 到 `<build>/test-deps`，**不进产物**）
- **状态**：built（本地 conan create 全绿：上游 49 passed + 消费者 7/7）

## 打包步骤
```bash
conan create archives/p/propka/3.5.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1) 先验证"测试能不能跑"（按规矩：跑不了就放弃该库）
```bash
# 只看 sdist：tests/*.py 齐全，但数据目录缺失 → 会直接 FileNotFoundError
ls <sdist>/tests/                    # 只有 *.py，没有 pdb/ 与 results/
PYTHONPATH=<sdist> python3 -m pytest tests -q
#   FileNotFoundError: Can't find pdbs test files ...
# 取上游仓库同 tag 归档补齐数据后再跑：
PYTHONPATH=<sdist>:<repo-tag-v3.5.1>:<test-deps> python3 -m pytest <repo>/tests -q
#   → 49 passed
```

### 2) 依赖判定（**实证而非直觉**）
propka 是科学计算类库，直觉上"肯定依赖 numpy"——但实测：
```bash
grep -rl 'import numpy' <sdist>/propka/     # 空 → 包内模块不 import numpy
grep -n install_requires <sdist>/setup.py   # 空；只有 tests_require=["numpy","pytest"]
```
Debian 的 `debian/control` 亦把 `python3-numpy` 标为 `<!nocheck>`（= 只在跑测试时才需要），
与实测一致 → 故**不声明任何 Conan requires**，numpy 只算测试期依赖。

### 3) 测试数据的口径（**必须披露的差异**）
| 来源 | 内容 |
|---|---|
| sdist `propka-3.5.1.tar.gz` | `propka/` 源码（**包产物就打它**）+ `tests/*.py` |
| 仓库归档 tag `v3.5.1`（`conandata.test_assets`，钉 sha256） | `tests/pdb`（12 个 PDB 输入）+ `tests/results`（7 个期望结果）——**仅测试用、不进产物** |

## 实测结果（本地 conan create）
```
测试期依赖已安装（https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple）：<build>/test-deps
[upstream tests] 测试资产 = <build>/upstream-tests（pdb 12 个 / results 7 个，补齐 sdist 未带的测试数据）
[upstream tests] pytest rc=0
[upstream tests] 49 passed in 6.64s
[ok]   产物齐备 / 关键文件齐备（8 个）/ import 成功 / __version__ == '3.5.1'
[ok]   真实离线功能：hybrid36.decode('A0000') == 100000
[ok]   子模块面齐备：propka.molecular_container / .atom / .group / .run / .hybrid36
checks=7 fails=0
RESULT: PASS
```

## 踩坑记录
1. **sdist 缺测试数据**：报错 `FileNotFoundError: Can't find pdbs test files`，看着像"测试坏了"，
   实为打包缺数据（`pdb/`、`results/` 未随 sdist 发布）→ 用同 tag 仓库归档补齐并披露。
2. **别按库类别猜运行期依赖**：propka 不 import numpy；判定靠 `grep -rl 'import numpy'` 与
   Debian 的 `<!nocheck>` 标注，不靠"科学库=要 numpy"的印象。
3. **模块名要按实测写**：propka 3.5.1 **没有** `protein.py`（有 `molecular_container.py`/`atom.py`/
   `group.py` 等），消费者校验的关键文件清单必须照实测列。
4. **pip 源平台私有源优先 + 同源重试 1 次**：numpy 是原生扩展，manylinux 轮子在 OHOS(musl) 上
   加载不了（pooch 的 CI #89930 已实测）；网络抖动（ReadTimeout）不该让 build 挂。
5. `/tmp` 只读 → `TMPDIR=/data/storage/el2/base/cache`。
