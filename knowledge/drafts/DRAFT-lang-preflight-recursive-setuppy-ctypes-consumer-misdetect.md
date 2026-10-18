# DRAFT-lang-preflight-recursive-setuppy-ctypes-consumer-misdetect：lang-preflight 对 setup.py 做全树递归匹配，纯 ctypes 绑定子目录（非构建系统）把 C 库误判成 mixed

> Source: genometools 1.6.2 前置适配（lang-preflight 实测 env_unsupported）；下游 ltrsift/1.0.2
> 对应 KV: knowledge/drafts/DRAFT-lang-preflight-recursive-setuppy-ctypes-consumer-misdetect.kv

## 一句话

`scripts/ohc/lang_detect.py` 的 manifest 扫描对 `setup.py` 用**全树递归**文件名
匹配（不同于 Cargo.toml/CMakeLists.txt 的顶层匹配），上游把 Python 绑定放在
`gtpython/setup.py` 子目录时，任务 cpp 会被判成 `mixed` → env_unsupported。
而该"绑定"若是 **ctypes 纯消费者**（运行时 dlopen 库、setup.py 不编译任何
扩展），它根本不是构建系统——判定的前提就不成立。

## 使用说明（三步复核，不要硬闯）

1. **定位触发点**：`find <src> -name setup.py -o -name pyproject.toml`，确认
   命中的是顶层还是子目录（本条仅适用于**子目录命中**）；
2. **验绑定性质**：读该 setup.py——
   - `Extension(...)`/编译 C 源 → 真绑定，本条不适用（按 onnx 判例走平台复核）；
   - 仅 `packages=[...].py` + 运行时 `ctypes.CDLL("libxxx.so")` → **纯消费者**，
     交付物语言由顶层构建系统决定；
3. **按 onnx 判例（DRAFT-onnx-1.20.0-lang-preflight-…-misdetect）整理交付物证据**
   交平台：顶层构建系统 + C 源占比 + 子目录消费者性质，语言结论以平台检查为准。

## 与 onnx 判例的边界（去重声明）

| | onnx 1.20.0 判例 | 本条 |
|---|---|---|
| 触发 | **顶层** pyproject.toml（优先级高于 CMake） | **子目录** setup.py 被递归匹配捞到 |
| 绑定形态 | pybind11 等编译型（D.4-2 覆盖） | ctypes 纯消费者（D.4-2 **不覆盖**） |
| 判定结果 | python（盖过 cpp） | mixed（冲突规则） |

两条互补：D.4-2 只救"编译型绑定 + cpp≥70%"；ctypes 消费者子目录只能靠本条
的交付物证据路径。

## 适用范围

- 任何顶层手写 Makefile/CMake、但源码树携带 `*/setup.py` 纯 ctypes/消费者
  子目录的 C/C++ 库（genometools gtpython 实证；同类结构常见于带脚本绑定的
  科学计算库）。
- 不适用：顶层就是 python manifest 的真混合库；pybind11/boost::python 编译型
  绑定（D.4-2 已覆盖）。

## 输入 / 输出

- 输入：lang-preflight JSON（expected/detected/language_evidence）+ 触发的
  setup.py 内容 + 顶层构建系统证据。
- 输出：三选一结论（cpp 交付物证据 / 接受迁移 / 如实 mixed）+ 平台复核材料。

## 实证（2026-10-04，genometools/1.6.2）

```
$ python3 scripts/ohc-run.py lang-preflight genometools 1.6.2 --src <src>
expected=cpp, detected=mixed
notes: 冲突: manifest=python 但统计 c 占 76% → mixed
```

- 触发文件：`gtpython/setup.py`（`packages=['gt','gt.core',…]` 全是 .py，
  `dlload.py` 运行时 `ctypes.CDLL` 加载 libgenometools.so）；
- 交付物：顶层 Makefile + `lib/libgenometools.so`（938 个 .c，76%）；
- 真机 r13：cpp 适配全流程跑通（L0–L5 pass），反证交付物确为 C 库。
