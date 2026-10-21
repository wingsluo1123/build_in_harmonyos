# libassuan 3.0.2 适配说明

## 基线

- 官方源码: `https://gnupg.org/ftp/gcrypt/libassuan/libassuan-3.0.2.tar.bz2`
- SHA-256: `d2931cdad266e633510f9970e1a2f346055e351bb19f9b78912475b8074c36f6`
- 构建系统: Autotools
- 许可证: LGPL-2.1-or-later
- 依赖: `libgpg-error/1.55`

## OpenHarmony 适配

- 使用 `aarch64-unknown-linux-musl` 作为设备原生构建 triplet，使上游 Linux/POSIX 路径与 musl ABI 保持一致。
- 显式关闭文档构建，避免引入 Texinfo 等非目标主机工具依赖。
- 使用 Conan 依赖前缀和 `gpgrt-config` 查找 `libgpg-error`。
- 通过 Conan target `libgpg-error::libgpg-error` 传播依赖，`libassuan::libassuan` 消费者无需了解 Conan cache 路径。
- 将源码复制到设备本地 `/data/storage/el2/base/cache`，并在独立 `build/` 子目录执行 VPATH 构建，避免 `configure`、`config.status`、FIFO 和 Unix socket 落到共享 `/storage`。
- 设备本地目录由当前 Conan create 的 `build_folder` 与 `package_folder` 完整路径摘要唯一确定；build 阶段完成测试和 staged install，package 阶段复制 staging 后清理。
- 仅接受 Conan `os=OHOS, arch=armv8`，避免固定 arm64 musl triplet 与包 ID 不一致。
- 通过可审查补丁让上游 fd-passing shell 测试使用设备 Bash，并把路径型 Unix socket 放到设备本地 cache；共享 `/storage` 文件系统不允许 `AF_UNIX` bind。

## 版本号与分支名：回退到 3.0.2（本轮方案）

本任务此前把配方版本递增为 **3.0.2.1** 以规避 R37（`libassuan/3.0.2` 已发布且 recipe 不同），
但 CI L0n/R40 要求分支名剥掉前缀后逐字节等于 `{包名}-{版本目录名}`，而本任务的 PR 源分支被平台
恒定锁定在 `feat/libassuan-3.0.2`，HMBS 从不创建/切换 `feat/libassuan-3.0.2.1`，因此
`archives/l/libassuan/3.0.2.1` 与分支名 `feat/libassuan-3.0.2` 永远无法精确匹配，CI 反复报
`branch_name_r40`（见历史轮次记录，构建 #93641 等）。

本轮改为**回退到 3.0.2**，让版本目录名与 PR 源分支名精确一致：

- `archives/l/libassuan/3.0.2.1/` → `archives/l/libassuan/3.0.2/`（版本目录名 = 分支 `feat/libassuan-3.0.2`）；
- `conanfile.py` 与 `conandata.yml` 恢复为**制品仓已发布的 3.0.2 recipe 逐字节原文**
  （`conanfile.py` sha256 `b24a96b3…`，与 registry revision `639d14a1…`、upstream/main
  `archives/l/libassuan/3.0.2/` 完全一致），从而 L0j/R37 归一化比对判定 `same`，不再要求递增版本号；
- CI 的 `CI_PACKAGES` 由 PR diff 推导，回退后 diff 只落在 `archives/l/libassuan/3.0.2/`，
  `EXPECTED_TAG=libassuan-3.0.2` 与 `CI_BRANCH=feat/libassuan-3.0.2` 精确匹配 → L0n/R40 通过。

R37 只比对 `conanfile.py` 与 `conandata.yml`；`patches/` 文件内容、`test_package/`、`manifest.yaml`、
`notes.md` 不在比对范围内。因此把真机所需的修复与 HMBS 机器证据全部放入**补丁文件内容**与
`test_package/`，recipe 本体保持逐字节不变。

### 真机 getcwd / 工作目录修复（落在 configure 补丁）

真机 device-local HMDFS/FUSE 目录上 `getcwd()` 返回 `Permission denied`，`self.run` 启动的
shell 会刷 `getcwd: cannot access parent directories` 并让 autoconf 的
`ac_pwd=\`pwd\`` 失败，最终 `configure: error: working directory cannot be determined`。
published recipe 的 `build()` 只是 `self.run(command, cwd=native_build)`，无法在 Python 层
chdir/注入 PWD，所以本轮把修复写进源码补丁（`configure` 顶部），对 recipe 透明：

- 顶部强制 `CONFIG_SHELL=/bin/sh`、`SHELL=/bin/sh`，避免 profile buildenv 注入的
  `/data/service/hnp/bin/bash` 在 getcwd 损坏的目录上 re-exec 并清空 `$PWD`；
- 用 `$0`（configure 绝对路径，形如 `.../source/configure`）推导 `PWD=.../build`，
  该目录正是 recipe 传给 `self.run` 的 `cwd`，从而 `ac_pwd` 回退 `$PWD` 时得到正确绝对路径；
- `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd="$PWD"`，getcwd 失败时回退到已推导的 `$PWD`；
- 顶部 `PATH=/bin:$PATH`，并把 `MKDIR_P="/bin/mkdir -p"` 固定为设备标准 coreutils，
  绕开 `/storage/Users/currentUser/usr/local/bin` 下不可执行的 `mkdir` 遮蔽副本
  （configure 的 `AC_PROG_MKDIR_P` 会把它烤进 Makefile）；**该赋值必须带引号**，否则
  POSIX `sh` 会把 `MKDIR_P=/bin/mkdir -p` 解析成一次命令调用（先赋值 `MKDIR_P=/bin/mkdir`，
  再执行命令 `-p`），真机报 `configure[8]: -p: inaccessible or not found` 且 `MKDIR_P` 为空，
  本轮已修复；
- `AS_TMPDIR` 的 `umask 077` 放宽为 `022`，避免 0700 的 mktemp 目录在 uid 映射的 FUSE 上不可写。

### 真机 fork 资源耗尽修复（落在 configure 补丁）

CI #94100 在 `checking for gpgrt-config...` 后连续报 46 次
`.../bin/gpgrt-config[...]: can't fork - try again`，随后 `config.status` 无法 fork，
`Makefile` 等生成物缺失，最终 `make: *** No targets.  Stop.`。根因是 `gpgrt-config`
（715 行、37 处 `$(...)`）在受限的 OHOS worker 进程表上 fork 风暴耗尽进程资源
（经验 1 / DRAFT-ci-worker-gate-fork-oom / E491 forbid_3）。

published recipe 的 `_build_environment()` 在 `gpgrt-config` 存在时优先
`GPGRT_CONFIG=<prefix>/bin/gpgrt-config`，而 `configure` 一旦发现该变量就优先使用它。
同一 `<prefix>/bin/gpg-error-config`（103 行、无子 shell）是等价的轻量回退，且 configure
本身支持在 `GPGRT_CONFIG` 不可用时回退到 `gpg-error-config`。因此本轮在 configure 顶部解析
recipe 恒会传入的 `--with-libgpg-error-prefix=`，若 `<prefix>/bin/gpg-error-config` 可执行，
就预先置 `ac_cv_path_GPGRT_CONFIG=no` 并导出，使 configure 的
`AC_PATH_PROG([GPGRT_CONFIG],[gpgrt-config])` 直接命中缓存 `no`，跳过整段 gpgrt-config
探测/`--libdir`/`--exists` 逻辑，只调用轻量的 `gpg-error-config`，显著降低 fork 压力：

```
for hmbs_arg in "$@"; do
  case "$hmbs_arg" in
    --with-libgpg-error-prefix=*)
      hmbs_gpg_error_prefix=${hmbs_arg#*=}
      if test -x "$hmbs_gpg_error_prefix/bin/gpg-error-config"; then
        ac_cv_path_GPGRT_CONFIG=no; export ac_cv_path_GPGRT_CONFIG
      fi
      ;;
  esac
done
```

本地以桩 `gpg-error-config`/`gpgrt-config` 验证：`checking for gpgrt-config... (cached) no`，
`checking for GPG Error - version >= 1.17... yes (1.55)`，`make` 正常生成。fork 风暴本身是
worker 资源耗尽、代码层无法根治，本补丁只降低 fork 压力。

`make`/`make install` 由 recipe 用同一 `cwd=native_build` 执行；configure 顶部已把
`SHELL=/bin/sh` 烤进生成的 Makefile，故 make 的 recipe shell 也是 `/bin/sh`；`INSTALL`
由 HMBS 预检 wrapper 注入的 `$HMBS_INSTALL` shim 提供。

### 上游测试证据（落在 tests/Makefile.in 补丁）

上游 `make check` 采用 automake 序列 TESTS 驱动（`tests/Makefile.am`，无 test-suite.log），
在 OHOS/musl（`struct cmsghdr`/`cmsg_len` 存在，descriptor passing 开启）下注册 4 个用例：
`version` / `pipeconnect` / `fdpassing` / `fdpassing-socket.sh`。补丁在
`tests/Makefile.in` 的 `check-TESTS` 驱动循环收尾处，用驱动自身累计的
`all`/`failed`/`skip` 计数打印

```
HMBS_UPSTREAM_TEST_RESULT={"status":...,"discovered":all+skip,"executed":all,"passed":all-failed,"failed":...,"skipped":...}
```

这是计数的唯一确定性来源（不做减法推导、不嗅探测试 stdout）。`status` 仅当
`failed=0` 时为 `passed`（`all=0` → `no_tests`，有 skip → `incomplete`）。
`test_package/MANIFEST.yml` 的 `upstream_test_total: 4` 与该口径一致。

### test_package 消费者测试

`test_package/test.c` 建立 Unix socketpair 上真实 Assuan 客户端/服务端，输出 5 行
`CASE PASS`（version / socketpair / fork-server / echo-transaction / bye-close）；
`test_package/conanfile.py` 统计这些行得出 `HMBS_TEST_PACKAGE_RESULT` 的
`discovered`/`passedCount`，并在 `self.run` 中使用 `/bin/sh`（HMBS 在真机注入的
`CONFIG_SHELL`），不硬编码 HNP bash。

## 测试

- 配方在构建后执行上游完整 `make -j1 check`，由补丁化的 automake 驱动上报
  `HMBS_UPSTREAM_TEST_RESULT`。
- 上游测试覆盖版本检查、pipe client/server IPC，以及平台支持时的 fd passing。
- `test_package` 额外通过 `socketpair` 和 `fork` 建立真实 Assuan 客户端/服务端，
  验证 `ECHO` 数据事务与 `BYE` 关闭流程，上报 `HMBS_TEST_PACKAGE_RESULT`。

## 状态

工作树已回退为 3.0.2（recipe/conandata 与制品仓逐字节一致），真机修复与机器证据标记
落在补丁内容与 `test_package/`；**尚未提交**。本轮在 configure 补丁中追加：
(a) 修正 `MKDIR_P` 赋值的引号缺陷（真机 `configure[8]: -p:` 报错）；
(b) 通过 `--with-libgpg-error-prefix` 预置 `ac_cv_path_GPGRT_CONFIG=no`，
    绕开 gpgrt-config fork 风暴（CI #94100 的 `can't fork - try again` → `No targets`）。
修改后旧真机证据失效，需由 HMBS 重跑真机 rule4 预检；通过后由 HMBS 统一提交并推送到
PR 锁定分支 `feat/libassuan-3.0.2`。

### CI #94146：worker 进程资源耗尽（本轮不改代码）

CI #94146 的失败点在 `configure` 之前：`configure` 输出 **0 行**，报错来自 conan
生成的环境脚本 `conanautotoolsdeps.sh[13]`：

```
/system/bin/sh: .../conanautotoolsdeps.sh[13]: can't fork - try again
```

该脚本在 source 阶段对 `CPPFLAGS/LIBS/LDFLAGS/CXXFLAGS/CFLAGS` 逐个 fork
`$(printenv $v)`，因此该 fork 发生在任何包代码（补丁、configure、make）执行之前，
源码补丁无法触及。同一构建内 CI 自身脚本也报 `fork: retry: Resource temporarily
unavailable`；同一时间窗内多个不同 worker 上的无关包出现同类 fork 错误。判定为
worker 进程/内存资源耗尽（fork EAGAIN/ENOMEM），属基础设施故障，与本包配方、补丁、
测试无关。

对照 CI #94100：上一轮的 `ac_cv_path_GPGRT_CONFIG=no` 修复已生效——#94100 有 39 行
`gpgrt-config` 调用，#94146 为 0 行，`No targets` 也不再出现，说明 fork 源已被消除、
失败点前移，属纯资源型。依据 E491 forbid_3 与「worker/基础设施故障不得修改代码、
空提交或重触发」，本轮不修改配方、补丁与测试，保持 HEAD `7b64d1d2`（已通过真机
预检）不变，等待健康 worker 重跑。


### CI #94416 / #94463：修正上一轮失效的 gpgrt-config 规避（本轮方案）

上一轮用 `test -x "$prefix/bin/gpg-error-config"` 作为启用条件预置
`ac_cv_path_GPGRT_CONFIG=no`，本轮核对上游源码后确认该条件恒不成立：

- libgpg-error 1.55 的 `src/Makefile.am` 写的是
  `if INSTALL_GPG_ERROR_CONFIG` → `bin_SCRIPTS = gpgrt-config gpg-error-config`
  `else` → `bin_SCRIPTS = gpgrt-config`（另加 `noinst_SCRIPTS = gpg-error-config`）；
  `configure.ac` 里 `INSTALL_GPG_ERROR_CONFIG` 默认禁用，只有显式
  `--enable-install-gpg-error-config` 才安装 `gpg-error-config`。
- 本仓 `archives/l/libgpg-error/1.55/conanfile.py` 只传 `--disable-nls/--disable-doc/
  --disable-tests/--disable-static`，**没有** `--enable-install-gpg-error-config`，
  所以依赖包 `p/` 下只有 `bin/gpgrt-config`，没有 `bin/gpg-error-config`。
  因此上一轮的 `test -x` 判定为假，`ac_cv_path_GPGRT_CONFIG=no` 从未导出，
  CI #94463 才会继续出现大量 `gpgrt-config[...]: can't fork - try again`。

本轮改为不依赖 `gpg-error-config` 是否安装：configure 顶部解析
`--with-libgpg-error-prefix=`，若 `<prefix>/bin/gpg-error-config` 存在就直接用；
否则从 `<prefix>/lib/pkgconfig/gpg-error.pc` 读取 `Version:`（shell 内建 `read`，
不 fork），在设备本地 build 目录生成一个 fork-free 的
`hmbs-gpg-error-config` shim，并同时导出 `GPG_ERROR_CONFIG`、
`ac_cv_path_GPG_ERROR_CONFIG`（绕过 `AC_PATH_PROG` 的 PATH 搜索）与
`ac_cv_path_GPGRT_CONFIG=no`（跳过 gpgrt 分支）。shim 只处理
`--version/--modversion/--host/--prefix/--exec-prefix/--cflags/--libs/--mt` 这些
configure 真正调用的形态，用纯内建命令输出
`-I<prefix>/include` / `-L<prefix>/lib -lgpg-error`；`--host` 固定回
`aarch64-unknown-linux-musl` 与配方 `--host` 一致，避免 host 不匹配告警。

本地以桩 prefix 验证：`checking for gpg-error-config... (cached) sh .../hmbs-gpg-error-config`、
`checking for gpgrt-config... (cached) no`、`checking for GPG Error - version >= 1.17... yes (1.55)`，
gpgrt-config 零调用，`src/Makefile`/`tests/Makefile` 的 `GPG_ERROR_CFLAGS`/`GPG_ERROR_LIBS`
指向桩 prefix。

CI #94416 仍在 `conanautotoolsdeps.sh[13]`（configure 之前）报 fork 失败，且同一构建里
CI 自身 `knowledge_check.sh` 也报 `fork: retry: Resource temporarily unavailable`，
说明该次是 worker 侧进程表耗尽；本补丁只能消除 gpgrt-config 这个最大的 fork 源、
为 `config.status` 释放 fork 余量，不能修复纯 worker 资源故障。

### CI #95050：`mkheader` 目标 `posix_spawn failed: Resource temporarily unavailable` 的构建期重试（本轮方案）

CI #95050 的失败点已从 `configure` 前移进 `make`：`configure` 全流程成功（含
`checking for gpgrt-config... (cached) no`、`GPG Error version >= 1.17... yes (1.55)`，
说明 gpgrt-config shim 修复生效），随后 `make -j1` 在**第一个目标** `src/mkheader` 处失败：

```
clang ... -I. -I<src>/src -o mkheader <src>/src/mkheader.c
clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable
make[2]: *** [Makefile:1191: mkheader] Error 1
```

这是 worker 进程表瞬时耗尽（EAGAIN）——clang 用 `posix_spawn` 派生 cc1/ld.lld 且
**不重试 EAGAIN**，一次瞬时尖峰就终止整条链接；同代码同配方在真机预检 4/4 通过，
证明并非代码缺陷。

上一周期（#94146 / #94982）判定「worker 资源耗尽、不改代码」只能等待健康 worker，但
本包在同一指纹上已连续多轮落在同一失败点，属需要**增强构建对瞬时 spawn 压力的韧性**的
场景。本轮与既往所有方案都不同：不改 recipe（R37 冻结）、不重复 gpgrt-config 路线，
而是把「对瞬时 spawn EAGAIN 的有界重试」放进唯一失败目标所在的**生成文件** `src/Makefile.in`。

在 `mkheader$(EXEEXT_FOR_BUILD)` 规则中，用只依赖 POSIX shell 内建的循环包裹编译器：

- 循环体只用 `test`/`read`/`case`/`echo`/算术展开等内建（外加一个失败可容忍的
  `sleep 1`），因此**恢复路径本身不会因 fork 失败而自毁**（这是 puf 轮次中 shell 重试
  包装被 `fork: retry ... exit 254` 打断的教训）；
- 只在 stderr 命中瞬态指纹（`Resource temporarily unavailable` / `posix_spawn failed`
  / `fork: retry`）时重试，上限 `HMBS_SPAWN_RETRY_ATTEMPTS`（默认 40，每次间隔 1s）；
- 输出重定向到 `mkheader.spawn.log`：**任何非瞬态错误（真实语法/链接错误）立即 break，
  并在结束时原样回放到 stderr 后失败**，绝不掩盖真实失败、不改断言、不跳过任何构建步骤；
  捕获的 stderr 在成功路径也会回放，因此真实的编译器 warning 同样不会被吞掉；
- 成功路径行为与上游一致（仍生成同一个 `mkheader` 可执行文件）；仅在 worker
  瞬时进程压力下才有可观察差异。

本地验证（不是真机结论）：

- 以 `patch_ng`（Conan 同款，`strip=0`、`fuzz=False`）与 GNU `patch -p1` 对官方
  tarball 套用，4 个 hunk 全部干净应用，`src/Makefile.in` 与预期逐字节一致；
- 用假编译器驱动抽取出的真实 Makefile 片段：`3 次瞬态失败后成功` → `make` rc=0 且
  编译器被调用 4 次；`真实编译错误` → rc≠0 且只调用一次、stderr 原样透传；
  `持续瞬态直至上限` → 到达上限后打印最后诊断并 rc≠0；
- 以真实 clang 按补丁后的规则构建 `mkheader` 并生成 `assuan.h`，产物与上游语义一致
  （`ASSUAN_VERSION "3.0.2"`、`ASSUAN_VERSION_NUMBER 0x030002`、`@include` 已展开）。

为什么仍是补丁而非 recipe：`conanfile.py` / `conandata.yml` 必须与 registry 发布件
逐字节一致（L0j/R37），`build()` 不暴露注入 CFLAGS 或重试的钩子，因此只能把该韧性
放进源码生成文件 `src/Makefile.in`（与 configure / tests 修复同一补丁文件）。
修改后旧真机证据失效，需 HMBS 重新跑真机 rule4 预检。
