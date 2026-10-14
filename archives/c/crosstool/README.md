# crosstool

crosstool 跟踪上游 [crosstool-ng](https://github.com/crosstool-ng/crosstool-ng)，
是一个可定制的交叉工具链生成器：通过 `ct-ng` 编排 GCC、binutils、libc 等组件的
下载、配置与构建，支持多种架构与操作系统。

## 功能概述

- 通过 kconfig 菜单（menuconfig/nconfig）定制工具链组件
- 内置大量预配置样例（`ct-ng list-samples`）
- 构建产物为可直接使用的交叉编译工具链
- 构建动作可按步骤查看与断点续建（`ct-ng list-steps`）

## OHOS 适配

- 构建系统为 autotools（`configure + make -j1`），配方无源码补丁
- OHOS 下配置时固定 `--build=aarch64-unknown-linux-gnu`，
  绕过随包 `config.guess` 对 OHOS 三元组识别缺失的问题
- 工具包形态（`package_type = "application"`）：只交付 `bin/ct-ng`，
  不提供开发库，`test_package` 直接执行二进制做功能冒烟验证，
  并用包内 `bin/ct-ng` 完整重放上游 `testing/upgrade` 8 用例升级回归套件

## 依赖关系

- C 编译器（clang）
- make、bash、awk、grep、sed、gzip（构建与安装钩子使用）
- 无 Conan 依赖（`requirements()` 为空）

## 参考资料

- 官网：https://crosstool-ng.github.io/
- 源码：https://github.com/crosstool-ng/crosstool-ng
- 文档：https://crosstool-ng.github.io/docs/
