# DRAFT — summary.py 手写 YAML 解析器 inline 空列表崩溃（框架通用）

## 错误特征
`scripts/ohc/summary.py` 的 `_parse_yaml_simple`（手写简易解析器）在遇到
manifest 中 inline 空列表形态 `knowledge_gained: []` 后，同一文件更晚位置
再次出现重复键 `knowledge_gained:` 列表项时崩溃：

```
AttributeError: 'str' object has no attribute 'append'
```

触发样例：`archives/q/qpdf/12.3.2/manifest.yaml` 第 8 行 `knowledge_gained: []`
（后续第 16 行重复键列表）。

## 触发条件
- 阶段：build/report（ohc-run.py finish / summary / generate_summary）
- 输入：任一 manifest.yaml 含 `key: []` inline 空列表 + 更晚重复键列表
- 工具：ohc-run.py finish、gen_summary

## 与已有条目的区别
- 本条目：仓库手写 YAML 解析器类型归一化缺陷（框架通用，非库特定）
- 无既有条目覆盖 summary.py/_parse_yaml_simple/inline 空列表/重复键
  （查重：summary.py、inline list、empty list、duplicate key、_parse_yaml_simple 均无命中）

## 根因分析
顶层 `key: value` 分支对非空 value 直接 `data[key]=val` 存为字符串；inline `[]`
因此被当字符串。重复键列表项走 `data.setdefault(key, []).append(item)`，
setdefault 返回既有字符串 → `.append` 崩溃。

## 修复
`if val == "[]": data[key] = []`（仅此一处最小改动；普通标量/多行块/既有列表不变）。

## 验证
- RED：unittest 失败 `AttributeError: 'str' object has no attribute 'append'`
- GREEN：`python3 scripts/ohc/tests/test_summary_inline_empty_list.py` → `Ran 2 tests ... OK`
- 标量控制组：`name`/`version`/`manifest_version` 保持 `str`，未被转列表
- 窄真实 summary：`generate_summary` 全仓库扫描越过 qpdf 输入完成（len=275763）

## 边界
手写解析器行为修复，非通用 YAML 规范声明；PyYAML 等标准解析器无此问题。
