# DRAFT-truecrack-3.5-autotools-mktemp-dir-config-status-fallback

> autotools 配方在真机只读/不可写 TMPDIR 下 mktemp -d 生成坏目录导致 config.status 失败时回退到 autoconf mkdir fallback 的通用修复内核

## 问题特征（真实日志片段/标记）

真机 preflight 在 compile 阶段失败，日志含：

- `config.status: error: could not setup config files machinery`
- `./config.status[764]: can't create ./confCelGKD/subs1.awk: Permission denied`
- `./config.guess: line 1340: .../tmp/cg23045-14606/dummy.c: Permission denied`
- `configure: error: cannot guess build type; you must specify one`
- 海量 `getcwd: cannot access parent directories`

平台能力标记：

- `HMBS_CAP_LOCAL_MKTEMP=1` / `HMBS_AUTOCONF_MKTEMP_FALLBACK=1`
- `HMBS_PLATFORM_CAPABILITIES={"tmpdir":"/storage/Users/currentUser/preflight/.../tmp",...,"local_mktemp":1}`

## 根因

autoconf `AS_TMPDIR` 在 configure 中执行形如 `tmp=$(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null && test -d "$tmp"`：

1. 真机 HMFS 的 TMPDIR 只读/不可写，`mktemp -d` 生成的 0700 目录因 UID 映射 + setgid 对当前进程不可写；
2. 但目录存在使 `test -d` 通过，configure 误采用该坏目录，随后写 `subs1.awk` 时 `Permission denied`，最终 `config.status: error: could not setup config files machinery`。

叠加因素：

- 2009 版 `config.guess/config.sub` 无法识别 HarmonyOS，`cannot guess build type`；
- configure 阶段 `umask 077` 使生成的临时文件/SHELL 环境在真机上不可访问。

## 修复方案（rec）

1. 在 `generate()` 中创建 `mktemp` 包装脚本（`exit 1`），经独立 `hmbs_conf_env` 只注入 configure 步骤，触发 autoconf 的 mkdir fallback（`HMBS_AUTOCONF_MKTEMP_FALLBACK`）；make 与运行器保持 `env="conanbuild"` 不受影响。
2. `./configure` 显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`，绕过旧版 `config.guess` 无法识别 OHOS；与 anubis 配方同款方案（Conan OHOS 工具链提供实际 ABI）。
3. 修正 autoconf 生成 `config.status` 中的 `umask 077→022`，消除 0700 目录对当前进程不可写的根因。
4. 真机复跑全部门禁（configure → make → test_package）确认通过。

## 禁止策略

- 禁止忽略 `config.guess` 无法识别 OHOS 的直接失败（`cannot guess build type`、`dummy.c: Permission denied`）而只修后置 config.status 症状——必须显式 `--build/--host`。

## 与相近条目的边界（查重）

- 命中条目仅共享通用平台样板（`HMBS_PLATFORM_CAPABILITIES` / TMPDIR 只读）或相邻异因条目；
- 无一覆盖本任务真正内核：autoconf `mktemp -d` 生成 0700 坏目录→`test -d` 通过→`config.status` 失败，以及 `umask`/`config.guess` 跨库通用策略，具备强增量性。

## 适用判断

适用于：真机 HMFS 只读/不可写 TMPDIR 上运行 autotools/autoconf 配方的各类 C/C++ 库。

- configure 阶段 `umask 077→022` 修复：跨库通用；
- `config.guess` 无法识别 OHOS 三元组时显式 `--build/--host`：跨库通用 autotools 适配策略；
- `HMBS_AUTOCONF_MKTEMP_FALLBACK` mkdir 回退：可复用于同类 autotools 配方。
