# hdparm

## 软件介绍

hdparm 是一个 Linux 命令行工具，用于查看和设置 ATA/SATA/SCSI 硬盘（含 SSD）的参数，主要能力包括：

- **设备识别**：读取型号、序列号、固件版本、传输模式、缓存大小等 identify 信息
- **性能测试**：`-t` / `-T` 测量缓存与磁盘读取吞吐
- **电源管理**：设置待机（`-S`）、休眠（`-y`/`-Y`）、APM（`-B`）等级
- **安全特性**：ATA Security 口令设置/解锁/冻结/擦除（`--security-*`）
- **高级特性**：写缓存、读写预读（`-a`/`-A`/`-W`）、DMA 模式、NCQ、TRIM（`--trim-sector-ranges`）
- **其他**：固件下载（`--fwdownload`）、光纤通道/SCSI 直通（SG_IO）

上游仓库：<https://sourceforge.net/projects/hdparm/>

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 9.65 | built | 首次适配 HarmonyOS PC（ohos-aarch64），应用 `0001-fix-getpass-musl-compat.patch` |

## 依赖

无第三方库依赖。仅使用 C 标准库与 Linux 内核 uapi 头文件；构建期依赖 `make` 与 `clang`。

## OpenHarmony 适配要点

1. **`getpass()` 缺失**：OHOS 使用 musl libc，不提供 GNU 扩展 `getpass()`。上游 `hdparm.c` 在 ATA Security 口令交互处调用该函数，直接编译会报隐式声明/未定义引用。补丁在 `#include "sgio.h"` 之后插入 `#ifndef getpass` 守卫的本地实现：`fgets` 读取口令，录入期间用 `termios` 关闭终端回显并在读取后恢复（与 glibc `getpass` 行为一致；非 TTY 场景 `tcgetattr` 失败则退化为普通读取）。
2. **构建系统为手写 Makefile**：非 autotools/CMake，配方直接 `self.run("make -j2 CC=<clang> LDFLAGS=-s")`，不使用 Autotools helper。
3. **未签名 ELF 不可执行**：OHOS 安全策略禁止执行未签名二进制，因此 `test_package` 不执行 `hdparm`，改为校验 ELF 加载契约（`PT_INTERP` = `/lib/ld-musl-aarch64.so.1`、`NEEDED` = `libc.so`、`.note.ohos.ident` 存在）。
4. **运行期强依赖块设备 ioctl**：`SG_IO`、`HDIO_DRIVE_CMD` 等需要内核与设备直通支持，属于运行时能力，与本包的编译/打包正确性无关。

## 使用方法

```bash
# 通过 conan 安装到本地缓存后，二进制位于包的 bin/ 目录
conan install --requires=hdparm/9.65

# 典型用法（需 root 与真实块设备）
hdparm -I /dev/sda          # 查看 identify 信息
hdparm -tT /dev/sda         # 缓存/磁盘吞吐测试
hdparm -B 128 /dev/sda      # 设置 APM 等级
```

> 命令声明见同目录 `commands.json`（`type: tool`，`versions.9.65.ref = hdparm/9.65`）。

## 目录结构

```
archives/h/hdparm/
├── README.md          # 本文件
├── commands.json      # 命令行工具声明（R38）
└── 9.65/
    ├── conanfile.py
    ├── conandata.yml
    ├── patches/0001-fix-getpass-musl-compat.patch
    ├── test_package/{conanfile.py,MANIFEST.yml}
    ├── manifest.yaml
    └── notes.md
```
