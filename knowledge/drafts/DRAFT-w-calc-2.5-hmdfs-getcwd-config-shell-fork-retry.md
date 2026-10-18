# DRAFT-w-calc-2.5-hmdfs-getcwd-config-shell-fork-retry
> OHOS 共享 profile 的 CONFIG_SHELL(hnp bash) 在 HMDFS 上 getcwd 失败致 autoconf configure 中止：改写 /bin/sh 并导出 PWD，并对 fork 抖动做标记门控有界重试

## 问题特征（真实日志片段/标记）
- 真机 compile 阶段 configure 以 `/data/service/hnp/bin/bash` 运行，反复输出：
  - `shell-init: error retrieving current directory: getcwd: cannot access parent directories`
  - `job-working-directory: error retrieving current directory: getcwd: cannot access parent directories`
- 随后以 `configure: error: working directory cannot be determined` 终止，配方 `autotools.configure()` 报 Error 1。
- 同 head 后续 CI 轮次在 configure 与 make 阶段出现：
  - `/system/bin/sh: .../conanautotoolstoolchain.sh[13]: can't fork - try again`
  - `knowledge_check.sh: fork: retry: Resource temporarily unavailable`
  - `Making all in common` 处 `/bin/sh: can't fork - try again`
- 关键指纹：`working directory cannot be determined`、`getcwd: cannot access parent directories`、`can't fork - try again`、`Resource temporarily unavailable`。

## 根因
- 共享 `ohos-aarch64` profile 的 `[buildenv]` 导出 `CONFIG_SHELL=/data/service/hnp/bin/bash`，`SHELL` 同为 hnp bash。
- autoconf 生成的 `configure` 在 `CONFIG_SHELL` 非空时**无条件** `exec $CONFIG_SHELL`；该 hnp bash 在 HMDFS 构建树上 `getcwd()` 失败，触发 shell-init / job-working-directory 的 errno 风暴，最终判定工作目录不可确定而中止。属 profile/环境级问题，非 w-calc 源码或配方缺陷。
- 后续 `can't fork - try again` / `fork: retry: Resource temporarily unavailable` 是同一共享真机进程/线程表瞬时耗尽（EAGAIN），与配方无关；同机无关脚本亦出现同类 EAGAIN，可确认为环境资源抖动。

## 修复方案（rec）
1. 在 `archives/w/w-calc/2.5/conanfile.py` 的 `build()` 内新增 `_neutralize_config_shell()`，向生成的 `conanbuild.sh` 末尾追加：
   - `export CONFIG_SHELL=/bin/sh`
   - `export SHELL=/bin/sh`
   - 并导出 `PWD`，使 `pwd` 走逻辑路径而非触发 getcwd。
   `/bin/sh` 为 toybox sh，getcwd 正常，可消除 configure 中止。
2. 新增 `_configure_with_fork_retry()`：把 `autotools.configure()` 改为**有界重试**（最多 3 次，退避 15/30s）。仅当捕获输出命中 `can't fork` / `cannot fork` / `try again` / `resource temporarily unavailable` 才重试，其它错误首次即抛出；命令用 `load_toolchain_args(self.generators_folder)` 取回 AutotoolsToolchain 的 `configure_args`，保持与原先 `Autotools.configure()` 完全一致的参数，并将 configure 输出打印回 CI 日志。
3. 将重试抽成通用 `_run_with_fork_retry(label, cmd, log_path, cwd)`，新增 `_make_with_fork_retry()`：解析 `tools.gnu:make_program` 与 `conanbuild.conf` 的 `make_args`，追加 `-j1`；`build()` 的 `make` 与 `_run_upstream_checks()` 的 `make check` 均改走该重试，覆盖 fork 抖动从 configure 转移到 make 的情形。
4. 在 `archives/w/w-calc/2.5/notes.md` 记录问题 6（configure + make 两处同类根因与统一方案），同步 `.hmbs/pr-body.md` 草稿。
5. 真机 compile 门禁验证：原问题消失，门禁全部通过。

## 禁止策略
- 禁止在共享 ohos profile 下保留 `CONFIG_SHELL`/`SHELL` 指向 hnp bash 并在 HMDFS 工作目录上执行 autoconf configure（正则 `configure: error: working directory cannot be determined` 必须不再出现）。
- 禁止对 fork 抖动做无标记门控或无限重试；只允许在命中 fork 指纹时做有界重试，其它错误首次即抛出。

## 与相近条目的边界（查重）
- tnftpd 三元组/shim 条目：识别 target triple 与编译器 shim；本条目不涉及三元组识别，仅在 CONFIG_SHELL/SHELL 被置为 hnp bash 时命中。
- tta tmpdir/umask 条目：临时目录隔离与 umask；本条目不做 tmpdir 隔离，也不改 umask。
- E165 shebang 条目：脚本 shebang 解释器改写；本条目改写的是 profile 导出的 CONFIG_SHELL/SHELL 环境变量，而非脚本首行。
- 命中条件严格限定：CONFIG_SHELL/SHELL 被共享 profile 置为 hnp bash **且**工作目录位于 HMDFS。

## 适用判断
适用于所有走共享 ohos profile 的 autotools 配方（configure 由 `CONFIG_SHELL` 决定解释器），且构建树位于 HMDFS 的场景；对 fork 密集型 configure/make 步骤同样适用标记门控有界重试骨架。不泛化到三元组识别、tmpdir 隔离或 shebang 改写场景。
