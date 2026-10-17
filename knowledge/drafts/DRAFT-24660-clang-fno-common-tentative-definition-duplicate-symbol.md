# DRAFT-24660: 现代 Clang（≥11）/GCC（≥10）默认 -fno-common，1990s C 代码库跨编译单元 tentative definition 链接失败

- **来源**：xfractint 20.4.10 适配（2026-10-16）；历史同因案例 swftools 0.9.2（E491 事件）
- **领域**：工具链默认值语义 × legacy C 惯用法（编译/链接）
- **邻近条目**：E491（swftools 四轴合条，其 forbid_1 一揽子禁 -fcommon——本条以 conflicts_with 挂接并给出三档决策边界）、E293（旧 C++ throw(...)/register 与 C++17，同"旧代码 × 新标准"族但语言轴不同）、E531（musl 缺 qsort_r，libc 族不同轴）

## 现象

```
ld.lld: error: duplicate symbol: <符号名>
clang-15: error: linker command failed with exit code 1
```

- 出现在**多年未动的 1990s-2000s C 代码库**上；符号往往"明明只该有一份"。
- 同一份代码在旧 GCC（<10）或显式 `-fcommon` 下能正常链接。
- 本 run 实例：真实库源码去 `-fcommon` 全量重编后恰好 3 个真实符号报重复
  —— `curwin`（unix/xfcurses.c）、`boxcolor`（common/zoom.c）、
  `b_const`（common/fractalb.c）。

## 根因（完整因果链）

1. 上游 Makefile 的 CFLAGS 未指定 `-fcommon`（1990 年代默认如此写）；
2. 现代工具链把默认值切了：**Clang 自 LLVM 11 起、GCC 自 10 起默认
   `-fno-common`**（本仓设备 clang 15.0.4 实测）；
3. 1990s C 惯用的 tentative definition——多个 `.c` 各写一份 `int x;`
   （常在"伪头文件"或成对源文件里）——在 `-fcommon` 语义下产生
   **common symbol**，链接期合并为一份；在 `-fno-common` 语义下每个
   编译单元各自产出**强定义**；
4. 链接期 `ld.lld` 报 `duplicate symbol` → 构建失败。

每一步都有独立实测支撑（见下"证据链"）。

## 诊断捷径

> `ld.lld: error: duplicate symbol` + 多年未动的 C 库 → 直推本因，
> 先试 `-fcommon` 再逐符号排查，不必先做符号表人工归并。

## 方案空间（三档决策边界，与 E491(forbid_1) 的冲突裁决）

| 档 | 场景 | 处置 |
|----|------|------|
| **rec**：加 `-fcommon` | **应用型可执行** + 全局符号面巨大 + 上游无维护活动 | CFLAGS 命令行整体覆盖加 `-fcommon`（其余旗标不变），按 **P006** 在 notes.md 记录技术债与期望的上游现代化方向（extern 声明 + 单一定义） |
| **fallback**：源级归并 | 被移植库代码/头文件库/符号面小 | 头文件改 `extern` 声明 + 唯一 `.c` 定义（Debian `1020-duplicate-globals` 式补丁做法）。语义最干净、是上游现代化正确方向；但符号面大时触碰面不可控，应用型场景作长期替代而非当轮首选 |
| **forbid**：新代码禁用 | 新写的代码 | 一律禁止依赖 common-symbol 语义——E491 forbid_1 原义在此域完全适用，无裁决空间 |

**与 E491 的关系**：E491(forbid_1) 对 `-fcommon` 是无决策边界的一揽子
禁止（"全局编译器兼容旗标掩盖声明/定义关系"）；本 run 以 `-fcommon`
构建 CI 全绿，实证该定性在"应用型 + 符号面巨大 + 无上游维护"场景下
过宽。本条不推翻 E491 在库代码/新代码域的原义，而是以
`conflicts_with: E491(forbid_1)` 挂接并给出三档边界——按知识库机制
"裁决"而非"翻案"；建议主编后续在 E491 侧加反向注记形成双向闭环。

## 证据链（全部可独立复跑；原始失败日志不留存）

> **日志留存说明**：CI 逐轮覆盖构建日志，`.ci_logs/` 仅存最终 PASS 轮
> （其构建命令行实含 `-fcommon`）。失败面证据以"合成探针（机理级）+
> 真实源码复现（实证级）"两级替代，任何人可在全新 shell 独立复跑。

1. **合成探针**（mktemp 双 TU，各含 `int shared_var;`）：
   - 默认参数链接 → `ld.lld: error: duplicate symbol: shared_var`（exit 1）；
   - `-fcommon` 链接 → 成功，运行期以 `get_x()==42` 退出码自检（exit 0）。
   - 设备 clang 15.0.4 实测；命令序列见 kv `verification_cmd`。
2. **真实源码复现**（Auditor 增强实证）：已通过 CI 的配方源码，仅去掉
   `-fcommon`、其余 make 覆盖不变，全量重编后链接失败（exit 2），
   duplicate symbol 恰为上列 3 个真实符号；同源码加回 `-fcommon` 即
   通过（权威 CI PASS 日志在案）。命令序列见 kv `verification_cmd`。
3. **上游先例**：Debian xfractint 补丁集对同一问题同款修复
   （Bug#966184 一族）——上游世界同样在为此默认值切换打补丁。

## 拒稿预演（对主编可能的质疑）

- "E491 match_keywords 已含 fno-common、rec_description 已有 extern
  归并指引，无需新条" → E491 是 swftools 单事件四轴合条，其 -fcommon
  内容是无决策边界的一揽子 forbid，无法指导"何时允许"；本 run 已实证
  该 forbid 在真实场景误判；conflicts_with 正是知识库处理条目冲突的
  规定机制。
- "单实例不足 L1" → L1 分层由工具链默认值保证复发面（clang ≥11 /
  GCC ≥10 全量，与具体库无关），不依赖第二实例；swftools（E491 事件）
  可作历史第二案例。

## 适用范围

- 1990s-2000s 手写 Makefile 的 C 应用（无 configure/cmake、跨文件
  tentative definition）在 clang ≥11 / GCC ≥10 下的移植；
- 见到 `ld.lld: error: duplicate symbol` 且符号分布在多个 `.c` 的
  legacy C 库构建失败。

## 关联文件

- `archives/x/xfractint/20.4.10/conanfile.py`（CFLAGS `-fcommon` 与技术债注释）
- `archives/x/xfractint/20.4.10/notes.md`（构建方式、补丁清单）
- `archives/x/xfractint/20.4.10/patches/`（0001/0002 最小补丁）

## 原则挂钩

- **P006**（CFLAGS hack 必须记录为技术债务）：`-fcommon` 属编译旗标
  绕过，须在 notes.md 记录技术债与期望的上游修复方式；
- **P010**（必须使用 LLVM 工具链）：本因即 LLVM 工具链默认值语义，
  记录于工具链族。
