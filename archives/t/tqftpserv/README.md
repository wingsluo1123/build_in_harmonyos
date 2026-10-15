# tqftpserv — Trivial File Transfer Protocol server over AF_QIPCRTR

**Package**: tqftpserv
**Version**: 1.2
**Upstream**: https://github.com/linux-msm/tqftpserv
**License**: BSD-3-Clause
**Build System**: Meson
**Type**: Application (daemon/CLI)

## Description

tqftpserv 是 Qualcomm 平台上的 TFTP 服务器，通过 AF_QIPCRTR（Qualcomm IPC
Router）套接字与 Modem 通信，用于远程文件系统挂载（rameedia/remoteproc 场景），
支持 zstd 压缩传输。

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| qrtr | 1.2 | AF_QIPCRTR socket 支持（libqrtr） |
| zstd | 1.5.7 | zstd 压缩固件传输（libzstd） |

## OHOS Adaptation

- systemd 不可用：`systemd-unit-prefix` 置空，补丁 `0001-ohos-systemd-init.patch`
  初始化 `systemd_system_unit_dir` 变量避免 undefined variable
- MesonToolchain 不写 ar/ranlib：从 `compiler_executables` 推导 llvm-ar/llvm-ranlib
- 上游无自动化测试；消费者测试验证 ELF aarch64 + 签名后执行 `tqftpserv -h`
