# rtnppd 1.7b — OpenHarmony 编译记录

## 基本信息
- 软件: rtnppd（TNPP 3.8 分组路由守护进程，串口/IP 寻呼组网）
- 版本: 1.7b
- 构建系统: makefile（无 configure，单一 Makefile）
- 目标: ohos-aarch64
- 依赖: 无
- 上游: https://sourceforge.net/projects/rtnppd/
- 源码: https://downloads.sourceforge.net/project/rtnppd/Original/1.7/rtnppd-1.7b.tar.gz

## 编译指导
- 纯 Makefile：
  `make CC=<工具链 cc> CFLAGS="-O2 -Wall" -j1`
- Makefile 自带 `$(CC)` 链接三个二进制（rtnppd/testq/tnpppage），无外部 `-l` 依赖
- make -j1（单作业，R9）
- 补丁全部为可移植性修复，无平台宏（PF5 干净）

## 补丁清单
- 0001-blowfish-h-stdint.patch — blowfish.h 引入 `<stdint.h>`，`u_int32_t/u_int64_t` 改为 `uint32_t/uint64_t`（musl 的 `sys/types.h` 不提供 BSD 名）
- 0002-blowfish-c-portability.patch — blowfish.c 同上类型替换 + 补 `<arpa/inet.h>`（htonl/ntohl）
- 0003-rtnppd-c-portability.patch — `<sys/fcntl.h>`（glibc 专有）改为 `<fcntl.h>`；补 `decrypt_packet()` 原型；`u_int64_t` 改 `uint64_t`
- 0004-testq-c-main.patch — testq 的 `main()` 补 `int` 返回类型 + 缺失的 `<stdlib.h>/<unistd.h>`
- 0005-tnpppage-c-return.patch — `send_tnpp_packet()` 的裸 `return;` 改为 `return 0;`

## 已知限制
- 上游 rtnppd 1.7b 无测试套件（Makefile 仅 default/rtnppd/testq/tnpppage/clean/install/install.config/key 目标），功能验证由 test_package 真实执行三个二进制（usage/getopt 启动路径）完成
- `rtnppd` 运行时需串口/IP 组网与配置文件，test_package 仅覆盖安全启动路径，不做真实组网（需 root/网络，CI 不可复现）
- 上游 `make install` 会写 `/etc//var/spool` 并用 dd 生成密钥，package() 改为直接拷贝产物

## 功能验证
- test_package/test.sh: 5 断言（其中 OHOS 特有 2 项）
  1. `rtnppd -h` 打印 usage 横幅并 exit(1)
  2. `tnpppage` 无参打印 usage 并 exit(1)
  3. `testq` 无参打印 usage 文本并 exit(1)
  4. OHOS 特有: 三个产物均为 AArch64 ELF（e_machine=0xB7）
  5. OHOS 特有: 三个产物均链接 OHOS/musl loader
