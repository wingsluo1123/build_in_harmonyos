# DRAFT-puf-1.0.0-config-status-tmpdir-sanity-fork-retry
> 旧版 Autotools 工程在 OHOS HMFS 上的系列兼容：config.status 临时目录迁出构建树（探针钉选可写 TMPDIR）+ AM_SANITY_CHECK mtime 误报降级 + fork/posix_spawn 资源压力重试

## 问题特征（真实日志片段/标记）

- 构建类型推断失败：`config.guess: unable to guess system type` / `configure: error: cannot guess build type`，日志同时出现 `UNAME_SYSTEM = HarmonyOS`。
- config.status 临时目录权限失败：`./config.status` 对 `./confstatXXXXXX/in`、`./confstatXXXXXX/out`、`./confstatXXXXXX/config.h` 全部 `Permission denied`，随后 `make` 报 `No targets specified and no makefile found`，`Package ... build failed (Error 2 at build() line 83 autotools.make)`。
- 构建环境健全性误报：`checking whether build environment is sane...` 之后 `newly created file is older than distributed files! Check your system clock` 硬中止 configure。
- 瞬态资源压力：`bash: fork: retry: Resource temporarily unavailable`；链接阶段 `clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable`。
- 平台能力标记：`HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","tmpdir":"/storage/Users/currentUser/preflight/.../tmp","jobs":1,"install_shim":true,"hardlink":0,"symlink":1,"chmod":0,"local_mktemp":1}`。
- 伴随噪音：大量 `job-working-directory: error retrieving current directory: getcwd: cannot access parent directories`。

## 根因

puf 1.0.0 归档内置 2005 版 Autotools 产物，在 OHOS 真机 HMFS/HMDFS 用户卷上暴露三类结构性不兼容，且相互独立、必须分别处理：

1. **构建类型无法推断**：内置 `config.guess` 不认识 HarmonyOS 的 `uname` 输出，configure 无法推断 build type；且旧 `config.sub` 不识别 `aarch64` CPU 与 `linux-ohos` OS。
2. **config.status 临时目录落在 HMFS 构建树**：生成的 `config.status` 硬编码在构建树内创建 `./confstatXXXXXX`（而非 `$TMPDIR`）。构建树位于 HMFS/HMDFS 用户卷 `/storage/Users/currentUser/preflight/...`，该文件系统上新建目录的属主/权限元数据不立即生效，导致紧接的重定向写 `in/out/config.h` 全 EACCES，Makefile 生成失败。该文件系统 `HMBS_CAP_CHMOD=0`（chmod 不受支持），因此对临时目录补 `chmod` 无法补救。
3. **AM_SANITY_CHECK mtime 误报**：这是建议性 mtime 比对——`sleep 1` 后创建 `conftest.file`，用 `ls -Lt` 断言其比 2005 年代旧的 `$srcdir/configure` 新；在 overlay/network/HMFS 类文件系统（延迟元数据 / 粗 mtime 粒度）或 `ls -Lt` 排序不可靠的主机上会误判并 `(exit 1)` 硬中止。
4. **瞬态 fork/posix_spawn 资源压力**：共享构建主机上 `fork()`/`posix_spawn` 间歇 EAGAIN。结构性差异在于 bash 会重试自己的 `fork()`，而 clang 不会重试 `posix_spawn` `ld.lld`，故仅延长 make 级重试窗口无法覆盖链接失败。

## 修复方案（rec）

1. **三元组 + config.sub 补丁（配套）**：配方 `generate()` 在 OHOS 时显式传 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`（附 armv8 守卫）跳过 `config.guess`；新增 `patches/0001-config.sub-ohos.patch` 让同版 `config.sub` 识别 `aarch64` CPU 与 `linux-ohos` OS，在 `conandata.yml` 声明补丁并加 `export_sources`/`apply_conandata_patches`。
2. **config.status 临时目录迁出构建树（核心）**：新增 `patches/0002-configure-confstat-tmpdir.patch`，把 heredoc 中的 `./confstatXXXXXX` 改为 `"${TMPDIR:-.}/confstatXXXXXX"`，使 config.status 使用配方钉选的 TMPDIR 而非 HMFS 构建树。
3. **探针钉选可写 TMPDIR**：配方 `build()` 前 `_pin_tmpdir()` 用「建目录→写→回读」探针把 `TMPDIR` 钉到可写非 HMFS 根（首选 `/data/storage/el2/base/cache`），以能力回读为准而非假定路径可写。
4. **AM_SANITY_CHECK 误报降级**：新增 `patches/0003-configure-sanity-check.patch`，把 `AM_SANITY_CHECK` 两支硬失败路径（`ls -t` 不可用、mtime 断言失败）降级为 WARNING 并继续，configure 不再被建议性守卫误中止。
5. **削减 fork 并做指纹化重试**：`generate()` 追加 `--disable-dependency-tracking` 去掉每个编译单元 `depcomp+mv` 子外壳；`_run_make_with_fork_retry()` / `_run_configure()` 把输出重定向到日志，**仅**在命中 fork 资源压力指纹（`fork: retry` / `Resource temporarily unavailable` / `cannot fork` / `posix_spawn` / `out of memory`）时退避后重跑 `-j1`，退避指数增长封顶（`min(5*2^(n-1),60)`，约 3.5 分钟），每次等待前 `gc.collect()`；真实编译错误立即原样上抛。
6. **链接 spawn 自身可重试**：新增 `_LINK_RETRY_WRAPPER`（POSIX sh）+ `_write_link_retry_wrapper()` / `_link_retry_make_arg()`，把 make 的 `CCLD` 覆写为 `'CCLD=$(SHELL) <build>/hmbs-link-retry.sh $(CC)'`（单引号让 make 展开 `$(SHELL)`/`$(CC)`，经 MAKEFLAGS 传播到 `src/`），wrapper 对链接命令循环多次重试，覆盖 clang 不重试 `posix_spawn` 的结构性缺口。
7. **test_package 防挂死**：`test.sh` 后台 HTTP server 由 `( ... ) &` 改为 `( ... && exec python ... ) >log 2>&1 </dev/null &` 并对子外壳重定向、`kill` 后补 `wait`，避免 mksh 下子外壳持有 `conan create | tee` 写端管道导致永不返回。

## 禁止策略

- 禁止用 `chmod 700 "$tmp"`（或任何对 confstat 目录的 chmod）修复 EACCES：HMFS/HMDFS 上 `HMBS_CAP_CHMOD=0`，chmod 本身不受支持，权限元数据不会因此恢复，修复轮会空转。正确做法是把临时目录迁出构建树并使用探针验证过的可写 TMPDIR。
- 禁止对真实编译/链接错误做重试：重试只在命中 fork/posix_spawn 资源压力指纹时触发，否则会掩盖真实缺陷、污染证据并拖入门禁超时。
- 禁止把 chmod/mktemp 能力缺失当作可通过补权限绕过的问题，必须以探针回读结果为准选择 TMPDIR。

## 与相近条目的边界（查重）

- 与 `DRAFT-ballandpaddle-0.9.0-autotools-config-guess`、`DRAFT-cronutils-1.0.0-autotools-configure`、`DRAFT-libyal-20200811-autotools-configure` 等既有 Autotools 条目均为「相邻但不相同」：它们覆盖单一症状（多为 config.guess/config.sub 三元组），本条目覆盖的是 **config.status 临时目录迁出 HMFS 构建树 + AM_SANITY_CHECK mtime 误报降级 + fork/posix_spawn 资源压力重试** 的组合内核，且明确记录 chmod 路线为何失败。
- 修复轮命中的既有经验（chmod 执行位、GLib/GStreamer 公共头链接等）均被经验判定 reject：puf 为纯 C 无 GLib/GStreamer 依赖，失败点是 HMFS 目录元数据滞后与 fork 压力，不是自有产物 chmod 问题。

## 适用判断

- 命中条件：上游归档内置旧版 Autotools（config.guess/config.sub/configure/config.status），在 OHOS HMFS/HMDFS 用户卷构建树内构建；日志出现 confstat 目录 `Permission denied`、`newly created file is older than distributed files`、`fork: retry` 或 `posix_spawn failed`。
- 不适用：已升级到新版 Autotools/config.sub 的上游；或构建树不在 HMFS/HMDFS 且 worker 无 fork 资源压力者。
- 处置顺序：先确认 `HMBS_PLATFORM_CAPABILITIES` 的 `chmod` 与 `tmpdir`，再落三元组补丁、confstat 迁出 + TMPDIR 探针、sanity 降级、指纹化重试与链接 wrapper，最后验证 test_package 不挂死。
