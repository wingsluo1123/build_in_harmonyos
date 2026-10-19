# mtd-utils (mtd)

**描述**: Memory Technology Device (MTD) userspace utilities - 内存技术设备（MTD/NAND/NOR Flash）用户空间工具集

mtd-utils 是 Linux MTD（Memory Technology Device）子系统的用户空间工具集，提供对 NAND/NOR Flash 存储设备的擦除、读写、格式化与映像管理能力，是嵌入式与存储场景下管理 Flash 设备的常用命令行工具集。

主要功能：
- **MTD 工具**: `flash_erase`（擦除 Flash 块）、`nanddump`（导出 NAND 内容）、`mtdinfo`（查询 MTD 设备信息）、`flashcp`（复制到 Flash）、`flash_lock/flash_unlock` 等
- **UBI/UBIFS 工具**: `ubiformat`（格式化 UBI 映像）、`ubinize`（生成 UBI 映像）、`ubiattach/ubidetach`（挂载/卸载 UBI 卷）、`mkfs.ubifs`（制作 UBIFS 文件系统）、`fsck.ubifs`（修复 UBIFS）等
- **JFFS2 工具**: `mkfs.jffs2`（制作 JFFS2 文件系统）、`jffs2dump`（JFFS2 映像检查）等

**官方网站**: https://www.linux-mtd.infradead.org/

**源码仓库**: https://git.infradead.org/mtd-utils.git （官方上游；GitHub 官方维护者镜像：https://github.com/sigma-star/mtd-utils）

**许可证**: GPL-2.0-only

## 编译信息

**构建系统**: autotools（git 源码无 configure，需先 `sh ./autogen.sh` 执行 autoreconf 生成 configure）

**依赖**（编译/运行均需，由 Conan 制品仓管理）:
- zlib/1.3.1
- lzo/2.10
- zstd/1.5.6
- libuuid/2.42.2
- openssl/3.0.21

> 注：mtd-utils 2.3.1 不依赖 lz4（configure.ac 无 lz4 检查）。

## OHOS 适配要点

- **autoreconf 前置**: git 源码无 configure，需先运行 `sh ./autogen.sh`（autoreconf）；config.guess 2.72 已能识别 HarmonyOS，configure 输出 `aarch64-unknown-linux-ohos`，无需 E007 平台识别补丁。
- **E011 umask 修复（HMDFS 特有）**: autoconf 生成的 configure 内嵌 `(umask 077 && mktemp -d "./confXXXXXX")` 创建 0700 临时目录，HMDFS 上 UID 映射导致 config.status 报 "Permission denied (subs1.awk)"。修复在 conanfile.py `build()` 内 autoreconf 之后 Python 替换 `umask 077`→`umask 022`（configure 为 autoreconf 构建产物，无法用 refresh-patch 追踪，故不入 patches/；与 akku/1.1.0 同方案）。
- **uuid 头文件布局**: 上游源码直接 `#include <uuid.h>`，但标准 libuuid（e2fsprogs/conan libuuid 包）头文件位于 `include/uuid/uuid.h`，需改为 `#include <uuid/uuid.h>`，对应补丁 `patches/0001-ubifs-utils-mkfs.ubifs-mkfs.ubifs.c.patch`。
- **安装目录**: 工具安装到 sbindir（`--prefix=/` 时即 `/sbin`），conanfile.py `package_info()` 声明 `bindirs=["sbin", "bin"]`（R38 commands.json 已声明）。

## 版本历史

- 2.3.1 (2026-10-17): 首次适配 HarmonyOS PC arm64；本地 conan verify 通过、W3 本地 CI 通过（status: built，未 upload 制品仓）

## 参考资料

- 官网: https://www.linux-mtd.infradead.org/
- 上游源码: https://git.infradead.org/mtd-utils.git
- 官方维护者 GitHub 镜像: https://github.com/sigma-star/mtd-utils
