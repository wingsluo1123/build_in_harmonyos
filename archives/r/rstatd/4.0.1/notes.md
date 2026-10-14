# rstatd 4.0.1 适配笔记

**生成日期**: 2026-10-03
**结论**: 适配成功，`conan create` 通过（rc=0），test_package 41 项断言全过。

---

## 1. 软件与上游

| 项 | 值 |
|---|---|
| 三方库 | rstatd（ONC RPC 远程统计守护进程） |
| 版本 | 4.0.1 |
| 上游 | http://rstatd.sourceforge.net/ （rstatd SourceForge 项目） |
| 源码 | `rpc.rstatd-4.0.1.tar.gz`，86883 字节 |
| SHA256 | `b1ff2da2fb8516335c8e430a479779630fce4955ad564156da381864bb301843` |
| MD5 | `116d9a8a35656e76f16c679d0596519a` |
| 许可证 | GPL-2.0-or-later（`COPYING`） |
| 构建系统 | autotools（autoconf 2.59，2005 年，**in-tree**，`srcdir = .`） |

**上游产物溯源**：该 tarball 的 MD5 `116d9a8a35656e76f16c679d0596519a` 与 Debian
（`rstatd_4.0.1-3` … `4.0.1-12`）和 Ubuntu（`rstatd_4.0.1-11`）重打包时使用的
`rstatd_4.0.1.orig.tar.gz` 完全一致，可确认是未经改动的上游发布件（R39）。

安装三个可执行文件：

| 程序 | 作用 |
|---|---|
| `rpc.rstatd` | ONC RPC 程序号 100001 的守护进程，提供负载/分页/上下文切换/磁盘/网络/在线用户等统计 |
| `rup` | RSTATVERS_USERS(5) 客户端 |
| `rsysinfo` | RSTATVERS_TIME(3) 客户端 |

---

## 2. W0 — 依赖发布检查

rstatd 是 SunRPC 客户端/服务端，核心依赖是 SunRPC（`<rpc/rpc.h>`、`<rpc/clnt.h>`、
`<rpc/pmap_clnt.h>` 以及 `xdr_*` / `svc_*` / `clnt_*` 实现）。

**结论：OHOS sysroot 里完全没有 SunRPC。** 实测：

```bash
find /mnt/c/Users/13909/ohos-sysroot -name 'rpc.h'        # 无输出
find /mnt/c/Users/13909/ohos-sysroot -name 'pmap_clnt.h'  # 无输出
```

按 R35 用 `conan download --only-recipe` 逐个探测制品仓（不存在时该命令报
`error:system acceleration policy not enabled`，这是"未发布"的固定表现）：

| 候选 | 结果 |
|---|---|
| `libtirpc/1.3.3` / `1.3.2` / `1.3.1` / `1.2.0` | 未发布 |
| `glibc/2.31` / `2.34` / `2.38` / `2.39` / `2.17` | 未发布 |
| `rpcsvc/1.4.3` / `1.4.4` | 未发布 |
| `sunrpc/1.0` | 未发布 |
| `nfs-utils/2.6.4` / `2.6.3` / `2.5.9` | 未发布 |
| **`libtirpc/1.3.7`** | **已发布**（`libti8b0cdb26520ed`） |
| `libnsl/2.0.1` | 已发布 |

因此**依赖已满足，无需先适配依赖包**：`self.requires("libtirpc/1.3.7")`。
本仓已有先例：`archives/l/libnsl/2.0.1` 同样 requires libtirpc/1.3.7，
`archives/l/libtirpc/1.3.7` 就是本仓已合入的配方。

---

## 3. W0b — CI 能力矩阵

| 工具链 | CI 现状 | 本包是否需要 |
|---|---|---|
| clang / make / cmake | ✅ | 是 |
| autoconf/automake | ❌ 无 | **否** —— tarball 自带 configure 与 Makefile，build() 不需要 autoreconf |
| **rpcgen** | ❌ 无 | **需要，但拿不到 → 见第 5 节** |

`rpcgen` 是本包唯一的工具链缺口，处理方式见第 5 节。

---

## 4. 源码适配（8 个补丁，全部登记在 conandata.yml）

补丁按"一次改动一个补丁"的方式用 `diff -u` 从原始 tarball 逐个生成，
保证按序 `patch -p1` 应用不冲突、不重复。**没有任何补丁使用平台宏
（`__OHOS__` / `_WIN32` 之类），R8 合规。**

### 0001 `rstat_proc.c`：删死包含 + 补 `__P()` 宏（portability）

* `#ifndef __GLIBC__ #include <nlist.h> #endif` —— OHOS 不是 glibc，走进了分支，
  而 musl 没有 `<nlist.h>`：

  ```
  rstat_proc.c:42:10: fatal error: 'nlist.h' file not found
  ```

  全树检索确认 `struct nlist` / `kvm` / `getkvm` **一次都没被使用**
  （`grep -rn 'nlist' *.c *.h *.in *.am` 除这一行外无输出），是纯死包含，删除。

* `char *(*local) __P ((void *, struct svc_req *));` —— `__P()` 是 glibc
  `<sys/cdefs.h>` 导出的原型括号宏，OHOS 既没有 `<sys/cdefs.h>` 也没有 `__P`：

  ```
  rstat_proc.c:167:16: error: expected ';' at end of declaration
  ```

  按 glibc 自己的定义补上（对 C99 编译器是空操作）：

  ```c
  #ifndef __P
  # define __P(args) args
  #endif
  ```

### 0002 `rup.c` / `rsysinfo.c`：`rindex()` → `strrchr()`，`char c` → `int c`

* `rindex()` 已被 POSIX 移除，musl 从未提供，链接期直接失败：

  ```
  ld.lld-15: error: undefined symbol: rindex
  ```

  用语义完全相同的标准函数 `strrchr()` 代替（两个文件各一处，用来取 `argv[0]` 的基名）。

* **这是会在真机上死循环的隐患**，不是洁癖问题：

  ```
  rsysinfo.c:182:38: warning: result of comparison of constant -1 with expression of
                        type 'char' is always true [-Wtautological-constant-out-of-range-compare]
          while((c = getopt(argc,argv,"h?v")) != EOF)
  ```

  OHOS clang 默认带 `-fno-signed-char`（`-dM -E --target=aarch64-linux-ohos` 可验证），
  `char` 无符号，`(char)EOF == 255 != -1`，`!=` 恒真 → 参数循环永不退出。
  改成 `int c` 即可。

### 0003 `getdata.c`：现代内核的 /proc 采集器选择（**功能适配，R40 关键项**）

这是本包最重要的适配点，**编译完全通过也不代表适配完成**。

`getdata_setup()` 用字面前缀比较选择采集器：

```c
if (0 == strncmp(u.release, "2.2", 3)) { getdata.disk = get_disk22; }
if (0 == strncmp(u.release, "2.4", 3)) { getdata.disk = get_disk24; }
if (0 == strncmp(u.release, "2.6", 3)) { getdata.disk = get_disk26; getdata.vm = get_vm26; }
```

鸿蒙 PC 的 Linux 内核是 5.x / 6.x，三个分支**都不匹配**，`getdata.disk` 保持初值
`get_disk()`，而它是这样的占位函数：

```c
static void get_disk(struct statsusers *s) {
	syslog(LOG_CRIT, "dummy function, should never be called!");
	exit(EXIT_FAILURE);
}
```

也就是说**守护进程收到第一个 STATS 请求就会 `exit(EXIT_FAILURE)`**，服务完全不可用。

改成按数值比较主次版本号：2.2 / 2.4 的赋值原样保留，2.5 及以上一律走 2.6 引入的
`/proc/diskstats` + `/proc/vmstat` 采集器；解析失败时明确报错退出而不是静默退化。
补丁不含任何平台宏，靠 `uname().release` 的数值语义工作。

### 0004 `rstat_main.c`：`<string.h>` / 冲突声明 / `fromlen`（portability）

* `strcmp()` 之前是隐式声明 → 补 `<string.h>`；
* `extern void rstat_service();` 与 `rstat_proc.h` 里带两个参数的原型冲突 → 删除冗余声明；
* `int fromlen, sock = 0, proto = 0;` 之后直接把 `&fromlen` 传给
  `getsockname()`，**长度未初始化** → 改成
  `socklen_t fromlen = sizeof(struct sockaddr_in);`（同时消掉指针符号不匹配警告）。

### 0005 采集器数据正确性（correctness）

`getdata.c` 有三处 `memset()` **参数顺序颠倒**：

```c
memset(s, sizeof(struct statsusers), 0);   /* 实际写入 0 字节！ */
memset(rx[i], sizeof(regex_t), 0);
memset(&u, sizeof(u), 0);
```

编译器的 `-Wmemset-transposed-args` 精确指出了位置。`getdata_collect()` 的语义是
"先清空回复结构体再采集"，参数颠倒后**上一次 RPC 调用残留的值会混进下一次应答**
（磁盘计数、`avenrun`、网络计数都可能带上陈旧值）。三处改为 `memset(p, 0, sizeof(T))`。

另外 `getdata22.c` / `getdata26.c` 调用 `strncmp()` 却没包含 `<string.h>`（隐式声明，
C2x 下是错误）→ 补上。

### 0006 删除冗余 K&R 声明（cleanup）

0002 补的 `<string.h>` 已提供 `bzero()` / `bcopy()` 的真实原型，两个客户端里的
`void bzero(); void bcopy();` 空参数重声明变成冗余且与原型冲突，删除。

### 0007 内置 rpcgen 生成的 `rstat.h`（**构建必需**）

`Makefile.am` 把 `rstat.h` 列进 `BUILT_SOURCES`，并用 `rpcgen -h -o rstat.h rstat.x`
生成，`rup.c` / `rstat_proc.c` 都 `#include "rstat.h"`。但发布 tarball **只带了另外三个
生成文件**（`rstat_svc.c` / `rstat_clnt.c` / `rstat_xdr.c`），没有 `rstat.h`
（`dist-hook` 会把四个都删掉，但实际发布的 tarball 留下了三个 `.c`）。
所以缺 `rpcgen` 就**无法开始构建**。

**为什么不能靠装包解决**：第 2 节已逐个探测，制品仓里没有任何包提供 `rpcgen`
（`libtirpc` 的包内也没有 —— 它的 `bin/` 是空的，`etc/` 只有 `netconfig` 和
`bindresvport.blacklist`）。

**为什么不裁剪软件**：本补丁带入的是 rpcgen 对**未修改的** `rstat.x` 的确定性输出，
而且可以证明所用生成器与上游一致 —— 用同一个 rpcgen 执行
`rpcgen -c -o rstat_xdr.c rstat.x`，生成的 `rstat_xdr.c` 与 tarball 自带的
`rstat_xdr.c` **逐字节相同**（972 行，`diff` 无差异）。这同时排除了"手工编造生成物"。

配方侧配套：`build()` 里对 `rstat.h` / `rstat_svc.c` / `rstat_clnt.c` / `rstat_xdr.c`
四个文件 `os.utime()`，让它们比 `rstat.x` 新，于是 make 永远不会触发
`rm -f $@; rpcgen ...` 那几条规则。

---

## 5. 配方里两处非平凡决策

### 5.1 libtirpc/1.3.7 已发布二进制不导出 `cpp_info`

第一次 `conan create` 直接编译失败：

```
./rstat.h:9:10: fatal error: 'rpc/rpc.h' file not found
rup.c:29:10: fatal error: 'rpc/rpc.h' file not found
...
```

原因：`archives/l/libtirpc/1.3.7/conanfile.py` 里确实写了
`cpp_info.includedirs = ["include", "include/tirpc"]` 和 `cpp_info.libs = ["tirpc"]`，
但**已发布二进制的 `conaninfo.txt` 里完全没有 cpp_info 段**（只有 `[settings]` 和
`[options]`）：

```bash
$ cat <libtirpc-pkg>/conaninfo.txt
[settings]
arch=armv8
build_type=Release
compiler=clang
...
[options]
shared=False
```

`archives/l/libnsl/2.0.1/test_package/conanfile.py` 的注释记录了同一现象
（"its libtirpc.pc carries the right Cflags, its cpp_info does not"），
那里是在 test_package 里绕过；本包在**主配方**里绕过，因为主配方就要编译。

配方 `_tirpc_flags()` 从 `self.dependencies["libtirpc"].package_folder` 解析出
`<pf>/include/tirpc`、`<pf>/include`、`<pf>/lib`，经 `CPPFLAGS=` / `LDFLAGS=` /
`LIBS=` 传给 configure，并在头文件或 lib 缺失时抛 `ConanException` 而不是静默产出
坏包。路径全部来自 Conan 包目录，**没有注入共享 `/usr/local`**（R49）。

### 5.2 in-tree 构建

生成的 Makefile 里是 `srcdir = .`，所以构建必须在源码目录内进行：

```python
def layout(self):
    basic_layout(self, src_folder="src")
    self.folders.build = self.folders.source
```

另外 2005 年的 autoconf 2.59 `configure` 自带的 `config.guess` 不认识鸿蒙的 `uname`，
会报 `cannot guess build type`。和本仓 libtirpc / classads / cityhash 一样，
显式传 `--build=<arch>-unknown-linux-ohos --host=<arch>-unknown-linux-ohos` 跳过
config.guess；编译器仍由 profile 提供。

还有一处 HMDFS 适配：autoconf 用 `(umask 077 && mktemp -d ...)` 建临时目录，
在 hmfs/hmdfs 上会 `config.status: error could not setup config files machinery`。
配方把 `configure` 里的 `umask 077` 放宽成 `umask 022`（与 sysstat 12.7.9、
libnsl 2.0.1 同处理），实测该 configure 里有 2 处。

---

## 6. W3 本地编译验证（硬门槛）

```bash
conan create archives/r/rstatd/4.0.1 --name=rstatd --version=4.0.1 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
```

**结果：rc=0。**

* recipe revision `ed294ccd29e6ca9a2a1401e9cfbd3cf2`
* package id `3adf8cc9dab3a2f2cba994e10df96c6de5b01756`
* 共 11 个编译单元，编译告警 **40 → 6** 条，且剩下的 6 条全部是上游风格问题，
  不影响正确性：

  | 数量 | 类别 | 位置与说明 |
  |---|---|---|
  | 3 | `-Wformat-security` | `rup.c` / `rsysinfo.c` 的 `printf(version)`，版本串是常量且不含 `%` |
  | 1 | `-Wunused-value` | `getdata.c` 的 `while (*bufp == ' ') *bufp++;`，`bufp++` 就是本意（跳过前导空格），副作用不会被优化掉 |
  | 1 | `-Wdeprecated-non-prototype` | `rsysinfo.c` 的 K&R 风格函数定义 `int pointopoint_v3(...)` |
  | 1 | clang `-W#warnings` | 上游 `#include <sys/errno.h>`，clang 自动改指向 `<errno.h>` |

  最初的 40 条里有 22 条来自内嵌的 `rstat.h`：用 Makefile 里那条
  `rpcgen -h -o rstat.h rstat.x` 的原样调用生成（而不是换个输出路径）后，
  头文件保护宏是正确的 `_RSTAT_H_RPCGEN`，这 22 条 `-Wextra-tokens` /
  `-Wc99-extensions` 警告随之消失。

打包内容（取自真实 package folder）：

```
bin/rpc.rstatd                157024  ELF 64-bit LSB pie, ARM aarch64, 解释器 /lib/ld-linux-aarch64.so.1
bin/rup                      146776  ELF 64-bit LSB pie, ARM aarch64
bin/rsysinfo                 145112  ELF 64-bit LSB pie, ARM aarch64
licenses/COPYING              17992
share/man/man1/rup.1            1734
share/man/man1/rsysinfo.1       1611
share/man/man8/rpc.rstatd.8       18
share/man/man8/rstatd.8         1155
```

> `AUTOMAKE_OPTIONS = foreign no-installman` 让 `make install` 不装 man 页，
> 配方里显式 `copy()` 了这四个页面。

---

## 7. 测试

### 7.1 上游测试：0 个

`Makefile.am` 没有 `TESTS` 也没有 `check_PROGRAMS`，automake 生成的 `check` 目标是空的，
发布 tarball 里也没有 test/ 目录 —— `make check` 无内容可跑。
所以 `build()` 不执行 `make check`，证据记录在 `test_package/MANIFEST.yml`。

### 7.2 test_package：41 项断言，实测 41 通过 0 失败

包只提供三个可执行文件、没有库，所以测试**直接对打包后的 `rpc.rstatd` 走 ONC RPC**。
为了让它有意义，测试**不复用**包内 rpcgen 生成的桩代码，而是自己按 `rstat.x` 实现
RPC/XDR 编解码 —— 一份独立的协议实现才能证明守护进程的线路格式和 /proc 采集都是对的。

**为什么走 inetd 模式而不是独立模式**：这是实测出来的关键差异。
`rstat_main.c` 在独立模式下把 `proto = IPPROTO_UDP` 传给 `svc_register()`，而 TI-RPC 的
`svc_register()` 在 `protocol != 0` 时**直接返回 `pmap_set()` 的结果**，所以没有运行中的
portmapper 时 `rpc.rstatd` 会 `exit(1)` 拒绝启动。而 inetd 模式下 `proto` 保持 0，
`svc_register()` 不碰 portmapper。inetd / systemd socket 激活本来就是 rstatd 的部署方式，
所以测试模拟的正是生产代码路径：bind 一个 UDP 端口 → `connect()` 到客户端 →
`dup2` 到 fd 0 → exec 守护进程。

覆盖内容：

| 组 | 内容 |
|---|---|
| [1] | `rup -v` / `rsysinfo -v` 退出 0 并打印版本横幅（守护 0002 的 `int c` 与 `strrchr`） |
| [2] | 无守护进程时 `rup 127.0.0.1` 非零退出并报错（错误路径） |
| [3] | RSTATVERS_USERS.RSTATPROC_STATS：27 个 XDR 字 = 108 字节；逐字段断言 `/proc/stat`（cp_time、v_intr、v_swtch 非零）、`/proc/loadavg`（avenrun 为 FSCALE 定点、合理上界）、`/proc/uptime`（boottime < curtime 且 curtime 是合理墙钟）、`/proc/vmstat`（pgpgin/pgpgout 非零）、`/proc/net/dev`（计数非负）、utmp（users 合理）、`/proc/diskstats` 采集器跑完没让守护进程退出 |
| [4] | RSTATPROC_HAVEDISK：结果恰好一个 u_int，磁盘数 ≤ DK_NDRIVE |
| [5] | 版本 1 / 2 / 3 均被服务并返回 27 字 statsusers 载荷（因为 `rstat_service` 固定用 `xdr_statsusers`）；版本 4 未注册 → PROG_UNAVAIL 且守护进程存活 |
| [6] | 版本 9 被拒（accept_stat=PROG_UNAVAIL），且被拒请求不会终止守护进程 |

一次真实运行的实测输出（节选）：

```
[3] RPC RSTATVERS_USERS.RSTATPROC_STATS
  ---- daemon pid=1171836, daemon udp port=43308, client port:...
  [PASS] daemon accepted RSTATPROC_STATS on RSTATVERS_USERS
  ---- cp_time = {624775,0,682854,17551196}
  ---- avenrun = {706,732,760}  (FSCALE = 1<<8)
  ---- boottime = 1791006987.000000  curtime = 1791012977.000000
  ---- paging: pgpgin=29466155 pgpgout=26382980 pswpin=0 pswpout=0
  ---- intr=70087032 swtch=111927281 users=0
  ---- net: ipkts=217667 ierr=0 opkts=747030 oerr=0 coll=0
  ---- dk_xfer = {475,878,101,5229874}
  [PASS] statsusers result is complete: 27 XDR words = 108 bytes
  ...
  [PASS] inetd-mode daemon exits 0 after serving one request (got 0)
== 41 checks, 0 failed ==
RESULT: PASS
```

**鸿蒙特有测试 4 项**（N ≥ 1），逐条记录在 `test_package/MANIFEST.yml`
的 `harmonyos_specific_tests`：现代内核 /proc 采集器（0003）、
`-fno-signed-char` 下的 getopt 死循环（0002）、OHOS 无 SunRPC 需 libtirpc、
musl 无 `rindex`。

---

## 8. 本地门禁环境的一个坑（不是本包缺陷）

本机 WSL 用 `qemu-aarch64` + `/opt/ohos-guest` 跑交叉编译出来的 aarch64 二进制。
`/opt/ohos-guest` 里的 OHOS libc.so **不导出 `__fd_chk`**，而 OHOS 的
`sys/select.h` 把 `FD_SET`/`FD_CLR` 映射成 `__fd_chk(fd)` 调用，于是任何链接
libtirpc `svc_run()` 的程序（三个都在内）都加载失败：

```
Error relocating .../bin/rup: __fd_chk: symbol not found
```

已核实这只是**本地 qemu 根目录陈旧**，不是包的问题：

* 真实 OHOS SDK sysroot 的 `libc.so` **有** `__fd_chk`
  （`readelf -sW` 确认为已定义 FUNC）；
* 同一 SDK 的 `usr/lib/aarch64-linux-ohos/libc.so` 与本机使用的编译 sysroot
  `/mnt/c/Users/13909/ohos-sysroot/usr/lib/aarch64-linux-ohos/libc.so` 都有该符号；
* 只有预置的 `/opt/ohos-guest/lib/libc.so` 没有。

因此本地门禁通过 `QEMU_SET_ENV=LD_PRELOAD=<本地 shim>` 注入一个空的
`void __fd_chk(int fd) {}`（该环境变量只注入 **guest**，不影响宿主进程）。
**配方、test_package、PR 里没有任何一处依赖它**；CI worker 是真实鸿蒙 PC，
直接原生运行，不需要这个 shim。

---

## 8.1 第一次 CI（#69263）暴露的真机阻塞缺陷与修复

第一次 CI（构建 **#69263**，worker `OpenHarmonyPCDeveloper-CI-019`）在真机上失败，
测试卡在第 3 组：

```
[3] RPC RSTATVERS_USERS.RSTATPROC_STATS
  ---- daemon pid=23074, daemon udp port=39385, client port=39719
  [FATAL] recv: no reply from the daemon (Resource temporarily unavailable)
```

而第 1、2 组通过（`rup -v` / `rsysinfo -v` 正常）。**根因是 `/etc/netconfig`**：

1. `rstat_main.c` 调 `svcudp_create(sock)`，在 TI-RPC 里它等价于
   `svc_com_create(fd, UDPMSGSIZE, UDPMSGSIZE, "udp")`；
2. `svc_com_create()` 的**第一件事**就是 `__rpc_getconfip("udp")`，而
   `__rpc_getconfip()` 去解析 `/etc/netconfig`，解析不到就 `return NULL`；
3. 该路径被编译进二进制（`tirpc/netconfig.h`：`#define NETCONFIG "/etc/netconfig"`），
   `src/getnetconfig.c` 里**没有任何 `getenv()`**，无法重定向；
4. 鸿蒙 PC 不带 `/etc/netconfig` → `svcudp_create()` 返回 NULL → `rstat_main.c`
   走到 `syslog(...); exit(1)`，守护进程直接死掉，一个请求也答不上。

真机日志里还有一条独立佐证：`rup 127.0.0.1` 报的是
`rup: RPC: Unknown protocol`（`clntudp_create` 里 `__rpc_getconfip` 失败时设的
`RPC_UNKNOWNPROTO`），而本地有 `/etc/netconfig` 时报的是
`RPC: Port mapper failure - Connection refused` —— 两者只差 netconfig 是否存在。

**本地复现**：用 `unshare -m` 把 `/etc/netconfig` 遮蔽成一个空文件后重跑，功能测试
稳定复现同一个 `[FATAL] recv: no reply from the daemon`，并能看到
`[diag] svcudp_create -> 0`（返回 NULL）。

**修复（补丁 0008）**：inetd 模式下套接字已经在我们的描述符上而且已 `connect`，
`svc_com_create()` 查 netconfig 只用于两件事——解析 nettype，以及在调用方传
`RPC_ANYSOCK` 时创建并连接套接字——两件都不需要。改用
`svc_dg_create(sock, UDPMSGSIZE, UDPMSGSIZE)`：它只调用 `__rpc_fd2sockinfo()` 和
`__rpc_get_t_size()`，**从不查 netconfig 数据库**，构造出的正是同一个数据报 transport。
独立模式保留 `svcudp_create()`（那里需要 TI-RPC 自己创建并连接套接字），因此仍需要
`/etc/netconfig`——已作为运行前提记录在第 10 节。

> 顺带排除了一个看似可行、实际错误的方案：先试过 `svc_vc_create()`。它同样不查
> netconfig，但它是**流式** transport，会 `getpeername()` 并且把数据报套接字切到
> 流式 XDR 分帧；实测守护进程进入 R（忙等）状态、收掉了请求却不回包。数据报场景必须
> 用 `svc_dg_create()`。

**修复验证**：`unshare -m` 遮蔽 `/etc/netconfig` 的条件下重跑功能测试，
**41 项断言全过**（`RESULT: PASS`）——即在真机缺失该文件的环境下守护进程已可正常应答。

---

## 9. 复现命令

```bash
# W3
conan create archives/r/rstatd/4.0.1 --name=rstatd --version=4.0.1 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing

# CI 同源门禁
CI_BRANCH=feat/rstatd-4.0.1 CONAN_PROFILE=ohos-aarch64-wsl \
  CI_PACKAGES="archives/r/rstatd/4.0.1" zsh ci/conan/build_and_test.sh
```

---

## 9.1 Pre-PR 独立审计（W4）

`scripts/pre_pr_audit.py generate` 产出审计输入后，由**独立子任务**（上下文隔离，避免自审盲区）
按 `.gitcode/code-style.md` + `.gitcode/review-memory.md` 审计，
报告落在 `reports/audit-result.json`。

**VERDICT: pass，P0 = 0、P1 = 0。** 审计过程中发现并已当场修掉的问题：

| 审计发现 | 处置 |
|---|---|
| `ok(1, ...)` 恒真断言，会虚增断言数 | 换成对 `dk_xfer` 实际扇区数的真实断言 |
| `kill(pid, 0)` 分不清"存活"与"未回收的僵尸"子进程 —— 而守护进程崩溃正是要抓的故障 | 改用 `waitpid(WNOHANG) == 0` |
| `MANIFEST.yml` 声称 rup"给出错误信息"，但代码只断言了非零退出码 | 补上对 stderr 文本的断言 |
| `run_capture()` 没有超时：若 getopt 死循环回归，会挂死而不是失败 | 加 30 秒超时并返回独立状态码 |
| 内嵌的 `rstat.h` 用的是另一种输出路径生成的版本，头文件保护宏为 `_RSTAT.H_H_RPCGEN`，与 Makefile 里 `rpcgen -h -o rstat.h` 的真实输出不一致（并因此带来 22 条告警） | 用 Makefile 原样的调用重新生成，改为 `_RSTAT_H_RPCGEN`，可直接逐字复核 |
| `notes.md` 已知限制一节把两个 man 页的大小写反了 | 更正 |
| 多个文本文件缺行尾换行 | 补齐 |

审计还独立复核了：tarball 的 md5/sha256/大小、`rpcgen -c` 与自带 `rstat_xdr.c` 逐字节一致、
7 个补丁 `patch -p1 --fuzz=0` 全部干净应用、补丁里无平台宏、`manifest.yaml` 与真实包内容一致、
以及"去掉 shim 后三个二进制都以 `__fd_chk: symbol not found` 失败"这一环境结论。

另外发现并修正了一个**补丁序列自身的问题**：最初 0005 是对原始 tarball 求的 diff，
而 0003 恰好改写了 0005 引用的上下文注释，导致按序应用时 0005 的 hunk 匹配失败。
现在整条补丁序列改为「相邻快照之间求 diff」重新生成，并用
`patch -p1 --fuzz=0` 对原始 tarball 全量验证通过。

---

## 10. 已知限制（如实记录）

1. **`rpc.rstatd` 独立模式需要运行中的 portmapper。** 这是上游设计（要注册到
   portmapper 才能被远端 `rup` 找到），不是本次适配引入的。鸿蒙 PC 默认没有
   portmapper，实际部署应走 inetd / systemd socket 激活 —— 测试走的正是这条路径。
2. **独立模式仍需要 `/etc/netconfig`。** 补丁 0008 已经让 **inetd 模式**（实际可用的部署
   方式）完全不依赖该文件；但独立模式必须由 TI-RPC 自己创建并连接套接字，仍要走
   `svcudp_create()` → `__rpc_getconfip()`。若要在鸿蒙 PC 上用独立模式，需先提供
   `/etc/netconfig`（libtirpc 自己的包内带了一份 `etc/netconfig` 可作内容参考）。
3. **二进制未 strip。** 沿用 autotools 默认，未额外引入 strip 步骤（避免超出本任务范围）。
4. `rpc.rstatd.8` 只有 18 字节（仅一行 `.so rpc.rstatd` 之类的占位内容），是上游 man 页
   本身的状态；`rstatd.8` 是完整内容（1155 字节）。

---

## 11. CI 侧反复失败：`[3]` 无应答，测试改为自带诊断（2026-10-12）

本 PR 的 CI 至今 0 通过 / 67 失败（其中绝大多数是 worker 侧的 eSSH bridge /
fork EAGAIN 基础设施故障）。真正落在配方与测试上的失败签名始终是同一处：

```
[3] RPC RSTATVERS_USERS.RSTATPROC_STATS
---- daemon pid=48490, daemon udp port=52240, client port=38464
[FATAL] recv: no reply from the daemon (Resource temporarily unavailable)
```

**本地无法复现，而且已经排除了最像的那个假设**（2026-10-12 实测，profile
`ohos-aarch64-wsl`）：

| 条件 | 结果 |
|------|------|
| 本机 `/etc/netconfig` 正常 | `== 41 checks, 0 failed ==` / `RESULT: PASS` |
| `unshare -m` 把 `/etc/netconfig` 遮蔽成空文件（T159 记的 CI 条件） | 41/41 PASS，`---- reply came from 127.0.0.1:xxxx` |
| 再把 `/etc/protocols`、`/etc/services` 一并遮蔽 | 41/41 PASS |

也就是说：补丁 0008 让 inetd 模式彻底不碰 netconfig 这件事是成立的，CI 上的失败
**不是** netconfig 造成的，而是 worker 运行时环境的某种差异（候选：inetd 子进程的
`connect()`/`dup2(cs2,0)`/`execl()` 之一在鸿蒙上失败，或守护进程起来后立刻退出）。

问题在于原测试把这条线索整个吞掉了：inetd 子进程**在 connect/dup2/exec 之前**就把
端口号回传给了父进程，因此它死在哪一步，父进程一概看不见 —— 只看到 20 秒后
`[FATAL] recv: no reply`。

**本次改动（只加取证，不放宽任何断言）**：`start_inetd_daemon()` 在拿到端口号之后用
`waitpid(WNOHANG)` 观察 300 ms，子进程若已退出就立刻报出**退出码与对应步骤**：

```
inetd child exited before the first request: exit 125 (dup2(socket, 0))
  -- rpc.rstatd never got a socket on descriptor 0
```

映射表覆盖 120/121/122/124/125/127（socket / bind / getsockname / connect / dup2 /
execl）；退出码若是别的值（例如 1），说明 `rpc.rstatd` 自己起来了又退出，那也同样是一条
以前拿不到的判据。改动后本地仍是 `== 41 checks, 0 failed ==` / `RESULT: PASS`。

下一步取决于 CI 给出的那个退出码：拿到它就能直接定位并给出真正的修复，而不再需要继续猜。

### 11.1 CI #85828 给出了那个退出码：daemon 自己 exit(1)（2026-10-12）

构建 **#85828**（worker `OpenHarmonyPCDeveloper-CI-014`，head `0f60ac76`，含补丁 0008）：

```
[3] RPC RSTATVERS_USERS.RSTATPROC_STATS
  [FATAL] inetd child exited before the first request: exit 1 (unknown step
  (see the child's exit code)) -- rpc.rstatd never got a socket on descriptor 0
```

exit 1 不在取证码表里，说明 120/121/122/124/125/127 全部没走 —— 子进程的
socket/bind/getsockname/connect/dup2/execl **全部成功**，`rpc.rstatd` 已经带着
fd 0 上的已连接 UDP socket 跑起来了，然后**自己**在 300 ms 内 exit(1)。
对照补丁后的 `rstat_main.c`，exit(1) 的全部来源按程序顺序是：

| # | 位置 | syslog 消息 | 触发条件 |
|---|---|---|---|
| 1 | `getdata_setup()`（补丁 0003） | `cannot parse kernel release "..."` | `sscanf(u.release, "%d.%d")` 失败 —— 且 getdata_setup() 在一切之前执行 |
| 2 | `svcudp_create()` 返回 NULL | `cannot create udp service.` | **仅独立模式**（getsockname(0) 失败 → inetd_connect=0）；inetd 模式已被补丁 0008 换成 svc_dg_create |
| 3 | `svc_register()` 失败 | `unable to register (RSTATPROG, ...)` | 对照 libtirpc 1.3.7 `src/svc.c` 的 svc_register()（PORTMAP 变体）：只挂 svc_head 链表，`protocol==0` 时不调 pmap_set、**不查 netconfig**，仅 mem_alloc 失败才返回 FALSE —— 可排除 |
| 4 | `svc_run()` 返回 | `svc_run returned` | poll() 非 EINTR 错误，fd 0 有效时基本不可能 |

所以 worker 上 exit(1) 只能来自 **#1（uname().release 解析失败）** 或
**#2（getsockname(0) 失败 → 走了独立模式 → svcudp_create 撞上缺失的
/etc/netconfig）**。两条路径的错误都走 syslog(LOG_ERR)，而 worker 上没有
syslog 消费者 —— 这就是连续几轮 CI 都在猜的原因。

**本轮改动（仍然只加取证，不放宽任何断言）**：新增
`test_package/syslog_shim.c`，经已有的 LD_PRELOAD 机制注入，做两件事：

1. 替换 `syslog()`：守护进程的所有诊断改为打到 stderr —— conan 的 test()
   日志本来就捕获 stderr，于是上一表的 syslog 消息在 CI 日志里直接可见；
2. 构造函数探针：在每个被注入的进程里打印 `getsockname(0)` 的返回值/errno/
   地址族、fd 0 的 SO_TYPE、以及 `/proc/sys/kernel/osrelease` —— 正是
   main() 分支选择所依赖的全部事实（#1 与 #2 的直接判据）。

顺带修掉 AI 检视 P2 指出的一个真问题：原 `conanfile.py` 在真机 worker 上也
LD_PRELOAD 了 fdchk shim，用"只做范围检查"的桩覆盖了真实 OHOS libc 的
`__fd_chk`（恰好会屏蔽这个测试想抓的故障类别）。现在 fdchk shim 仅当宿主机
存在 qemu guest 根（`/opt/ohos-guest`，notes.md §8 的本地环境标记）时才注入；
syslog shim 为诊断专用、本轮恒注入。两个 shim 编译失败都只降级不阻断测试。

本地门禁重跑（profile `ohos-aarch64-wsl`，2026-10-12）：`== 41 checks, 0 failed ==`
/ `RESULT: PASS`。探针与 syslog 重定向均已生效（日志中可见
`[rstatd-probe pid=...] getsockname(0)=0 ... so_type=SOCK_DGRAM` 与守护进程的
syslog 内容）。下一轮 CI 的日志将直接给出 #1/#2 的裁决。

## 2026-10-14 修复：OHOS release 串不是 "<major>.<minor>"

CI 构建 #87224 的日志给出了 notes.md §「exit(1) 来源表」里第 1 行的直接判据：

```
[rstatd-syslog prio=2] cannot parse kernel release "HongMeng Kernel 1.13.0"
```

也就是说：补丁 0003 第一版用 `sscanf(u.release, "%d.%d")` 解析**整串**，而 OHOS 的
`uname().release` 带着厂商前缀 `HongMeng Kernel `，于是解析返回 0，`getdata_setup()`
按当时的写法 `exit(EXIT_FAILURE)` —— 守护进程在服务第一个请求之前就死了，
test() 第 102 行因此拿到 Error 2。

改法：先跳过前缀，定位 release 串里**第一个数字序列**再解析 `major.minor`。
上游的 2.2 / 2.4 两个分支原样保留；其余（2.10、3.x、1.13……）统一走 2.6 引入的
`/proc/diskstats` + `/proc/vmstat` 采集器；只有「整串一个数字都没有」才继续硬失败
（那是真的读不到内核版本，不该假装成功）。

`patches/0005` 里 getdata.c 的 hunk 因为 0003 把 `getdata_setup()` 加长了 24 行而
失效（它原先是 `@@ -308,13 +308,13 @@`），已按 **0003 之后**的真实源码树重新生成
成 `@@ -326,13 +326,13 @@`；0005 另外两项（getdata22.c / getdata26.c 补 `string.h`）
未动。八份补丁按 0001..0008 顺序在真实上游源码树上 dry-run + 实套全部 rc=0。

A/B 对照（`logs/kver_check.c`，可直接重跑）：

| uname().release | 旧判据 | 新判据 |
|---|---|---|
| `HongMeng Kernel 1.13.0` | **EXIT(1)** | get_disk26 + get_vm26 |
| `6.18.33.2-microsoft-standard-WSL2` | get_disk26 | get_disk26 |
| `2.6.32-642.el6.x86_64` | get_disk26 | get_disk26 |
| `2.4.21` | get_disk24 | get_disk24 |
| `2.2.26` | get_disk22 | get_disk22 |
| `2.10.0` | get_disk26 | get_disk26 |
| `""`（空串） | EXIT(1) | EXIT(1) |

本机门禁（profile `ohos-aarch64-wsl`）：`== 41 checks, 0 failed ==` / `RESULT: PASS`
（在打的 0003 之上再跑，41 项断言全过）。
