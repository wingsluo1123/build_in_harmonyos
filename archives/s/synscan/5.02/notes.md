# synscan 5.02 — 适配笔记

> 上游：https://digit-labs.org/files/tools/synscan/ （发布源 digit-labs.org 直链）
> 版本：5.02   语言：C  构建系统：autotools（configure + Makefile.in）
> 状态：工作树完成，待真机 rule4 预检

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | synscan（SYN 端口扫描工具集） |
| 版本 | 5.02 |
| 产物 | `synscan`（发 SYN 包）、`sslog`（libpcap 监听 SYN/ACK），外加解析引擎静态库 `libsynscan.a` |
| 依赖 | libpcap/1.10.6（configure 硬性要求，sslog 链接） |
| 许可证 | GPL-2.0 |
| 构建 | ./configure --with-libpcap=<stage> --prefix=/ ; make linux |

## 二、OHOS 适配要点

### 1. libpcap 依赖（configure 硬性 AC_ERROR）
- 上游 configure 对 libpcap 做硬性探测，缺失即 `AC_ERROR(libpcap not found)`。
- `--with-libpcap=DIR` 要求 `DIR/pcap.h` + `DIR/libpcap.a` 直接存在（随后 `-I DIR -I DIR/bpf -L DIR -lpcap`）。
- 发布的 `libpcap/1.10.6` 包把 `pcap.h` 放在 `include/pcap/`、`libpcap.a` 放在 `lib/`，不满足 DIR 扁平布局。
- 配方 `_stage_libpcap()` 把 `pcap.h` + `libpcap.a` copy 到 build 私有 stage 目录（R49 私有 prefix），configure 传 `--with-libpcap=<stage>`。

### 2. HMFS 临时目录（patch 0001）
- 2011 年老 autoconf 的 AS_TMPDIR 用 `(umask 077 && mktemp -d "./confXXXXXX")` + 077 mkdir 回退建 ./conf* 临时目录。
- HMFS 设备文件系统上 077/setgid 目录会变成属主不可写，config.status 在 `./conf*/subs1.awk: Permission denied` 失败（与 libapreq2 2.17 / cln 1.3.7 / tta 2.2 / rancid 3.14 同指纹）。
- patch 0001 去掉 mktemp 分支，恒用 `umask 022 && mkdir` 建临时目录；配方同时以 `umask 022 && CONFIG_SHELL=/bin/sh SHELL=/bin/sh` 运行 configure 作双保险。

### 3. 老 autoconf 无需 config.guess/config.sub
- 该 configure（~2011, autoconf 2.59）只 `ac_config_guess="$SHELL .../config.guess"` **定义**字符串，从不执行；也不做 build/host 三元组猜解。
- 显式 CC（AutotoolsToolchain 注入 OHOS clang）下 AC_PROG_CC 直接通过，无需 config.guess/config.sub、无需 --build/--host。

### 4. 手工打包，避开 make install
- `make install` 目标会 `strip synscan; strip sslog` 且用 `@INSTALL_PROGRAM@`，在 OHOS 上可能 strip 出不可运行产物 / INSTALL shim 兼容问题。
- package() 直接 copy 两个二进制 + `libsynscan.a` + 5 个公共头文件。

### 5. 解析引擎打包为 libsynscan.a
- `net.c/common.c/obuf.c`（纯解析逻辑，**零 libpcap 依赖**）用 `ar rcs libsynscan.a common.o net.o obuf.o` 归档随包发布。
- 暴露 net_parse_portlist / net_parse_iplistv4 / net_portlist_sum / net_iplistv4_sum / 端口与 IP 迭代器 / net_ipv4_parse_flags 等接口。
- 目的：synscan 运行扫描需要 raw socket + libpcap + root，真机无 root 环境跑不了 SYN 扫描；但解析引擎是核心逻辑，可无特权真机运行。test_package 链接 libsynscan.a 以 20 项断言真实覆盖，满足 R34 与诚实测试。

## 三、上游测试审计（no_tests）

- **上游无任何自动化测试**：`Makefile.in` 只有 default/freebsd/linux/macos/netbsd/openbsd/solaris-sparc-gcc/install/clean/distclean 目标，无 `check`/`TESTS`/`check_PROGRAMS`；`configure.in` 只有 AC_PROG_CC/AC_HEADER_STDC/AC_CHECK_HEADERS/AC_CHECK_FUNCS + libpcap/getopt_long 探测，无测试宏；tarball 无 `t/ tests/ test/` 目录。
- 按 `upstream_tests_exist: false`、`upstream_test_total: 0`、`status: no_tests` 如实上报，审计见 test_package/MANIFEST.yml 的 upstream_test_audit。

## 四、消费者测试（test_package，真机实跑）

test.sh 维护确定性计数器（SYNSCAN_TEST_TOTAL/PASS/FAIL），3 个用例：
- **A** `bin/synscan -V` → 打印版本 + 退出码 0（参数解析阶段提前退出，早于 root/raw-socket 检查）
- **B** `bin/sslog -V` → 同上
- **C** `./test_synscan_api` → CMake 编译的消费者，链接 libsynscan.a，20 项 parse-API 断言（内部 SYNSCAN_API_TOTAL/PASS/FAIL），全过则退出 0

conanfile 解析 SYNSCAN_TEST_* 生成 `HMBS_TEST_PACKAGE_RESULT`（discovered=3, passedCount=3）；上游无测试 → `HMBS_UPSTREAM_TEST_RESULT` 输出 `status:no_tests, discovered:0`。

### 已做证伪（实际行为确认，非臆测）
- `net_parse_portlist`/`net_parse_iplistv4` 用 strtok/strchr **原地改写**入参：传字符串字面量会段错误，必须用可变 char[] 缓冲区。
- `net_portlist_add` **头插**导致迭代顺序与解析顺序相反（"80,443,8000-8010" 迭代从 8000 开始）；断言按 成员+个数 而非顺序。
- `net_parse_portlist_item` 对端口号**无上界校验**（"70000" 截断为 4464 仍接受）——断言只对真正非法形式（upper<lower、"abc"）断言 NULL。
- `net_ipv4_parse_flags` 对未知标志只 `warning` 返回 SYN_OK 且 flags 不变（上游真实怪癖，不依赖）。
- 故意把 test_synscan_api 换成 return 1 的桩重跑，test.sh 正确报 FAIL/exit 1 —— 证明 harness 真能抓到失败（非假通过）。

## 五、待真机确认
- configure/make linux 在 OHOS clang 下通过（net/if.h、BYTE_ORDER、getopt_long、raw socket 头均已具备）。
- libsyncap.a 链接 `-lpcap`（来自 libpcap 包）无额外系统库需求。
- test_package CMake/find_package(synscan) 在该设备上生成 synscan::synscan 目标并链接 libsynscan.a。
- 上游测试缺失/计数以真机证据轮结果为准；PR 正文「上游测试用例通过率」等测试数字留待真机 evidence 轮填写。

### 编译失败修复（真机轮：make linux 无 linux 目标）
- 报错 `make: *** No rule to make target 'linux'. Stop.`。
- 根因：`build()` 中 configure 命令未指定 cwd，Conan `self.run` 默认在 build_folder 执行，生成的 Makefile/config.h 落到 build_folder；而 `make linux` 指定 `cwd=self.source_folder`（该目录只有 Makefile.in，无 Makefile）。make 找不到 Makefile 即报 "No rule to make target 'linux'"（已本地以空目录复现同款报错）。
- 修复：给 configure 命令补 `cwd=self.source_folder`，与 `make linux` 同目录，Makefile 生成到 source_folder，make 即可找到 linux 目标（已本地验证 in-source configure 后 Makefile 含 linux 目标且 make linux 进入编译）。

### CI 失败修复（fork/exec EAGAIN 瞬态，非配方缺陷）
- 现象（同一 head `8e30df64` 在 4 台 worker 上跑出 2 红 2 绿，源树完全一致）：
  - build #88960（CI-004）失败：`configure[35]: can't fork - try again` → `ConanException: Error 1 while executing`；
  - build #89224（CI-027）失败：`ConanException: Error while running cmd` / `Error: [Errno 11] Resource temporarily unavailable`（Popen fork 失败）；
  - build #89038（CI-018）、#89133（CI-025）**通过**（L1_RESULT=pass，test_package 3/3）。
- 判定：这是共享 CI worker 的**瞬态 fork/exec 资源压力（EAGAIN）**，作用于 `configure` 阶段（该老 autoconf 会 fork 大量 sh/compiler 探测）；`can't fork - try again` 与 `[Errno 11]` 是同一资源根因的两种报法。同 SHA 跨 worker 结果不一致 + 失败点在 configure fork 密集步骤 = 环境资源型（DRAFT-11327 判据）。
- 已有缓解（本轮前）：无 autoreconf 自举（发行包自带 configure）、`make linux -j1`、`/bin/sh`、`umask 022`；配方已处低 fork 开销，未新增自举。
- 修复：在 `build()` 对 **configure 一步**加**有界重试**（最多 3 次、退避 15/30s），且**仅在捕获输出命中 fork 压力标记**（`can't fork` / `cannot fork` / `try again` / `resource temporarily unavailable`）时才重试；命中其它错误（缺 libpcap、语法等真实 configure 错误）立即上抛，绝不掩盖。与已合入的 libcmis/0.6.3 同型方案。
- 边界：`make linux` 阶段目前未见同型 EAGAIN；如后续真机出现再按证据处理，不预先宽化重试范围。
