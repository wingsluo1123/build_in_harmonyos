# synscan 5.02 — HarmonyOS 编译记录

## 概述

synscan（https://digit-labs.org/files/tools/synscan/）是高性能 SYN 端口扫描工具集，
由两个命令行程序构成：`synscan`（通过原始套接字发送构造的 TCP SYN 包）与 `sslog`
（用 libpcap 监听返回的 SYN/ACK，判断端口是否开放）。

**编译状态**: ✅ 成功（built）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS HongMeng Kernel aarch64 |
| 编译器 | clang 15 |
| C 库 | musl libc |
| 依赖 | libpcap/1.10.6（configure 硬性要求，sslog 链接） |

## 编译步骤

```bash
# synscan release tarball 自带生成的 configure + Makefile.in，无需 autoreconf
./configure --with-libpcap=<libpcap 暂存目录> --prefix=/   # 应用 patch 0001
make linux          # 选中上游 Linux/raw-socket 路径（-DLINUX）
ar rcs libsynscan.a common.o net.o obuf.o   # 归档解析引擎供消费者/测试使用
```

产物（package() 手工 copy，不走 make install）：`bin/synscan`、`bin/sslog`、
`lib/libsynscan.a`、`include/{net,iter,obuf,common,synscan}.h`。

## 补丁说明

### 0001 - configure: HMFS 临时目录 umask 修复

上游 `configure` 的 AS_TMPDIR 段用 `(umask 077 && mktemp -d ./confXXXXXX)`（+077
mkdir 回退）建临时目录写 subs1.awk；HMFS 上 077/setgid 临时目录属主不可写，导致
config.status 失败于 `./conf*/subs1.awk: Permission denied`（同 libapreq2 2.17 /
cln 1.3.7 / tta 2.2 / rancid 3.14 指纹）。补丁移除 mktemp 分支并改为
`umask 022 && mkdir`。

## 已知问题

- synscan/sslog 的**运行时扫描**依赖原始套接字 + libpcap + root（`getuid()/geteuid()`
  检查），真机无 root 环境无法跑完整 SYN 扫描路径；`-V`/`--version` 在参数解析阶段
  提前退出（早于 root/raw-socket 检查），可用于二进制冒烟。
- 解析引擎（net.c/common.c/obuf.c 的 IP/端口列表解析、迭代器、计数、TCP 标志解析）无
  libpcap 依赖且不需特权，已归档为 `libsynscan.a` 供消费者/测试真实调用。

## 验证结果

（工作树阶段本地以 gcc 全量验证 configure + make linux + 解析 API 消费者；最终以
hmbs 真机 `conan create` 为准）
- 本地 gcc 全量跑通 configure + `make linux`（synscan/sslog 生成）+ `ar` 归档。
- 解析 API 消费者（链接 libsynscan.a）20 项断言全过；`synscan/sslog -V` 退出码 0。
- 上游 synscan 5.02 无任何自动化测试（no_tests），由 test_package 消费者视角验证
  （20 项解析 API 断言 + 两个 `-V` 二进制冒烟）。
