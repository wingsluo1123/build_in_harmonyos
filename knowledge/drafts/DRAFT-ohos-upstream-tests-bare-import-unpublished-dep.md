# DRAFT-ohos-upstream-tests-bare-import-unpublished-dep — 上游测试裸导入未发布依赖导致套件不可收集

> Contributor: 4A81 / Status: **DRAFT** / Updated: 2026-09-16 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-upstream-tests-bare-import-unpublished-dep`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `E387` | 图谱 | LLVM lit 测试框架适配；**psutil 缺失仅使 `--timeout` 不可用**（警告非错误）| 那是"psutil 缺失只削弱一个可选功能，测试仍能跑"；**本条是 psutil 在导入期被裸 import，导致测试套件整体无法收集**。实测 E387 中 psutil 语境为 `--timeout` 警告，不含"套件不可收集"判据 |
| — | — | — | 全库对 `test_requires` × 未发布依赖、`测试不可收集` 等组合**命中 0 条** |

**全库查证**：对 `psutil`、`裸 import`、`test_requires` × `未发布`、
`无法收集`、`显式申报` 等关键词，在 `knowledge/index.tsv`、
`knowledge/graph/index.tsv`、`knowledge/graph/*.kv`、`knowledge/doc/*.md`、
`knowledge/drafts/*.kv`、`knowledge/drafts/*.md` 中 grep —— 除本条目外
**命中 0 条**专讲此机制的条目（`psutil` 仅 2 处命中，均在 `E387`，
语境为 lit `--timeout`）。

## Scope（何时用）

上游测试辅助模块存在**导入期裸 import**，且该依赖**未发布到制品仓**。

典型信号：`tests/__init__.py` 里直接 `import psutil`（无 try/except 守卫）。

## Symptom

不是"某个用例跳过"，而是 pytest **连收集都做不到**：

```console
$ python3 -m pytest src/greenlet/tests -q --collect-only
ModuleNotFoundError: No module named 'psutil'
```

> ⚠️ **易误判点**：错误是 `ModuleNotFoundError`，容易被当作本适配的构建/环境缺陷
> 去排查。真因有两个：① 上游测试文件在**导入期**裸 import；② 制品仓**没有**该依赖。

## Root Cause

```python
# src/greenlet/tests/__init__.py:17  —— 无 try/except 守卫
import psutil
```

导入测试包即执行该行 → 抛 `ModuleNotFoundError` → 收集阶段失败。

而 psutil **未发布到 ohpcd**，按 **PF4**（依赖须先发布后使用）**不能**作为
`test_requires` 引入。于是形成困境：

| 不可取的做法 | 为何不可取 |
|---|---|
| 静默跳过并当作"测试通过" | 违反 **R51**（不可运行必须逐条写清技术原因）|
| 伪报"上游未提供测试" | 上游**有**测试，只是缺一个测试期依赖——记录失真 |
| 引入未发布依赖 | 违反 **PF4**，卡住 CI 依赖闸，PR 无法合并 |

## Recommended Solution

### 主方案（priority 1）— 显式探测 + 显式申报

在 `build()` 内**先独立探测**该依赖，再决定是否跑 pytest：

```python
probe = subprocess.run([py, "-c", "import psutil"], capture_output=True)
if probe.returncode != 0:
    self.output.warning(
        "上游测试跳过：tests/__init__.py 裸 import psutil，且 psutil 未发布"
        "（PF4 禁止作 test_requires）—— 包可用性由 test_package 覆盖")
    return
```

同时：

- `test_package/MANIFEST.yml` 内 `upstream_test_in_build: false` 并写明原因；
- **消费者测试承担该包真正可用性的验证责任**，且断言要有实质——
  对编译型扩展而言，**import 成功本身即证明链接问题已解决**（如 greenlet 的
  `-lpython3.12` / 签名问题）。

**为何要独立探测而非"跑 pytest 失败后猜原因"**：pytest 的 stderr 里
`ModuleNotFoundError` 可能被其他收集错误淹没，独立探测给出**无歧义**的理由。

**自愈式设计**：将来该依赖一旦发布，探测自动通过、上游测试随即真实执行，
**无需改配方**。

### 回退方案（priority 2）— 最小 shim

仅当该依赖确实必需、且短期内不会发布时，可提供一个**最小 shim**（只实现被测
代码实际用到的少数接口）。**代价高且脆弱**：shim 与真库行为不一致会给出
**虚假通过**，必须极其克制，并在 notes.md 明确标注"测试运行在 shim 之上"。

### 禁止做法

- ❌ 静默跳过或把失败当作通过——违反 R51，使质量记录失真；
- ❌ 把未发布依赖直接写成 `test_requires`——违反 PF4，卡住依赖闸。

## 实测证据（2026-09-16，greenlet 3.5.6 适配）

| 项 | 结果 |
|---|---|
| 触发点 | `src/greenlet/tests/__init__.py:17` 裸 `import psutil`（无守卫）|
| 复现 | pytest 收集阶段即 `ModuleNotFoundError: No module named 'psutil'` |
| psutil 发布状态 | ohpcd **无** → PF4 禁止作 `test_requires` |
| 处置 | 配方 `_run_upstream_tests()` 显式探测并输出理由；`MANIFEST.yml` 标 `upstream_test_in_build: false` |
| 验证转移 | test_package 以 9 组真实断言覆盖扩展的构建正确性与运行时行为（import 成功即证明链接链已通）|
| 运行日志实证 | `WARN: upstream greenlet tests skipped: tests/__init__.py imports psutil unconditionally and psutil is not available (not published on ohpcd; PF4 blocks adding it as a test_requires)` |

## 测试覆盖边界

本条处理"**上游有测试但缺测试期依赖**"。区分相邻情形：

- 上游**根本不提供**测试（如 cif-tools 2.0.0 的 `BUILD_TESTING` 整块被注释）→
  属"上游未提供"，应如此申报；
- 依赖存在但**版本不满足** → `E241` / `E305`；
- 缺的是**可选功能**依赖而非导入期硬依赖（如 lit 缺 psutil 只削弱 `--timeout`）→ `E387`。

## 关联条目

- 相似：`E387`（psutil 缺失，但仅为可选功能降级）
- 差异：见上方差异化定位表
