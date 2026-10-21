# ethtool 7.1 适配笔记

## 编译环境

- 构建系统: autotools ｜ 编译日期: 2026-10-08
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang），平台 HarmonyOS PC aarch64 / HongMeng Kernel 1.12.0
- 状态: **failed**（conan-verify G2 连续两轮红、根因已受控实测定位且修复已 A/B 验证，按停损规则等第 3 轮授权后转 built）

## 取源（R39，官方直链）

- 主源 `https://www.kernel.org/pub/software/network/ethtool/ethtool-7.1.tar.xz`：HTTP 200 / 456260 字节；本地复算 sha256 = `4d78c26edc0255bc92f4b995b5fd66108d75ff966ed4694f6025a6d370bc2496` 与 conandata 逐字一致；`tar -tJf` 首行 `ethtool-7.1/`，源树 84 个 `.c`
- 同源旁证：kernel.org 软件目录页列有 6.15/6.19/7.0/7.1；git.kernel.org refs/tags 有 `v7.1`（上游 tag `v7.1`）
- 不走 Debian 池、不加镜像前缀

## 依赖（W0）

- `preflight_check.sh ethtool/7.1` **RC=0**：`[OK] 已发布: libmnl/1.0.5`、`[OK] 版本号未被占用`
- 精确取得（未用通配 `conan list` 判 binary）：
  - `conan download libmnl/1.0.5 --only-recipe -r ohpcd` RC=0，rrev `5f009907578ba031715d5ff883557dde`
  - `conan install --requires=libmnl/1.0.5 --build=never` RC=0，下载二进制 pkg `6b129b068851896169fae42d399fa922d239ce8a`
- `recipe-search ethtool` RC=0：top1 = ethtool/6.15 [autotools] score=0.5 +补丁（同包先例，骨架已参照）

## 门禁记录（两轮红 = 停损触发）

| 轮 | 命令 | 结果 | 第一条真实错误 |
|----|------|------|----------------|
| 1 | `conan-verify ethtool 7.1` | G1 PASS、G0 PASS、**G2 FAIL** | `configure: creating ./config.status` → `configure: error: could not make ./config.status`（reports/conan-create.log） |
| 2 | 同上（已加 0001-configure.patch） | G1 PASS、G0 PASS、**G2 FAIL（同一错误文本）** | 同上 |

### 根因（受控实测，两条叠加，均已定位）

1. **E011 族：HMDFS 上 `umask 077` 创建的临时目录不可写**
   - 最小复现（未打补丁 + ASCII pkg-config 路径）：`configure: creating ./config.status` → `./config.status[757]: can't create ./confXXXXXX/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`（本机独立日志 cfg-repro2.log:48）
   - 修复 = `patches/0001-configure.patch`：conf 临时目录创建块去掉 `umask 077` 包裹（改 022）并补 `chmod 755`（原 configure 6289/6294 两处）——E011/E114 受控方案，与同包 6.15 已合入配方同一思路；**不引入任何平台宏**（R8/PF5）
   - 修复后本机 `configure` RC=0、Makefile 正常生成；第 2 轮 conan 源码树回读确认 `umask 022`+`chmod 755` 已生效 ⇒ 补丁路线成立
2. **非 ASCII 路径进入 pkg-config 输出（A/B 实测）**
   - 现象：`CONAN_HOME` 目录名含中文 ⇒ conan 生成的 `libmnl.pc` 的 `prefix=` 带中文 ⇒ `MNL_CFLAGS` 非 ASCII ⇒ config.status 生成循环失败，错误文本与两轮 G2 完全一致
   - A/B：A（conan 原生 pc，prefix 中文字节实测 `\xe4\xb8\xbb\xe7\x90\x86`）`configure` RC=1 且错误与 G2 逐字同；B（同一头文件/库拷到 ASCII 路径并改写 prefix）`configure` RC=0
   - 第 2 轮失败的直接原因 = 运行脚本仍写中文路径（conan 不做 realpath、字面前缀落进缓存路径）；修复 = **ASCII 真身 + 中文符号链接**（`home-ethtool71` 为真身、`home-主理-N-ethtool` 为其符号链接），先例 = radioclk「非 ASCII home 在 configure 自处理路径咬人」的已批准偏离
   - ⇒ 同类别连续 2 轮红，**按规则停损**：第 3 轮（改脚本 CONAN_HOME 为 ASCII 路径）待主理授权

### 框架 `build` 一条龙的如实记录（⛔ 未改 scripts/）

- `ohc-run.py build ethtool 7.1` 退出码 2：Step3/4 的「失败自动重试」把 `curl -fsSL …` 重试串当成参数喂给了 configure/make（日志可见 `configure: error: unrecognized option: '-fsSL'`、`make: sSL: No such file or directory`），Step5 无后续输出退出；构建工作目录无 Makefile / config.log ⇒ 框架探索步未产出真实构建。按 §12.60①：**配方门禁以独立 conan-verify 为准**
- 前置：`scripts/software-registry.yaml` 无 ethtool 条目，`build` 的 Step1 取不到 URL ⇒ 先 `init-build ethtool 7.1 --url=<kernel.org 直链> --tar=tar.xz`（EXPECTED_SHA256 环境变量同值校验通过）生成构建上下文

## 运行期能力面（一手实测，本机 + A 机 + B 机三处读数一致；A/B 经 SSH 由 sshd 起进程）

| 面 | 读数 |
|----|------|
| 正对照（同套接字基础 ioctl） | `SIOCGIFFLAGS(0x8913)` rc=0、`SIOCGIFINDEX(0x8933)` rc=0 |
| **SIOCETHTOOL(0x8946)** | **errno=13 EACCES**（含只读 `ETHTOOL_GDRVINFO`；lo/eth0/wlan0 全拒） |
| **NETLINK_GENERIC（genetlink）** | socket **创建即 errno=13 EACCES** |
| NETLINK_ROUTE | socket OK；修正版 RTM_GETLINK dump 收 17916B/8 块/含 NLMSG_DONE（首版探针漏 ifinfomsg 16B 致 Timeout，已自纠重跑） |
| /sys/class/net | listdir errno=13 EACCES；`/proc/net/dev` 可读（15–16 行） |
| 进程态 | `CapEff=000000000000002a`（无 CAP_NET_ADMIN/CAP_NET_RAW）、`Seccomp=2`、`Seccomp_filters=1`、uid=20020084（A 机 20020105） |
| 对照组 | `AF_CAN` errno=97 EAFNOSUPPORT（can-utils 同款墙复现） |

**上游无非特权降级路径（源码穷举）**：`args[]` 表里 `no_dev=true` 仅 2 条 = `-h|--help`（ethtool.c:6386）与 `--version`（:6392）；全部功能命令走 `ETHTOOL_G/S` ioctl（ethtool.c 94 处）或 genetlink；`--disable-netlink` 只是 netlink→ioctl 互退（:6420/:6677，两面同墙）；`fopen` 的 `gregs_dump_file`（:3548）/`do_writefwdump`（:4775）都要先 `send_ioctl` 拿到设备数据。

**披露口径（对外统一措辞）**：本平台测试进程无相应 capability，功能面未能实测；已实测 `-h`/`--version` 与构建产物完整。⛔ 不写「在鸿蒙上不可用」这类平台级定性（对外口径归主理/用户）。

## 源码修改

| 文件 | 症状 | 根因 | 方案 |
|------|------|------|------|
| `patches/0001-configure.patch`（19 行，portability） | `config.status` 写 `confXXXXXX/subs1.awk` Permission denied / `could not make ./config.status` | HMDFS 上 `umask 077` 得到的目录不可写（E011） | 去掉 `umask 077` 包裹（改 022）并 `chmod 755`，保留真实临时目录创建 |

已试失败方案：不打补丁直跑（复现如上）；仅改进程 umask 无效（configure 脚本内部显式 `umask 077`）。除此之外源码树零改动。

## 测试

- 本机 work tree 实测（补丁后）：`make -j2` RC=0（35 条 warning，全部为 `-Wgnu-variable-sized-type-not-at-end` 族、非致命）；`./ethtool --version` → `ethtool version 7.1`；`./ethtool -h` 输出 Usage 正常

### ★2026-10-17 rule4 返修：上游用例**真实执行**读点（口径修正 + 两配置实测）

> 平台原判：「上游有用例 3 个但一个也没测（0/3）」。**3 的来源是我们旧 MANIFEST 把「测试源文件」当成了「用例」**；
> 且旧记录 `N_executed=1` 只是源码树里手跑的一次，**没有按上游 `make check` 的真实配置矩阵执行**。本轮两处都改掉。

**① 口径修正（源码级，Makefile.am 行号）**

| 项 | 上游事实（`ethtool-7.1/Makefile.am`） | 是否用例 |
|----|--------------------------------------|----------|
| `test-cmdline` | `:80 TESTS = test-cmdline`、`:81 check_PROGRAMS = test-cmdline`、`:83 test_cmdline_SOURCES = test-cmdline.c test-common.c $(ethtool_SOURCES)` —— **恒注册** | ✅ 是 |
| `test-features` | `:84 if !ETHTOOL_ENABLE_NETLINK` → `:85 TESTS += test-features`、`:86 check_PROGRAMS += test-features` —— **条件注册**（默认 `--enable-netlink` 时不注册） | ✅ 是（条件） |
| `test-common.c` | 只在 `:83`/`:88` 的 `*_SOURCES` 里（公共辅助源 + `send_ioctl` mock），**从不进 `TESTS`/`check_PROGRAMS`** | ❌ 不是用例 |

⇒ 上游**注册用例 = 2**（不是 3）。源文件仍如实保留 3 个口径（`upstream_test_source_files`），不缩分母。

**② 真实执行读数（三套独立构建 + `make check`）**

| 配置 | 身份 | `TESTS`（上游注册） | `make check` 结果 | rc |
|------|------|--------------------|-------------------|----|
| `./configure --disable-netlink` | **★出厂配置**（2026-10-17 起 `conanfile.py` 即传 `--disable-netlink`，见 `manifest.yaml build.configure_options`） | test-cmdline + test-features | `TOTAL 2 / PASS 2 / FAIL 0 / SKIP 0 / ERROR 0` | **0** |
| `./configure`（默认 `--enable-netlink`） | 历史/对照配置（改动前的出厂配置） | test-cmdline | `TOTAL 1 / PASS 0 / FAIL 1`（子用例 **249/257**） | 2 |

**②' 出厂配置的端到端复验（2026-10-17 返修后重跑；改动 = `conanfile.py` 传 `--disable-netlink`）**

- `ohc-run.py conan-verify ethtool 7.1`：**G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS**（L2/L4/L5 PASS），末行 `✅ 配方验证通过: ethtool 7.1`，rc=0（`reports/conan-verify-report.md`；Verdict PASS，Date `2026-10-17T16:49:52`）。
- `conan create` 的实跑命令行**逐字含该选项**（`reports/conan-create.log:108`）：
  `.../b/configure --prefix=/ '--bindir=${prefix}/bin' ... --disable-netlink` ⇒ 证明出厂构建真的用了关闭 netlink 的配置。
- `test_package` 5 条消费者断言全部实跑通过（`reports/conan-create.log` 内 5 条 `(test package): RUN:` 行：`ethtool --version` → `grep -q "ethtool version 7.1"` → `ethtool -h` → `grep -q "Usage:"` → `grep -q -- "--disable-netlink"`）⇒ **5/5**。
- 出厂配置下上游套件独立复测（同上游 tarball sha256 `4d78c26edc0255bc92f4b995b5fd66108d75ff966ed4694f6025a6d370bc2496` + 同 `0001-configure.patch` + 配方同一个 configure 选项 `--disable-netlink`；配方另加的 `${CONAN_PREFIX}` 只影响安装前缀、不进测试矩阵）：`./configure --disable-netlink && make -j8 && make check` → **rc=0，TOTAL 2 / PASS 2 / FAIL 0 / SKIP 0 / ERROR 0**。
- 关闭 netlink 不破坏消费者断言（实测）：`ethtool-config.h` 中 `ETHTOOL_ENABLE_NETLINK` **0 处**（宏确实未定义），而 `ethtool -h` 仍输出 `--disable-netlink	do not use netlink, fall back to ioctl interface` 行 ⇒ 第 5 条 `grep -q -- "--disable-netlink"` 仍成立。
- ⇒ **出厂配置 == 测试配置**：出厂 `make check` 就是上表第一行的 2/2，不存在「只有旁路配置才绿」的张力。

**②'' 上游套件在 `conan create` 内真实执行（2026-10-17 最后一步；`upstream_test_in_build: true`）**

- 配方改动：`conanfile.py` 的 `build()` 在 `make` 之后追加 `autotools.make(target="check", args=["-j1"])`，**fail-closed**（测试红即构建红；无 `|| true` 兜底、不改上游断言、不缩分母）；`test_package/MANIFEST.yml` 同步 `upstream_test_in_build: true` + `upstream_test_command: "make check"`。
- 重跑 `ohc-run.py conan-verify ethtool 7.1`（过 build-slot，`SLOT_DONE:ok MemAvailable=5652MB`）：**G0/G1/G2/G3/G4 全 PASS**，末行 `✅ 配方验证通过: ethtool 7.1`，rc=0（`reports/conan-verify-report.md`，Verdict PASS / Date `2026-10-17T17:04:35`）。
- **G2 的 `conan create` 内 `make check` 逐字读数**（`reports/conan-create.log`）：
  - `:612` `ethtool/7.1@ohpcd/stable: RUN: make check -j1`
  - `:1362` `make  check-TESTS`
  - `:1365` `PASS: test-cmdline`
  - `:1366` `PASS: test-features`
  - `:1368` `Testsuite summary for ethtool 7.1`
  - `:1370-1374` `# TOTAL: 2` / `# PASS:  2` / `# SKIP:  0` / `# XFAIL: 0` / `# FAIL:  0`（其后 `# ERROR: 0`）
- ⇒ 上游两个注册用例**在出厂构建流程内部**真实执行并全部通过；`test_package` 5 条消费者断言同批实跑（`reports/conan-create.log:1435/1438/1440/1695/1697`）。
- 需要额外环境吗：**不需要**。`make check` 在 conan 的 build 环境内直接可用（同一 `make`、同一 clang；netlink 关闭后测试二进制不链接 libmnl，仅 `LDADD=-lm`），未追加任何额外环境变量、未用 `|| true` 兜底。

**③ 对照配置（`--enable-netlink`）那 1 条 FAIL 的根因已逐条钉死（不是"环境不允许"式声明）**

- 失败的 **8 条子用例恰好是且仅是** `test-cmdline.c` 里**全部** `IS_NL`/`!IS_NL` 条件项 —— `:28`、`:30`、`:31`、`:69`、`:85`、`:292`、`:293`、`:294`（全文条件项共 8 条，零遗漏零多余）。逐条原文：
  - `E: ethtool --json devname returns 1`（`:28`，期望 0）
  - `E: ethtool 16_char_devname! returns 1`（`:30`，期望 0）
  - `E: ethtool 127_char_devname0123…abcde returns 1`（`:31`，期望 0）
  - `E: ethtool --change devname xcvr external returns 0`（`:69`，期望 1）
  - `E: ethtool --change devname speed 100 duplex half port tp autoneg on advertise 0x1 phyad 1 xcvr external wol p sopass 01:23:45:67:89:ab msglvl 1 returns 0`（`:85`，期望 1）
  - `E: ethtool --set-fec devname encoding foo returns 1`（`:292`，期望 0）
  - `E: ethtool --set-fec devname encoding auto foo returns 1`（`:293`，期望 0）
  - `E: ethtool --set-fec devname encoding none returns 1`（`:294`，期望 0）
- **实测首错（逐字，`LD_PRELOAD` 探针挂在 `socket()` 上，`reports/upstream-test-cmdline-afnetlink-probe.log`）**：
  `socket(AF_NETLINK=16,type=3,proto=16) -> -1 errno=13` —— 在 `./test-cmdline` 一次运行内**出现 125 次、125 次全 errno=13（EACCES）**。
- **源码级因果链（行号）**：`netlink/nlsock.c:405 mnl_socket_open(NETLINK_GENERIC)` → 返回 NULL（EACCES）→ `nlsock_init` 返回负值 → `netlink/netlink.c:420 netlink_init()` 返回负值 → `netlink.c:492-495` `reason = "netlink interface initialization failed"; goto no_support;` → `netlink.c:514 no_support:` **静默回落 ioctl 路径**（无报错）。
  回落后的行为逐条与「ioctl-only」一致：`ethtool 16_char_devname!` 直接给出
  `netlink interface initialization failed, device name longer than 15 not supported`（该 reason 字符串只可能由 `netlink.c:493` 赋值）；
  `ethtool --json devname` 给出 `ethtool: parameter '--json' can be used only with netlink`（`ethtool.c:6754 exit_nlonly_param`）；
  且这 4 条命令加 `--disable-netlink` 后**返回码与报错逐字相同**（4/4 一致）。
- **旧笔记的归因已作废**：旧文写「8 条不是能力面所致，因为 `send_ioctl` 是 mock」——该推论错误。8 条与 `send_ioctl` mock 无关，也**与运行期网卡能力无关**，而**与运行期能否创建 AF_NETLINK socket 直接相关**；`test-cmdline.c:305` 的 mock 在整个失败路径上根本没有被调用（探针证明失败发生在其之前的 socket 创建）。
- **本配置下无法通过的原因**：`IS_NL` 是**编译期**宏（`test-cmdline.c:15-19`，取 `ethtool-config.h` 的 `ETHTOOL_ENABLE_NETLINK 1`），而期望值只有 netlink 路径真能跑通才成立；
  平台把 AF_NETLINK socket 创建拦成 EACCES（进程 `CapEff=000000000000002a`、`Seccomp=2`），netlink 路径**在运行期不可达** ⇒ 这 8 条条件项在 `--enable-netlink` 配置下**不可满足**。
  ⛔ 未修改上游任何断言、未改 `IS_NL` 口径、未缩分母。

**④ 消费者断言（test_package，5 条）**：见 `test_package/MANIFEST.yml` 的 `assertion_count`；随 `conan create`（G2）真实执行 **5/5**。

## 路径 B「解法对打」（hit 四条件第 1、2 条，只对打 E237 / E240）

### 1）签名是否不同（四条件 1：稳定错误签名 + 触发条件）

| 条目 | 稳定错误签名 | 触发条件 | errno/性质 |
|------|--------------|----------|-----------|
| 本包 | `SIOCETHTOOL(0x8946)` → errno=13（含只读 `ETHTOOL_GDRVINFO`）；`socket(AF_NETLINK,SOCK_RAW,NETLINK_GENERIC)` → errno=13；`/sys/class/net` → errno=13 | 无 CAP_NET_ADMIN/CAP_NET_RAW（`CapEff=000000000000002a`）、`Seccomp=2` 的测试进程发起网卡配置 ioctl / genetlink socket 创建 | **EACCES（权限拦截，接口本体存在）** |
| E237 | `/proc/acpi: No such file or directory`、`/sys/bus/acpi` 不存在、`grep -r NETLINK_GENERIC /proc/net/` 落空 | acpid 启动即探测 ACPI 事件源 | **ENOENT（内核接口缺失）** |
| E240 | `CGDisplayCopyDisplayMode` / CoreGraphics 符号与 API 不可用 | 显示工具调用 macOS 系显示 API | 符号/框架面缺失 |

- **两类墙的判别对照（本包实测）**：`socket(AF_CAN)` → **errno=97 EAFNOSUPPORT**（家族真缺失会走这个码）vs `NETLINK_GENERIC` → **errno=13**（家族在、被权限拦）；正对照 `SIOCGIFFLAGS/SIOCGIFINDEX` rc=0 证明同一 fd 的基础 ioctl 可用 ⇒ 被拦的恰是 ethtool 两面，不是整个网络栈。
- ⇒ 本包签名**在已知条目之外**（图谱 grep `SIOCETHTOOL`/`genetlink-EACCES` 0 命中），属四条件 1 的「已知条目外的新行为偏差 ⇒ 升 B」。

### 2）解法是否不同（四条件 2，关键）

**对 E237（rec=`compile-verify-with-runtime-degradation`，实选其选项 1 `compile-verify-only`）**

- **同形部分（如实认作复用组分，不冒充首创）**：交付骨架 = 编译/verify 全绿 → 作为纯可执行包发布 + 运行依赖缺失写进 notes；forbid 口径（不声称可正常运行）同向。
- **多做了三件 E237 没写的事**：
  1. **归因证据包**：E237 的 `verification_cmd` 只有存在性检查（`ls /proc/acpi`、`grep … /proc/net`），区分不了「接口缺失 ENOENT」与「权限拦截 EACCES」；本包用**差分正对照（同 fd 基础 ioctl rc=0）+ 三机复测（A/B 由 sshd 起进程）+ 进程态（CapEff/Seccomp）+ 两类墙对照（AF_CAN errno=97）**做归因 —— 这一步直接决定甲乙判定与对外措辞，是可复用的判据流程。
  2. **上游降级路径穷举**：`no_dev=true` 仅 `-h|--help`(:6386) 与 `--version`(:6392)、功能命令 94 处 ioctl 或 genetlink、`--disable-netlink` 仅两面互退、`fopen` 落盘先要 `send_ioctl` ⇒ 先证明「上游无非特权替代」再定交付口径；E237 无此层。
  3. **test_package 5 条消费者硬断言**：把「二进制真的跑起来了」变成 CI 可执行判据（退出码 + 非空 + 版本/用法特征串 `grep -q`、无 `|| true`）；E237 选项 1 的验证止于 notes 声明，`rec_impl=compile-verify-only`，没有消费者断言层。
- **少/不同**：未做 E237 选项 2/3（运行期探测 patch、平台 shim）——本包上游自带 `no_dev` 信息面，无需 patch 加探测，且按 R8 不加平台宏。

**对 E240（rec=`capability-split-with-negative-tests`）**

- **解法核心不同**：E240 = **实现了 OHOS 后端**（`OH_NativeDisplayManager_GetDefaultDisplayWidth/Height/RefreshRate` 提供只读指标）+ 对不支持的 list/set 做**负向断言**（`rec_impl=source-patch-and-conan-test-package`）；本包**无后端可实现**（ioctl/genetlink 全 EACCES，上游也没有可插拔后端位），走的是**不实现、只把上游自带 `no_dev` 信息面做成正断言 + 全量披露**。正向断言唯一可支持面 vs 负向断言不支持面 —— 断言方向、判据与写法都不同。
- **E240 的 fallback 也未采用**：其 fallback 是「连只读指标都拿不到就 `validate()` 拒发、不发误导性 CLI」；本包按 ② 类裁决与 appres/ddccontrol 先例走「可执行包 + 信息面断言 + 全披露」——该取舍属对外口径，由主理/用户定，不由配方单方改判。
- **对你的原问精确作答**：**对功能面 = 没有解法、只披露**（如实记「功能面未能实测」）；**对交付面 = 有解法**（差分归因证据包 + 信息面正断言把 CI 判据从「声称」变成「可执行」），而这条交付解法 E237/E240 都没写成可执行规则。

### 3）结论（三选一，待终审）

**选 `create`（组合型知识，按手册/03 §「组合型知识不判重」申报）**：
- 组分清单：E237 交付骨架（编译验证+降级披露）+ E223 configure 补丁方案 + E357 信息面探针口径 + E287/E240 能力拦记账与断言设计；
- 组合后新增面：**「内核接口本体存在、被 capability 拦死」这一格的判据流程**（差分正对照归因 + 两类墙 errno 判别 + 上游无替代穷举 + 信息面正断言交付），池内 0 命中、`OHOS行为探针清单` 无该机制域行；
- 签名层证据：图谱 grep 0 命中、draft-review TOP5 全 <0.5（E008 0.33/E303 0.31/E363 0.23/E237 0.15/E246 0.05）。
- **张力如实交回**：若终审以「交付骨架与 E237 选项 1 同形」改判 `hit(E237)`，则四条件 1 的「症状一致」也需一并放宽（E237=ENOENT 接口缺失 vs 本包=EACCES 权限拦截，且 AF_CAN errno=97 证明本平台家族缺失另有其码）——该取舍归主理。

## 依赖版本

- libmnl/1.0.5（rrev `5f009907`，二进制已发布并精确取得）

## 验证结果

- **conan-verify 第 5 轮（2026-10-17，改动 = `conanfile.py` 在 build() 内追加 `autotools.make(target="check")`、`upstream_test_in_build: true` 后重跑）全绿**：**G0 PASS、G1 PASS、G2 PASS（其内真跑 `make check`：`PASS: test-cmdline` / `PASS: test-features`）、G3 PASS、G4 PASS**、L2/L4/L5 PASS；末行 `✅ 配方验证通过: ethtool 7.1`，退出码 0（`reports/conan-verify-report.md` 内 Verdict PASS / Date `2026-10-17T17:04:35`、`reports/conan-create.log`）。
- **conan-verify 第 4 轮（2026-10-17，改动 = `conanfile.py` 传 `--disable-netlink` 后重跑）全绿**：同上口径（历史记录，Date `2026-10-17T16:49:52`）。
- **conan-verify 第 3 轮（2026-10-08，只改运行环境 CONAN_HOME 为 ASCII 路径后）亦全绿**：同上口径（历史记录，改动前的出厂配置）。
- **回归结论 N/M（2026-10-17 rule4 返修后重测；出厂配置 == 测试配置；上游套件在 `conan create` 内真跑）**：
  - 上游注册测试：**2/2**（出厂 `--disable-netlink` 配置 `make check` rc=0：`TOTAL 2 / PASS 2 / FAIL 0`；★**该 2/2 已在 G2 的 `conan create` 内真实执行**：`reports/conan-create.log:1365 PASS: test-cmdline`、`:1366 PASS: test-features`、`:1370-1374 # TOTAL: 2 / # PASS: 2 / # FAIL: 0`；两用例名与行号见上「① 口径修正」）。
    历史/对照配置（改动前的出厂 `--enable-netlink`）下 `TOTAL 1 / PASS 0`，`test-cmdline` 子用例 **249/257**，
    8 条 FAIL **= 该文件全部 `IS_NL` 条件项**，实测首错 `socket(AF_NETLINK=16,type=3,proto=16) -> -1 errno=13`（125/125 次 EACCES），
    因果链 `nlsock.c:405 → netlink.c:420 → netlink.c:492-495 → :514 静默回落 ioctl` —— 正因该路径是死路径，2026-10-17 已把出厂配置改为 `--disable-netlink`
    （⛔ 未改上游断言、未缩分母、未动 `IS_NL`）
  - 上游判定：**注册用例 2 个（不是 3）** —— `test-common.c` 从不进 `TESTS`/`check_PROGRAMS`（`Makefile.am:83`/`:88`），不是用例
  - 消费者断言（test_package，随 G2 内 conan create 执行）：**5/5**（`--version` 退出码、版本特征串 `ethtool version 7.1`、`-h` 退出码、`Usage:`、`--disable-netlink`，全部 `grep -q` 直断）
  - 源码树编译：`make -j2` 退出码 0（35 条 `-Wgnu-variable-sized-type-not-at-end` 非致命 warning）
- **门禁状态**：conan-verify ✅ → `finish … built` ✅（见下）→ graph validate RC=0 → W4 判决件 `reports/audit-result.json`（待主理亲读）。
---

**编译结束**: 2026-10-08 22:21
**最终状态**: built
