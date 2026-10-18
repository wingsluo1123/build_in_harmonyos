# SOAPsnp 1.03 构建报告

原 Makefile 的7个编译单元使用 Clang15、C++17、Release 构建。boost/1.84.0、zlib/1.3.1 使用已发布二进制并静态链接。

实际 Conan 构建、安装及官方 W3 的 L0/L1/L2/L4/L5 通过。安装产物为 ELF64/AArch64，具备 PIE、NX 和完整 RELRO。

实际验证环境：OHOS 7.0.0.32 Beta/API26/AArch64 QEMU，官方 profile 元数据为 OHOS6。
