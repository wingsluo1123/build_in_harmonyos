# lksctp-tools 1.0.21 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18 sysroot, musl)
- 状态: built

## 编译步骤

```bash
# 1. bootstrap（GitHub archive tarball 无 configure，须 autoreconf 自举）
#    本机 automake 1.17 安装破损（缺 Automake::Config.pm），临时以 automake-1.16.5 前置 PATH
PATH=/storage/Users/currentUser/tmp/autotools-bin:$PATH ./bootstrap
# 2. configure + build
./configure --prefix=/storage/Users/currentUser/usr/local
make -j1
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-lksctp-tools-1.0.21
make check        # upstream func_tests 编译通过；运行需内核 SCTP，OHOS 无 SCTP 模块时 Protocol not supported
# 3. Conan 配方验证（OHOS aarch64 profile）
ohc-run.py conan-init / conan-verify lksctp-tools 1.0.21   # G0-G4/L2/L4/L5 全部 PASS
# 4. finish（W2 结构 + W3 本地 CI 模拟 + W5 知识完整性）
ohc-run.py finish lksctp-tools 1.0.21 built
# 5. HarmonyOS 专项测试（test_package 消费者验证，两次独立日志+SHA256）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | HMDFS UID 映射：umask 077 创建的 0700 临时目录对当前进程不可写（E011） | configure/config.status 中 `umask 077` → `umask 022` |
| 2 | redefinition of 'sockaddr_storage' (linux/socket.h vs sys/socket.h) | OHOS 内核 UAPI linux/socket.h 与 musl sys/socket.h 均定义 sockaddr_storage（E091） | sctp.h.in 与 func_tests 对 linux UAPI include 加 `__linux_sockaddr_storage` define-guard |
| 3 | configure: cannot guess build type (uname -s=HarmonyOS) | config.guess 不认识 HarmonyOS（E007） | generate() 显式 `--build/--host=aarch64-unknown-linux-musl` |
| 4 | conan create 缺 configure | GitHub archive tarball 从不含 configure | build() 中 `autotools.autoreconf()` + tool_requires automake/libtool（同 argp-standalone） |

## 源码修改

- `patches/0001-0011-*.patch`: func_tests 移除直接 include `<linux/socket.h>`（musl sys/socket.h 已提供，E091）；`test_1_to_1_rtoinfo.c` 改用 `<netinet/in.h>`
- `patches/0012-src-include-netinet-sctp.h.in.patch`: sctp.h.in 对 `<linux/sctp.h>` include 加 sockaddr_storage 重命名守卫（E091，仅 musl/OHOS 生效）

## 依赖版本

- 无第三方 requires（纯 libsctp 库，只依赖 OHOS 系统 libc/libc++）
- tool_requires: automake/1.18, libtool/2.5.4（autoreconf 自举用）

## 验证结果

```bash
# conan create（OHOS aarch64, --build=missing）: PASS, test_package 1/1 Test Passed
# HarmonyOS 专项测试（test_package 消费者）:
#   r1: exit 0 — sctp_opt_info EBADF 可达 + SOL_SCTP/IPPROTO_SCTP=132
#   log: reports/harmonyos-specific-test-r1.log
#   sha256: b36215ee4b0eb3395e14ff85545f3cd6be9309f4f79595614dddc1bf61561430
# upstream func_tests: 编译通过（35 个测试程序）；运行需 SCTP 内核支持，
#   OHOS 无 SCTP 模块（/proc/net/sctp 不存在）→ Protocol not supported（环境边界，非适配缺陷）
```

## 交付物

- `archives/l/lksctp-tools/1.0.21/`: conanfile.py + conandata.yml + manifest.yaml + notes.md + test_package/ + 12 patches
- `archives/l/lksctp-tools/commands.json`: SCTP 工具集（sctp_darn/sctp_test/checksctp）R38 声明

## 注意事项

- func_tests 需内核 SCTP 模块，OHOS 无则不可运行；依赖可用性门禁（L0i）检查的是**依赖**（本库无 requires），非当前库自我消费
- 知识判定：E091/E011/E007 均等价命中 → 路径 A（reuse_existing），未创建新草稿