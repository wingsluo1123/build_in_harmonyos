# DRAFT-11418 — host/目标双编译的 Kconfig 符号重映射 + select 强制回写双陷阱：无 OpenSSL 设备构建 host 工具

- **条目 ID**: `DRAFT-11418-uboot-ohos-host-kconfig-remap`
- **严重度**: 1（两个坑叠加、单独处理都无效；修复模式固定可复用）
- **类别**: kconfig, toolchain, build, host-tools
- **触发工具/阶段**: clang | kconfig | conf | mkimage — conan_build
- **来源**: u-boot 2026.07 适配（task #11418，OHOS PC 真机 2026-09-29，上游 denx 发行包 + 补丁）

## 错误特征

```
fatal error: 'openssl/evp.h' file not found    （host 工具编译期）
undefined reference to `fit_config_verify`      （若漏掉 0006，链接期）
```

## 场景

无 OpenSSL 设备上构建 host 工具，两个独立坑叠加：

**设备/HNP/SDK 三处均无 openssl 开发头**（bind.org 仅私有
libcrypto.so.3 无头文件；SDK sysroot 仅自研密码库 libohcrypto/
libnet_ssl）。上游文档化开关 `TOOLS_LIBCRYPTO=n` 后：

**坑 1（重映射漏网）**：host 代码里 `CONFIG_IS_ENABLED(FIT_SIGNATURE)`
经 `include/linux/kconfig.h` 的 USE_HOSTCC 重映射解析为
**CONFIG_TOOLS_FIT_SIGNATURE**（`tools/Kconfig:63`，`depends on
TOOLS_LIBCRYPTO`、def_bool y）→ 自动回落 n，openssl 头不再被包含。
但上游两处裸引用未走重映射：

- `tools/image-host.c:1397` 裸 `#ifdef CONFIG_FIT_SIGNATURE`——
  该文件内唯一未走重映射的守卫，host 编译仍编译出引用
  TOOLS_LIBCRYPTO 门控对象（fit_config_verify）的代码；
- `tools/Makefile:67` 的 `fit_check_sign` 启用条件用目标符号
  CONFIG_FIT_SIGNATURE，而签名对象（FIT_SIG_OBJS）按
  TOOLS_LIBCRYPTO 门控 → 工具启用但对象缺失，链接失败。

- `include/image.h:1788` 裸 `#if defined(CONFIG_FIT_CIPHER)`——
  USE_HOSTCC 块内用目标符号守卫 host 加密能力；host 工具编译包含
  共享的 generated/autoconf.h，目标侧 FIT_CIPHER=y（如
  sandbox_defconfig 显式开启）时宏必然定义 → 无 OpenSSL 设备上
  `#include <openssl/evp.h>` 直接炸（aisimage.o 实测）。

**坑 2（select 强制回写）**：`scripts/config -d TOOLS_LIBCRYPTO` 后
被 syncconfig 强制拉回 y——`TOOLS_KWBIMAGE`（`tools/Kconfig:41`）
default y 且 `select TOOLS_LIBCRYPTO`，Kconfig 的 select 无视用户
显式关闭。真机 .config 终态实证（复现实验证明 `-d` 本身工作正常、
RC=0）。全树仅此一处 select 源（mvebu SPL 的 `select TOOLS_KWBIMAGE`
对 sandbox/qemu_arm64 不触发）。

**坑 3（default-y 回写）**：TOOLS_LIBCRYPTO 本身 default y，`-d`
后若跑 olddefconfig 会按默认值重新置 y（真机实证）→ 不能跑
olddefconfig，靠 make 启动时 `conf --syncconfig` 按 depends 自动
收敛 TOOLS_FIT_SIGNATURE*。

## 推荐方案（patch 0005/0006 + 配方配置法，全部真机验证）

- **0005**：`image-host.c:1397` 裸 `#ifdef` 改
  `CONFIG_IS_ENABLED(FIT_SIGNATURE)`（与文件内其余守卫一致，host
  编译解析为 CONFIG_TOOLS_FIT_SIGNATURE）；
- **0006**：`tools/Makefile` 的 fit_check_sign 门控改
  `CONFIG_TOOLS_FIT_SIGNATURE`（与 FIT_SIG_OBJS 的 TOOLS_LIBCRYPTO
  门控对齐）；
- **0007**：`include/image.h:1788` 裸 `#if defined(CONFIG_FIT_CIPHER)`
  改 `CONFIG_IS_ENABLED(FIT_CIPHER)`（host 构建经重映射解析为
  CONFIG_TOOLS_FIT_CIPHER）；`tools/Kconfig` 新增 TOOLS_FIT_CIPHER
  （depends on TOOLS_LIBCRYPTO，def_bool y，仿 TOOLS_FIT_SIGNATURE）——
  有 OpenSSL 能力保留、无 OpenSSL 正确回落；
- **配方**：defconfig 后 `scripts/config -d TOOLS_KWBIMAGE -d
  TOOLS_LIBCRYPTO`，不跑 olddefconfig。

修复后：只关 TOOLS_LIBCRYPTO 即得无 OpenSSL 构建，目标侧 FIT 签名
校验/RSA 库/UT_LIB_RSA 测试全部保留；mkimage 失去签名能力（上游
文档化行为）。

## 影响

适用任何「Kbuild 系 host/目标双编译 + 无 OpenSSL 设备」在 OHOS 的
适配（内核/uboot/busybox 类）。两个坑都与 u-boot 无关：select 强制
回写是 Kconfig 通用语义；USE_HOSTCC 重映射是 Kbuild 通用机制
（barebox、buildroot 同款）。

**排查特征**：`-d` 后 grep .config 仍是 `=y` → 找 select 源；host
编译报 openssl 头缺失但目标配置已关 → 查重映射漏网。

## 恢复

若上游拒绝改裸引用，可退而关目标符号 FIT_SIGNATURE 本身——但会
连带失去目标侧签名校验与 UT_LIB_RSA 测试（损失大，不推荐）。若
select 源不可关（如与需求冲突），可对 .config 直接 sed 删除
select 符号的 `=y` 行——但下次 syncconfig 仍会回写，必须在 make
之后每轮重建，仅作应急。正解仍是关 select 源。

## 证据链

真机 2026-09-29（上游 denx 2026.07 发行包 + 补丁，reports/）：

- 首轮 `-d FIT_SIGNATURE -d TOOLS_LIBCRYPTO` + olddefconfig：
  olddefconfig 把 default y 的 TOOLS_LIBCRYPTO 打回 y（.config
  实证）；
- 二轮只 `-d TOOLS_LIBCRYPTO` 不跑 olddefconfig：syncconfig 后
  .config 终态 `CONFIG_TOOLS_LIBCRYPTO=y`（select 强制回写实证；
  复现实验证明 `scripts/config -d` 本身正常、RC=0，写出的
  `# CONFIG_TOOLS_LIBCRYPTO is not set` 被 syncconfig 覆盖）；
- grep 全树定位唯一 select 源 TOOLS_KWBIMAGE（`tools/Kconfig:41`）；
- 三轮同时 `-d TOOLS_KWBIMAGE -d TOOLS_LIBCRYPTO`：.config 终态
  两者 not set、TOOLS_FIT_SIGNATURE 经 depends 自动消失，
  image.h:1480 的 FIT_SIGNATURE 门不再触发（此前轮次卡在 flex fork
  失败/进程配额，从未编译到 aisimage.o）；
- 四轮（资源放开后全量推进）：aisimage.o 炸在 image.h:1788 裸
  FIT_CIPHER 门（autoconf.mk 已无 TOOLS_LIBCRYPTO → Makefile 的
  -DCONFIG_FIT_CIPHER 注入确认跳过；autoconf.h 仍有目标符号
  CONFIG_FIT_CIPHER=1 实证——共享头是唯一来源）→ 0007 修复；
- 详见 patches/0005-0007 与 notes.md 决策表第 11 条（坑1-3）。

## 验证命令

```sh
bash scripts/config --file <obj>/.config -d TOOLS_KWBIMAGE -d TOOLS_LIBCRYPTO
grep -E "CONFIG_TOOLS_(KWBIMAGE|LIBCRYPTO|FIT_SIGNATURE)" <obj>/.config
# 修复前：=y（select 强制回写）；修复后：not set / 消失
```

## 局限

1. 若未来上游给 TOOLS_FIT_SIGNATURE 增加新的 select 源，本配方需
   同步 `-d`；
2. mkimage 失去签名能力（上游文档化行为），构建期验证不覆盖
   signing 路径。
