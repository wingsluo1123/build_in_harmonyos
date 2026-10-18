# sqlparse 0.6.0

## 软件与环境

sqlparse 是纯 Python 的非校验式 SQL 解析/格式化库，0.6.0 起要求 Python 3.10 及以上
（上游 `pyproject.toml` `requires-python = ">=3.10"`）。本配方把 Python 模块安装到包内
`lib/python`，通过 Conan 环境（`PYTHONPATH`）提供；命令行使用 `python3 -m sqlparse`
（上游 `[project.scripts] sqlformat = "sqlparse.__main__:main"`）。

**没有任何第三方运行时依赖**：上游 `pyproject.toml` 的 `dependencies` 为空，
`optional-dependencies` 只有 `dev = [build]` 与 `doc = [sphinx, furo]`，
均不进入运行期。因此本包 `requires` 为空是上游事实，不是漏写。

## 源码

- 上游：https://github.com/andialbrecht/sqlparse （tag 0.6.0）
- 制品源：PyPI 官方 sdist `sqlparse-0.6.0.tar.gz`，
  sha256 `113c35c75365ab9cc9c7231d68c6428fb11c085fc8e9eb1ad659b7ddbf6cd2b9`，
  与 PyPI 公布的摘要逐字一致（2026-08-13 上传，178477 B）。
- 未修改上游源码或测试（`sources` 直接取官方 sdist，`patches: {}`）。

## 为什么新增 0.6.0（而不是停在 0.5.5）

上游 `CHANGELOG` 的 `Release 0.6.0 (Aug 13, 2026)` 段列出了 4 项安全修复：
CVE-2026-59893（lexer 二次复杂度 DOS）、CVE-2026-54284（分组嵌套 DOS）、
CVE-2026-71491（纯注释语句 DOS）、CVE-2026-59894（python/php 输出格式反斜杠未转义）。
0.5.5 不含这些修复，故按 R37「上游发布新版本 → 新版本号」新增 0.6.0。

## 构建与测试（真机实测，非声明）

- 构建方式：纯 Python，无 C/C++ 编译。`source()` 取官方 sdist；`build()` 内先
  `pytest --collect-only` 清点上游用例，再跑完整官方套件；`package()` 复制
  `sqlparse/**.py`（engine/filters 子包一并入包，实测 21 个 `.py`）+ `py.typed` + `LICENSE`。
- 构建系统说明：上游元数据是 hatchling（PEP 517），本配方不走 PEP 517 构建，
  直接按源码树落盘 site 布局，因此不需要 hatchling/setuptools/wheel。
- 上游测试依赖以源码归档 + 固定 sha256 提供（pytest 8.3.5、pluggy 1.5.0、
  packaging 24.2、iniconfig 2.0.0；Python <3.11 另加 exceptiongroup 1.2.2、tomli 2.2.1），
  只解压到本包构建目录并经临时 `PYTHONPATH` 使用，不要求 pip、不改共享 Python 环境。
- 实测（`conan create archives/s/sqlparse/0.6.0`，退出码 0）：
  - 收集 **509** 个用例（`509 tests collected in 0.71s`）
  - **506 passed**、0 failed、0 error、0 skipped
  - 2 xfailed、1 xpassed，均为上游自带标记，未删改或跳过任何用例：
    - `XFAIL tests/test_format.py::TestOutputFormat::test_python_multiple_statements_with_formatting - Needs fixing`
    - `XFAIL tests/test_format.py::test_format_right_margin - Needs fixing`
    - `XPASS tests/test_regressions.py::test_issue484_comments_and_newlines - Needs to be fixed`
  - 消费者测试 **5/5 通过**（`Ran 5 tests in 0.187s / OK`）：模块来源与版本、parse、
    split、format、`python3 -m sqlparse` CLI 五条实质路径。
  - 上游测试与消费者测试分别统计，不合并冒充上游结果。

## 与 0.5.5 配方的差异（均为洁净度修正，不改变构建语义）

1. `package()` 增加 `py.typed`（上游随包分发的 PEP 561 标记，0.5.5 漏装）。
2. 上游 pytest 运行环境加 `PYTHONDONTWRITEBYTECODE=1`，避免在源码树生成 `__pycache__`。
3. 消费者测试（`test_package`）运行环境同样禁用字节码写入。实测依据：首版构建后
   `test()` 从 `package_folder` 导入模块，在制品目录里写出 21 个 `.pyc`（3 个
   `__pycache__`）；修正后同一构建产出 `pyc=0`、`__pycache__=0`。
4. `package()` 的 `copy` 加 `excludes=("__pycache__/*", "*.pyc")` 作防御。

## 已知限制

- 该库不校验 SQL 语法，也不连接数据库；`parse/format/split` 为纯文本处理。
- 消费者需自备 Python 解释器（与 0.5.5 一致）；本包只提供模块与 `PYTHONPATH`。
- `python3 -m sqlparse` / `sqlformat` 的可用性依赖消费者的 Python 3.10+；
  本配方按平台默认解释器（实测 Python 3.12）验证。
---

**编译结束**: 2026-10-17 11:39
**最终状态**: built
