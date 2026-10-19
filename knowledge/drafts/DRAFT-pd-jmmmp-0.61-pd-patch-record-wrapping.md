# Pd 补丁按「未转义分号」结束 record：折行与内嵌子 patch 会让行式解析器误报，测试补丁文本必须转义 `;` 与 `,`

- **草稿 ID**: DRAFT-pd-jmmmp-0.61-pd-patch-record-wrapping
- **来源**: pd-jmmmp 0.61 HarmonyOS PC 适配（141 个 Pd 补丁的静态校验 + 无头 Pd 运行时验证）
- **分类**: puredata / data-package / testing / parser / encoding
- **状态**: 本地草稿（随 PR #16741 提交，未写正式索引）

## 问题 / 错误签名

- **静态校验误报**：对 `multiarray.pd` 这类文件做行式解析，会报
  `malformed connect line`（约 280 条）与
  `unbalanced subpatches: 101 '#N canvas' vs 98 '#X restore'`。
  这些补丁本身在 Pd 里完全正常，错误全部来自解析方式。
- **运行时假错误**：测试补丁的说明文本里写了未转义的 `;`，正跑日志出现
  `error: verify_jmmmp.py: no such object` + `error: canvas: no method for 'so'`，
  看起来像库或依赖缺失，实际是补丁记录被自己截断。

## 根因

1. **record 终止符是「未被转义的分号」**。Pd 写盘时把超长 record 折行成多条物理行，
   续行本身没有任何前缀；只要按物理行切分，续行就会被当作新 record 解析。
2. **消息框可以内嵌整段子 patch**。`multiarray.pd` 用 `#X msg` 保存一个完整子补丁，
   内部所有 `;` / `,` 都写成 `\;` / `\,`。行式解析器不认转义，于是把里面的
   `#X canvas` / `#X connect` 当成真实节点统计。
3. **同一转义规则反向作用在测试补丁上**。`#X text` / `#X msg` 里若有裸 `;` 或 `,`，
   Pd 会把它当 record 终止符，后半句变成新的对象表达式，从而产生
   `no such object` / `canvas: no method for` 这类与库无关的报错。

## 最小修复方案

`test_package/verify_jmmmp.py` 里先重组逻辑 record，再解析：

```python
def _ends_record(line):
    stripped = line.rstrip()
    if not stripped.endswith(";"):
        return False
    backslashes = 0
    index = len(stripped) - 2
    while index >= 0 and stripped[index] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 0          # 偶数个反斜杠 => 真终止符

def records(text):
    buffer = []
    for line in text.splitlines():
        buffer.append(line.rstrip())
        if _ends_record(line):
            yield " ".join(part.strip() for part in buffer if part.strip())
            buffer = []
```

生成测试补丁时统一转义：

```python
def escape_box(value):
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
```

## 验证

| 检查 | 行式解析 | record 解析 |
|---|---|---|
| `multiarray.pd` 结构错误 | ~280 条 malformed connect + 101/98 不配对 | 0 |
| 141 个 `.pd` 总体 | 有误报 | 0 错误 |
| 测试补丁正跑日志 | `verify_jmmmp.py: no such object` | 0 条 couldn't create / no such object |
| 9 组断言值 | 受污染 | 与预期逐值一致（`1 2 3 7` / `10 12 14` / `100 255 177.5` …） |

## 适用范围与反例

- 适用于任何对 `.pd` 做静态校验的数据包，以及任何用 `.pd` 驱动 `test_package` 的适配。
- **反例（不要做）**：把正跑日志里出现 `couldn't create` 一律判失败。上游抽象对象自己
  会打印 `error:`（例如 `receive~ $2-posmod: no matching send`、`expr: no such table`），
  这和「对象没创建出来」是两件事；正确做法是断言**创建失败计数**（含负向对照的期望值）
  与哨兵行，而不是关键字全量匹配。
