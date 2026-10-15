# pluto

## 简介
pluto 是 libreswan 的 IPsec IKEv1/IKEv2 守护进程，负责 IKE 协商、IPsec SA（安全关联）的建立与管理，是 libreswan 套件的核心组件。本归档为 OpenHarmony PC（aarch64）适配版本。

## OHOS 适配
- 上游为自定义顶层 Makefile（无 configure/CMake），适配参数经 `make` 命令行注入
- `OSDEP=linux` 强制（无 `mk/defaults/harmonyos.mk`）
- `LINUX_VARIANT=generic` 必需：OHOS 无 `/etc/os-release`，否则 `ifneq ($(LINUX_VARIANT),)` 门控的 linux-variant 源文件（`kernel_iface_linux.c`、`defaultroute_linux.c` 等）被静默排除，链接期缺符号
- 加密后端为 **NSS**（非 OpenSSL）：`NSS_CFLAGS`/`NSS_LDFLAGS` 从 conan `nss`/`nspr`/`libevent` 包推导
- **OHOS `linux/socket.h` 头文件冲突**：bionic 式自动生成头缺 glibc 的 `sockaddr_storage` struct 级守卫，与 `<sys/socket.h>` 冲突 → 构建期 `-D_UAPI_LINUX_SOCKET_H` + `-include ohos_compat.h` 统一修复（不改内核头消费者源码）
- **XFRM uAPI 兼容**：OHOS 内核头较旧，缺 libreswan 5.4 使用的新版 XFRM 属性（IPTFS/SA 方向/卸载）→ `kernel_xfrm.c` 加 `#ifndef` compat 块（取上游真实值）；**R40 运行时边界**：编译通过 ≠ 内核运行时支持这些特性
- `getpass(3)` 不在 OHOS libc（POSIX 2008 已废弃）→ `whack/send.c` stdin fallback
- 10 个可选依赖 OHOS 制品仓无 → `USE_*=false` 裁剪（unbound/DNSSEC/ldns/libcurl/systemd-watchdog/nflog/nftables/iptables/PAM/libcap-ng/cat）
- `WERROR_CFLAGS=` 降级：OHOS bionic 式头文件在 `-Werror` 下报告警（如 `CMSG_NXTHDR` 符号比较）
- `xmlto` 制品仓无包 → 构建时生成 stub 产出空 manpage（纯文档，不影响功能）

## 依赖
- nss/3.118.1（加密后端）
- nspr/4.37（NSS 运行时，plc4/plds4）
- libevent/2.1.13（事件驱动，event_core/event_pthreads）

## 功能验证
```bash
# L1 冒烟：执行 daemon 二进制，验证版本与能力横幅（NSS/XFRM 已编译进）
pluto --version
# 期望输出含: Libreswan 5.4.1 ... XFRM ... NSS (IPsec profile) (NSS-KDF)

# 上游自测入口（CI test.sh 内同样执行并断言 exit=0）
_enumcheck  _hunkcheck  _keyidcheck   # 零参数自测 check 工具（含 leak detective）
algparse --tp    # proposal 解析（上游 local-check 入口）
algparse --ta    # test_ike_alg 官方向量自测（AES-CBC/CTR/GCM + HMAC-SHA1 KDF）
```

## R40 适配完整性边界（编译通过 ≠ 适配完成）
- **XFRM 内核接口**：compat 块补齐的 IPTFS/SA 方向/硬件卸载等新版 XFRM 特性，OHOS 内核运行时是否实现无法在编译期验证
- **10 个被裁剪的可选功能**：DNSSEC 密钥校验、unbound、libcurl、systemd-watchdog、nflog/nftables/iptables 内核日志与策略、PAM 认证、libcap-ng 能力、cat —— 对应周边集成不完整，核心 IPsec/IKE 功能保留
- **上游端到端回归**（testing/pluto 1434 个 KVM 双 VM 测试）无法在本环境运行（无 KVM/内核 XFRM 运行时/root），见 test_package/MANIFEST.yml

## 参考
- 上游: https://libreswan.org
- 适配笔记: 5.24.1/notes.md
