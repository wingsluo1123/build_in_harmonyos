# DRAFT-SHADOW-CI-QUEUE-RUNNER-SELF-MATCH-DEADLOCK：单包排队 runner 的进程探测匹配到自己导致永久等待，自排除与原子锁写法

> Source: rmcast 2.0.0 真机适配（2026-10-13，设备上实测发现 procmail runner 死锁）
> 状态：DRAFT — same-stem .md/.kv pair

## 一句话

设备 shadow CI 的排队循环用 `ps -ef | grep -E 'conan|clang|make' | wc -l`
判断设备是否空闲——但**自己父进程的 cmdline 里就含这些关键字**（如
`sh -c ... conan-home ... ; sh run-<pkg>-shadow.sh`），于是 runner 匹配到
自己，`wc -l` 永远 ≥1，**永远等不到空闲，也永远不开始构建**，且表现为
"设备忙"阻塞后续所有排队任务。

## 使用说明（可复制流程）

### ① 判据：如何确认是自匹配死锁（而不是真忙）

1. 看 runner.log：`queued: N build procs busy` 每 30s 一条、持续几十分钟且
   N 恒定不变；
2. `ps -ef | grep -E '<runner 的 pattern>' | grep -v grep`，逐条检查命中的
   进程 cmdline——若只有**该 runner 自己及其父 `sh -c` 包装**，即自匹配死锁；
3. 关键特征：**没有任何子进程**在真正构建（无 clang/make/python3 conan 子进程）。

### ② 修复：三种写法（按健壮性递增）

```sh
# A. 自排除（最小改动）：排除自己的 pid 与父 pid
n=$(ps -ef | grep -E 'conan|clang|make' | grep -v grep \
      | grep -v " $$ " | grep -v " $PPID " | wc -l)

# B. 匹配真实工作进程而非关键字：conan 的实际工作进程是 python3，
#    编译是 clang/make —— 匹配"可执行名+参数形态"，避免裸 'conan'
n=$(ps -ef | grep -E 'python3 .* conan (create|test)|[c]lang |[m]ake ' | grep -v grep | wc -l)

# C. 原子锁（最稳，推荐）：不用进程探测，用 mkdir 的原子性
LOCK=$HOME/.build-queue.lock
if mkdir "$LOCK" 2>/dev/null; then
    trap 'rmdir "$LOCK"' EXIT INT TERM
    ... do build ...
else
    echo "queued: lock held"; sleep 30
fi
```

要点：
- `[c]lang` 方括号技巧只防 grep 自己，**防不了父 wrapper**（其 cmdline 是
  别的字符串），所以 A/B 里都要同时处理父子关系；
- 用 `ps -ef` 的第三、四列（PID/PPID）排除 `$` 与 `$PPID` 比 grep 字符串可靠；
- C 方案把"空闲判定"从易错的进程枚举变成文件系统原子操作，且天然支持
  多任务公平排队（先到先得），应作为新脚本的首选。

### ③ 营救已死锁的 runner

确认死锁后可安全 kill 掉 runner（它尚未开始构建，无工作损失）：
在 runner.log 追加原因说明 → `kill <runner_pid> <parent_pid>` →
该任务的宿主会看到 runner 退出，可修复后重跑。

## 适用范围

- 一切"轮询进程列表以判定设备/构建机空闲"的排队脚本（真机 shadow CI、
  错峰执行器、批量构建调度）；
- 也适用于 `pgrep -f <pattern>` 形态的等价 bug（pgrep -f 同样匹配父 wrapper）。

不适用：基于文件锁/任务队列系统的调度（本就不存在该 bug）；
构建进程本身由外部系统管理、runner 只做单次执行的场景。

## 输入 / 输出

- 输入：排队脚本的空闲判定 pattern；ps/日志输出。
- 输出：判定结论（真忙 / 自匹配死锁）+ 修复后的空闲判定代码
  （自排除 grep、ps 列排除、或 mkdir 原子锁）。

## 示例（rmcast 真机适配实证）

- procmail 3.24 runner：`while :; do n=$(ps -ef | grep -E 'conan|clang|make'
  | grep -v grep | wc -l); [ "$n" = 0 ] && break; ...; done`；
- 死锁链：父 `sh -c rm -rf .../conan-home/p ...; sh run-procmail-shadow.sh`
  的 cmdline 含 "conan-home" → 命中 'conan' → n=1 永真；
- 实测 runner.log `queued: 1 build procs busy` 持续 8+ 小时、无任何子进程；
- 营救：留言 + kill 两个 pid 后设备立即空闲（xroar 任务已结束）；
- rmcast 任务随后拿到设备，conan create + test_package 一次通过。

## 查重

- 知识图谱 E 系列、drafts 全量检索 `排队|queue|死锁|deadlock`：现有命中均为
  kqwait/appstream/cdb 等包的无关 case，**无排队自匹配死锁条目**；
- 与 E330（capability-tested shell / noexec）无关（那是脚本执行能力）；
- 与 L1e/E225（test 产物缓存复用）无关（那是测试执行阶段）。

## 关键词

单包排队, shadow CI, ps grep 自匹配, 死锁, 空闲判定, mkdir 原子锁,
pgrep -f, 父进程 cmdline, runner, 错峰执行
