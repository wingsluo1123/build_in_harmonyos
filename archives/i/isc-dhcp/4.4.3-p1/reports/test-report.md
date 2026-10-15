# isc-dhcp 4.4.3-p1 测试报告

> **项目**: isc-dhcp 4.4.3-p1（ISC DHCP：dhcpd 服务器 / dhclient 客户端 / dhcrelay 中继 / omshell 管理工具；含 libdhcp/libomapi/libdhcpctl 三库与捆绑 BIND 9.11.36 静态闭包）
> **测试日期**: 2026-10-14
> **测试环境**: HarmonyOS PC，aarch64（OHOS clang 15.0.4，aarch64-linux-ohos；OHOS SDK，sysroot musl；conan 2.29.1，profile ohos-aarch64）
> **测试类型**: 上游 ATF 单元测试套件（`make check`，13 程序 / 56 用例）+ conan test_package 消费者测试（7 校验点）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游登记测试程序 | 13 | 100% |
| 上游登记用例 | 56 | 100% |
| 上游通过 (PASS) | 56 | 100% |
| 上游失败 (FAIL) | 0 | 0% |
| 上游跳过 (SKIP) | 0 | 0% |
| test_package 校验点 | 7 | 100% |
| test_package 通过 | 7 | 100% |

**核心功能通过率**: ✅ **100%（56/56 用例 + 7/7 校验点）**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过。** 上游 ATF 套件真机全量执行：common / client / relay / server 四个 tests 目录共 13 个测试程序、56 个用例全部通过（0 失败 0 跳过），`make check` 退出码 0；`conan create` 内 test_package 消费者测试 7 个校验点全部通过——`dhcpd`/`dhclient`/`dhcrelay` 三个守护程序与 `omshell` 在目标环境实跑（静态链接闭包加载执行），CMake 消费者链接随包三库 + 捆绑 BIND 四库并实调 OMAPI API。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 打包取件路径与应用前缀不匹配（CI 实证） | 包内缺 7 个关键产物，test_package 阶段 CMakeDeps 报错 | 🟡（已解决：`DESTDIR` 直装包目录 + 7 产物 fail-closed） |
| mksh 下 `type \| awk` 提取 atf-run 路径错位 | 全部上游测试被静默跳过（假绿） | 🟡（已解决：补丁 0008 改 POSIX `command -v`） |
| `make check` 无 ATF 接入时空转"假绿" | 测试可信度 | 🟡（已解决：`tests=True` 而无 atf_prefix 时配方直接拒绝） |
| atf-run 工作目录默认 `/tmp` 只读 | 工作目录创建失败 | 🟡（已解决：`ATF_WORKDIR` 指向可写目录） |
| E011/HMDFS、脚本直执行、config.guess/sub 等平台适配 | 构建期 | 🟡（已解决：8 个补丁 + 配方内 `MKDIR_P` 归一，见 notes.md） |

### 2.3 可用功能清单

```
✅ dhcpd / dhclient / dhcrelay : 包内实跑 --version 退出 0（可执行文件 + 三库 + BIND 闭包加载执行）
✅ omshell                     : 包内实跑退出 0
✅ OMAPI / dhcpctl API         : 消费者程序链接随包库并实调 omapi_init / dhcpctl_initialize / dhcpctl_connect
✅ 上游 ATF 套件               : 13 程序 / 56 用例全通过（-o tests=True + 环境侧 atf-0.19 启用）
⚠️ 真实 DHCP 报文交互          : 守护进程需绑定接口/开套接字/维护租约库，包测试环境不可提供
```

### 2.4 已知限制

1. `dhcpd`/`dhclient`/`dhcrelay` 为网络守护程序，真实流量验证不在包 CI 范围；验证口径 = 上游 ATF 套件（协议状态机与配置解析逻辑）+ 消费者侧加载与 API 实调双层覆盖。
2. 上游测试执行依赖环境侧外带 atf-0.19（OHOS 真机现编，非交付物）；CI 默认构建 `tests=False`，`test_package/MANIFEST.yml` 已如实申报 `upstream_test_in_build: false`。

---

## 三、测试详情

### 3.1 上游测试（`make check`：13 程序 / 56 用例全通过）

| 指标 | 实测值 |
|------|--------|
| 入口 | `make check`（经 `-o tests=True -c user.isc-dhcp:atf_prefix=$HOME/atf19` 配置 `--with-atf`） |
| 运行机制 | 生成的 `tests/unittest.sh` 逐目录调用 `atf-run`（`ATF_WORKDIR` 指向可写目录；atf-report 的 `/dev/stdout` 报告在 OHOS 沙箱被拒属显示层，判定以 atf-run 退出码为准） |
| 程序分布 | common 6 程序 25 用例 / client 1 程序 1 用例 / relay 1 程序 3 用例 / server 5 程序 27 用例 = **13 程序 / 56 用例** |
| 结果 | 四个 tests 目录 atf-run 退出码全 0；`make check` 退出码 0（逐用例原始输出随档 reports/atf-run-*.out；原始构建日志因体积未随档、本地留存） |
| 跳过 / 失败 | 0 / 0 |

### 3.2 test_package 消费者测试（7 校验点全通过）

| 校验点 | 内容 | 结果 |
|--------|------|------|
| `dhcpd --version` | 实跑退出 0 | ✅ PASS |
| `dhclient --version` | 实跑退出 0 | ✅ PASS |
| `dhcrelay --version` | 实跑退出 0 | ✅ PASS |
| `omshell` 加载运行 | 实跑退出 0（无 --version 旗标，加载运行即证） | ✅ PASS |
| 消费者链接 + `omapi_init()` / `dhcpctl_initialize()` | CMake 消费者链接随包 libdhcp/libomapi/libdhcpctl 与捆绑 BIND 闭包，两个 API 实际调用 | ✅ PASS |
| `dhcpctl_connect` 连接路径 | 无服务器环境下真实执行并回库错误串（路径确实运行） | ✅ PASS |

### 3.3 失败的测试

无。

### 3.4 跳过的测试

无（0 跳过。CI 默认构建不执行上游套件，属 `MANIFEST.yml` 如实申报的 `upstream_test_in_build: false` 口径，非跳过）。

---

## 四、关键问题分析

### 问题1: 打包取件路径与应用前缀不匹配（CI 实证）

**现象**：CI `conan create` 构建成功、打包成功，但 test_package 阶段 CMakeDeps 报
`Library 'dhcp' not found in package`——包内只有 4 个 BIND 归档，三个 DHCP 库与四个可执行文件全部缺失。

**根因分析**：`package()` 从硬编码的 `staging/usr/local` 取件，而 Conan `AutotoolsToolchain`
默认以 `--prefix=/` 配置（`--bindir/--sbindir=${prefix}/bin`、`--libdir=${prefix}/lib`），
`make install DESTDIR=<build>/staging` 实际落在 `staging/{bin,lib,include,etc}`；早期设备手工链
用的是默认 `/usr/local` 前缀，故未暴露。

**解决方案**：`package()` 改为直接 `make install DESTDIR=<package_folder>`（仓库 autotools
惯例：固定前缀 `/` 使安装直落 Conan 标准布局），并在打包后对 7 个关键产物
（4 可执行 + 3 库）做 fail-closed 检查——缺任一即报错，杜绝空安装静默出包。
`etc/` 配置样例整体归置 `res/isc-dhcp`（`tools.files.copy` 为复制非搬移，收尾用 `rmtree`）。

### 问题2: mksh 下 atf-run 定位错位致全部上游用例被静默跳过（假绿）

**现象**：`make check` 显示成功但零用例执行；`tests/unittest.sh` 内建的 `-x` 守卫判假，
整套 ATF 套件被跳过。

**根因分析**：脚本用 `type atf-run | awk '{print $3}'` 提取工具路径；OHOS 的 mksh 下
`type` 输出为 `atf-run is a tracked alias for <path>`，`$3` 取到单词 `a`，路径提取错位。

**解决方案**：补丁 0008 改用 POSIX `command -v`（bash/mksh/dash 输出一致）。配套在配方
层面做 fail-closed：`tests=True` 而未提供 `user.isc-dhcp:atf_prefix` 时 `validate()` 直接拒绝，
杜绝"不接 ATF 时 make check 只编译 libt_api.a 即返回成功"的空转假绿。

### 问题3: atf-run 工作目录 `/tmp` 只读

**现象**：`atf-run` 报 `mkdtemp(3) failed: Read-only file system`（`/tmp/atf-run.XXXXXX`）。

**根因分析**：atf-run 工作目录取 ATF 配置变量 `atf_workdir`（默认 `/tmp`，OHOS 上为只读挂载），
不读 `TMPDIR` 环境变量。

**解决方案**：配方在 `make check` 前置于 `ATF_WORKDIR=<可写目录>`（ATF 文档的环境覆盖名），
目录选择沿用仓库惯例 `_writable_tmpdir()`。另：`atf-report` 默认把报告写到 `-`（`/dev/stdout`），
OHOS 沙箱拒绝打开——属显示层问题（源码 `open_outfile()` 实锤），不修改；判定以 atf-run
退出码为准（`unittest.sh` 末尾 `exit $status`）。

### 问题4: 构建期平台适配（8 补丁摘要）

config.guess/config.sub 的 HarmonyOS/`*-linux-ohos` 三元组（顶层与捆绑 BIND 两处）、
configure 的 mktemp 探测 umask 077→022（E011：HMDFS 用户卷拒收 0700 目录）、bind/Makefile.in
的 `$(SHELL)` 前缀（OHOS 拒绝直接 exec 非签名解释器脚本），以及配方内 configure 后全树
`MKDIR_P` 归一并前置 `MKDIR_P='mkdir -p'`（toybox mkdir 被 autoconf 2.70+ 探测拒收所致）。
逐条根因与验证见 `notes.md`「遇到的问题与解决方案」。

---

## 五、测试环境

```
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -o tests=True \
    --build=missing --build="isc-dhcp/*" \
    -c user.isc-dhcp:atf_prefix=$HOME/atf19
# ---- 关键片段（路径前缀省略为 …/p） ----
$ ATF_WORKDIR='/storage/Users/currentUser/tmp' make check
# → common / client / relay / server 四目录 tests/unittest.sh 全通过，退出码 0
$ "…/p/bin/dhcpd" --version
isc-dhcpd-4.4.3-P1
$ echo | "…/p/bin/omshell"        （加载运行，退出 0）
$ "./test_package"
isc-dhcp consumer OK: omapi_init/dhcpctl_initialize ran; dhcpctl_connect to 127.0.0.1:1 reported: no more
RC=0

日志归档: 逐用例原始输出随档 reports/atf-run-*.out；原始构建/CI 日志（conan-create*.log、w3-local-ci.log）因 PR 体积控制未随档，本地留存
```

---

## 六、W3 本地模拟 CI（结果摘要）

设备侧按平台 CI 同款流程（`ci/conan/setup.sh` + `ci/conan/build_and_test.sh archives/i/isc-dhcp/4.4.3-p1`）运行，关键片段：

```
━━━ Build Summary ━━━
  Total:   1
  Success: 1
  Failed:  0
  Pass rate: 100.0% (1/1)
[step] All packages built and tested successfully ✅
W3_SETUP_RC=0
W3_RC=0
```

（门禁明细：L0/L1/L2/L5 全 pass；L1e 破坏性负向测试确认真实依赖；L4 补丁危险函数扫描 warn 非阻塞。原始日志 `w3-local-ci.log` 因 PR 体积控制未随档，本地留存。）

*报告生成时间: 2026-10-14*
