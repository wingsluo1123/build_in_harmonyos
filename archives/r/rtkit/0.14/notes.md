# rtkit 0.14 — HarmonyOS PC (aarch64) 适配记录

- **上游**：https://gitlab.freedesktop.org/pipewire/rtkit/（v0.14）
- **构建系统**：Meson
- **产物类型**：application（3 个可执行程序 + D-Bus/polkit/systemd 集成文件）
- **依赖**：`dbus/1.14.10`、`libcap/2.69`（均为制品仓已发布二进制）
- **编译环境**：`conan create -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同左`
- **编译结果**：CONAN_CREATE PASSED，`rtkit/0.14:5aa31737c0d840740b8ed019523eab266b355474`

## 1. 选型说明

上游 GitHub 仓库 <https://github.com/heftig/rtkit> 已于 2025 年归档，最后版本为
0.13；项目现由 PipeWire 维护在 <https://gitlab.freedesktop.org/pipewire/rtkit/>。
本适配取现行 canonical 仓库的 **v0.14**，源码 URL 为官方 GitLab 归档地址
（非 fork / 非镜像）。

## 2. 关键适配点（4 项）

### 2.1 `dbus-1.pc` 别名

`rtkit` 的 `meson.build` 查找 `dependency('dbus-1')`，而制品仓的 `dbus/1.14.10`
配方未声明 `pkg_config_name`，`PkgConfigDeps` 因此只产出 `dbus.pc`：

```
../meson.build:25:11: ERROR: Dependency "dbus-1" not found (tried pkg-config and cmake)
```

配方 `generate()` 中在 `PkgConfigDeps.generate()` 之后把 `dbus.pc` 复制为
`dbus-1.pc`（安装目录变量已在 `project_options` 显式给出，故别名只需让依赖
可被发现）。该做法与 `accountsservice/26.27.3` 的 `_create_dbus_pc_alias` 同源。

### 2.2 libsystemd 关闭

OHOS 无 systemd，`<systemd/sd-daemon.h>` 不存在；以 `-Dlibsystemd=disabled`
关闭后，`sd_notify` 相关代码由 `HAVE_LIBSYSTEMD` 宏剔除。

### 2.3 安装路径锚定到包前缀

`dbus-1.pc` 中的 `system_bus_services_dir` / `interfaces_dir` 指向构建机绝对路径，
不覆盖会把 `.service`/`.xml` 装到包外并被 conan 丢弃。配方显式指定：

```
dbus_systemservicedir = share/dbus-1/system-services
dbus_interfacedir     = share/dbus-1/interfaces
dbus_rulesdir         = share/dbus-1/system.d
polkit_actiondir      = share/polkit-1/actions
systemd_systemunitdir = lib/systemd/system
```

### 2.4 OHOS ELF 签名（关键，否则真机无法执行）

鸿蒙内核对未签名的可执行文件直接返回 **EPERM**。实测未签名的产物：

```
$ <pkg>/libexec/rtkit-daemon --help
sh: <pkg>/libexec/rtkit-daemon: Operation not permitted
```

配方 `package()` 中（仅 `os == "OHOS"` 时）对 `bin/` 与 `libexec/` 下所有 ELF 执行
`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`。
签名后同一命令正常输出帮助（见 §4）。

### 2.5 锚定 meson 归档器（CI #93569 实测踩坑）

首次 CI（构建 #93569）在 `conan-build-test` 第 40 秒失败，日志：

```
../meson.build:1:0: ERROR: Unknown linker(s): [['llvm-ar']]
Running `llvm-ar --version` gave "[Errno 2] No such file or directory: 'llvm-ar'"
```

根因：Conan 的 `MesonToolchain` 只在 Android NDK 分支给 meson native file 写
`ar`，其余情况留空，meson 于是自行猜测归档器 —— clang 下猜出**裸名** `llvm-ar`
并按 `PATH` 查找。CI worker 的执行 PATH 只有
`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:~/.local/bin`，不含
`/data/service/hnp/bin`，查找失败。

> 该问题在本地**不会暴露**：本机交互 shell 的 PATH 恰好含 `/data/service/hnp/bin`，
> 故 `conan create` 一次通过。这正是"本地绿≠CI 绿"的典型场景。

修法：配方 `generate()` 中 `_pin_meson_archiver()` 用 profile 已提供的编译器目录
（`tools.build:compiler_executables.c`）推出归档器**绝对路径**（优先 `llvm-ar`，
回退 `ar`）写入 native file 的 `[binaries]`：

```ini
[binaries]
ar = '/data/service/hnp/bin/llvm-ar'
c = '/data/service/hnp/bin/clang'
cpp = '/data/service/hnp/bin/clang++'
```

验证：以 CI 同款精简 PATH 复现并重跑 `conan create` —— 归档器锚定生效、编译与
test_package 全部通过。

### 2.6 worker spawn 资源耗尽的退避重试（CI #93599 实测）

归档器问题修掉后，CI 第 2 轮（构建 #93599）失败签名变了：

```
../meson.build:1:0: ERROR: Unable to detect linker for compiler `/data/service/hnp/bin/clang -Wl,--version`
stderr: clang-15: error: unable to execute command: posix_spawn failed: Resource temporarily unavailable
clang-15: error: linker command failed with exit code 1
```

发生在 meson setup 的**第一次 clang 调用**（链接器探测），即 worker 的
fork/posix_spawn 资源临时耗尽（EAGAIN），属基建抖动（同包换 worker 常可过），
与配方无关。

配方侧加固（既有口径认可的两种之一）：`build()` 中 meson 调用改为
`_run_with_spawn_retry()`，**仅**对 EAGAIN 特征
（`Resource temporarily unavailable` / `posix_spawn failed` /
`unable to execute command` / `can't fork` / `Cannot allocate memory`）
做 30/60/120/180 秒退避重试；其余错误（真实编译/链接失败）首次即抛出，
不做盲目重试（R43）。

单元验证（三段）：命中 EAGAIN 时重试至成功；真实编译错误仅尝试 1 次即抛出；
重试预算耗尽时抛出并提示换 worker 重触发。

> **⚠️ 该实现实测无效，已在 §2.7 更正并重写**：它拿 `str(exc)` 去匹配 EAGAIN 签名，
> 而 conan 的 `ConanFile.run()` 失败时抛出的异常**不含子进程输出**（只有
> `Error 1 while executing`），故重试一次都不可能触发。CI #93688 即因此被 EAGAIN
> 直接打红。

### 2.7 EAGAIN 重试落地的两处修正（CI #93688 实测）

第 3 轮 CI（构建 #93688，PR #16067）失败签名又变了，并暴露了 §2.6 实现的硬缺陷：

```
rtkit/0.14: RUN: meson setup --native-file "…/conan_meson_native.ini" "…" "…" --prefix=/
/system/bin/sh: …/build-release/conan/conanbuildenv-release-armv8.sh[13]: can't fork - try again
ERROR: rtkit/0.14: Error in build() method, line 144
    self._run_with_spawn_retry(meson.configure, "meson setup")
while calling '_run_with_spawn_retry', line 171
    step()
    ConanException: Error 1 while executing
```

**根因（两条，第 1 条是本次红 CI 的直接原因）**：

1. **重试是死代码**。`ConanFile.run()` 在命令非零退出时只抛
   `ConanException("Error %d while executing" % retcode)` —— 子进程的
   stdout/stderr **不进异常消息**。§2.6 拿 `str(exc)` 匹配 EAGAIN 签名，一次都
   不可能命中，于是第 144 行那次调用原样抛出、构建直接红。
2. **worker fork 彻底枯竭**。这次连 conan 生成的 env 脚本都 fork 不动：该脚本
   （`conanbuildenv-release-armv8.sh`）要拼反注册脚本，每个变量都跑
   `value=$(printenv $v)`，而命令替换必须 fork。也就是 meson 根本没起来 —— 仍属
   基建抖动，与源码/配方逻辑无关。

**修法（均在配方 `build()` 一侧）**：

1. **改为按命令输出判定签名**：这一步经 `_log_run_output()` 临时替掉实例上的
   `run`（`Meson.configure()`/`build()` 内部调用 `self._conanfile.run(cmd)` 且
   不接受 stdout 参数），把该步命令的 stdout/stderr 落到 `conan-meson-setup.log` /
   `conan-meson-compile.log`，再按**日志内容**匹配 EAGAIN 签名（与 megactl / zrc 的
   `_run_logged` 同源）；重定向不是管道，退出码仍是命令本身的退出码。日志随后整段
   回显进 CI 日志，评审仍看得到全部编译输出与告警。
2. **setup 重试前清 meson 私有状态**：meson 以 `meson-private/coredata.dat` 判定
   "目录已配置"，中途失败的目录再跑 setup 会被拒绝（`--wipe` 又要求目录已配置），
   故重试前定向删除 `meson-private`/`meson-info`/`meson-logs`/`build.ninja`/
   `compile_commands.json`，保留 conan 的 `conan/` 生成器目录。
3. 签名表补齐 `cannot fork` / `fork: retry`（与既有的 7 项 EAGAIN 口径对齐）。

**验证**：

- **单元验证（5 段 18 断言）**：harness 复刻 conan 的真实语义（非零退出只抛
  `Error 1 while executing`、子进程输出只进调用方给的流），覆盖 ①回归护栏——异常
  消息确实不含任何签名，旧实现必然漏判；②输出含 EAGAIN → 第 2 次尝试成功，
  `on_retry` 恰好 1 次，成功日志被回显；③真实编译错误 → 只尝试 1 次即抛出，
  不浪费轮次；④持续 EAGAIN → 尝试 5 次后抛出并提示换 worker；
  ⑤`_reset_meson_build_state` 只清 meson 产物、保留 `conan/`。全部 PASS。
- **本地 W3 复验**（CI 同款参数 `conan create … -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64
  --build=missing --build=rtkit/*`，并 `unset PYTHONPATH` 以免 meson 配方假通过）：
  `conan create` 通过，test_package 4/4 通过，`conan-meson-setup.log`（1884 B）与
  `conan-meson-compile.log`（791 B）按预期生成且内容已回显。

**评估过但本轮不做**：

- `-j1` 压 fork：本包 `meson compile` 实测为 `-j20`，但只有 8 个构建边（并行度远
  用不满）；且本次失败发生在 **setup** 阶段，`-j1` 对其无作用。改动需重写 conan
  拼好的命令串，收益不抵偏离风险。
- 锚定 `pkg-config`：本机 meson 日志实测 `Found pkg-config: YES
  (/data/service/hnp/bin/pkg-config)`，该工具的 PATH 查找正常，无需再锚（§2.5 的
  `ar` 是另一类失败）。

## 3. 上游测试回填（N/N′ = 1/1）

**口径更正（2026-10-16，评审 rule4 少报反馈）**：上一版申报 N/N′ = 0/0，与上游文件树
实测不符 —— 上游虽无自动化测试套件，但源码树内**确实存在 1 个测试用例程序**：

```bash
$ tar tzf rtkit-v0.14.tar.gz | grep -i test
rtkit-v0.14/rtkit-test.c          # 含 test 的文件恰好 1 个
```

| 清点口径 | 实测 | 是否计入 N |
| --- | --- | --- |
| 上游源码树含 test 的测试程序（`rtkit-test.c`） | **1** | ✅ **主 N = 1** |
| `meson.build` 中的 `test()` 调用 | 0 处（全文仅 `executable()` / `install_*` / `configure_file`） | ✗ |
| 源码树 `tests/` 目录 | 不存在 | ✗ |
| `*.test` / 测试脚本 / 测试数据 | 0 个 | ✗ |
| 上游 `.gitlab-ci.yml` | 仅 `meson setup` + `ninja` | ✗（CI 不跑测试） |

结论：上游**无自动化测试套件**（无 `test()` 注册、无 `tests/` 目录），但**有 1 个测试用例**，
故 **N = 1**，不取 0（此前按"无自动化套件→0"申报，属少报）。

**N′ = 1（真机实跑、原样执行）**：`rtkit-test` 由 `-Dinstalled_tests=true`（上游默认）安装到
`libexec/installed-tests/rtkit/rtkit-test`，本适配在鸿蒙真机上**原样执行**该二进制
（`device-test/run-device-test.sh` 第 3 步，未改动上游任何源码或用例内容），**rc=0**：

- 3 项 daemon 属性读取全部通过，且与 daemon 默认值逐字一致（`20` / `-15` / `200000 ns`）；
- 程序内 2 项提权调用（`MakeThreadHighPriority` / `MakeThreadRealtime`）返回 `I/O error`，
  属环境限制（无 polkit 授权服务、无 `CAP_SYS_NICE`），非实现缺陷 —— 见 §5.1/§5.2。

完整执行转录见 `reports/device-test.log`。

## 4. test_package 实测（4 组断言，PASSED）

`conan create` 内嵌执行 `test_package/test.sh`，输出：

```
== 1. daemon 可执行且报告版本 ==
✅ rtkit-daemon rtkit-daemon 0.14
== 2. daemon CLI 契约：D-Bus 服务选项齐备 ==
✅ rtkit-daemon 暴露 7 项关键选项
== 3. rtkitctl CLI 契约：控制命令齐备 ==
✅ rtkitctl 暴露 6 项控制命令
== 4. daemon root 特权契约 ==
✅ 非 root 被拒绝并退出 rc=1
✅ rtkit test_package 全部通过
```

> `test.sh` 不落任何临时文件（本沙箱 `/tmp` 只读），全部断言走 shell 变量。
> 第 4 条（非 root 拒绝启动）在 root 环境下按设计跳过，此时实际执行 3 条；
> 本机实测 uid=20020085，4 条全部执行。

## 5. 鸿蒙真机端到端消费用例（PASSED）

**设备**：HUAWEI MateBook Pro，HarmonyOS kernel 1.12.0，aarch64（本机即真机）。

**链路**：`rtkit 客户端库 (rtkit.c)` → **D-Bus 系统总线** → `rtkit-daemon` → 回包。

**复现方式**：先按 §5.3 准备 `RTKIT_PKG`（本配方 `conan create` 产物）与
`DBUS_DAEMON`（需自行构建）两个输入，再执行 `device-test/run-device-test.sh`
（资产随归档，见 `device-test/`）。脚本并非零外部依赖的“一键复现”。

> **该脚本的第 3 步就是上游测试用例 `rtkit-test` 的原样执行**（见 §3），因此本节同时是
> 上游用例 N′ = 1 的证据。**完整转录（含 `rtkit-test` 全部输出与 daemon 侧日志）见
> `reports/device-test.log`**；下方为同一份输出的节选：

```
== 1. 启动私有 D-Bus 系统总线 ==
✅ unix:abstract=rtkit-test-bus,guid=001878110834482c27b9fd436ad204af
== 2. 启动 rtkit-daemon 并注册 org.freedesktop.RealtimeKit1 ==
✅ daemon Running
== 3. 消费端：rtkit 客户端库经 D-Bus 读取 daemon 属性 ==
Max realtime priority is: 20
Failed to become high priority: I/O error
Failed to become realtime: I/O error
Min nice level is: -15
Rttime limit is: 200000 ns
before:
	SCHED_RESET_ON_FORK: no
	SCHED_OTHER with nice level: -10
after high priority:
	SCHED_RESET_ON_FORK: no
	SCHED_OTHER with nice level: -10
after realtime:
	SCHED_RESET_ON_FORK: no
	SCHED_OTHER with nice level: -10
== 4. 消费端：rtkitctl 控制命令（D-Bus 方法调用） ==
✅ rtkitctl --reset-known rc=0
✅ rtkitctl --reset-all rc=0
✅ rtkitctl --suspend rc=0
✅ rtkitctl --resume rc=0
== 5. 服务端证据：daemon 侧确实在处理请求 ==
rtkit-daemon[14254]: Supervising 0 threads of 0 processes of 1 users.
✅ rtkit 真机端到端测试全部通过
```

> 说明：转录中两行 `Failed to become ...` 出现在属性读取行之间，是 stdout 重定向到文件后的
> 块缓冲所致；`rtkit-test.c` 的实际执行顺序为「3 项属性读取 → `before` → 提权 → `after`」。
> `before` 显示的 `nice level: -10` 是本沙箱环境的**固有** nice 值（`nice` 与 `os.nice(0)`
> 均实测为 `-10`），非被测程序所致；`after` 两次读数与之相同，与两次提权返回 `I/O error` 自洽。

**证据闭环**：客户端读到的 `20 / -15 / 200000` 三项与 daemon 自身默认值逐字一致
（`rtkit-daemon --help`：`--max-realtime-priority (20)`、`--min-nice-level (-15)`、
`--rttime-usec-max (200000)`），且 daemon 侧日志同步出现 `Supervising ...`
状态行 —— 证明数值确实由运行中的 daemon 经总线返回，而非客户端本地常量。
`rtkitctl` 的 4 个控制命令全部 rc=0（总线不可达时实测会连接失败，构成反向对照）。

### 5.1 本沙箱的既有限制（已实测，非推断）

| 限制 | 实测证据 | 测试对策 |
| --- | --- | --- |
| 无 root（uid 20020085，`sudo` 不可用，user namespace 被 seccomp 拦截：`unshare` 返回 SIGSYS） | `rtkit-daemon` 非 root 直接 `Need to be run as root.` | `device-test/gate-shim.c`：**仅第一次** `getuid()` 返回 0，过 daemon 启动门禁；之后返回真实 uid |
| 本机无 D-Bus 总线守护进程 | 全盘无 `dbus-daemon`；制品仓 `dbus/1.14.10` 只含客户端库（`libdbus-1.a`） | 另行构建 `dbus-daemon` 作为测试基础设施（见 §5.3） |
| 本机 uid 无 passwd 条目 | `id` 报 `bad uid 20020085`；总线日志 `Could not get password database information for UID` → 握手被丢弃，客户端只见 `Did not receive a reply` | `device-test/passwd-shim.c`：合成 passwd 条目，不改动任何权限 |
| 无法设置 `SCHED_RR` | `sched_setscheduler(0, SCHED_RR, 10)` → `EPERM`；`RLIMIT_RTPRIO` 硬限 `(0, 0)` 且不可提升（`CapEff=0x2a`，无 `CAP_SYS_NICE`） | **不伪装**：本用例验证 D-Bus 服务端到端链路；特权提升按实际失败如实呈现（见 §5.2） |
| `/storage` 下无法 bind 路径套接字（EPERM） | `dbus-daemon ... unix:path=...` → `Failed to bind socket: Operation not permitted` | 总线改用**抽象套接字** `unix:abstract=rtkit-test-bus` |

> **重要说明（口径）**：`gate-shim` 只解除 daemon 自身的 root 门禁，**不赋予任何内核
> 能力**。因此本用例证明的是「服务端到端链路可用」，**不等于**「实时调度在真机上已生效」。
> 在同时具备 polkit 授权服务与 root / `CAP_SYS_NICE` 的标准 Linux 桌面上，同一条链路
> 会完成 `SCHED_RR` 提升；本机（HarmonyOS PC）无 polkit，故即使以 root 运行，
> 该授权步仍会失败（见 §5.2）。

### 5.2 特权提升的实测结果（如实呈现）

```
Failed to become high priority: I/O error
Failed to become realtime: I/O error
```

daemon 侧对应日志：

```
rtkit-daemon[...]: Warning: PolicyKit call failed: The name org.freedesktop.PolicyKit1
                   was not provided by any .service files
```

根因：`verify_polkit()` 在 `org.freedesktop.PolicyKit1` 无 owner 时即返回 `-ENOENT`
（rtkit-daemon.c:1322-1325），该失败发生在调度所需的**内核能力检查之前**，客户端因此
只看到 `-EIO`（`DBUS_ERROR_FAILED` → 客户端 default 分支）。也就是说，本次实测中
**内核能力相关分支从未被执行**；内核侧限制（`CapEff=0x2a` 无 `CAP_SYS_NICE`、
`RLIMIT_RTPRIO` 硬限 0/0、`sched_setscheduler` 直接 EPERM）是 §5.1 的独立实测结论，
与本条失败路径是两个独立事实。两点都与 rtkit 自身实现无关；D-Bus 调用本身已成功
送达 daemon 并被 daemon 正常解析与应答（这正是端到端链路成立的证据）。

### 5.3 测试基础设施的来源与构建（夹具，未随 PR 提交）

**复现前提**：`device-test/run-device-test.sh` 需外部提供两个输入 ——
`RTKIT_PKG`（已构建的 rtkit 包目录，由本配方 `conan create` 产出）与
`DBUS_DAEMON`（可执行的 dbus-daemon）。后者本机不存在，需按下述方式自行构建。

| 项 | 值 |
| --- | --- |
| 上游 | dbus 1.14.10（`https://dbus.freedesktop.org/releases/dbus/dbus-1.14.10.tar.xz`，sha256 `ba1f21d2bd9d339da2d4aa8780c09df32fea87998b73da24f49ab9df1e36a50f`） |
| 本地二进制 sha256 | `af6d24c8679dbf23ff41287bbaadb594c0559fd98f500b2bb0ed8b169975fc1d` |
| 版本自报 | `dbus-daemon --version` → `D-Bus Message Bus Daemon 1.14.10` |
| 构建方式 | 复用制品仓 `archives/d/dbus/1.14.10/conanfile.py`，共改三处：①`name` 改为 `dbusharness`（避免污染 `dbus/1.14.10` 的本地缓存修订）；②构建目标由 `dbus-1` 改为 `dbus-daemon`；③在 `cmake.configure()` 变量里显式补 `EXPAT_LIBRARIES` / `EXPAT_INCLUDE_DIR`（见下）。执行 `conan create -pr:h=ohos-aarch64 -pr:b=同左` |
| 构建前提 | 本机无总线守护进程；制品仓的 `dbus` 包只构建客户端库（`libdbus-1.a`），不含 daemon |

构建过程中发现的上游 CMake 问题（仅记录，便于复现）：

- `bus/CMakeLists.txt` 用 `${EXPAT_LIBRARIES}` / `${EXPAT_INCLUDE_DIR}` 链接 daemon，
  而 conan 的 CMakeDeps 只提供 `expat::expat` 目标、不设这两个变量 →
  `ld.lld: error: undefined symbol: XML_ParserCreate_MM` 等一串 expat 符号；
- 显式给出 `EXPAT_LIBRARIES=<expat 包>/lib/libexpat.so` 与 `EXPAT_INCLUDE_DIR` 后链接通过。

该临时配方仅用于测试取证，**不属于本次交付**（W2：一个 PR 只交付一个软件），
因此 `device-test/` 下随归档提供的是 rtkit 侧的夹具（两个 shim 源码 + 总线配置 +
一键脚本），dbus-daemon 本体需按上表自行构建。

## 6. 结论

- 编译：`conan create` 通过（OHOS aarch64 / clang 15 / musl）。
- 交付完整性：`test_package/`（含测试源）、`conanfile.py`、`conandata.yml`、
  `MANIFEST.yml`、`commands.json`、`manifest.yaml` 齐备。
- 真机验证：产物在 HarmonyOS PC 上实际执行；`rtkit` 的 D-Bus 服务端到端链路
  （客户端库 → 总线 → daemon → 回包）在真机上跑通。
- 上游测试：上游无自动化测试套件，但含 1 个测试程序 `rtkit-test.c` —— **N = 1 / N′ = 1**，
  已在鸿蒙真机上原样执行通过（rc=0）；上一版记 0/0 属少报，已更正（§3）。
- 已知限制：实时调度的**实际生效**需 root / `CAP_SYS_NICE`，**且需可用的 polkit
  授权服务**（`org.freedesktop.PolicyKit1`，rtkit 的授权动作由它裁决）。本机两者
  都不具备，故即使以 root 运行，该授权步仍会失败；详见 §5.1/§5.2。
---

**编译结束**: 2026-10-15 20:49
**最终状态**: built
