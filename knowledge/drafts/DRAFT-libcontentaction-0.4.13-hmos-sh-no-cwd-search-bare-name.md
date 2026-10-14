# HMOS 的 sh 不搜索当前目录：裸相对名执行一律 rc=127

> Draft: `DRAFT-LIBCONTENTACTION-0413-HMOS-SH-NO-CWD-SEARCH-BARE-NAME`
> Stem: `libcontentaction-0.4.13-hmos-sh-no-cwd-search-bare-name` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-LIBCONTENTACTION-0413-HMOS-SH-NO-CWD-SEARCH-BARE-NAME
- **严重度**: 3
- **类别**: shell|testing|cross-compile-divergence
- **触发工具**: conan|ci
- **阶段**: testing|build

## 错误特征

设备侧（鸿蒙 PC / CI worker）执行裸相对名：

```
sh: test-defaults.py: inaccessible or not found
rc=127
```

或（ctest 场景）：

```
Error 127
needed by ./test_lca_consumer
```

而同一个文件显式写 `./` 就正常：

```
sh -c 'exec "$@"' sh ./s.sh   → SCRIPT_RAN ，rc=0
```

## 根因

设备的 `sh` 解析**不含 `/` 的裸名字**时只查 `PATH`，**不查当前目录**。Linux 上很多测试框架把 testbed 目录放进 `PATH`，
于是"裸名可用"；设备侧没有这一层，直接 rc=127。**与配方源码/依赖/工具链无关**。

（常见误判：把它当成"ctest 的 WORKING_DIRECTORY 配错"去加 `WORKING_DIRECTORY` —— 无效，而且会把真因盖住。）

## 影响范围

- test_package / 测试脚本 / build 脚本里**用裸相对名调用**辅助脚本或二进制（`test-*.py`、`run_*.sh`、ctest `COMMAND`）的包；
- 尤其"把上游自带测试套件搬进 test_package"的适配（本类最常见）；
- 表征：CI 失败在 WSL/交叉环境**永不复现**。

## 附带实测（同一轮旁证）

鸿蒙 PC（cwd 已在脚本所在目录，脚本 `s.sh` chmod 755）：

```
sh -c 'exec "$@"' sh s.sh              →  rc=127   (sh: s.sh: inaccessible or not found)
sh -c 'exec "$@"' sh ./s.sh            →  SCRIPT_RAN  rc=0
env PATH=/usr/bin:/bin sh -c 'exec "$@"' sh s.sh   →  rc=127   ← 排除 PATH 污染解释
```

## 推荐方案

1. **调用处补 `./`**（最稳，不改上游语义）；
2. 或在脚本开头 `PATH="$PWD:$PATH"`（改动面更大，注意别把副作用带进产物）；
3. **双向自检**（设备侧）：旧 rc=127 → 新 rc=0；且**绝对路径调用与不存在的名字仍按原样失败**（防假通过）；
4. **纪律**：凡 WSL/交叉环境不复现的 CI 失败，**先上设备做最小复现再改配方**（本条正是"凭日志猜 cwd"猜错的实例）。

## 验证命令

```sh
cd /tmp && printf '#!/bin/sh\necho OK\n' > s.sh && chmod 755 s.sh
sh -c 'exec "$@"' sh s.sh;                 echo "bare rc=$?"        # 期望 127
sh -c 'exec "$@"' sh ./s.sh;               echo "dot rc=$?"         # 期望 0
env PATH=/usr/bin:/bin sh -c 'exec "$@"' sh s.sh; echo "ctl rc=$?"  # 期望 127
```

## 与既有条目的边界（查重后人工核对）

| 条目 | 它讲的是什么 | 与本条的区别 |
|---|---|---|
| **E529** 给 OHOS CMake test_package 配方自己的工具 PATH | 工具（cmake）**根本不在 PATH 上**（来自 tool_requires），修法是在 test_package 的 `generate()` 注入工具目录 | 本条是"**文件就在当前目录**，但 shell 不查 cwd"。**首选修法是 `./name`**（不改任何环境）；只有确实需要 cwd 语义时才退而改 PATH，且要评估副作用 |
| **E346** hmmac 沙盒拒绝 `SHELL=/bin/sh` → Error 127 | 沙盒**权限**问题 | 与本条的查找语义无关 |
| **crashme-2.8.5** 消费者测试把 126/127/255 误判为通过 | **判定逻辑假绿** | 本条解释"为什么会是 127"，那条讲"127 被当成 PASS" |

> 官方 `scripts/ohc-run.py draft-review` 的相似度 TOP3：**E307 0.37 / E108 0.33 / E250 0.33**（灰区，预审建议 `review-similar`）：
> E307 讲 test_package 的**依赖面**（header-only 不该引 CMakeToolchain）；E108 讲**缺 GNU install(1)**；E250 讲**缺 Go 工具链**。
> 三条都靠**共用错误串**（`inaccessible or not found` / `Error 127`）提高相似度；本条的差异是「**文件存在，只是 shell 不查 cwd**」。
> 另需区别于 **E543-draft-16B3**（OHOS 上 CPython `subprocess` 走 `posix_spawn` 不解析 PATH ⇒ 裸名探工具报 ENOENT）：那条是 **Python/子进程执行器**的解析问题，本条是 **shell 的当前目录查找**；修法也不同（它要绝对路径/显式 PATH，本条首选 `./`）。

> 查重词面命中（`inaccessible or not found` 177 / `Error 127` 204 / `: No such file or directory` 404）**全是通用错误串**；机制关键词（`sh 不搜索当前目录` / `bare relative name` / `PATH 当前目录` / `WSL 不复现`）**全部 0 命中**。

## 取证记录

- 来源：libcontentaction 0.4.13 适配 PR !13898 的 CI 整改（CI #79942）；任务 agent 在鸿蒙 PC 上最小复现后自我纠正；
- 值守 Agent 于 2026-10-10 14:2x **独立复现**（受控 PATH 对照），见 `work/pathb-draft/` 与 `work/路径B候选-HMOS裸名-20261010.md`；
- 查重：`kb_novelty.py check "sh 不搜索当前目录"` → 0 命中（NEW）；`"current directory not in PATH"` → 0 命中（NEW）；
- 边界：知识库中 43 条提到"当前目录"的条目**都是 HMDFS 文件系统限制**（E060/E167/E175），与 shell 查找语义无关。