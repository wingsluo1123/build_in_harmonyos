# DRAFT-9511：上游 Python 测试套件与新版 Pillow 的 rational 类型兼容——归一化 IFDRational 而非弱化断言

> Contributor: kasumizawa-miyuu（9C4A） | Status: Draft | Updated: 2026-10-16
> Source: 任务 9511 piexif 1.1.3 适配（分支 feat/piexif-1.1.3，PR 编号创建后回填）

## 背景

piexif 1.1.3（纯 Python EXIF 库，python-require 适配）的上游 unittest 套件
`tests/s_test.py`（55 例）用 `PIL.Image._getexif()` 交叉校验 piexif 的解析结果。
上游 `requirements.txt` 钉 `Pillow==4.2.1`（2020 年），而 OHOS 制品仓可用的 Pillow
为 10.4.0（`python-require` 包 `pillow/10.4.0`，cp312-linux-ohos）。两个版本的
`_getexif()` 对 EXIF rational 值的返回类型不同：

- Pillow 4.2.1：`(numerator, denominator)` 元组（如 `(180, 1)`）；
- Pillow ≥ 6： `IFDRational` 对象（数值等价 Fraction，打印为 `180.0`）。

## 症状（可复现）

`PYTHONPATH=<pillow>/lib/python3.12/site-packages:<src> python3 tests/s_test.py`：

```
ERROR: test_load_m (__main__.ExifTests.test_load_m)
  File "tests/s_test.py", line 585, in _compare_value
    self.assertEqual(pack_byte(*v1), v2)
struct.error: 'B' format requires 0 <= number <= 255

FAIL: test_load (__main__.ExifTests.test_load)
AssertionError: b'\xb4\x01' != 180.0

FAILED (failures=1, errors=2)   # 55 例中 3 例
```

其余用例全过——说明 piexif 库本身解析正确，失败集中在"与 PIL 的交叉校验"路径。

## 根因

`_compare_value` 按 Python 类型分支处理：

```python
def _compare_value(self, v1, v2):
    if type(v1) != type(v2):
        if isinstance(v1, tuple):
            self.assertEqual(pack_byte(*v1), v2)   # ← BYTE 数组语义（0..255）
        ...
```

`pack_byte` 分支本为 BYTE 数组（如 GPSVersionID `(0,0,0,1)` vs `b'...'`）设计；
当 v2 是 `IFDRational` 时，rational 元组（如 `(4294967295, 1)`）会进入该分支：
大数触发 `struct.error`，小数则拿 `b'\xb4\x01'` 与 `180.0` 比较必然失败。
嵌套 rational 元组（`BlackLevelDeltaH`、`LensSpecification`）则是
`((1,1),(1,1),(1,1))` vs `(IFDRational(1),...)` 同类型等值比较失败。

关键事实：**这是上游测试助手与新版 Pillow 的类型契约漂移，不是 piexif 的适配缺陷，
也不该通过删改断言来"修"**（R51 禁弱化；平台也禁"测试失败但构建成功"）。

## 方案（可跨库复用）

补丁只改测试文件（`tests/s_test.py` 的 `_compare_value`），加一层归一化：

```python
def normalize(v):
    if hasattr(v, "numerator") and hasattr(v, "denominator") \
            and not isinstance(v, int):
        return (v.numerator, v.denominator)
    if isinstance(v, tuple):
        return tuple(normalize(x) for x in v)
    return v
v1 = normalize(v1); v2 = normalize(v2)
```

- Pillow 侧 `IFDRational` 的 `numerator/denominator` 保留原始 n/d（含 `(0,0)`→nan 的
  极端值也可逐元组比较），归一化后与 piexif 侧元组**逐位相等**，原断言语义完全保留；
- BYTE 数组路径不受影响（tuple vs bytes 分支原样保留）；
- 不注入平台宏、不改库代码、不动其它用例。

## 真实验证

- 修复前：`FAILED (failures=1, errors=2)`（test_load / test_load_m / test_load_unicode_filename，
  均为上述类型漂移的三种形态）；
- 修复后：`Ran 55 tests` / `OK`（55/55，100%）；`conan create`（W3 本地 CI，与平台同脚本）
  `L0/L1/L1e/L4/L5` 全过，`.ci-result.json` exit_code=0；
- 测试依赖以 `build_requirements()` → `tool_requires("pillow/10.4.0")` 引入（仅构建期，
  不进入包运行时依赖图）。

## 适用范围与边界（查重差异化）

- 适用：**上游 Python 库的自动化测试套件依赖被钉旧版的 Pillow（或同类"返回类型被冻结在
  旧版"的依赖）**，而目标平台只有新版包；且断言本身数值语义不变、只需类型归一化。
- 不适用：库代码本身依赖旧 API 行为（须改库代码或写适配层）；断言依赖旧版**数值语义**
  变化（须逐例评估，不能一律归一化）。
- 与现有条目边界（`knowledge/graph/index.tsv` 全库 grep）：
  - `E580/E583/E429/E636`（Python 扩展后缀/EXT_SUFFIX/ABI 命名）：讲 **C 扩展文件名的
    平台标签归一化**；本条不涉及任何 `EXT_SUFFIX`/`.so`/ABI 问题，纯 Python 层的类型契约漂移；
  - `E319`（纯 Python 包打包）与 `DRAFT-multipledispatch-python-require-conan-staging`：
    讲 **打包/布局/PYTHONPATH**；本条讲 **上游测试对旧版依赖返回类型的假设**；
  - 关键词检索 `IFDRational` / `_getexif` / `pack_byte` / `rational` 在 `knowledge/`
    官方条目与草稿中命中 0 条（查重命令与结论见 PR 正文）。

## 复现/取证命令

```bash
# 复现（未打补丁的上游源码 + OHOS pillow 10.4.0）
PYTHONPATH=<pillow>/lib/python3.12/site-packages:<src> python3 tests/s_test.py
# 验证（打补丁后）
#   Ran 55 tests ... OK
```
