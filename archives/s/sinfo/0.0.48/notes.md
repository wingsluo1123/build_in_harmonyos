# sinfo 0.0.48 适配笔记

## 编译环境
- 构建系统: autotools（上游 2014 年 orig tarball 已预生成 configure/Makefile.in，无需 autoreconf）
- 编译日期: 2026-10-15
- 编译器: clang/clang++ 15（OpenHarmony SDK llvm，交叉三元组 `aarch64-linux-ohos`）
- 状态: built

## 软件概况

sinfo — 分布式系统信息（作者 Jürgen Rinas）：

- `sinfod`（sbin/）：守护进程，采集本机系统负载、内存占用与 top-N 进程，
  周期性向广播地址（默认 255.255.255.255:60003）发送测量消息，同时在
  UDP/TCP 60002（SINFO_REQUEST_PORT）上应答客户端的直接查询；默认
  daemonize，`-F` 前台运行。
- `sinfo`（bin/）：ncurses 客户端，`-h host[:port]`（默认 127.0.0.1）直连
  sinfod 查询；交互式 curses 界面（默认）或 `-H`（主机名列表）/ `-L`
  （主机+负载）/ `-I`（IP 列表）/ `-W`（HTML）纯文本输出模式；
  `--udp`（默认）/`--tcp` 选择查询协议。
- `sshallsinfo`（bin/）：上游附带的小工具，`sinfo --hostsandipmode`
  列出在线主机后逐台 `ssh` 执行给定命令（215 字节 shell 脚本）。
- 上游 RPC 层为自制 idlx 代码生成器产物（消息序列化），生成文件已随
  tarball 预生成（2014 mtime > 2011 .idlx），无需构建期生成。
- 上游主页 http://www.ant.uni-bremen.de/whomes/rinas/sinfo/ 已失效
  （302 → 大学院系页，~2016 起）；Debian pool 保留 pristine orig tarball。

## 编译步骤

```bash
# 交叉编译（WSL，host=OHOS/armv8/clang15/libc++/cppstd17，build=x86_64 Linux）
cd /root/ohpcd-work/build/sinfo-0.0.48
conan create /root/ohpcd-work/wt-sinfo/archives/s/sinfo/0.0.48 \
    -pr:h ohos-aarch64-wsl-xbuild -pr:b default --build=missing
```

1. 配方 `source()` 拉 Debian pool 的 pristine orig tarball 并
   `apply_conandata_patches`（四补丁）
2. `generate()` 出 `AutotoolsToolchain` + `AutotoolsDeps`，configure 参数
   `--enable-static --disable-shared --with-boost-signals=no --with-boost-system=no`，
   configure 参数追加 `ac_cv_func_malloc_0_nonnull=yes`（Conan 2.29.1 AutotoolsToolchain 无 configure_vars 属性，按 autoconf VAR=VALUE 命令行惯例）
3. `build()` 内 `configure` + `make -j1`（R9：HMDFS 不允许 jobserver FIFO）
4. `package()` 走 `make install`，产物 `bin/sinfo`、`bin/sinfod`、
   `bin/sshallsinfo`（上游 ssh 扇出脚本，见下）（Conan AutotoolsToolchain
   默认把 --sbindir 重定向到 ${prefix}/bin，上游 sbin/ 布局被收敛到 bin/）、
   `lib/sinfo/`（pkglib 内部静态归档）、
   `share/man/man1/{sinfo.1,sshallsinfo.1}`、`share/man/man8/sinfod.8`、
   `licenses/COPYING`
5. `test_package/` 用 `sh test_sinfo.sh <sinfo-bin> <sinfod-bin>` 跑 9 个
   端到端用例（版本/帮助 + 守护进程环回直连查询 + 干净退出）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `checking build system type...` 失败 / `Invalid configuration 'aarch64-linux-ohos': system 'ohos' not recognized` | tarball 自带 2014-02-15 版 config.guess/config.sub 不识别 HarmonyOS；交叉时 config.sub 拒绝 linux-ohos，CI（OHOS 原生）上 config.guess 猜不出 build 三元组 | 补丁 0002 给 config.guess 注入自终止 `*:HarmonyOS:*:*` 分支（echo 三元组 + exit 0，该代脚本无 GUESS 兜底）；补丁 0003 让 config.sub 两处 pattern（maybe_os 表 + OS 列表）接受 `linux-ohos*` |
| 2 | `config.status: error: could not setup config files machinery`（HMDFS 上 `can't create ./confXXXXXX/subs1.awk: Permission denied`） | E011（同族签名 E114）：2014 预生成 configure 用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录，HMDFS 上目录映射属主 UID 与进程 UID 不同，drwx------ 连属主都不可写 | 补丁 0001 把 configure 里两处 `umask 077` 改成 `umask 022` |
| 3 | `configure: error: Could not link against libboost_system!` | configure.ac 的 AX_BOOST_SYSTEM 是 autoconf-archive 老宏：System 自 Boost 1.69 起 header-only，制品仓 boost/1.84.0 只构建 filesystem/regex/program_options/iostreams 四个编译库（无 libboost_system），宏找不到库即 AC_MSG_ERROR | `--with-boost-system=no` 跳过找库检查；代码只用 header-only 的 asio/signals2/system/bind，无链接损失 |
| 4 | AX_BOOST_SIGNALS 同类问题（`boost/signals.hpp` 不存在 / 找不到 libboost_signals） | Boost.Signals v1 已在 Boost 1.74 删除；代码实际用的是 header-only 的 Boost.Signals2 | `--with-boost-signals=no` 跳过检查 |
| 5 | 交叉编译下 sinfo 客户端链接期 `undefined reference to rpl_malloc` | AC_FUNC_MALLOC 交叉编译默认按 malloc(0)==NULL 处理 → config.h `#define malloc rpl_malloc`；sinfo/ 下 7 个包含 config.h 的翻译单元的 malloc 调用全部被宏替换 | `tc.configure_args.append("ac_cv_func_malloc_0_nonnull=yes")`（Conan 2.29.1 无 tc.configure_vars；musl 与 glibc malloc(0) 语义一致，均为合法指针/NULL 皆可，实际返回非 NULL） |
| 6 | `make -j` 卡住/报 FIFO 权限 | E074：HMDFS 不允许创建 jobserver 管道 | `autotools.make(args=["-j1"])` |
| 7 | `AC_CHECK_LIB(ncurses, use_default_colors)` 探测失败 | conan ncurses 包只提供宽字符库 libncursesw（无 libncurses） | 预期行为：HAVEDEFAULTCOLORS 不定义，sinfocurses.cc:441 的 `use_default_colors()` 走 `#ifdef HAVEDEFAULTCOLORS` 守卫优雅降级（仅影响终端底色方案，功能不受损） |
| 8 | libmessageio 编译失败：`boost/bind/bind.hpp:299:9: error: no matching function for call to object of type 'boost::_mfi::mf1<void, TCPMessageServerConnection, Message &>'`（tcpmessageserverconnection.cc 的 sendMessageSignal.connect） | ServerConnectorBase::sendMessageSignal 是全库唯一的按值 signals2 信号（`signal<void (Message)>`），它连接的成员槽 queueAndSendMessageSlot 以非 const 左值引用收参；Boost 1.84 的 bind 以右值调用 mf1<void, C, Message&>，非 const 左值引用无法绑定右值，无可行 operator() 重载 | 补丁 0004：槽签名 `Message &` → `const Message &`（头文件 + 实现共 2 行）；全库信号/槽签名审计确认其余组合均为左值引用信号 → 引用/const 引用/按值槽，天然兼容 |

## 源码修改

| 文件 | 原因 | 方式 | 补丁 |
|------|------|------|------|
| `configure` | E011 临时目录不可写 | 编辑：两处 `umask 077` → `umask 022` | 0001 |
| `config.guess` | 识别 HarmonyOS 三元组 | 编辑：主 case 注入自终止的 `*:HarmonyOS:*:*` 分支（aarch64/arm/x86_64/i686 → `<arch>-unknown-linux-ohos`） | 0002 |
| `config.sub` | 接受 `-linux-ohos` | 编辑：maybe_os 表加 `linux-ohos*`、OS 列表加 `-linux-ohos*` | 0003 |
| `libmessageio/tcpmessageserverconnection.h` / `.cc` | Boost 1.84 bind 兼容（按值信号连接非 const 引用槽无可行调用） | 编辑：queueAndSendMessageSlot 参数 `Message &` → `const Message &`（2 行） | 0004 |

四个补丁均用 `patch -p1 --dry-run` 在 pristine tarball 上验过可干净应用（无 fuzz）；
patched config.guess/config.sub 实测输出 `x86_64-unknown-linux-gnu`（WSL）与
`aarch64-unknown-linux-ohos`（config.sub 归一化）正确。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| boost | 1.84.0 | header-only 用法（asio/signals2/system/bind/posix_time）；制品仓 OHOS/armv8 二进制 32b74e3e19b062f993e717bc9d8150ae65c2c340 |
| ncurses | 6.6 | sinfo 客户端链接依赖（静态 libncursesw，R26）；制品仓 OHOS 二进制 21b17f8b2bc0e9511e276e3d57a23893067cefe5 |

## 验证结果

```bash
$ conan create ... -pr:h ohos-aarch64-wsl-xbuild -pr:b default --build=missing
# （见 build 输出：config.guess/config.sub 三元组、make -j1、包 ID）
$ file bin/sinfo bin/sinfod
bin/sinfo:   ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked
bin/sinfod:  ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked
$ readelf -l bin/sinfod | grep interpreter
      [Requesting program interpreter: /lib/ld-linux-aarch64.so.1]
$ readelf -d bin/sinfod | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
```

（OHOS PC glibc ABI：解释器 `/lib/ld-linux-aarch64.so.1`、NEEDED 仅
`libc.so` — libc++/ncurses/boost 全部静态链入，运行时只依赖 OHOS PC 基础
libc。）

`test_package`（R34 实质消费者测试）：9 用例 9 断言，已在本机 WSL 以
qemu-user（aarch64 binfmt）对真实包产物实跑全绿（CI 的 OHOS worker 上
`can_run` 为真后原生重复同一脚本）：

```
$ sh test_package/test_sinfo.sh <pkg>/bin/sinfo <pkg>/bin/sinfod
ok - sinfo -V prints packaged version (rc=0)
ok - sinfod -V prints packaged version (rc=0)
ok - sinfo -? prints help and exits rc=1
ok - sinfod -h prints help and exits rc=1
ok - sinfod -F starts in foreground and stays alive
ok - sinfo -q -H lists the daemon host (UDP)
ok - sinfo -q -L lists host load (UDP)
ok - sinfo -q --tcp -H lists the daemon host (TCP)
ok - sinfod exits on SIGTERM
1..9
# passed: 9
# failed: 0
```

覆盖：双二进制版本横幅（rc=0，含 0.0.48）、帮助文本（rc=1）、sinfod
前台守护（`-F -q -b 127.0.0.1`，广播收窄到环回）启动存活、sinfo 客户端
UDP/TCP(60002) 直连 `-H`/`-L` 查询输出非空、SIGTERM 干净退出。

上游测试 1 项未运行（libmessage/testmessage check_DATA 黄金文件 diff，
交叉编译无法执行目标架构二进制，见 test_package/MANIFEST.yml）。

## 测试四维账本

| 维度 | 数量 | 说明 |
|------|------|------|
| 上游静态声明 N_static | 1 | `make check` 唯一钩子：libmessage/testmessage 的 check_DATA（testmessage 输出 diff testmessage.out.approved）；各 Makefile.am 无 TESTS/check_PROGRAMS |
| 实际执行 N_executed | 0 | 交叉编译环境无法执行目标架构二进制，配方未集成 |
| 跳过/未执行 | 1 | testmessage（同上，见 MANIFEST.yml note） |
| 新增消费者测试 N_consumer | 9 | test_package/test_sinfo.sh 9 用例 9 断言（版本×2、帮助×2、守护存活×1、查询×3、干净退出×1） |

## 注意事项

- sinfod 默认 daemonize 并向 255.255.255.255:60003 广播；测试/受限环境用
  `-F -q -b 127.0.0.1` 把广播收窄到环回
- 客户端 sinfo 的 `-h` 是 `--host`（查询目标），帮助是 `-?`/`--help`（rc=1）；
  `-V` 版本（rc=0）
- 编译期端口可用 configure 选项改：`--enable-SINFO_REQUEST_PORT=n`（默认
  60002）、`--enable-SINFO_BROADCAST_PORT=n`（默认 60003）
- 上游 idlx 生成文件（*.idlx.{client,parser}.{h,cc}）依赖其自制 idlxcompiler
  （上游已不可得）；切勿在构建中触发重新生成（触碰 .idlx mtime 会让 make
  尝试调用不存在的 idlxcompiler）
- 本包为 application：`cpp_info.bindirs=["bin"]`、`libs=[]`；Conan
  AutotoolsToolchain 默认 `--sbindir=${prefix}/bin` 把上游 sbin/ 布局收敛
  到 bin/，sinfo、sinfod 与 sshallsinfo 同目录；lib/sinfo/ 下的 pkglib 静态归档
  （libmessage 等）是上游内部支持库，已随 `make install` 落包但不作为
  公开链接接口（`libdirs=[]`）

**编译结束**: 2026-10-15
**最终状态**: built

### R j1: install 阶段钉 -j1（2026-10-16）

package() 原先调用 utotools.install()（不带 jobs），会沿用 	ools.build:jobs（worker 上
实测 -j20）。并行 make 需要创建 jobserver fifo，而 worker 拒绝该操作：

    make: jobserver mkfifo: <tmp>/GMfifo…: Operation not permitted

轻则报错，重则让 make 误判 install 目标已完成而**静默什么都不装** —— 同批的
istgt/0.4-20111008 就是这样产出空壳包（test_package 的 A1~A4/A7/A8 全 FAIL，见其 CI #94874）。

处置：utotools.install(args=["-j1"])，与仓内既有做法一致（house 规则 E074；先例
meterec/0.9.3、smartlist/3.15、json-parser/1.1.0）。uild() 侧本就已 -j1，本次补齐
install。只降低安装阶段并行度，不改变产物内容，也不改任何测试与断言。
