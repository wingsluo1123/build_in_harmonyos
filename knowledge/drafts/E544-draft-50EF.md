# E544 — OHOS CI worker 进程槽位临界：某一步的并发进程数超出空闲槽位即确定性 posix_spawn EAGAIN

## 错误特征
```
clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
link.sh[27]: can't fork - try again
spawn-resource exhaustion persisted through N attempts
```

- 编译步骤（每个文件 = shell→clang→`clang -cc1`）**全部成功**，却在**链接**（或运行刚生成的辅助可执行文件）时失败；
- 同一命令、同一位置**反复**失败：重试 20s×10、跨 3 次完整重建（共 30 次）无一成功——性质是「确定性」而非「负载抖动」；
- 失败机 `procs≈668`（持续稳定）/`load≈21`，而**同一台设备**本地同配方同源码（`procs≈180`）一次通过；
- 反直觉点：`clang -### -c a.c b.c c.c` 显示每个文件都会 spawn 一个 `clang-15 -cc1`（**并非**进程内集成汇编），所以「编译不 spawn、只有链接才 spawn」的直觉是错的。

## 触发条件
- 构建系统: 任意——上游自带 `build.sh`/bootstrap 脚本、把链接交给辅助 shell 脚本的项目最典型
- 阶段: compilation（链接步）或 testing（运行刚生成的可执行文件）
- 平台: OHOS worker（进程槽位贴近上限），以及任何 `RLIMIT_NPROC` / pids 控制器紧张的容器

## 根因分析

内核在 `clone()`/`vfork()` 上返回 `EAGAIN` 的来源是**进程/线程配额**（`RLIMIT_NPROC`、pids 控制器），不是内存或 fd。因此判据是「**该步同时需要几个进程**」：

| 步骤 | 并发进程链 | 实测结果 |
|---|---|---|
| 普通编译 | shell → clang → clang -cc1（3） | 通过 |
| `link lua`（命令替换 + 直接链接） | shell → 命令替换子 shell → clang → 链接器（4） | 通过 |
| tup 最终链接（旧形态） | shell → 命令替换子 shell → **`link.sh`** → clang → 链接器（5） | **必失败** |

即该机只剩约 4 个空闲槽位——链路里多出的一层 shell 就足以越界。这也解释了失败位置的确定性与 30 次重试的无效性（不是负载抖动，等下去也不会空出槽位）。

## 解决方案

### 推荐方案
把脆弱步的**并发进程数**压到与「本来就能通过的编译步」同级（本例 5 → 3）：

1. 不要用 `out=$(cmd)` 捕获长命令输出——命令替换会让一个子 shell 在整个 spawn 期间常驻，恰好多占一个槽位。改为重定向到文件 + 内建 `read`/`case` 回放并判特征；**被包裹的命令必须写在条件上下文里**：

   ```sh
   if "$@" >"$spawn_log" 2>&1; then rc=0; else rc=$?; fi
   ```

   （裸写 `"$@"` 在 `sh -e`/`sh -e ./build.sh` 下会在首败时直接结束脚本，回放与重试全部不可达，失败特征也不会进 stdout——外层配方的特征匹配同样失效。）
2. 不要在链路里插入额外 shell：上游辅助脚本（如 tup 的 `link.sh`）若只有一两条命令，就地展开到调用方；避免 `(echo;echo) | $CC -x c -c -` 这类自己要再占一个子 shell 的管道。
3. 重试窗口按构建预算给足（本例 15 次、退避 20→60s ≈ 13 分钟），并在每次重试前用 `/bin/sh -c :` 探针记录「能否创建进程」，用于区分「整机槽位耗尽」与「本步需求过高」。
4. 兜底重试次数要与单包超时匹配（本例外层 2 次 × (13min + 构建) < CI 的 3600s）。

### 禁止做法
- ❌ 当成「负载抖动」盲目重推、或只拉长盲等窗口：位置确定性的失败是结构性问题；
- ❌ 只加次数不降并发（PR #91572 的 10×20s、共 30 次全败即此）；
- ❌ 为省进程而绕过 SDK 的链接器包装（`ld.lld` 是 `#!/bin/sh` + `exec -a "$0" … lld --code-sign "$@"` 脚本）：需自行拼 sysroot/crt 与代码签名参数，风险远大于收益。

## 验证
```bash
# 1) 反例（说明「条件上下文是必需的」）：不打印 reached
/bin/sh -e -c 'f(){ false; rc=$?; echo reached; }; f'

# 2) 重试路径在 set -e 下必须可达（应看到特征回放 + retrying + 次数递增）
/bin/sh -e -c 'spawn_attempts=3; spawn_wait=1; spawn_log=./spawn.log
retry_spawn() { ... }   # 取自 build.sh
retry_spawn /bin/sh -c "echo \"posix_spawn failed: Resource temporarily unavailable\" >&2; exit 1"'
# → 回放 3 次特征、打印 2 条 retrying、以 rc=1 返回，脚本未被 set -e 误杀

# 3) 并发峰值（忙轮询采样 /proc，无 spawn）：旧形态 +5、新形态 +4、普通编译步对照 +4

# 4) 端到端
python3 scripts/ohc-run.py finish tup 0.8 published        # conan create + test_package → exit_code=0
CI_PACKAGES="archives/t/tup/0.8" zsh ci/conan/build_and_test.sh
```

## 关联条目
- 相关: E405（同属「OHOS 上进程创建语义与 Linux 不同」这一族：那条是 `posix_spawn` 不搜索 PATH → ENOENT，本条是进程配额 → EAGAIN）
- 相关: E055、E253（OHOS/HarmonyOS 进程创建与安全策略差异）
