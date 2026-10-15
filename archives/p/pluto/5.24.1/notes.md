# pluto 5.24.1 适配笔记

## 编译环境
- 构建系统: 自定义顶层 Makefile（无 configure/CMake）
- 编译日期: 2026-10-08
- 编译器: clang (OHOS SDK 15.0.4)
- 目标: aarch64-linux-ohos (arm64)
- 状态: built（本地验证通过，conan 配方已生成）

## 编译步骤

源码为 libreswan 5.4.1 官方 release（pluto 为其 IKE 守护进程组件）。
应用 2 个补丁（getpass fallback + XFRM uAPI compat）+ 1 个构建期 shim
（ohos_compat.h，由 recipe build() 创建，见下）后，`make programs` 命令行注入适配参数：

```bash
make programs \
  OSDEP=linux LINUX_VARIANT=generic \
  USE_UNBOUND=false USE_DNSSEC=false USE_LDNS=false USE_LIBCURL=false \
  USE_SYSTEMD_WATCHDOG=false USE_NFLOG=false USE_NFTABLES=false \
  USE_IPTABLES=false USE_AUTHPAM=false USE_LIBCAP_NG=false USE_CAT=false \
  WERROR_CFLAGS= \
  CFLAGS="-O2 -D_UAPI_LINUX_SOCKET_H -include ohos_compat.h" \
  NSS_CFLAGS="-I<nss>/include -I<nspr>/include/nspr -I<libevent>/include" \
  NSS_LDFLAGS="-L<nss>/lib -L<nspr>/lib -L<libevent>/lib \
    -lnss3 -lsmime3 -lnssutil3 -lfreebl3 -lplc4 -lplds4 \
    -lnspr4 -levent_core -levent_pthreads" \
  PREFIX=<prefix> -j4
```

产物: `OBJ.linux.aarch64/programs/pluto/pluto`（约 11.6 MB arm64 ELF）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `OSDEP=harmonyos` 无对应 mk | 无 `mk/defaults/harmonyos.mk` | 强制 `OSDEP=linux` |
| 2 | 链接缺符号（find_kernel_ifaces4/6、nl_addattr_nest_end、resolve_default_route） | `LINUX_VARIANT` 从 `/etc/os-release` 取值，OHOS 无此文件 → 变量为空 → `ifneq ($(LINUX_VARIANT),)` 门控的 linux-variant 源文件被静默排除 | `LINUX_VARIANT=generic`（非空即可） |
| 3 | NSS 头/库找不到 | libreswan 加密后端是 NSS（非 OpenSSL），make 系统 `NSS_CFLAGS/NSS_LDFLAGS ?= -lnss3…` 无 `-L` 路径 | 从 conan nss/nspr/libevent 包推导 `-I`/`-L`/`-l` 注入 |
| 4 | `getpass` 隐式声明（-Werror） | `getpass(3)` POSIX 2008 已废弃，不在 OHOS libc | `whack/send.c` 加 `whack_getpass()` stdin fallback（补丁 0001） |
| 5 | `sockaddr_storage` 重定义 | OHOS `linux/socket.h` 是 bionic 式自动生成头，只有文件守卫、无 glibc 的 struct 级守卫；`linux/rtnetlink.h→linux/netlink.h→linux/socket.h` 与 `<sys/socket.h>` 冲突 | 构建期 `-D_UAPI_LINUX_SOCKET_H`（跳过内核副本）+ `-include ohos_compat.h`（补 `__kernel_sa_family_t`）；不改内核头消费者源码 |
| 6 | XFRM uAPI 属性未声明（XFRMA_IPTFS/SA_DIR/MODE_IPTFS/OFFLOAD_PACKET） | OHOS 内核头较旧，predates libreswan 5.4 使用的新版 XFRM 属性；自带的 external/linux-xfrm-headers 强挂会引发 #5 同类冲突 | `kernel_xfrm.c` 加 `#ifndef` compat 块，取上游真实值（XFRM_MODE_IPTFS=5、XFRM_OFFLOAD_PACKET=4，补丁 0002）；**R40 运行时边界** |
| 7 | `CMSG_NXTHDR` 符号比较等 -Werror 告警 | OHOS bionic 式头文件与 glibc 类型差异 | `WERROR_CFLAGS=`（?=. 可命令行覆盖）降级为告警，保留 -Wall |
| 8 | `PAM` 头找不到 | PAM 门控变量是 `USE_AUTHPAM`（`USE_PAM_AUTH` 只是 -D 宏，不控源文件） | `USE_AUTHPAM=false` |
| 9 | manpage 生成失败（xmlto 不存在） | xmlto 不在 OHOS 制品仓；manpage 是文档非功能 | conanfile 构建时生成 stub xmlto（man 格式按 `refnames.sh` 逐 refname 出空文件，单 XML 可含多 manpage；html 出 `<stem>.html`） |

## 源码修改

- `lib/libswan/whack/send.c` — 新增 `whack_getpass()` stdin fallback，替换 `getpass()`（补丁 0001）
- `programs/pluto/kernel_xfrm.c` — `#include "linux/xfrm.h"` 后加 XFRM uAPI compat 块（补丁 0002）
- `ohos_compat.h` — 补 `__kernel_sa_family_t` typedef，构建期 `-include`（**非补丁**：由 recipe `build()` 用 `save()` 创建，见 conanfile.py `_OHOS_COMPAT_HEADER`）

## 依赖版本

- nss/3.118.1（加密后端，libnss3/libsmime3/libnssutil3/libfreebl3）
- nspr/4.37（libnspr4/libplc4/libplds4）
- libevent/2.1.13（libevent_core/libevent_pthreads）

## 验证结果

```bash
$ LD_LIBRARY_PATH=<nss/lib>:<nspr/lib>:<libevent/lib> pluto --version
Libreswan 5.4.1 IKEv2 IKEv1 XFRM XFRMI esp-hw-offload FORK PTHREAD_SETSCHEDPRIO NSS (IPsec profile) (NSS-KDF)
$ file OBJ.linux.aarch64/programs/pluto/pluto
pluto: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

能力横幅确认：NSS 加密后端 + NSS-KDF 已编译进，XFRM/XFRMI 内核接口已编译进。

## 上游测试清点（R51）

- `testing/pluto/` 下 **1434 个** IKEv1/IKEv2 端到端脚本回归测试（KVM/QEMU 双 VM 框架）——不可执行（PR 正文验证结果 6 条实证）
- `testing/programs/` 下 **15 个** check 工具——执行 12（9 个上游 local-check：asn1/authby/dn/flags/ip/jambuf/seedbits/time/vendorid + 3 个零参数自测：enum/hunk/keyid）；3 个不可执行（getpeercon_server 为 USE_LABELED_IPSEC 门控 / kernel/ 为 KVM 模板 / ttodatacheck 为手工诊断工具）
- `programs/cavp/` 下 **3 个** NIST ACVP 向量（test.acvp.ikev1_dsa/ikev1_psk/ikev2）——全部执行通过
- `programs/algparse/` **2 个模式**——`--tp` proposal 解析（上游 local-check 入口）+ `--ta` test_ike_alg（lib/libswan AES-CBC/CTR/GCM + HMAC-SHA1 KDF 官方向量自测）——均执行通过
- `make check` → `regress` 目标驱动 KVM 框架（本环境不可执行）

**执行情况：17/17 个可运行上游测试入口全部通过**（其中 5 个——3 个零参数自测 + algparse --tp/--ta——已纳入 conan 包并经 CI test.sh 复核执行；其余 12 个（9 个 local-check + 3 个 cavp 向量）经本地执行验证通过、未纳入 conan 包）；全量 1656 = 222 单元 + 1434 集成，未执行 1639 项逐条原因见 PR 正文。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| OBJ.linux.aarch64/programs/pluto/pluto | ~11.6 MB | pluto IKE daemon（arm64 ELF） |

## R40 适配完整性边界（编译通过 ≠ 适配完成）

1. **XFRM 内核接口**：compat 块补齐的 IPTFS 流量整形 / SA 方向 / 硬件卸载等新版 XFRM 特性，OHOS 内核运行时是否实现无法在编译期验证——属 R40 深度适配边界
2. **10 个被裁剪的可选功能**：DNSSEC 密钥校验、unbound、libcurl、systemd-watchdog、nflog/nftables/iptables 内核日志与策略、PAM 认证、libcap-ng 能力、cat —— 周边集成不完整，核心 IPsec/IKE 功能保留
3. **上游端到端回归**（1434 个 KVM 双 VM 测试）无法在本环境运行

## 注意事项

- `LINUX_VARIANT` 必须非空（`generic` 即可），否则 linux-variant 源文件被静默排除、链接缺符号
- PAM 门控是 `USE_AUTHPAM`（不是 `USE_PAM_AUTH`）
- 头文件冲突修复是**构建期**（-D + -include），非源码修改——换 OHOS SDK 版本若 `linux/socket.h` 形态变化需复核
- XFRM compat 值取上游 `external/linux-xfrm-headers` 真实值，非猜测
---

**编译结束**: 2026-10-08 22:05
**最终状态**: built
