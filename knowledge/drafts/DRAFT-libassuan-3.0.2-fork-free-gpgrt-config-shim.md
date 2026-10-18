# DRAFT-libassuan-3.0.2-fork-free-gpgrt-config-shim

> 受限设备上 fork 重型 config 辅助脚本（gpgrt-config 家族）引发进程表耗尽时：生成 fork-free shim（.pc 读版本）并预置 ac_cv_path 缓存跳过，辅以瞬时 posix_spawn EAGAIN 有界重试

## 问题特征（真实日志片段/标记）

- configure 阶段反复刷 `can't fork - try again`（实测单轮 46 次），随后 `config.status` 无法生成 Makefile，make 报 `make: *** No targets. Stop.`
- conan 生成的环境脚本 `conanautotoolsdeps.sh[13]: can't fork - try again`，同一构建 CI 自身 `knowledge_check.sh` 也报 `fork: retry: Resource temporarily unavailable`
- make 阶段首个目标 `src/mkheader` 报 `clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable`（瞬时 EAGAIN）
- 日志中 `checking for gpgrt-config...` 表明 configure 优先调用 fork 重型脚本

## 根因

- autotools 系 configure 优先探测并调用 fork 极重的 `gpgrt-config`（约 715 行、37 处 `$()` 子 shell）。受限设备/worker 进程表有限，连续 fork 触发 `can't fork - try again`，configure/make 全链路中断。
- libgpg-error 1.55 默认只安装 `gpgrt-config`，轻量回退脚本 `gpg-error-config` 需 `--enable-install-gpg-error-config` 才安装；本仓 libgpg-error/1.55 配方未传该开关，轻量路径缺失，fork 风暴不可绕过。
- 即便绕过 configure，make 阶段 clang 的 posix_spawn 仍可能受进程表瞬时 EAGAIN 影响，需目标级有界重试兜底。
- 约束：R37 门禁要求 conanfile.py/conandata.yml 与已发布 recipe 逐字节一致，修复只能落在 patches/ 源补丁与 notes.md（patches/ 内容不在 R37 比较范围内）。

## 修复方案（rec）（编号步骤，含具体文件与命令）

1. `patches/0001-tests-fdpassing-socket-ohos.patch`：在 configure 顶部解析 `--with-libgpg-error-prefix`。
2. 当 `<prefix>/bin/gpg-error-config` 不存在时，从依赖的 `gpg-error.pc` 读取版本（shell 内建 `read`，不 fork），在设备本地 build 目录生成 fork-free `gpg-error-config` shim。
3. 预置并导出 `GPG_ERROR_CONFIG` / `ac_cv_path_GPG_ERROR_CONFIG` / `ac_cv_path_GPGRT_CONFIG=no`，令 `AC_PATH_PROG` 命中缓存 `no`，回退轻量路径，gpgrt-config 零调用。
4. 对 `src/mkheader` 等首个 make 目标，仅当 stderr 含 `Resource temporarily unavailable`（瞬时 posix_spawn EAGAIN 签名）时，有界重试单条 compile+link 命令（不无界重试）。
5. 验证：以 `patch_ng strip=0`（Conan 同款）在干净官方 tarball 上套用补丁，本地跑 configure 确认 `checking for gpgrt-config... (cached) no`、`GPG Error - version >= 1.17... yes (1.55)`、gpgrt-config 零调用、make 正常。
6. 同步更新 notes.md 记录根因与上一轮为何无效；保持未提交等待真机预检。

## 禁止策略

- 禁止在日志仍出现 `can't fork - try again` / `fork: retry: Resource temporarily unavailable` 时，以「worker 进程表耗尽、纯环境/基础设施问题」为由零改动跳过（recipe 被 R37 冻结时，修复应落在 patches/ 源补丁）。
- 禁止仅靠无界/无条件重试掩盖瞬时 EAGAIN；重试必须有界且仅在含瞬时 spawn 签名时触发。
- 禁止为绕开 fork 风暴改动 R37 冻结的 conanfile.py/conandata.yml（与已发布 recipe 必须逐字节一致）。

## 与相近条目的边界（查重）

- DRAFT-13532 / DRAFT-14257 / DRAFT-14257-clang15 / DRAFT-13649：本任务修复轮命中的既有条目，覆盖 configure/getcwd 或 clang 编译等相邻异因，均不覆盖「fork 风暴 → fork-free shim」内核。
- DRAFT-8958（coreutils 遮蔽 install/mkdir EPERM）：本任务前序轮次命中，属 PATH 遮蔽问题，与 fork 风暴异因。
- DRAFT-darts-0.32-shell_getcwd（classads/darts getcwd/PWD 回退）：与本任务 getcwd/PWD 环节同源，但本条目聚焦 fork 风暴新内核，相邻但不相同。

## 适用判断

- GnuPG 家族 autotools 系库（libassuan/libgpg-error/gpgme/gnupg/pinentry 等）在受限设备/worker 上的 configure 与 make 阶段。
- 触发特征：fork 重型 config 辅助脚本（gpgrt-config 家族）在进程表受限时反复 `can't fork - try again`，且 make 阶段伴随瞬时 posix_spawn EAGAIN。
- 适用前提：依赖方提供 .pc 文件可供 shim 读版本，且修复可落在 patches/ 源补丁（recipe 被 R37 冻结时尤其关键）。
