# U-Boot (uboot)

[U-Boot](https://docs.u-boot.org) — 通用引导加载器（Denx）。

## 本仓适配内容

- **sandbox 目标**：U-Boot 编译为宿主 userspace 二进制，包内
  `u-boot-sandbox` 可经 `-c "命令"` 交互；全量 C 侧单元测试（919 子测试，
  按 u-boot.sym 链接器列表符号枚举）逐子测试独立进程执行——上游 pytest
  同款口径（单进程 `ut all` 有跨用例状态污染，上游不裸跑）。
- **host 工具**：mkimage（ITS→FIT 镜像打包）、dumpimage/fit_info（FIT
  解析）、mkenvimage（环境镜像）、fdtgrep。
- **固件**：`firmware/u-boot-qemu_arm64.bin`（qemu_arm64_defconfig，
  aarch64，OHOS 上以 clang 原生构建——显式 `HOSTCC=clang CC=clang`，
  2026.07 上游已移除 LLVM=1 伞开关）。

## 用法示例

```sh
# FIT 打包
mkimage -f boot.its boot.itb
# 校验解析
dumpimage -l boot.itb
# sandbox 单元测试冒烟（单套件；全量 919 子测试逐进程口径见 test_package）
u-boot-sandbox -c "ut lib; exit"   # 汇总行 failures: 0 即通过
```

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2026.07 | published | denx 官方发行包 + 15 枚移植/上游修复补丁，显式 clang 构建 |

许可证：GPL-2.0-or-later（上游 Licenses/gpl-2.0.txt 随包安装）。
