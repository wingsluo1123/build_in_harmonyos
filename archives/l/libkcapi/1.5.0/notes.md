# libkcapi 1.5.0 适配笔记

## 构建环境

- 构建系统: Autotools
- 编译日期: 2026-07-15
- 编译器: clang / clang++
- 平台: HarmonyOS PC (aarch64)
- 状态: built

## 源码

- URL: https://github.com/smuellerDD/libkcapi/archive/refs/tags/v1.5.0.tar.gz
- SHA-256: `f1d827738bda03065afd03315479b058f43493ab6e896821b947f391aa566ba0`

## Conan 配方

Git tag 快照不包含 `configure`，而 CI Worker 不提供 `aclocal`。配方因此导出由
上游 `configure.ac` 和 `Makefile.am` 生成的 `prebuilt.tar.gz`，构建时解压这些
Autotools 文件，再以 `--disable-shared --enable-static` 配置、编译和安装。

`0001-lib-kcapi-kernel-if.c.patch` 处理 OHOS Linux UAPI 头文件中的
`sockaddr_storage` 名称冲突。

## 验证

`test_package` 编译并链接 `libkcapi::libkcapi`，调用 `kcapi_version()` 验证头文件、
静态库和消费者 CMake 元数据。
