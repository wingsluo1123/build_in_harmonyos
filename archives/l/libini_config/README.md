# libini_config

libini_config 是 SSSD ding-libs 项目中的 INI 配置解析库，提供 INI 文件解析、配置对象、规则校验与序列化 API。

## 功能

- 从内存或文件解析 INI 配置并构建配置对象。
- 提供整数/字符串/数组等类型取值与校验 API。
- 通过 pkg-config（`ini_config`）与 CMake（`libini_config::libini_config`）消费。

## OpenHarmony 适配

- 在 HarmonyOS PC arm64（`os=OHOS`、`arch=armv8`）上使用 clang/LLVM 15 原生构建。
- 适配 GNU Autotools 对 `aarch64-unknown-linux-ohos` 的识别。
- 针对 HMDFS 临时目录权限、文件模式归一化、`open_memstream` 大小发布和 musl regex 诊断差异提供可移植补丁。
- 构建完整上游源码树并运行全部 Automake 测试，产物仅交付 `libini_config`。

## 依赖

库本身不增加 Conan 运行时依赖；上游 Check 测试使用 `check/0.15.2` test requirement，Autotools 重生成使用 `autoconf/2.72`、`automake/1.18`、`libtool/2.5.4` tool-requires。

## 参考资料

- 上游仓库：https://github.com/SSSD/ding-libs
- 1.4.0 Conan 配方：[`1.4.0/`](1.4.0/)
