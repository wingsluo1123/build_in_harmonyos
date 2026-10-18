# iw 6.17 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure / 非 autotools）
- 编译日期: 2026-10-17
- 编译器: clang 15.0.4（aarch64-linux-ohos，起的 OHOS SDK sysroot）
- 状态: built
- 依赖: libnl/3.11.0（ohpcd 制品仓已发布，仅 .a ⇒ 静态链入）

## 编译步骤

源码：`https://www.kernel.org/pub/software/network/iw/iw-6.17.tar.xz`
（官方 kernel.org 网络工具目录，163756 B，
`sha256=7d182e498289ab39b257da6780d562e415377107f50358ee5b55b8cfe40b1e33`）

1. `conan install` 拉 libnl/3.11.0，`PkgConfigDeps` 生成
   `libnl-3.0.pc` / `libnl-genl-3.0.pc` 到 generators_folder。
2. 打 1 个 portability 补丁（见下「源码修改」）。
3. `make -j1`，环境：`CC=clang`、`PKG_CONFIG_PATH=<generators_folder>:$PKG_CONFIG_PATH`。
   Makefile 用 `pkg-config --atleast-version=3.2 libnl-3.0` 探测，缺 .pc 时直接
   `$(error Cannot find development files for any supported version of libnl)`。
4. `package()` 手工落位 `bin/iw`、`share/man/man8/iw.8`、`licenses/COPYING`
   （OHOS 无 coreutils `install`，且上游 install 目标还要 gzip 手册页）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `error: redefinition of 'sockaddr_storage'`（ap.o 等**每个** TU 都报），`linux/socket.h:23` vs `sys/socket.h:377` | OHOS musl 派生 sysroot 的 `<linux/socket.h>` **无条件**定义 `struct sockaddr_storage`；glibc 的同名 UAPI 头用 `#ifndef __GLIBC__` 屏蔽。libnl 的 `<netlink/netlink.h>` 先引 `<sys/socket.h>` 再引 `<linux/netlink.h>` → `<linux/socket.h>`，故冲突必然发生（E119/E1604） | `0001-Makefile.patch`：`CFLAGS += -D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t="unsigned short"` —— 跳过冲突头并补 typedef。与 batctl 2025.2 同族（它用 `-include ohos_compat.h`），区别是**不新增文件、不用平台宏** |
| 2 | 运行期 `Failed to connect to generic netlink.` rc=1 | app 沙箱在**创建** `socket(AF_NETLINK, SOCK_RAW, NETLINK_GENERIC=16)` 时即返回 `EACCES(13)`；`NETLINK_ROUTE(0)` 反而可创建可 bind。iw 经 generic netlink 访问 nl80211 ⇒ 所有需内核回话的子命令不可用 | 平台能力墙，非配方缺陷。CLI 契约面照常可用；断言如实固定该 rc/文案（见 test_package） |

### 关键实测读数（本条 B 的知识主张依据）

netlink socket 能力探针（本机 python3；**未分配协议号是关键判别**）：
```
NETLINK_ROUTE(0):    socket OK, bind OK
NETLINK_GENERIC(16): socket FAILED errno=13 (EACCES) Permission denied
NETLINK_NETFILTER(12): errno=13 (EACCES)
未分配 proto=30/31:    errno=13 (EACCES)   ← 未注册的协议号也是 EACCES
```
⇒ 未分配协议号同样给 **EACCES** 而非 `EAFNOSUPPORT(97)`，证明这是**沙箱按协议号
白名单放行**（只放行 `NETLINK_ROUTE(0)`），**不是**"内核缺 NETLINK_GENERIC 协议族"
（后者应为 EAFNOSUPPORT）。写记录时别照抄"内核缺协议族"的措辞，会误诊。
iw 二进制（无 LD_LIBRARY_PATH 直接运行；`readelf -d` 只有 `NEEDED libc.so`）：
```
$ iw --version   → iw version 6.17        rc=0
$ iw             → Usage:/Commands: 全表  rc=0
$ iw help        → Usage:/Commands: 全表  rc=0
$ iw dev         → Failed to connect to generic netlink.  rc=1
$ iw phy         → Failed to connect to generic netlink.  rc=1
```

### 上游测试口径（rule4 预检，判定优先）

- **上游注册自动化用例数 = 0**，**不是**"有用例但没跑"。rule4 的 FAIL 谓词原文为
  「上游**有用例 N 个**但一个也没测（0/N）」，**要求 N>0** ⇒ N=0 不触发。
- R51 六探针全 0 命中（test/tests 目录、TESTS=/check_PROGRAMS=、test*.c、
  ctest/add_test、*RUNTEST*、demo/examples）。全树 52 文件；全树 `grep -i test`
  唯一命中是 `NL80211_CMD_TESTMODE`（nl80211 驱动透传命令，非测试）。
- Makefile 里唯一的 `check:` 目标是
  `$(MAKE) all CC="REAL_CC=$(CC) CHECK=\"sparse -Wall\" cgcc"`
  即 **sparse/cgcc 静态分析 lint**（本机 sparse/cgcc 均不存在）——不是测试套件。
  ⛔ 因此**不**照抄 ethtool 先例的 `autotools.make(target="check")` +
  `upstream_test_in_build: true`：那会失败或**空跑假绿**。
- 同上口径的平台 approved 先例：fuse #16210、fstobdf #16251（上游 N=0）、
  esmtp #16097、edid-decode #16167。

## 源码修改

单个 portability 补丁（`platform_only: True`，不含平台宏 `__OHOS__`）：

- `0001-Makefile.patch`（+8 行，含 7 行原因注释）：
  ```make
  CFLAGS += -D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t="unsigned short"
  ```
  即**预锁冲突的 UAPI 头 guard** 并补上 netlink UAPI 需要的那一个 typedef。
  与仓内 batctl 2025.2 / babeld 1.13.1 / blockdomains 0.1 同族，但**不新增头文件**、
  也**不使用平台宏**：两个宏直接在 CFLAGS 里定义，glibc 环境下该 guard 只是冗余、
  行为逐字不变（E1604 的 forbid 口径：语义应是"哪一侧 libc"，不是"哪个平台"）。

## 依赖版本

| 依赖 | 版本 | 来源 | 形态 |
|------|------|------|------|
| libnl | 3.11.0 | ohpcd 制品仓（`conan list "libnl/*" -r ohpcd` 实测 3.7.0 + 3.11.0） | 仅静态库 `.a` |

## 验证结果

```bash
# 1) 配方可复现（G0–G4 全 PASS，见 reports/conan-create.log）
python3 scripts/ohc-run.py conan-verify iw 6.17

# 2) 消费者断言（11 条真实断言；conan create 内实跑 SUMMARY: 11 passed, 0 failed）
python3 test_package/test_iw.py <package_folder>
```

## 注意事项

- **运行期能力墙**：本平台 generic netlink（NETLINK_GENERIC=16）socket **创建**即
  EACCES。任何"跑起来能扫到 WiFi"的预期在此平台上都不成立；iw 的可用面是
  CLI 契约 + 交叉编译产物正确性。这与 `ethtool/7.1` 的 netlink 面同源
  （ethtool 的 `--disable-netlink` 正是为此）。
- 补丁是**编译期**修复，与上述运行期能力墙无关、不可混淆：前者是 sysroot 头
  不一致（可修），后者是沙箱权限策略（不可修）。
---

**编译结束**: 2026-10-17 19:38
**最终状态**: built
