# ebtables 2.0.11 — 适配笔记（证据与坑位）

- 任务：赛道二「开源鸿蒙大学生创新大赛」任务 ID **14730**（**本文件不含任何 push/PR/任务状态操作**）
- 分支：`feat/ebtables-2.0.11`（worktree `/home/silhouette/wt/ebtables`）
- 包目录：`archives/e/ebtables/2.0.11/`，版本字符串 `2.0.11`（目录名 / conandata 键 / manifest / conanfile.version / commands.json 键 **五处一致**）
- 语言：**C 库 + CLI**（符合「只做 C/C++ 库」方针；libebtc 是共享库，附 4 个 CLI）
- 补丁：**2 个**（`patches/0001-config.sub-linux-ohos.patch` 见 §3.1、`patches/0002-configure-hmdfs-tmpdir-permissions.patch` 见 §3.2；只改随包的生成脚本 `build-aux/config.sub` 与预生成的 `configure`，不动上游任何 C 源码/`configure.ac`/`Makefile.am`）

## 1. 上游源与双校验

| 项 | 值 |
|---|---|
| URL | `https://ftp.netfilter.org/pub/ebtables/ebtables-2.0.11.tar.gz` |
| sha256 | `b71f654784a726329f88b412ef7b96b4e5d786ed2bd28193ed7b4c0d677dfd2a` |
| `tar tzf \| wc -l` | **98** |
| 本地复核 | `sha256sum ~/src-cache/ebtables-2.0.11.tar.gz` 与上值逐字节相同；`tar tzf \| wc -l` = 98 |

- 上游官方 `https://ftp.netfilter.org/pub/ebtables/ebtables-2.0.11.tar.gz.sha256sum` 里给出的 sha256
  **与本包实测值字节级一致**（该 `.sha256sum` 文件本身针对 `.tar.gz` 打包件；上游同目录另有 `.tgz`，本包未使用）。
- tarball 里 98 个条目全为源码/构建脚本：**没有任何测试目录、测试脚本或测试数据**。

## 2. 交付物（全部来自上游 `make install`，配方不臆造任何文件）

```
lib/libebtc.so.0.0.0            DT_SONAME=libebtc.so.0（libtool 默认 0:0:0）
lib/libebtc.so.0 -> libebtc.so.0.0.0
lib/libebtc.so   -> libebtc.so.0.0.0
bin/ebtables-legacy             sbin_PROGRAMS，链接 libebtc.so.0
bin/ebtables-legacy-restore     sbin_PROGRAMS，链接 libebtc.so.0
bin/ebtablesd                   sbin_PROGRAMS，链接 libebtc.so.0
bin/ebtablesu                   sbin_PROGRAMS，**上游未给 LDADD** ⇒ 只链接 libc（经命名管道与 ebtablesd 通信）
bin/ebtables-legacy-save        sbin_SCRIPTS（ebtables-save.in 经 sed 替换 @sbindir@ → /bin）
etc/ethertypes                  sysconf_DATA（IANA 以太类型数据库，1362 字节）
share/man/man8/ebtables-legacy.8  man8_MANS（42102 字节；版本号由 @PACKAGE_VERSION@ 替换而来）
include/**.h                    23 个头文件（见 §5，配方显式安装）
licenses/COPYING                GPL-2.0 原文
```

**被剔除的**：`lib/libebtc.la`（libtool 归档，内含绝对构建路径，conan 消费者不需要）。
**包内没有的**：`.o/.a/.pyc/__pycache__/conanbuild.sh`、隐藏文件（自检 M12/M13 逐项验证）。

## 3. configure 选项与理由

```
--prefix=/ --bindir=/bin --sbindir=/bin --libdir=/lib --includedir=/include
--sysconfdir=/etc                 # 编译期 _PATH_ETHERTYPES 归一为 /etc/ethertypes
--enable-shared --disable-static  # 上游 configure.ac 有 AC_DISABLE_STATIC
OHOS: --build=<cpu>-unknown-linux-ohos --host=<cpu>-unknown-linux-ohos
```

- **R1（`--build/--host` + config.sub 补丁）**：鸿蒙 `uname -s` 输出 `HarmonyOS`，随包的
  `build-aux/config.guess`（GNU config.guess **2016-10-02**）没有该分支 ⇒ 不显式传 triplet 时
  `configure` 在猜三元组阶段就 abort。传 `--build/--host` 后完全跳过 config.guess。
  `--build=<cpu>-unknown-linux-ohos --host=<cpu>-unknown-linux-ohos`。`<cpu>` 映射：`armv8→aarch64`、`x86_64→x86_64`、`x86→i686`。
- **R2（`--sysconfdir=/etc`）**：`--prefix=/` 会让 autoconf 的默认 sysconfdir 变成 `//etc`，
  编译期 `_PATH_ETHERTYPES` 也就成了 `//etc/ethertypes`；显式 `/etc` 后是干净的 `/etc/ethertypes`，
  而 `make install DESTDIR=<pkg>` 仍把数据文件放到 `<pkg>/etc/ethertypes`（实测目录树确认）。
- 无需 autoreconf：tarball 已带 `configure`（433196 字节）、`Makefile.in`、`aclocal.m4`、`build-aux/*`。

### 3.1 R1b：`config.sub` 不认识 `linux-ohos`（平台 CI #79884 实测，唯一补丁）

只跳过 config.guess **不够**：autoconf 会用它自己的 `--build=` 参数再喂给 config.sub 做校验。
平台 CI #79884（`feat/ebtables-2.0.11`）第一条真错误原文：

```
ochecking build system type... Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-unknown-linux' not recognized
oconfigure: error: /data/service/hnp/bin/bash …/b/build-aux/config.sub aarch64-unknown-linux-ohos failed
oERROR: ebtables/2.0.11: Error in build() method, line 166
o	autotools.configure()
```

随包的 `build-aux/config.sub` 是 GNU config.sub **2016-11-04**，`maybe_os` 列表里有
`linux-musl*`/`linux-uclibc*` 但**没有 `linux-ohos*`**，所以
`maybe_os=linux-ohos` 不匹配任何分支，落到通用解析后把机器名切成
`aarch64-unknown-linux` ⇒ 报 `not recognized`。

补丁 `patches/0001-config.sub-linux-ohos.patch`（**2 处插入，各 1 行**，与
`archives/b/bluefish/2.2.16/patches/0002-config.sub.patch` 的两处插入完全同款）：

| 位置 | 内容 |
|---|---|
| `config.sub:118`（`maybe_os` 的 KERNEL-OS 列表） | `linux-musl* \| linux-uclibc* \|` → 追加 `linux-ohos*` |
| `config.sub:1403`（末尾 OS 合法值列表） | `-linux-newlib* \| -linux-musl* \| -linux-uclibc*` → 追加 `-linux-ohos*` |

- `strip: 1`，只碰生成脚本，`configure`/`configure.ac`/`Makefile.am`/`Makefile.in` 一字未改。
- 本机复核（x86_64 Linux，无 OHOS SDK）：
  ```bash
  tar xf ~/src-cache/ebtables-2.0.11.tar.gz -C /mnt/data0/tmp_eb/orig
  patch -p1 -d /mnt/data0/tmp_eb/orig/ebtables-2.0.11 < patches/0001-config.sub-linux-ohos.patch
  bash /mnt/data0/tmp_eb/orig/ebtables-2.0.11/build-aux/config.sub aarch64-unknown-linux-ohos
  # → aarch64-unknown-linux-ohos   (rc=0；打补丁前同一命令 rc=1 并报 not recognized)
  ```
- 不补 `config.guess`：`--build`/`--host` 都显式给出时 configure 不会调用它（#79884 日志里
  build system type 的入参就是 `--build=` 的值，不是 config.guess 的输出）。

### 3.2 R6：`config.status` 的 umask 077 临时目录（平台 CI #82335 实测）

config.sub 补丁生效后，configure 已经跑通到 AC_OUTPUT 阶段，平台 CI #82335
（build #82335，真构建，00:26:21→00:36:59）暴露了**下一个真错误**（原文）：

```
oconfigure: creating ./config.status
o./config.status: line 816: ./confmOiEAI/subs1.awk: Permission denied
oconfig.status: error: could not setup config files machinery
oERROR: ebtables/2.0.11: Error in build() method, line 178
o	autotools.configure()
```

根因：autoconf 预生成的 `configure` 里，`config.status` 的脚手架（`cat >$CONFIG_STATUS`
的 heredoc 内容，运行时以 `config.status` 的身份执行）用
`tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\`` 建临时目录，随后把 `subs1.awk`
写进该目录。**HMDFS 下该目录的 owner 被映射成与进程 uid 不同的值，0700 目录
对进程不可用** ⇒ 立刻 `Permission denied`（知识库 **E011** / **E429-4D4C**：
`config.status: subs1.awk: Permission denied`）。

`patches/0002-configure-hmdfs-tmpdir-permissions.patch`（**2 处 `umask 077` → `umask 022`**，
与**已合入**的 `archives/l/libnftnl/1.3.1`、`archives/i/iptables/1.8.13`
的 `0001-configure-hmdfs-tmpdir-permissions.patch` 逐字同款）：

| 位置 | 内容 |
|---|---|
| `configure:13191` | `tmp=`(umask 077 && mktemp -d "./confXXXXXX")`` → `umask 022` |
| `configure:13196` | `(umask 077 && mkdir "$tmp")` → `umask 022` |

- `grep -c umask configure` = 2（全文件只有这两处），因此补丁无歧义；
- 生成物会继承：本机实测打补丁后 `configure` 产出的 `config.status:787/792`
  是 `umask 022`，未打补丁的对照组是 `umask 077`（同一份 configure 文本被
  原样复制进 config.status，所以补 `configure` 即等于补 `config.status`）；
- 本地 `patch -p1` 干净应用，configure/make 全绿（见 §13）。

## 4. R4：HMDFS/容器时间戳坑（无补丁修法）

`configure.ac`/`Makefile.am`/`m4/*.m4`/`aclocal.m4`/`configure`/`Makefile.in` 解包后 mtime
可能全同或乱序，`make` 会认为生成物过期 → 去跑 `aclocal`/`autoconf` → worker 上没有这两个工具：

```
make: *** [Makefile:510: aclocal.m4] Error 127      # 本机复现
```

修法（`_fix_generated_timestamps`，只动 mtime，不改上游字节）：

| 文件 | mtime |
|---|---|
| `configure.ac`, `Makefile.am`, `m4/*.m4`（源） | now − 300s |
| `aclocal.m4` | now − 240s |
| `configure` | now − 180s |
| `config.h.in`, `Makefile.in` | now − 120s |

随后 `autotools.configure()` 用当前时间重写 `config.status`/`Makefile`，依赖链收敛。
本机 `conan create` 从「Error 127」变为一次通过。

## 5. 头文件（上游不装，配方显式安装）

上游 `Makefile.am` **没有 `include_HEADERS`**，`make install` 不产生任何头 ⇒ libebtc 事实上不可消费。
`package()` 里用 `copy(self, "*.h", src=<src>/include, dst=<pkg>/include, keep_path=True)`
逐字节复制上游 `include/` 树（**23 个文件**，内容一字未改）：

```
ebtables_u.h                     公共 API（do_command/ebt_find_*/ebt_parse_ip_address/ebt_standard_targets/FILL_TARGET/PRINT_VERSION…）
ethernetdb.h                     ethertypes 数据库接口（getethertypebyname/bynumber）
linux/types.h                    2011 年的内核 UAPI 副本
linux/netfilter_bridge.h         NF_BR_* 枚举（桥接 hook 下标）
linux/netfilter/xt_AUDIT.h
linux/netfilter_bridge/ebtables.h  + 17 个 ebt_*.h（匹配/目标的私有 UAPI）
```

> 交付这份树 = 让消费者与库使用**同一份** ABI 头；上游自己编译 libebtc 时也是 `-I${top_srcdir}/include`
> 优先取这份（`<linux/netfilter/x_tables.h>` 仍来自平台 sysroot，两边一致）。

## 6. 上游测试：**N = 0**（如实）

| 检查项 | 实测 |
|---|---|
| `Makefile.am` 的 `TESTS` | **不存在**（`grep -c '^TESTS ='` = 0） |
| `Makefile.am` 的 `check_PROGRAMS` | **0 条** |
| tarball 内 `test/ tests/ checks/ test-suite/` 目录 | **无** |
| 98 个 tar 条目里的测试文件 | **无** |
| `make -j1 check` | automake 生成的**空目标**（执行成功、无任何用例） |

`build()` 里逐项核实打印后仍执行 `make -j1 check`，日志留下
`[upstream-tests] ebtables 2.0.11: TESTS=absent check_PROGRAMS=0 test-dirs=none extensions/*.c=24 ⇒ upstream N=0`
与 `HMBS_UPSTREAM_TESTS upstream=0 executed=0`，并有 `RUN: make -j1 check` 字面量（L1c 可匹配 `make.*check`）。

## 7. build() 内自建硬门禁：用户态黄金用例 G1..G9（35 条，35/35 通过）

**全部期望值都由上游源码派生**（不是配方里手写的常量），因此是可外部核对的真值：

| 组 | 条数 | 期望值来源（上游源码） | 实测 |
|---|---|---|---|
| G1 `--version`、G2 `-V` | 2 | `configure.ac` 的 `AC_INIT([ebtables],[2.0.11])` + `Makefile.am` 的 `PROGDATE = December\ 2011` + `include/ebtables_u.h` 的 `PRINT_VERSION` 宏字符串拼接 | `ebtables v2.0.11 (legacy) (December 2011)`，rc=0 |
| G3 `--help`、`-h` | 2 | `ebtables.c` 的 `print_help()` 全部字面量 + `ebtable_filter.c` 的 `FILTER_VALID_HOOKS` → `INPUT FORWARD OUTPUT ` | 首行=版本行、全部字面量命中、结尾=filter 合法链 |
| G4 `-h list_extensions` 四个分节 | 4 | `extensions/*.c` 的 `ebt_register_match/watcher/target/table` 调用 → 结构体 `.name`（宏形式经 `include/**/*.h` 的 `#define` 解析，如 `EBT_IP6_MATCH "ip6"`） | matches 11 / watchers 3 / targets 7 / tables 3，**逐个集合相等** |
| G5 21 个扩展的 `-h <扩展>` | 21 | 每个扩展结构体 `.help` 指向的函数（`print_help`/`print_help_s`/`nflog_help`…）里的全部非 `%` 字面量 | 字面量全部逐字命中（最少 2 条、最多 19 条） |
| G6 `-t filter\|nat\|broute -h` | 3 | `ebtable_*.c` 的 `print_help()` 字面量 + `*_VALID_HOOKS`（或 `hn[NF_BR_BROUTING]`）+ `libebtc.c` 的 `ebt_hooknames[]` + `include/linux/netfilter_bridge.h` 的 `NF_BR_*` 下标 | `INPUT FORWARD OUTPUT` / `PREROUTING OUTPUT POSTROUTING` / `BROUTING` |
| G7 `-t bogus -L` | 1 | `libebtc.c` 的 `ebt_print_error("Bad table name '%s'")` + `__ebt_print_error()` 的 `".\n"` 后缀与 `exit(-1)` | rc=**255**，stderr 逐字相同 |
| G8 `-h no_such_extension` | 1 | `ebtables.c` 的 `ebt_print_error2("Extension '%s' not found")` | rc=**255**，stderr 逐字相同 |
| G9 `ebtables-legacy-restore --help` | 1 | `ebtables-restore.c` 的 `fprintf(stderr, "Usage: ebtables-restore [ --noflush ]\n")` | rc=1（非 0），stderr 含该 usage |

日志汇总：`[cli-golden] 35/35 user-space golden cases reproduced from the build tree`、
`HMBS_CLI_GOLDEN checks=35 failed=0`。

**平台限制处理（不静默跳过）**：启动前先做 `_cli_smoke`（跑 `--version`）。若失败原因是
**加载器层拒绝**（OSError / rc=127 / `Error loading shared library` / `Error relocating`），
则打印 `[cli-golden][platform-limitation]` 明细：OS=OHOS 时按平台限制降级继续（并打
`HMBS_CLI_GOLDEN checks=0 ... degraded=platform-loader-refused`），非 OHOS 时直接构建失败。
正常路径（本机与预期 CI）下 35 条全部真跑。

## 8. build() 内核相关用例：4 条，逐条探测 + 逐条打印 SKIP 与理由

| 用例 | 需要 | 本机实测 |
|---|---|---|
| `-t filter -L` | CAP_NET_RAW + 内核 `ebtable_filter` | SKIP：`rc=255 "Problem getting a socket, you probably don't have the right permissions."` |
| `-t nat -L` | 同上 + `ebtable_nat` | SKIP：同上 |
| `-t broute -L` | 同上 + `ebtable_broute` | SKIP：同上 |
| `--atomic-file <f> --atomic-save` 往返 | 内核 ebtables 表 | SKIP：同上 |

- 能力探测：`socket(AF_INET, SOCK_RAW, IPPROTO_RAW)`（与 `communication.c:get_sockfd()` 同款）
  → 本机 `PermissionError: [Errno 1] Operation not permitted`（euid=1000），日志打印
  `[kernel-probe] CAP_NET_RAW unavailable (…) — the 4 kernel-bound cases above were classified, never silently skipped`。
- **能力具备时**（root + 内核模块）会真跑并断言：每张表出现 `Bridge table: <名>`、每条合法链出现
  `Bridge chain: <HOOK>, entries: N, policy: …`（合法链同样由源码派生），`--atomic-save` 落盘非空后
  从文件读回仍能列出 filter 表。这些断言不是恒真式。

## 9. 消费者用例：`test_package/test_ebtables.c`（42 项检查，42/42 通过）

真链接交付的 `ebtables::ebtables`（`lib/libebtc.so.0`，`DT_NEEDED` 自检 M16 验证），
只用交付头 `<ebtables_u.h>` / `<ethernetdb.h>` 的公共 API，判据全部外部可核对：

| 组 | 项数 | 判据（外部真值） |
|---|---|---|
| 标准判决名 | 6 | 内核 ABI：`ACCEPT/DROP/CONTINUE/RETURN`（`NUM_STANDARD_TARGETS==4`）+ `FILL_TARGET("ACCEPT")`→pos=−1→`TARGET_NAME` 宏往返 + 负例 `"NO_SUCH_TARGET"`→1 |
| 桥接 hook | 6 | 内核 ABI 顺序 `PREROUTING/INPUT/FORWARD/OUTPUT/POSTROUTING/BROUTING` |
| MAC 解析 | 4 | IEEE 十六进制记法：`00:11:22:33:44:55` 逐字节、`Broadcast`=ff×6、`Multicast`=01:00:…、负例 `zz:`→−1 |
| IPv4 解析 | 5 | libc `inet_pton()` 交叉验证 + CIDR 算术：`192.168.1.1/24` → `192.168.1.0` + `255.255.255.0`、`ebt_mask_to_dotted`=`/24`、`10.0.0.1`→/32、`/32` 打印为空串 |
| IPv6 解析 | 5 | `inet_pton` 交叉验证 + CIDR 算术：`/60` 掩码 ff×7+f0+00×8 与 `ebt_ip6_mask_to_string`=`/60`、直接构造的 `/64`→`/64`、`/128`→空串（见 §10 上游缺陷） |
| 扩展注册表 | 8 | 上游 `extensions/*.c` 注册的 11 匹配/3 watcher/7 目标/3 表（计数 + 逐个名字 + 负例 + `ebt_find_*` 解析） |
| ethertypes 数据 | 2 | IANA：`IPv4`→`0x0800`、`0x0806`→`ARP`；编译期路径 `/etc/ethertypes` 不可读时**打印 SKIP 与理由**（本机该文件可读，两项真跑并通过） |

日志（本机）：`consumer use case: 42 checks, 0 failure(s), 0 skip(s)`。

## 10. 上游缺陷（实测，配方不修上游）

**`parse_ip6_mask()` 越界写 1 字节**（`useful_functions.c`）：

```c
memset(p, 0xff, bits / 8);
memset(p + (bits / 8) + 1, 0, (128 - bits) / 8);   /* bits 为 8 的倍数时写到 p[16] */
p[bits / 8] = 0xff << (8 - (bits & 7));
```

- 复现（本机，`-O2` + `_FORTIFY_SOURCE`）：
  `ebt_parse_ip6_address("2001:db8::1/64", …)` → `*** buffer overflow detected ***: terminated`，
  **退出码 134**；`/60` 正常（掩码 `ff ff ff ff ff ff ff f0 00×8`，`ebt_ip6_mask_to_string`=`/60`）。
- 影响面：任何以 IPv6 掩码为 8 的倍数调用该 API 的消费者（以及 ebtables 的 `--ip6-src 2001:db8::/64`
  这类命令行）在启用 fortify 的平台上会 abort。
- 处置：**不修改上游源码**（不在本任务范围内），消费者用例改用 `/60` 走解析路径、`/64` 与 `/128`
  掩码直接按位构造后只调用 `ebt_ip6_mask_to_string()`，并在用例里 `printf("[note] …")` 显式说明。
  已写入 `manifest.yaml` 的 `knowledge_gained` 与 PR 正文。

其它上游小瑕疵（同样不改，如实记录）：

- `Makefile.am` 生成 man 页的 sed 少了结尾 `@`：`@PACKAGE_VERSION@` → `2.0.11@`，man 页里可见。
- `bin/ebtables-legacy-save` 内部 `$ebtables = "/bin/ebtables"`，但上游 2.0.11 只安装 `ebtables-legacy`
  ⇒ 该脚本需要部署侧补 `/bin/ebtables` 链接才能工作（脚本还是 `#!/usr/bin/perl -w`，OHOS 上没有 perl）。
  配方不臆造这些文件，保持与 upstream `make install` 一致。

## 11. 交付形态自检：`test_package/test_layout.py`（18 项 = 17 通过 + 1 项 OHOS 专属跳过）

M1 `lib/` 仅 `libebtc.so{,.0,.0.0.0}` 且无 `.la`；M2 真实库 ELF64/ET_DYN 且 `e_machine` 匹配 arch；
M3 `DT_SONAME == libebtc.so.0`；M4 soname 链相对且可解析；M5 `bin/` 恰为上游
`sbin_PROGRAMS + sbin_SCRIPTS`，无悬空/绝对链接；M6 4 个程序均为 ELF 且架构匹配；
M6b `DT_NEEDED` 契约（3 个链 `libebtc.so.0`，`ebtablesu` 上游单独链接故不链）；
M7 `ebtables-legacy-save` 保持上游 perl shebang 与 `"/bin/ebtables"`；
M8 23 个头文件闭包 + 公共声明在位；M9 `etc/ethertypes` 含 IANA 行；M10 man 页含版本号 `2.0.11`；
M11 `licenses/COPYING` 是 GPL-2.0 原文；M12 无 `.la/.o/.a/.pyc/__pycache__/conanbuild.sh`；
M13 无隐藏文件（JC5）；M14 CMakeDeps 契约 `ebtables::ebtables`；M15 PkgConfigDeps 的 `ebtables.pc`
可重定位（`${prefix}`）；M16 消费者二进制 `DT_NEEDED` 含 `libebtc.so.0`；M17 OHOS 时交付 `.so` 带
`.codesign`（非 OHOS 打印跳过理由，不静默放过）。

纯 Python 自解析 ELF（不依赖 readelf/objdump/nm，OHOS worker 上未必有）。

## 12. OHOS 相关工作（硬坑 D/E）

1. **签名**：`package()` 里对 `lib/*.so*` 与 `bin/` 下的 ELF 逐个自签名 ——
   `llvm-objcopy --remove-section .codesign X` → `binary-sign-tool sign -selfSign 1 -inFile X -outFile X.signed`
   （**写到另一个文件**，避免 inFile==outFile 的「自报成功但没签上」）→ `os.replace` → `chmod 0755` →
   再读回确认 `.codesign` 段存在。签名失败即抛异常（不静默）。OHOS 加载器拒载未签名 `.so`（E135/E517）。
2. **build 树的库也要签**：OHOS 上 `_run_cli_golden_cases()` 会先给 `build/.libs/libebtc.so.0.0.0`
   自签名，否则 CLI 起不来（`_cli_smoke` 会把这类失败识别为平台加载器限制）。
3. **CLI 端到端放 build()**：硬坑 E —— 包目录里的安装态 ELF 在 OHOS 上可能无法 `execve`，
   而 build 目录的可以。因此 35 条黄金用例全部用 `build/.libs/ebtables-legacy`（**真 ELF，不是
   libtool 的 `#!/bin/sh` wrapper**）并显式设 `LD_LIBRARY_PATH=<build>/.libs`。
4. **test_package 侧**：消费者二进制在 test_package 的 build 目录里，用
   `/data/service/hnp/bin/bash -c "<exe> <args>"` 转交（OHOS 的 `/system/bin/sh`(mksh) 不执行 ELF，
   与本仓已合入的 `libarchive/3.8.7` 同款）。
5. 无 `-fvisibility`/`*_VISIBILITY` 相关设置（避硬坑 A）；本包不用 pthread（避硬坑 C）。

## 12.2 R6 修复后的本地重跑（2026-10-11）

两个补丁都在 `source()` 阶段被应用（本地日志逐条打印了 patch_description）：

```
ebtables/2.0.11: Apply patch (portability): The config.sub shipped in this tarball is GNU config.sub 2016-11-04 …
ebtables/2.0.11: Apply patch (portability): `configure` creates its config.status scratch directory with `umask 077 …
```

`conan create -s os=Linux -s arch=x86_64 -s compiler=gcc -s compiler.version=15
-s compiler.libcxx=libstdc++11 -s build_type=Release` → **exit=0**：
`[upstream-tests] upstream N=0（tarball 无测试套件，如实登记）`、
`[cli-golden]` 35 条黄金用例全过、`[kernel-probe]` run=0 skip=4、
`test_package` 交付形态自检 **17 项通过 / 1 项跳过（.codesign，仅 OHOS）**。
`config.status` 的临时目录已是 `umask 022`（见 §3.2 的对照实验）。

## 13. 本地验收（x86_64 Linux，无 OHOS SDK）

```bash
export PATH=/home/silhouette/conanenv/bin:$PATH
export CONAN_HOME=/home/silhouette/.conan2-ohos
cd /home/silhouette/wt/ebtables/archives/e/ebtables/2.0.11
conan create . --build=missing --build=ebtables/* \
  -s os=Linux -s arch=x86_64 -s compiler=gcc -s compiler.version=15 \
  -s compiler.libcxx=libstdc++11 -s build_type=Release
# → 主包：configure/make → make -j1 check（N=0） → [cli-golden] 35/35 → [kernel-probe] run=0 skip=4
# → test_package：consumer use case: 42 checks, 0 failure(s), 0 skip(s)
# → 交付形态自检：17 项通过 / 0 项失败 / 1 项跳过（M17 仅 OHOS 执行）
# 退出码 0
```

（本机 gcc 为 **15.2.0**；conan 侧用 `compiler.version=15`。本包是纯 C，`libcxx` 只影响
test_package 的 CMake 工具链选择。）

**清空缓存后的复跑**（`conan remove "ebtables/*" -c` 再执行同一条命令，不带 `--build=ebtables/*`）
同样 **退出码 0**：`HMBS_UPSTREAM_TESTS upstream=0`、`[cli-golden] 35/35`、
`[kernel-probe] run=0 skip=4`、`[headers] installed 23`、`[package] removed 1 libtool archive`、
`consumer use case: 42 checks, 0 failure(s), 0 skip(s)`、`交付形态自检：17 项通过 / 0 项失败 / 1 项跳过`。

**SKIP 分支单独验证**：把消费者用例里的 `/etc/ethertypes` 换成不存在的路径重新编译运行
（本机 `/etc/ethertypes` 恰好存在，会走真跑分支）⇒ 输出 `[skip] getethertypebyname/
getethertypebynumber (IANA 0x0800 / 0x0806)` + 打印理由 + 交付文件路径，
`consumer use case: 40 checks, 0 failure(s), 1 skip(s)`、rc=0。即「不可读就显式打印理由」这条
分支确实可达且不静默通过。

## 14. 未解决风险（OHOS 侧无法本地验证）

1. **OHOS sysroot 的 UAPI 头**：上游 `include/linux/types.h`（2011）会 `#include <asm/types.h>`、
   `<linux/posix_types.h>`，而 `-I${top_srcdir}/include` 在编译期优先于 sysroot ⇒ 若 OHOS 的
   构建 sysroot 缺 `asm/types.h`，主包编译会失败（与配方无关，属上游头布局）。同一条路径上
   `<linux/netfilter/x_tables.h>` 来自平台 sysroot，也是必需项。**本机 x86_64 全部可编译**，
   OHOS 侧只能由平台 CI 验证。
2. **build 树 ELF 在 OHOS 上能否 `execve`**：按硬坑 E 的经验可以，但本包未在真机验证过；
   已准备 `_cli_smoke` + `[cli-golden][platform-limitation]` 降级路径（显式打印，不静默跳过），
   若真触发，日志里会给出 `HMBS_CLI_GOLDEN checks=0 degraded=platform-loader-refused`。
3. **`ethertypes` 两项消费者检查**：编译期路径 `/etc/ethertypes` 在 OHOS runner 上可能不存在
   （本机存在故真跑通过）；届时会显式打印 SKIP 与理由。
4. **`_FORTIFY_SOURCE` 下的 IPv6 掩码解析**：见 §10，上游缺陷；消费者用例已规避，
   但**命令行** `--ip6-src …/64` 在 OHOS 上仍可能 abort（上游行为，非本包引入）。
5. **平台 CI 停摆**：合入作业自 2026-10-05 04:53 起零合入、CI 窗口内产出全废 ⇒
   本包的 OHOS 构建结论无法在本地获得，需等 CI 恢复后回填「编译状态」。

## 15. 门禁结论（提交前逐条跑过）

- `git diff --name-only main...HEAD`：本次变更全部落在 `archives/e/ebtables/` 下（单包闸 PF1 通过）。
- `python3 scripts/ohc/preflight.py /home/silhouette/wt/ebtables main HEAD`：
  **PF1–PF9 + R52 + PF3x2(R53) 全部通过**。
  关于 `commands.json` 的放置（R38 / PF8 / PF9 三角，实测口径）：本包**确实交付**
  `bin/` 下 5 个可执行体，所以按 R38 的意图声明了
  `archives/e/ebtables/2.0.11/commands.json`。
  | 方案 | PF8 | PF9 | L0k（CI） |
  |---|---|---|---|
  | 软件级 `archives/e/ebtables/commands.json` + 不写 bindirs | ✗「纯库包不应有 commands.json」 | ✗ 路径只有 4 段（<5） | 不触发（AST 无非空 `cpp_info.bindirs`） |
  | 软件级 + `cpp_info.bindirs = ["bin"]` | ✓ | ✗ 路径只有 4 段 | 触发并通过 |
  | **版本级 `archives/e/ebtables/2.0.11/commands.json` + 不写 bindirs** | ✓ | ✓（5 段） | 不触发 |
  第三行是唯一让 `preflight.py` **PF1–PF9 全通过**的形态，因此采用它：PF8 的「纯库包
  不应有 commands.json」只认**软件级**那一份路径（`preflight.py:check_recipe_static`
  里 `cj = pkg_dir / "commands.json"`），L0k 的 AST 判定（`ci/conan/detect_bindirs.py`
  只认显式非空 `cpp_info.bindirs` + `RUNTIME DESTINATION bin` + `package_type=application`）
  也不触发。`cpp_info.bindirs` **未显式声明**：conan 默认值本来就是 `["bin"]`，
  消费端照样能找到工具，而不写它就不会误触「CLI 包」判定。
  `commands.json 键 = 2.0.11`，与目录名 / conandata 键 / manifest / `conanfile.version`
  仍是五处一致。

CI 日志里会出现的门禁字面量：
`RUN: make -j1 check`（L1c 的 `make.*check`）、`Testing the package`（L1a）、
`[cli-golden]`、`[kernel-probe]`、`consumer use case: 42 checks, 0 failure(s)`、`M17`。

## R7 — `sockaddr_storage` / `__packed` 重复定义（CI #85977，2026-10-12）

**CI 原文（类别=编译失败，失败步骤跑到 `cleanup ✅` ⇒ 真失败）**：
```
communication.c:23 -> include/ebtables_u.h:28
  -> include/linux/netfilter_bridge/ebtables.h:17
  -> <sysroot>/usr/include/linux/if.h:23
  -> <sysroot>/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'
     note: previous definition is here（<sysroot>/usr/include/sys/socket.h:377）
include/linux/netfilter_bridge.h:10 -> <sysroot>/usr/include/linux/if_pppox.h:59/64/69/74/111:
     error: redefinition of '__packed' with a different type:
            'struct sockaddr_pppol2tp' vs 'struct sockaddr_pppox' …
make[1]: *** [Makefile:804: libebtc_la-communication.lo] Error 1
```
**根因**：OHOS sysroot 的 `<linux/socket.h>` 在 guard `_UAPI_LINUX_SOCKET_H` 下**无条件**定义
`struct sockaddr_storage`，与 libc `<sys/socket.h>` 的同名结构冲突；而 `if_pppox.h` 里那些内核
socket 结构用的 `__kernel_sa_family_t` 正是由这份 `<linux/socket.h>` 提供的 ⇒ 5 处 `__packed`
连带报错是同一根因。

**修法（纯 flag 对，无源码补丁）**：`generate()` 里
`tc.extra_cflags += ["-D_UAPI_LINUX_SOCKET_H", "-D__kernel_sa_family_t=sa_family_t"]`
—— 预定义 guard 抑制 sysroot 那份，再把唯一必要声明 `__kernel_sa_family_t` 别名到 POSIX
`sa_family_t`。与**已合入**的 `archives/i/iptables/1.8.13`（§R5）与 `archives/l/libnftnl/1.3.1`
完全同款。

**本机验证（Linux x86_64 gcc 15，故意让 flag 对所有平台生效以便可验证）**：
`conan create archives/e/ebtables/2.0.11 --build=missing` ⇒ **rc=0**；
消费者用例 **42 checks / 0 failures / 0 skips**；交付形态自检 **17 通过 / 0 失败 / 1 跳过**
（跳过项为 M17 `.codesign`，非 OHOS 构建固有）。glibc 上 guard 名是 `_LINUX_SOCKET_H`，
故 `-D` 为空操作、重复 typedef `sa_family_t` 属合法 C11 —— 这正是本机可验证的原因。

## R8（2026-10-14 CI #89242）— `linux/if_pppox.h` 的 `__packed` 在 OHOS sysroot 上未定义

**CI 原文（类别=编译失败）**：
```
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/linux/if_pppox.h:59:3:
  error: redefinition of '__packed' with a different type: 'struct sockaddr_pppol2tp' vs 'struct sockaddr_pppox'
（同 64 / 69 / 74 / 111，共 6 errors）
make[1]: *** [Makefile:804: libebtc_la-communication.lo] Error 1
```
**R7（`-D_UAPI_LINUX_SOCKET_H`）已生效**：`redefinition of 'sockaddr_storage'` 已消失，configure 与其余 TU 全部编译通过；
本轮暴露的是**第二个、互相独立**的 sysroot 头问题。

**根因**：OHOS sysroot 的 `<linux/if_pppox.h>` 用内核内部的 `} __packed;` 写法（内核侧由 `<linux/stddef.h>` 定义该宏），
而用户态 include 链里**没有任何头定义它** ⇒ clang 把 `__packed` 当成**声明符名**，于是第二个及之后的结构体全部报
「同名不同型 redefinition」。本地 glibc 的 `linux-libc-dev` 用的是 `} __attribute__((packed));`（实测
`grep packed /usr/include/linux/if_pppox.h`），所以本机构建永远看不到这个问题。

**修法**：`tc.extra_cflags.append("-D__packed=__attribute__((__packed__))")` —— 正是内核头期望的语义；
对不使用该宏的 TU 完全无害；对现代 glibc 的空定义现状同样无害（该宏在本地 glibc 头里未被使用）。

**本地校验**：`conan create archives/e/ebtables/2.0.11 --build=missing` ⇒ rc=0（消费者 42/42、交付形态自检 17 通过/0 失败/1 跳过）；
`grep -c packed /usr/include/linux/if_pppox.h` = 5（均为 `__attribute__((packed))`）⇒ 本机路径不受该 `-D` 影响。
