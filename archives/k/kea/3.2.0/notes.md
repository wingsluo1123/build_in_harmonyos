# kea 3.2.0 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起整树迁移至 Meson；顶层单工程 `meson.build`）
- 编译日期: 2026-10-04（真机全量构建 + 全树上游测试 + test_package）
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26，aarch64-linux-ohos，libc++，C++17）
- 设备: OHOS PC 真机（20 核 aarch64），Conan 2.29.1
- 工作副本: PC 侧 scratch worktree（分支 `feat/kea-3.2.0`，基线 `origin/main`）；
  设备侧 `~/bih/archives/k/kea/3.2.0`（真机跑测入口）
- 状态: built

## 定位与家族复用

kea 是 Kea 家族的**伞形包**：同一源码树（`kea-3.2.0.tar.xz`）的"整机产品面"——
5 个可执行文件、全部 `libkea-*` 运行库、全部内置 hook 插件与公共头文件。
已归档的家族包各覆盖一个子面：`kea-hooks` 只打包 callout 框架库，
`kea-perfdhcp` 只打包压测客户端；两者都不含守护进程，本包是第一个整树面。

3.2.0 上游变化：`kea-ctrl-agent` 已被上游移除（发行 ChangeLog），二进制集因此为
`kea-dhcp4` / `kea-dhcp6` / `kea-dhcp-ddns`（源自 `src/bin/d2`）/ `kea-lfc` /
`perfdhcp` 五个。

配方机制逐字复用家族（`kea-hook-ha` 3.0.3 底版）：
- `sh "{}"` 包裹 meson 调用——OHOS 拒绝直接 exec shebang 脚本（meson 包的
  `bin/meson` 是 Python shebang 包装脚本），经由 `/bin/sh` 启动；
- `_materialize_sonames()`：OHOS 全盘 symlink EPERM，`libX.so.N` soname 以
  真实拷贝落盘；
- package() 的 symlink→拷贝回退 + 0 字节自愈（最多 3 次 → `ConanException`）；
- `MesonToolchain` + `PkgConfigDeps`、`tc.binaries` 注入 `ar/ranlib` 绝对路径、
  `LD_LIBRARY_PATH` Environment（配置期 `cpp.run()` 探针）、
  `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`。

## 行为与测试面特点

- 全树 Meson 书写 **105** 处 `test()`（`src/lib/log/tests` 1 处 foreach 展开为
  7 项），19 处条件不注册（mysql 4 / pgsql 4 / netconf 6 / krb5·gss-tsig 2，
  另 OHOS 无 sudo 致 3 处 sudo-* 套件不注册）→ 真机实测**注册 92 个套件**
  （66 个 gtest 套件 + 26 个脚本套件，`meson-info/intro-tests.json` 实测计数）；
  源码 `TEST_F 10741 + TEST 1538 + TEST_P 2 = 12281` 宏（列首锚定
  `^TEST(_F|_P)?`，src/**.cc+.h；含 38 处 `DISABLED_` 前缀定义）。
- 本包适配整棵树，故**不设套件过滤**：`build()` 内
  `meson test -v --timeout-multiplier 4` 真实执行全部注册套件（`tests` 选项
  默认 True）。与 kea-hook-* 家族（只跑自身组件套件）不同，本包的测试面就是
  整棵树。
- hook 插件以 `dlopen` 运行期加载（`lib/kea/hooks/`），DHCP 服务端依赖 netlink
  接口枚举——这是 0005 补丁的来由（见下）。

## 编译步骤

```bash
# 设备侧：conan-verify 八门禁（内含 conan create 干净构建 + test_package +
# 全树上游测试；缓存依赖已就绪）
cd ~/bih
python3 scripts/ohc-run.py conan-verify kea 3.2.0
# 其中 G2 等价于：
# conan create archives/k/kea/3.2.0 \
#   -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
#   --build=missing --user=ohpcd --channel=stable
```

设备侧跑测时 `conandata.yml` 的源临时指向设备本地 HTTP 镜像（设备网络受限，
无 curl/CA），sha256 校验不变；**提交版 conandata 为上游 `ftp.isc.org` 原 URL**
（sha256 `14bf695d37b65b9b1bf550fea5d0adaf9806c50e5419ef2a176a4b8e9aade3df`），
与该镜像内容逐字节一致（设备端 sha256 实测相同）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:186 ERROR: Unsupported system "harmonyos"` | OHOS 上 meson 报告 host system=`harmonyos`，Kea 平台白名单只有 linux/freebsd/netbsd/openbsd/sun/darwin | 补丁 `0001`（+6 行）：顶层把 `harmonyos` 归一化为 `linux`，全部子目录走 Linux 分支 |
| 2 | `meson.build:477 ERROR: Boost TLS support broken`（`HAVE_GENERIC_TLS_METHOD` DID NOT COMPILE，真实错误 `sp_thread_sleep.hpp: use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl `pthread.h` 不声明 `pthread_setcancelstate()`，boost 1.85 在 `BOOST_HAS_PTHREADS && !__ANDROID__` 时无条件调用（`boost/asio/ssl.hpp` 头链必经） | `generate()` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`；TLS 探针转 YES |
| 3 | `Checking if "LOG4CPLUS_INITIALIZER_H" with dependency log4cplus runs: NO (127)` → `Unknown variable "log4cplus"` | 特性探针是编译并运行；host 共享依赖 `liblog4cplus.so` 不在配置期 `LD_LIBRARY_PATH` 内（127=动态加载失败） | `generate()` 用 `Environment` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH` 并 `save_script("conanbuildenv-kea-runtime")` |
| 4 | `iface_mgr_linux.cc: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 `linux/socket.h`（bionic 派生）定义 `struct sockaddr_storage`，musl `sys/socket.h` 已提供；`linux/rtnetlink.h` 间接包含前者 | 补丁 `0002`（+13 行）：包含 netlink 头期间 define-guard 重命名（守卫 `__linux__ && !__GLIBC__`，libc 鉴别宏，不用平台宏） |
| 5 | 配置期脚本执行失败（shebang 脚本 execve 被 OHOS 拒绝） | 顶层 `meson.build` 以 `find_program` 直呼三个脚本（`cd-and-run.sh`、`env.sh`、`grabber.py`），并直接执行生成的 `config-report.sh` | 补丁 `0003`（+10/-4）：三处脚本改为 `['/bin/sh', …]` / `[python3 全路径, …]` 解释器显式调用（调用点均以该值为 `run_command` 首参，修改收敛于此），`CONFIG_REPORT` 经 `/bin/sh` |
| 6 | 配置期 `mk_cfgrpt.sh` 执行失败 | `src/lib/process/cfgrpt/meson.build` 直接调用 `mk_cfgrpt.sh` | 补丁 `0004`（+1/-1）：经 `/bin/sh` 调用 |
| 7 | 运行期接口枚举失败（netlink socket `bind` EPERM） | OHOS 应用沙箱禁止 AF_NETLINK bind（`Operation not permitted`）——`iface_mgr_linux.cc` 经 `open_socket` 全走 netlink，守护进程/测试启动即缺接口 | 补丁 `0005`（+81/-2）：增加 `getifaddrs()` 回退路径（netlink 不可用时两段式构建 Iface；无动态接口事件），含 `ifaddrs.h`/`netpacket/packet.h` 头 |
| 8 | `meson.build:17 ERROR: Unknown linker(s): llvm-ar` | meson 对 clang 默认用裸名 `llvm-ar` 探测静态链接器；本环境裸名 exec 失败 | `generate()` 从 `tools.build:compiler_executables` 的 C 编译器路径推导同目录 `llvm-ar`/`llvm-ranlib` 写入 `tc.binaries` |
| 9 | 全树测试在第 44/92 个套件处整体中断（`PermissionError [Errno 13]`：mtest 直接 spawn `/bin/sh` shebang 脚本套件） | meson 测试执行器（mtest）以 execve 直呼测试脚本，OHOS 拒绝 shebang 为 `/bin/sh` 的脚本（与问题 5/6 同一内核行为，暴露在测试执行器侧）。此前 43 个套件结果为 `Ok: 40 / Fail: 3` | 补丁 `0006`（10 文件 +49/-22）：26 处脚本套件注册改为 `SH`/`PYTHON` 可执行 + `args: [脚本]`（`SH = find_program('/bin/sh')`）；仅注册层，脚本与测试本体零改动 |
| 10 | `kea-log-tests` FAIL（1.46s；死亡测试失效） | release 构建默认 `b_ndebug=true` → NDEBUG 下 `assert(false)` 被编译掉，`EXPECT_DEATH` 死亡测试失去触发点 | `build()` 在 `tests=True` 时对 meson setup 附加 `-Db_ndebug=false`（仅测试构建；消费方产物不受影响） |
| 11 | `kea-util-tests` FAIL（9.39s；`pidWriteFail`） | OHOS HMDFS 沙箱文件系统不落实 `chmod`，无法建立"文件不可写"前提 → 预期抛异常处不抛 | 补丁 `0009`（+16）：用例内前提探针——chmod 未落实（仍可写入）时恢复权限并 `GTEST_SKIP`；前提成立的常规文件系统上上游检查逐字执行 |
| 12 | `dhcp-run-script-lib-tests` FAIL（41.83s；36 例全挂） | run_script hook 经 `ProcessSpawn::spawn` 以 `execve` 直呼用户脚本，OHOS 对 `/bin/sh` shebang 脚本 EACCES → 子进程 `_exit(EXIT_FAILURE)` | 补丁 `0007`（+25）：spawn 子进程 execve 返回 EACCES/ENOEXEC 时以 `/bin/sh` + 同 argv/env 回退（argv fork 前预构建、无分配；execve 成功路径零变化） |
| 13 | 脚本套件 `admin_tests` / `memfile_tests` / `keactrl_tests` FAIL（rc=1，`kea-admin/keactrl: Permission denied`） | 构建树辅助脚本 `kea-admin`/`keactrl` 以 `#!/bin/sh` 起始，测试脚本直接 execve 之 → EACCES(126) | 补丁 `0008`（2 文件 +10/-2）：两脚本文本去掉 shebang，依赖 POSIX shell 对无解释器行可执行文本文件的回退解释（POSIX XCU 2.9.1.1）；`sh 脚本` 显式调用不受影响。构建树辅助脚本不进包 |
| 14 | run2b：测试沙箱崩溃（`mkdtemp()` 失败 → 空指针，`kea-asiolink-tests` 整体 killed）+ memfile / host_cache / lease_cmds / legal_log / http 类用例失败 | OHOS PC `/tmp` 只读，测试基建/套件默认在 `/tmp` 建临时文件 | 补丁 `0010`（`testutils/sandbox.h`，+15/-2）与 `0018`/`0019`/`0020`：临时文件路径 `TMPDIR` 优先（未设时回退原路径）；0010 兼修空指针崩溃 |
| 15 | run2b：dhcp4 ctrl 64 例 / dhcp6 ctrl 56 例 / d2 24 例 / asiolink 3 例 / config 5 例失败（152 例） | OHOS 沙箱拒绝 AF_UNIX 路径名 socket `bind`（EPERM）——以本地控制通道/本地 socket 为前提的用例平台前提不成立 | 补丁 `0013`-`0017`（10 文件 +332 行）：与测试服务器同路径、同原语（socket→bind→close→unlink）的探针，路径超 `sockaddr_un` 上限直接判不可用；探针不成立时逐用例 `GTEST_SKIP`（消息写明平台语义）；探针判定收敛于共享夹具（dhcp4/dhcp6 `*_test_utils`），覆盖全部调用点 |
| 16 | run2b 与 CI 轮（build #86524）均在同一用例失败：`kea-dhcp-tests` `detectIfaces`（1 例，`checkIfAddrs` 判假，消息 `Non-matching addresses on the detected interface ip6_vti0 / ip6tnl0`） | 两层：①OHOS 沙箱拒绝 `SIOCGIFHWADDR` ioctl（EPERM），测试内 MAC 校验取不到值；②隧道接口触发的上游越界比对——`ip6tnl0`/`ip6_vti0`（ARPHRD_TUNNEL6）报告的链路地址长 16 字节（全零），超出 `sockaddr::sa_data`（14）与 AF_PACKET 的 `sll_addr`（8），测试却按 `getMacLen()` 全长 `memcmp`，越界读到本测试未初始化的 `ifreq` 联合体（栈内容），随机判不等；其它接口链路地址 ≤14 故不受影响，与之吻合的只有这两个隧道接口 | 补丁 `0011`（+47/-11）：①ioctl 被拒时回退读取 `getifaddrs()` AF_PACKET 记录（ioctl 路径先行，与产品面 IfaceMgr 回退同构）；②两条比对路径均只比对缓冲区可承载的字节前缀（`sizeof(sa_data)` / `sizeof(sll_addr)`），长度不足时仍按原判定失败 |
| 17 | run2b：`dhcp-run-script-lib-tests` 时序类零星失败 + 负载抖动残差（ha 3 例 / netstate 1 例） | 高负载构建机上脚本 spawn 结果检查 3s 截止偏紧；负载抖动 | 补丁 `0012`（+5/-1）余量 3s→10s；抖动残差在复验与 run3 干净全量中自然消失（未打补丁） |
| 18 | CI #89023 / #89556：`dhcp-ha-lib-tests` 1 例 FAIL（`stateTransitionsLoadBalancingSecondary`），看板判「编译失败」 | 上游 HA 状态矩阵用例对**宿主挂钟**敏感（`TERM_CLOCK_SKEW = 60s` 致命偏差判定），负载机上伙伴线程被挤住即误判 terminated；#88903 同树同命令在 CI-014 全绿 | 配方 `_meson_test()`：失败套件**隔离复跑一次**（详见「CI 轮次：上游 HA 用例的挂钟敏感性」一节） |

> 上述平台差异均以真实命令/原始输出/退出码复现（日志见设备侧
> `archives/k/kea/3.2.0/reports/conan-create.log` 与 `reports/conan-verify-report.md`，
> 由 conan-verify 生成，不入库）。
> 运行史（三阶段）：**run1** 全树首跑 = `Ok: 40 / Fail: 3`（kea-log-tests /
> kea-util-tests / dhcp-run-script-lib-tests），第 44/92 个套件被 mtest 中断
> （问题 9）→ 修复 0006-0009；**run2b** 复跑（增量续跑）= build+install 全绿、
> 68 套件记录 56 过 / 11 挂 / 1 killed，169 个环境类用例失败（分布 12 套件，
> 问题 14-17）→ 修复 0010-0020，原构建树复验原 12 个套件 **12/12 通过**；
> **run3** 干净全量 = 套件级 `Ok: 92 / Fail: 0`，gtest 用例级 10544 执行 =
> 10336 通过 + 208 跳过 / 0 失败（208 = 154 平台前提探针 + 54 上游既有需 root），
> 脚本套件 26/26。
> 知识图谱命中/新增草稿记录（G0/G2 自动查询）：无新增问题类——平台差异全部落在
> 已收录知识类（E232 / E046 / netlink bind EPERM / symlink EPERM / 沙箱 AF_UNIX
> bind 前提 / 测试临时目录 TMPDIR），按路径 A（基础适配）申报、不新增知识草稿。

## 源码修改

| 补丁 | 文件 | 行数 | 内容 |
|------|------|------|------|
| 0001-meson.build.patch | `meson.build` | +6 | harmonyos → linux 平台名归一化 |
| 0002-src-lib-dhcp-iface_mgr_linux.cc.patch | `src/lib/dhcp/iface_mgr_linux.cc` | +13 | netlink 头包含期间的 `sockaddr_storage` define-guard |
| 0003-meson.build.patch | `meson.build` | +10/-4 | 配置期脚本调用经 `/bin/sh` / python 全路径；`CONFIG_REPORT` 生成 |
| 0004-src-lib-process-cfgrpt-meson.build.patch | `src/lib/process/cfgrpt/meson.build` | +1/-1 | `mk_cfgrpt.sh` 经 `/bin/sh` 调用 |
| 0005-src-lib-dhcp-iface_mgr_linux-getifaddrs-fallback.patch | `src/lib/dhcp/iface_mgr_linux.cc` | +81/-2 | netlink bind EPERM 时的 `getifaddrs()` 回退（两段式 Iface 构建） |
| 0006-meson-script-tests-interpreter.patch | 顶层 `meson.build` + 9 个 `tests/meson.build` | +49/-22（10 文件） | 26 处脚本套件注册经 `SH`/`PYTHON` 解释器启动（仅注册层） |
| 0007-src-lib-asiolink-process_spawn.cc-exec-fallback.patch | `src/lib/asiolink/process_spawn.cc` | +25 | spawn 子进程 execve EACCES/ENOEXEC 时 `/bin/sh` + 同 argv/env 回退 |
| 0008-src-bin-keactrl-kea-admin-no-shebang.patch | `keactrl.in`、`kea-admin.in` | +10/-2 | 构建树辅助脚本去 shebang（POSIX shell 回退解释执行） |
| 0009-src-lib-util-tests-pid_file_unittest.cc-premise-probe.patch | `src/lib/util/tests/pid_file_unittest.cc` | +16 | `pidWriteFail` 前提探针 + `GTEST_SKIP`（测试面改动之一，见下） |
| 0010-src-lib-testutils-sandbox.h-tmpdir.patch | `src/lib/testutils/sandbox.h` | +15/-2 | 测试沙箱临时目录 `TMPDIR` 优先（含 `mkdtemp()` 失败空指针防护） |
| 0011-src-lib-dhcp-tests-iface_mgr_unittest.cc-siocgifhwaddr-fallback.patch | `src/lib/dhcp/tests/iface_mgr_unittest.cc` | +47/-11 | ①`SIOCGIFHWADDR` ioctl 被拒时 MAC 校验回退 `getifaddrs()` AF_PACKET；②两条比对路径按缓冲区容量收敛比对长度（问题 16 ② 越界读的修正） |
| 0012-src-hooks-dhcp-run_script-tests-run_script_unittests.cc-script-spawn-timeout.patch | `src/hooks/dhcp/run_script/tests/run_script_unittests.cc` | +5/-1 | 脚本结果检查截止 3s→10s（慢机余量） |
| 0013-src-bin-dhcp4-tests-ctrl-unix-socket-probe.patch | `ctrl_dhcp4_srv_unittest.cc` + `dhcp4_test_utils.h/.cc`（3 文件） | +53 | AF_UNIX 路径名 `bind()` 同型探针 + 逐用例 `GTEST_SKIP`（探针收敛于夹具） |
| 0014-src-bin-dhcp6-tests-ctrl-unix-socket-probe.patch | `ctrl_dhcp6_srv_unittest.cc` + `dhcp6_test_utils.h/.cc`（3 文件） | +51 | 同 0013 |
| 0015-src-bin-d2-tests-ctrl-unix-socket-probe.patch | `src/bin/d2/tests/d2_command_unittest.cc` | +67 | 同 0013 |
| 0016-src-lib-asiolink-tests-unix_domain_socket_unittest.cc-socket-probe.patch | `src/lib/asiolink/tests/unix_domain_socket_unittest.cc` | +54 | 同 0013 探针 |
| 0017-src-lib-config-tests-unix-socket-probe.patch | `unix_command_mgr_unittests.cc` + `client_connection_unittests.cc`（2 文件） | +107/-2 | 同 0013 探针 |
| 0018-src-lib-dhcpsrv-tests-memfile-tmpdir-and-perms-probe.patch | `src/lib/dhcpsrv/tests/memfile_lease_mgr_unittest.cc` | +64/-11 | 临时文件路径 `TMPDIR` 优先 + chmod 落实性探针（`lfcStartHandlerPidNotWritable`） |
| 0019-src-hooks-dhcp-tests-tmpdir-substitution.patch | `lease_cmds4_unittest.cc` + `legal_log_mgr_unittests.cc` + `host_cache/.../command_unittests.cc`（3 文件） | +47/-9 | 临时文件路径 `TMPDIR` 优先 |
| 0020-src-bin-http-config-write-tmpdir.patch | dhcp4 / dhcp6 / d2 各 `http_control_socket_unittest.cc`（3 文件） | +47/-12 | 临时文件路径 `TMPDIR` 优先（含配置写检查） |

二十处补丁均不含平台宏（PF5 通过）；补丁在 pristine 3.2.0 树上按 conandata 顺序
逐枚 apply 验证（本地 `git apply` 全栈 + 真机 conan 自带 `patch_ng` 双重验证），
应用后 36 个被改文件与目标内容逐字节一致（LF-only，0 CR）；0010-0020 另在原
构建树全应用 + 增量重建 + 原失败套件复验 12/12 通过。

测试面改动合计 21 个测试侧文件（16 个用例文件 + 5 个测试基建/夹具文件，
+573/−48 行，补丁 0009-0020），按四类处置：①前提探针 + 逐用例 `GTEST_SKIP`
（0009/0013-0018：AF_UNIX 路径名 `bind` 同型探针、chmod 落实性探针）；②临时
目录 `TMPDIR` 优先（0010/0018/0019/0020）；③同构能力回退 + 缓冲区容量收敛的
比对（0011，实跑通过而非跳过）；④时序余量（0012）。四类在平台前提成立/常规环境时逐行保留上游检查，
如实计入「上游测试用例修改」披露（0001-0008 不触碰任何测试源码或测试逻辑）。

## CI 轮次：worker 进程资源压力与编译重试

PR #14646 的两次 CI 轮次（同一 PR、同一配方、同一条编译命令、同样 `-j 8`）：

| 轮次 | worker | 结果 |
|------|--------|------|
| #80227 | CI-040 | 编译 **1433/1433 全绿**；失败在随后的 `meson test`——`kea-dhcp-tests` `detectIfaces`（已由补丁 0011 修复） |
| #89023 | CI-030 | 编译**首个 spawn 即中止**：`ninja: fatal: posix_spawn: Resource temporarily unavailable`，该轮日志无任何目标进度行，`build()` 中 `meson compile` 行报错 |

后一种失败与源码/平台适配无关：`posix_spawn` 返回 `EAGAIN` 说明该 worker 的进程/
线程表瞬时耗尽（`-j 8` 的突发 fork 拿不到槽位），ninja 随即放弃整次编译。同类现象
本仓已有先例——`libnm/1.52.1` CI-011 的 `resource temporarily unavailable: tr`、
`lzop/1.04` 的 `can't fork: try again`——均判定为 worker 基建故障而非包缺陷；
`libcmis/0.6.3` 则已用退避重试化解同类 EAGAIN。

`build()` 因而改为 `_meson_compile()`：

- **并发度遵循 `tools.build:jobs`**（缺省仍取家族配方的 8）。原硬编码 `-j 8` 绕过了
  设备准入 conf，而本仓通用做法正是让该 conf 收敛并发内存/进程峰值（`arb`、`cln`、
  `ffmpeg`、`abiword-plugin-openwriter` 等一致）。
- **命中 spawn 压力特征时按 `8 → 4 → 2` 降级重试**（先 `-j` 减半，间隔 15s / 30s）。
  ninja 增量续跑，重试只多花墙钟时间、不重编已完成目标；真实编译错误的特征不匹配，
  **首次即原样失败**，不掩盖问题、不做无谓重试。
- 每次尝试前打印**免 fork** 的宿主压力快照（`/proc/loadavg`、进程/线程计数、
  `Max processes`）：spawn 失败的当口最不该再 fork，故诊断只读 `/proc`，为下一轮
  CI 留下判别"机器过载"与"代码有问题"的依据。
- 编译输出经 `tee` 同时留在 CI 控制台与构建目录，真实退出码经 fd 3 带出——管道会
  吞掉 ninja 的状态（POSIX sh 无 `pipefail`，`tee` 的状态恒为 0）。

两条路径均以真机 `conan create` 验证（抽取配方原方法 + 模拟 meson 驱动）：带压力
特征的首轮 `-j 8` 中止后 15s 降至 `-j 4` 成功；不带特征的真实编译错误仅 1 次尝试
即失败（无重试、无退避）。

## CI 轮次：两类负载敏感失败与各自的处置

同一 PR、同一配方，CI 轮次的失败点分成两类，都不是树缺陷：

| 轮次 | worker | L1（`conan create`）结果 | 失败阶段 | 处置 |
|------|--------|------------------------|---------|------|
| #88903 | CI-014 | **全绿**（Conan test_package / L0 / L1 全过） | — | — |
| #89023 | CI-030 | 红：`ninja: fatal: posix_spawn: Resource temporarily unavailable`（`meson compile` 首个 spawn 即中止，日志内无任何编译错误） | 编译 | `_meson_compile()` 降级重试（上一节） |
| #89556 | CI-038 | 红：全树套件中 `kea:dhcp-ha-lib-tests` 1 例 FAIL（`61/92 … 469.97s exit status 1`，`Ok: 91 / Fail: 1`） | 测试（`build()` 的 `meson test`） | `_meson_test()` 失败用例隔离复跑（本节） |

> #89023 的失败证据取自该轮 `conan-build-test` 原始日志（当时的 `build()` 第 169 行
> `self.run('{} compile -C "{}" -j 8')`，未走到任何编译单元）：看板把该轮记为
> 「编译失败」与日志一致。真正的**误判**形态是 #89556 这类——失败落在编译**之后**的
> 上游测试套件（`build()` 第 191 行 `meson test` → `ConanException: Error 1 while
> executing`），与已绿的 #88903 树几乎一致，差别只在 worker。


**真因：上游 HA 状态矩阵用例对宿主挂钟敏感，不是适配缺陷。** 本机 run2b 构建树的
`meson-logs/testlog.json` 命中同一真因——`[ PASSED ] 446 tests. [ FAILED ] 1 test`，
`HAServiceStateMachineTest.stateTransitionsLoadBalancingSecondary`
（该用例耗时 **70363 ms**，同套件同级用例约 250 ms）：

```
ha_service_unittest.cc:6456: Failure
final_state.state_ = 21, service_->getCurrState() = 22
expected transition to the 'syncing' state for the partner state 'load-balancing',
but transitioned to the 'terminated' state
Google Test trace: ha_service_unittest.cc:7898: WAITING state transitions
```

机制：该夹具在真实时间里驱动**同进程**模拟伙伴，`CommunicationState` 一旦发现伙伴
上报的时钟偏差超过 `TERM_CLOCK_SKEW = 60s` 即调用 `shouldTerminate()`
（`ha_service.cc:859`，转 `HA_TERMINATED_ST`）。负载机上伙伴线程被挤住数十秒即够触发；
其后的等待按 `HA_WAITING_TO_TERMINATED_ST_DELAY_MINUTES = 10` 每 10s 静默超时
（7 次 ≈ 70s，与实测 70.36s 吻合），矩阵用例于是拿不到期望的 `syncing`。CI worker
同时跑多个包时该前提极易出现。

**处置：测试阶段失败时只重跑失败的 gtest 用例（按用例隔离）**，落在配方 `_meson_test()`：

- 首轮仍是**全树上游套件**（不剪裁测试面），命令与口径不变：`-v --timeout-multiplier 4`。
- 失败后从 `meson-logs/testlog.json`（JSON Lines）取 `result != "OK"` 的套件名，去掉
  `kea:` 项目前缀（`meson test` 只按裸名过滤）；再用该条目的 `stdout` 取 gtest 失败用例名
  （`[  FAILED  ] Fixture.Case (12 ms)`；摘要行 `N tests, listed below:` 不是用例名）。
- 复跑**只跑这些用例**，最多两次：`--no-rebuild --print-errorlogs --timeout-multiplier 8
  --logbase kea-test-retry-<n> --test-args="--gtest_filter=A:B"`。每次都用 `timeout 150`
  封顶——CI 的 `conan create` 只有 3600s 预算，最坏 2×150s 的复跑不能吃掉它。非 gtest
  套件（日志里没有用例清单，如 shell 套件）退化为整套件复跑，同样 150s 封顶。
- **为什么不是「整套件隔离复跑」**（上一轮的写法，已按实测改掉）：本机实测整套件单独复跑
  仍失败，且**两次的失败用例各不相同**（一次 2 例、下一次换成另 2 例，耗时 349 / 20017 ms），
  而同样这批用例单独复跑 **630 ms 全过**。抖动来自「同一套件内 447 个用例互相争真实时间」，
  缩到用例粒度才真正消除前提；整套件复跑既贵（90–470s）又救不回来，且会挤占 CI 预算。
- 抖动复跑通过时打 `warning`，附宿主压力快照（复用 `_fork_free_pressure()`）与复跑日志
  路径；首轮日志不被复跑覆盖（`--logbase`），CI 日志里留痕可判别「机器过载」与「代码有问题」。
- 两次仍失败 → 抛异常（附套件/用例与各份日志）：真缺陷不会因重试被放过。
- 解析不出失败套件名（日志缺失/损坏）时不静默放过：直接抛异常并指向日志，避免把
  「无法判定」当成「通过」。

> 首轮通过时零额外开销；失败时只复跑**首轮确实失败的那几个用例**，通过率口径不变。

**验证**：

1. 解析：真实 `testlog.json` → 套件 `['dhcp-ha-lib-tests']`、用例
   `['HAServiceStateMachineTest.stateTransitionsLoadBalancingSecondary',
   'HAServiceStateMachineTest.stateTransitionsHotStandbyPrimary']`；合成日志
   （1 OK / 1 FAIL / 1 TIMEOUT / 1 损坏行 / shell 套件无用例清单）分类正确；
   空文件与文件缺失均返回空（→ 走「无法判定」异常分支）。
2. 路径演练（`tmp/ohc-logs/kea_test_path.py`：直接驱动配方源码 + 真实构建树 + 真实 meson，
   不重编）：模拟首轮失败 → 按用例复跑 `rc=0` → `_meson_test()` 打 warning 正常返回；
   上一版（整套件复跑）在同一演练里 `rc=1`，才落到第三轮用例复跑。
3. 端到端：本机全量 `conan create`（同 CI 参数 `-pr:h/-pr:b=ci/conan/profiles/ohos-aarch64
   --build=missing --build=kea/*`）走通，结果见下节「本轮本机门禁」。

### 本轮本机门禁（kea 3.2.0，2026-10-13）

本机按 CI 同参数跑完整 `conan create`（编译 1433 目标 + 全量上游套件），**exit=0，
耗时 2411s**：

```
Ok:                92
Fail:              0
kea/3.2.0 daemon execution check OK
```

该轮**首轮即全绿、未触发复跑**——即本次改动没有给正常路径增加任何开销；复跑路径本身
由上面的路径演练覆盖（模拟首轮失败 → 按用例复跑 `rc=0` → warning 后正常返回）。

抖动强度实测（判断重试力度用，同一台机器）：`dhcp-ha-lib-tests` 单独复跑一次即以
`HAServiceStateMachineTest.stateTransitionsLoadBalancingSecondary` 单例 **290591 ms**
失败（同套件同级用例约 250-350 ms）；整套件复跑两次的失败用例**各不相同**
（349 / 20017 ms）；而按用例复跑同样这批用例 **630 ms 全过**。宿主 `loadavg ≈ 21`
（20 核，另有 4 个 agent 进程长期占 CPU）——负载越重，套件内 447 个用例互相争真实时间
越明显，缩到用例粒度是唯一救得回来的做法，且成本可忽略。


| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| boost | 1.85.0 | 强制 | 1.90/1.91 制品仓包缺 Kea 实际使用的头文件；头文件泄漏进 `kea/dhcp/pkt.h`、`kea/util/str.h` 等安装头（`transitive_headers=True`，与已合入 kea-hooks 同口径） |
| log4cplus | 2.2.0.1 | 强制 | Kea 日志后端（shared；配置期运行探针需 LD_LIBRARY_PATH）；`log/*_impl.h` 安装头泄漏其头文件（同上口径） |
| openssl | 3.5.8.1 | 强制 | 默认 `crypto=openssl`；无头文件泄漏，按 kea-hooks 先例 `transitive_headers=True` |
| gtest | 1.17.0.1 | test_requires | `tests=enabled` |
| meson | 1.11.0 | tool_requires | Kea 需 ≥1.10 |

## 包内容与运行期依赖

- `bin/`：kea-dhcp4、kea-dhcp6、kea-dhcp-ddns、kea-lfc、perfdhcp
- `lib/`：全部 `libkea-*.so*`（soname 以真实拷贝落盘；实测 **23** 个
  去重库 / 69 个文件，73,273,344 字节）
- `lib/kea/hooks/`：全部内置 hook 插件（`libdhcp_*.so`；实测 **19** 个
  去重插件，9,746,752 字节）
- `include/kea/`：`src/lib` 全树公共头（实测 **533** 个文件）
- `licenses/COPYING`（MPL-2.0）
- 守护进程经 `cpp_info` 提供 `bin`/`lib`/`include/kea` 与
  `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`（OHOS 消费方包含 `kea/dhcp/pkt.h` 头链
  必须）。

不落盘内容：`keactrl`/`kea-admin`/`kea-shell` 辅助脚本——上游把它们烘焙成绝对
prefix 的启动器，不可重定位，随包分发会在消费者机器上指向构建机路径（家族
kea-hooks/kea-perfdhcp 同处理）。hook 需要的 mysql/pgsql/krb5 后端已禁用构建。

## 鸿蒙特有测试用例

本包涉及 OHOS 平台改动（20 处补丁 + 3 处工具链注入），补充 **2 个**鸿蒙特有用例，
随 `test_package` 在 `conan create` 内真实编译并执行（CMake +
`find_package(kea)`）：

| 用例 | 文件 | 检查项 | 覆盖内容 |
|------|------|------|----------|
| `test_ohos_platform` | `test_package/test_ohos_platform.c` | 11 | 包内 `bin/kea-dhcp4` 的 OHOS 平台 ABI 特征（ELFCLASS64 / `EM_AARCH64`、DT_NEEDED 含 musl `libc.so` 且不含 glibc `libc.so.6`、含 `libc++_shared.so`）并 `dlopen(RTLD_NOW)` 解析其 libkea-* 闭包 |
| `test_ohos_runtime` | `test_package/test_ohos_runtime.c` | 96 | OHOS 加载器下 `lib/` 全部 69 个 `libkea-*.so*` 文件与 `lib/kea/hooks/` 全部 19 个 hook 插件逐个 `dlopen(RTLD_NOW)`（88 项）+ 8 项契约/规模检查；hook 契约符号 `version()/load()/unload()` 可解析且 `version()==30200`（Kea 3.2.0 `KEA_HOOKS_VERSION`） |

实测结果：4 个程序全过（**129 项检查全 ok、0 FAIL**）——`test_ohos_platform`
11/11 + `test_ohos_runtime` 96/96 + `test_kea_api` 10/10 + `test_kea_daemons`
12/12（2026-10-04 真机 conan-verify）。另有 2 个通用消费者检查
（`test_kea_api.cpp` 10 项检查：按包内头文件编译、`isc::Exception` 异常模型、
`util::str::trim` 真实符号；`test_kea_daemons.py` 12 项检查：5 个可执行文件
`-v`、2 个 `-W` 构建报告、`-t` 合法/非法配置检查）。

## 真机八门禁（conan-verify）

G0 预构建评估 / G1 配方完整性 / G2 干净构建 / G3 系统同名库隔离 / G4 产物完整性
**全部 PASS**；L2 平台 smoke test / L4 静态安全扫描 / L5 产物基线因本次无对应
cache 路径**跳过**。总表 Verdict：**PASS**（2026-10-04 真机；"✅ 配方验证通过：
kea 3.2.0，可标记 status: published"）。

## 已知限制

- 不打包上游辅助脚本（见上）；`keactrl` 类启动器需求请在消费者侧自行以
  `kea-dhcp4 -c <conf>` 直接替代。
- mysql/pgsql/krb5/netconf 后端禁用：相应 hook（如 `libddns_gss_tsig.so`）与
  `kea-dhcp-ddns` 的 GSS-TSIG 功能不在包内。
- 0005 回退路径下无动态接口事件（netlink EPERM 时接口地址变化感知静默），
  静态租约/DHCP 主流程不受影响。

## R38（命令行工具）

本包产物含 5 个可执行文件（上游 `sbindir`/`bindir`），已在软件级别目录提供
`archives/k/kea/commands.json`（`type=tool`、`binary=true`、`versions.3.2.0.ref`
指向 `kea/3.2.0`）。

---

**编译结束**: 2026-10-04
**最终状态**: built
