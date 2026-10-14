# DRAFT-ohos-runtime-lock-dir-fallback — OHOS PC 运行时锁/PID/状态目录路径不可假设：toybox sh 对不存在路径的 exec fd 重定向失败即终止脚本

> **Contributor**: sea_crab | **Status**: DRAFT | **Updated**: 2026-09-26
> **Severity**: blocking (2) | **Category**: runtime / filesystem / shell / ohos / platform-detect
> **Audience**: 所有在 OHOS PC 上运行脚本类应用/守护进程的配方维护者（conan package_type=application）、CI 直跑冒烟脚本作者、把上游 init/事件入口带到 OHOS 的移植者

## 触发（trigger）

- 脚本把锁/PID/状态文件放在 `/var/lock`、`/var/run` 或 `/tmp`（脚本生态的三大惯例位置）；
- OHOS PC 设备上：`ls -ld /var /var/lock /var/run` 全部 **"No such file or directory"**，`touch /tmp/xxx` 实测报 **"Read-only file system"**（2026-09-26 实测）——三类目录全部不可用，且 `mkdir -p` 也建不出来（根文件系统对普通用户不可写）；
- 脚本以 **toybox sh**（`/bin/sh`）执行并对这些路径做 **exec fd 重定向**（`exec 8>/var/lock/app.lock` 这类两阶段 flock 锁的标准写法）。

典型案例（本条 source_event）：laptop-mode-tools 1.74 的 `usr/sbin/laptop_mode`——顶部硬编码 `exec 8>$LMT_REQ_LOCK`（`/var/lock/lmt-req.lock`）、`exec 9>$LMT_INVOC_LOCK`，状态文件硬编码 `/var/run/laptop-mode-tools/state`。

## 症状（symptom）

```text
sh: can't create /var/lock/lmt-x.lock: No such file or directory
（脚本立即终止，rc=1，任何业务诊断输出都没有）
```

失败点在脚本任何 `log`/`echo` 之前，只有一行重定向错误，极易误判为"脚本自身缺陷"或"权限没配好"，而不是平台目录缺失。

## 机制（root cause）

1. **平台探测证据**：设备无 `/var`（自然无 `/var/lock`、`/var/run`）；`/tmp` 只读（`touch` 报 `Read-only file system`；设备 mount 表根分区显示为 tmpfs/hmfs 混合，与上游发行版 `/tmp` 可写惯例不符）。三类惯例目录在 OHOS PC 上同时失效是本条的充分触发面。
2. **工具实现证据**：`laptop_mode` 的两阶段 flock 方案（LMT_REQ_LOCK 外锁 + LMT_INVOC_LOCK 内锁，`lock_retry()` 重试 10 次）是标准的 `exec N>file; flock -n N` 写法，锁文件路径全部硬编码 `/var/lock/`，没有任何存在性/可写性防御。
3. **解释器语义证据（间歇性来源）**：toybox sh 把 **exec fd 重定向失败当作致命错误立即终止脚本**（special builtin 语义）；hnp bash 则容忍 exec 重定向失败继续执行。同一个脚本换解释器，症状从"必现启动即死"变成"完全正常"——在 bash 下探索通过、CI/`/bin/sh` 下必现失败，正是最难归因的间歇性形态。
4. **失败面**：即使解释器容忍（bash），锁文件依然没有建立成功，单实例/事件合并语义**静默丢失**——比崩溃更隐蔽。

## 验证（verification，自包含、只读）

```sh
# 复现（任意新 shell；重定向目标目录不存在 → 不会创建任何文件，只读探针）:
ssh <ohos-host> "sh -c 'echo before; exec 9>/var/lock/x; echo after'"
# → 输出仅 "before"，stderr: sh: can't create /var/lock/x: No such file or directory
#   rc=1；"after" 永不打印 —— 证明 exec 重定向失败即终止脚本

# 解释器差异（同一探针换 bash）:
ssh <ohos-host> "bash -c 'echo before; exec 9>/var/lock/x; echo after'"
# → "before" 与 "after" 都打印，rc=0 —— bash 容忍失败继续运行（掩盖而非修复）

# 平台探测:
ssh <ohos-host> "ls -ld /var /var/lock /var/run; touch /tmp/.probe"
# → 前三者 No such file or directory；touch: '/tmp/.probe': Read-only file system
```

## 修复（rec：路径可覆盖 + 不可写回退 + 写入非致命）

三层防御，全部最小侵入（实例：`archives/l/laptop-mode-tools/1.74/patches/0002-laptop-mode-runtime-portability-ohos.patch`，conan create + 权威 CI 全门禁 PASS）：

1. **路径可覆盖**：把锁/PID/状态目录收敛为环境变量，默认值保持上游行为：
   ```sh
   LMT_LOCK_DIR="${LMT_LOCK_DIR:-/var/lock}"
   LMT_RUN_DIR="${LMT_RUN_DIR:-/var/run/laptop-mode-tools}"
   LMT_REQ_LOCK="$LMT_LOCK_DIR/lmt-req.lock"   # 原硬编码全部改为引用变量
   ```
2. **不可写回退**：使用前做可写探针，失败则按序回退，仍不可用则"无锁降级"（单实例 CLI 工具可接受）并打 VERBOSE 日志：
   ```sh
   if ! ( : > "$LMT_LOCK_DIR/.lmt-lock-probe" ) 2>/dev/null; then
       for _fb in /tmp/app-locks "$HOME/.app-locks"; do
           if mkdir -p "$_fb" 2>/dev/null && ( : > "$_fb/.lmt-lock-probe" ) 2>/dev/null; then
               LMT_LOCK_DIR="$_fb"; break
           fi
       done
   fi
   ```
3. **写入非致命**：`mkdir -p "$LMT_RUN_DIR" 2>/dev/null`、`touch "$LMT_RUN_DIR/enabled" 2>/dev/null`、`echo ... > "$LMT_RUN_DIR/state" 2>/dev/null`——状态读写都有存在性守卫，失败不退出。

### fallback（诚实权衡）

- **换解释器**（`/data/service/hnp/bin/bash script`）可绕过 exec 重定向致命终止。掩盖而非修复：bash 的容忍是实现细节而非 POSIX 承诺，且锁根本没有建立成功，并发语义静默丢失。仅作过渡手段并需在 PR 标注解释器依赖。
- **不适用**："以 root 运行即可建出 /var/lock"——设备无 root；且即便 root 可写，根文件系统只读策略下依旧失败。

### 反模式（forbid）

- `exec N>/(var/lock|var/run|tmp)/...` 无探针无回退：toybox sh 下该行即脚本终止点，且发生在任何业务输出之前（forbid_1）。
- 假设 `mkdir -p /var/lock` 能建出目录：根文件系统对用户不可写，目录不会出现，锁/单实例语义名存实亡（forbid_2）。

## 证据与关联

- 案例 run：laptop-mode-tools 1.74（候选 8eb190476d，权威 CI PASS：`Total=1 Success=1`，含 L1e 破坏性反向验证 + L2 冒烟；patch 0002 后 `laptop_mode --version/--help` 与 test_package 11 项断言全过）。
- 探针证据：Builder 2026-09-26 设备实测（上节全部命令为只读探针，可独立复跑）。
- 去重（graph/drafts/经验仓零命中）：`grep -ril 'var/lock'`、`'exec 8>'` 在 `knowledge/graph` 与 `knowledge/drafts` 零命中；`/var/run` 仅命中 keyd 案（见下）；经验仓 `ophs_ci_review` 对 `var/lock`、`lock.dir`、`/var/run` 均零命中。
- 相近条目与差异：
  - **DRAFT-keyd-2.5.0-ohos-input-subsystem-mac-invisible**：共享"设备无 /var/run"的平台探测事实，但失败面是 C 程序 `open()` IPC 套接字路径 ENOENT（rc=255，编译产物层面的路径问题）；本条失败面是 **shell 解释器对 exec fd 重定向的致命终止语义 + 锁/状态目录的可覆盖/回退模式**，波及所有脚本类应用与 CI 直跑。两案互补（同族平台目录缺失，不同技术轨道），建议交叉引用；是否合并编号由主编定。
  - **DRAFT-hnp-bash-pwd-unbound-set-u-scripts**：同族"OHOS 执行环境语义不可假设"（PWD 未定义 vs exec 重定向致命），且共享"bash 与 toybox sh 语义差异制造间歇性"的教训模式；失败面不同（环境变量 vs 文件系统路径），修复轨道不同（显式传 PWD vs 可覆盖路径 + 回退）。
- 原则挂钩：P014（环境与平台语义的非显性冲突——消费方须显式管理运行时假设而非依赖发行版惯例）。
