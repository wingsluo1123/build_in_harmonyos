# libkeccak

libkeccak 是一个 C 语言库，提供 Keccak/SHA-3/SHAKE/RawSHAKE 哈希算法的实现。它是 sha3sum 工具的核心依赖库。

## 功能概述

- **SHA-3** 系列：SHA3-224, SHA3-256, SHA3-384, SHA3-512
- **Keccak** 系列：Keccak-224, Keccak-256, Keccak-384, Keccak-512
- **SHAKE** 系列：SHAKE-128, SHAKE-256（可变长度输出）
- **RawSHAKE** 系列：RawSHAKE-128, RawSHAKE-256
- **cSHAKE** 系列：cSHAKE-128, cSHAKE-256（可定制 SHAKE）
- **HMAC**：基于 Keccak 的 HMAC 实现
- **状态管理**：状态的创建、复制、序列化/反序列化、重置、擦除
- **工具函数**：十六进制编码/解码、文件哈希计算

## OHOS 适配

### 适配要点

- **构建系统**：纯 Makefile（非 autotools），无 `configure` 脚本。通过 `make` 命令行变量覆盖 `CC`、`CFLAGS`、`CPPFLAGS`。
- **编译器覆盖**：`config.mk` 中 `CC=c99`，需通过 `make CC=clang` 覆盖。
- **编译警告**：clang 不支持 GCC 的 `__optimize__("-O0")` 属性，仅产生 `-Wignored-attributes` 警告，不影响编译结果。
- **Conan 集成**：使用 `basic_layout(src_folder=".")` + `make -C {self.source_folder}` 解决 Conan 构建目录与源码目录分离问题。
- **源码下载**：GitHub API URL 无文件扩展名，需在 conandata.yml 中添加 `filename` 字段帮助 Conan 检测 tar.gz 格式。

### 已知问题

无。所有测试通过，无补丁需要。

## 依赖关系

### 编译依赖
- libc
- clang（编译器）
- make
- coreutils
- binutils/llvm-ar

### 运行依赖
- libc

## 参考资料

- 项目主页：https://github.com/maandree/libkeccak
- SHA-3 标准：NIST FIPS 202
- Conan 引用：`libkeccak/1.4.3@ohpcd/stable`
