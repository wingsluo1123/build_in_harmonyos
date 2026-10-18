# librem-ec 0.9.2 HarmonyOS 适配笔记

> 档案创建时间: 2026-10-18
> 状态: blocked（内核模块，等待内核头包或交叉编译方案）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | librem-ec（上游包名 librem-ec-acpi-dkms） |
| 版本 | 0.9.2 |
| 构建系统 | Kbuild（Linux 内核外部模块） |
| 源码 | https://source.puri.sm/nicole.faerber/librem-ec-acpi-dkms/-/archive/v0.9.2/librem-ec-acpi-dkms-v0.9.2.tar.gz |
| 镜像 | https://distfiles.alpinelinux.org/distfiles/v3.20/librem-ec-acpi-dkms-v0.9.2.tar.gz |
| SHA256 | f238547e170d6b8a56ca724b71ca0719bee19dd14257079f463444d32b42c0a2（13093 字节，已本地验证） |
| 许可证 | GPL-2.0-only |
| 上游主页 | https://source.puri.sm/nicole.faerber/librem-ec-acpi-dkms |

## 二、W0 依赖检查

librem-ec-acpi 无 Conan 依赖，其唯一构建依赖是 Linux 内核头与已配置的内核构建树。
OHPCD 制品仓与 HarmonyOS sysroot 均不提供该依赖，这是根本阻塞点（同族先例 acpi_call 1.2.2）。

## 三、源码与构建系统分析

- tarball 共 22 个条目：`librem_ec_acpi.c`（797 行）、Kbuild 风格 `Makefile`、`debian/` 打包脚本、`usr/share/initramfs-tools/` 钩子。
- `Makefile` 仅定义 `all`（`make -C /lib/modules/$(uname -r)/build M=$(PWD) modules`）与 `clean`，无 check/test 目标。
- `debian/rules` 将 configure/build/test/clean 全部覆盖为空操作，仅保留 install 与 dkms 助手。
- `librem_ec_acpi.c` 包含 13 个内核内部头：`linux/acpi.h`、`linux/hwmon.h`、`linux/input.h`、`linux/leds.h`、`linux/module.h`、`linux/power_supply.h`、`acpi/battery.h` 等。
- 驱动注册 Purism ACPI ID `316D4C14` / `PURI4543`，实现电池阈值、LED、hwmon、电源与输入设备。
- `debian/librem-ec-acpi-dkms.dkms` 声明 `BUILT_MODULE_NAME=librem_ec_acpi`、`AUTOINSTALL=yes`，属典型 DKMS 内核模块。

## 四、librem-ec 的功能

Purism Librem 14 笔记本嵌入式控制器（EC）的 ACPI 驱动：向内核注册 ACPI 设备，
暴露电池充放电阈值、键盘/通知 LED、风扇与温度 hwmon、电源状态与按键输入，
用户态通过 sysfs/leds/hwmon/power-supply 节点观察，无独立用户态二进制。

## 五、为何无法在 HarmonyOS 构建

### 编译期阻塞

`librem_ec_acpi.c` 依赖的头全部位于 Linux 内核源码树，非标准 libc。
OHOS sysroot 不提供 `linux/module.h`、`linux/acpi.h` 等外部模块编译所需的头与 Kbuild 基础设施，
亦无 `/lib/modules/*/build` 内核构建树。`MODULE_LICENSE`、`module_init`、
`struct acpi_device_id` 在 bionic 导出的 UAPI 头中命中为零。

### 运行时阻塞（即使能编译）

1. `acpi_evaluate_integer/object` 等 ACPI 内核 API 在鸿蒙内核不存在；
2. LED/hwmon/power-supply 内核子系统注册接口与 Linux 行为不一致；
3. `.ko` 加载需要 root 与 `insmod`，沙箱与 CI worker 均无该权限。

### 不裁剪原则

本包无可独立交付的用户态组件：全部逻辑位于内核模块内，
不存在上游自建的 `bin_PROGRAMS` 用户态形态。按 jool/acpi_call 分层交付先例，
内核态部分如实申报为未验证通过，不伪造内核头、不交付预编译 `.ko`。

## 六、仓库内同类配方

| 配方 | 类型 | 状态 | 说明 |
|------|------|------|------|
| `acpi_call/1.2.2` | 内核模块（Kbuild） | blocked | 同构阻塞，源码快照加 fail-closed 契约 |
| `acpitool/0.5.1` | 用户态 CLI | 构建通过 | 无需内核头 |
| `acpica/20251212` | 用户态工具 | 构建通过 | iASL 编译器 |
| `acpid/2.0.34` | 用户态守护进程 | 已收录 | 守护进程 |

差异：其余 ACPI 配方均为用户态程序，仅本包与 acpi_call 为纯内核模块。

## 七、可能的解阻塞路径

1. 为 OHOS 打包内核头 Conan 包（若鸿蒙内核基于 Linux，抽取对应头与 Kbuild 树，工作量大）；
2. 在 Linux 主机按目标内核版本交叉编译 `.ko`（要求内核 ABI 匹配）；
3. 用 `acpica` 用户态库重写 EC 方法调用（不再是同一驱动，仅功能近似）；
4. 维持现状：导出上游源码快照供检查，内核态验证保持阻塞（当前方案）。

## 八、上游测试

上游无任何自动化测试。唯一验证方式是在 Purism 硬件上
`insmod librem_ec_acpi.ko` 后观察 LED/hwmon/电源节点或调用 ACPI 方法，
需要 root、匹配的内核头与 ACPI 固件支持。

## 九、打包说明

- 版本号采用上游 tag `v0.9.2`，制品 `librem-ec/0.9.2`。
- `conandata.yml` 主 URL 为 Alpine 权威镜像（已校验 sha256），
  官方 Purism GitLab 归档保留为回退，CI 可自动尝试。
- 无补丁：快照包不对源码做任何修改。
- `package()` 导出 `librem_ec_acpi.c`、`Makefile`、`README.md`、`LICENSE` 至 `src/`，
  `test_package` 对其中 `.c` 文件执行 8 项源码契约断言。
- `build()` 故意为空操作，避免在无内核头环境伪造编译成功。

## 十、本地验证记录

首轮仅完成工作树，真机预检待 HMBS 后台执行后回填。
`test_package` 设计 8 项断言全部来自源码确定性 grep，
`HMBS_TEST_PACKAGE_RESULT` 与 `HMBS_UPSTREAM_TEST_RESULT` 均由
`check_source.sh` 真实执行后输出，不做字符串计数或算术修补。

## 十一、参考

- `archives/a/acpi_call/1.2.2/`（同构内核模块先例）
- `knowledge/doc/E1805.md`（Kbuild 内核模块 fail-closed 契约）
- `knowledge/drafts/DRAFT-jool-modules-lts-6.18.39-kernel-module-not-deliverable.kv`（分层交付判定）
