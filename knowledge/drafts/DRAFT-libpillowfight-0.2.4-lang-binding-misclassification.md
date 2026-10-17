# DRAFT — lang-preflight 将带 Python 绑定层的 C 库误判为 python（setup.py / setuptools）

- **软件**：libpillowfight 0.2.4
- **任务**：`libpillowfight-0.2.4-r02-full-adaptation-and-contract-bound-evidence-pc1-35-20260928T035500Z`
- **状态**：DRAFT（配对 `DRAFT-libpillowfight-0.2.4-lang-binding-misclassification.kv`）
- **编号**：`DRAFT-libpillowfight-0.2.4-lang-binding-misclassification`（待人工审核后分配正式 E 编号）

## 1. 现象

`lang-preflight`（默认任务语言 cpp）对 libpillowfight 0.2.4 判
`detected_language: python`，并自动写 `env_unsupported` 终态：

```json
{"detected_language": "python", "status": "env_unsupported",
 "language_evidence": {"build_system": "setuptools",
   "manifest": "setup.py 存在（python 打包 manifest）",
   "source_stats": "源文件 32 个（python:17, c:15, bash:1），主体占比 53%"}}
```

但该库主体是纯 C：CMake 主构建 + `-DNO_PYTHON` 编译 12 个 C 算法源文件。

## 2. 根因（两层）

1. **manifest 优先级**：`_manifest_scan` 先查 `setup.py/setup.cfg`（命中即判
   python/setuptools），`CMakeLists.txt` 分支在其后；顶层两者并存时 setup.py 恒胜。
2. **绑定检测盲区**：`_detect_binding` 只识别 `pybind11 / boost_python /
   Python_Additions / find_package(Python)`；libpillowfight 的 Python 层是
   `setuptools Extension`（setup.py 里 `Extension(...)` 编译 pypillowfight C 扩展）
   加 pytest 测试（tests/*.py 13 个），不触发绑定覆盖。源码统计 python:17 含
   13 个测试文件 + 打包脚本，占比 53% < 70%，不构成单语言主体，最终按 manifest 判 python。

## 3. 设备可执行复现

```sh
SRC=/storage/Users/currentUser/builds/libpillowfight-0.2.4.work
head -12 "$SRC/CMakeLists.txt"          # project(libpillowfight) / -DNO_PYTHON / add_library(...)
grep -n 'Extension' "$SRC/setup.py"     # setuptools Extension（C 扩展绑定）
find "$SRC" -name '*.c' | wc -l         # 15
find "$SRC" -name '*.py' | wc -l        # 17（13 个为 tests/*.py）
grep -n 'language' "$PWD/archives/l/libpillowfight/0.3.1/manifest.yaml"   # language: C
```

## 4. 处置（libpillowfight 0.2.4 实测有效）

按 R47 边界规则复核：绑定包按主体语言判、辅助脚本/测试不算主体、c↔cpp 兼容族。
证据链：CMakeLists.txt 主构建 + 15 个 C 源（库主体）+ setup.py Extension 绑定形态 +
同库 0.3.1 已按 C 合入先例 → 判 C（cpp 兼容族，任务默认 cpp 匹配），继续 C 适配。
终态报告附 lang-preflight 原始输出 + 复核证据 + 先例，供分析端复核。

## 5. 边界与反例

- **不是所有 setup.py 都存在**：纯 Python 项目判 python 正确，应遵循工具终态。
- **pybind11/boost_python 绑定**：工具已覆盖（D.4-2），判 cpp。
- **反例**：manifest 与统计矛盾且 ≥70% 另一语言 → mixed，按冲突规则处理。
- **限制**：复核必须基于真实源码证据，不得改 `--lang`/输入使判定变绿（gaming）。

## 6. 复用提示

凡"顶层 setup.py 与 CMakeLists.txt 并存、C/C++ 为主体 + Python 绑定/测试"的库
（如携带 pytest 测试的 C 库），lang-preflight 可能误判 python；先用 CMakeLists +
C 源计数 + 绑定形态 + 同库先例建立证据链，再决定继续适配或遵循终态。

## 7. 复现证据（本任务）

| 项 | 值 |
|---|---|
| 工具原始判定 | `detected_language: python` / `build_system: setuptools` / 统计 53% |
| 库主体证据 | `CMakeLists.txt: project(libpillowfight)` + `-DNO_PYTHON` + 12 个 C 算法源 |
| 绑定形态 | `setup.py: setuptools.Extension`（pypillowfight） |
| 先例 | `archives/l/libpillowfight/0.3.1/manifest.yaml: language: C`（已合入） |
| 复核结论 | 判 C，conan create + test_package 通过（见 test-report.md） |
