# fuse for HarmonyOS (OpenHarmony)

## 概述

`fuse` 是 libfuse 的 **FUSE 2.x 线（Libfuse2 旧 ABI）** 在 HarmonyOS/OpenHarmony
(aarch64) 上的适配归档：提供 `libfuse.a` / `libulockmgr.a` 静态库、FUSE 2.x 头文件
与两个命令行工具 `fusermount`、`ulockmgr_server`。

旧 ABI 与 FUSE 3.x（`libfuse3`）**并存且互不替代**：Conan 侧两者包名/引用不同、
各自独立前缀，因此同一台机器同时安装互不冲突；消费方按自身使用的 ABI 选择。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | fuse（FUSE 2.x / Libfuse2 legacy ABI） |
| 版本 | 2.9.9 |
| 下载地址 | https://github.com/libfuse/libfuse/releases/download/fuse-2.9.9/fuse-2.9.9.tar.gz |
| 官方仓库 | https://github.com/libfuse/libfuse |
| 许可证 | LGPL-2.1（库）/ GPL-2.0（工具） |
| 构建系统 | autotools（configure + make） |
| 包类型 | library（含 bin/ CLI，故软件级声明 commands.json） |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| SDK | ohos-sdk 26.0.0.18 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 (LLVM) |
| 构建 | autotools (autoconf 2.72 / automake) |

## 已适配版本

- [2.9.9](./2.9.9/)

## 关键适配点

1. **E011 — umask 077**：`configure` 用 `umask 077` 建 `config.status` 的
   `confXXXXXX` 临时目录；HMDFS 上该目录对当前进程不可写，configure 直接
   `cannot create ... Permission denied`。补丁把两处 `umask 077` 改为 `022`。
2. **E007/E072 — 2016 版 config.sub**：自带 `config.sub` 时间戳 `2016-11-04`。
   传 `--build/--host=aarch64-unknown-linux-gnu` 该版本即接受，无需替换
   `config.guess`/`config.sub`，也避开自带 `ltmain.sh` 对 `-ohos` 的不稳定处理。
3. **E085 — pthread_cancel 缺失**：`example/` 的程序链接 `libfuse.so` 时撞
   OHOS bionic 未实现的 `pthread_cancel`/`pthread_setcancelstate`
   （`undefined reference`）⇒ `--disable-example` 跳过示例；库本身不受影响。
4. **R26 — 系统同名库静态化**：`libfuse` 与系统同名，动态 `.so` 会污染 `/lib`，
   故 `--enable-static --disable-shared`，并通过 `validate()` 拒绝 `shared=True`。
5. **`_FILE_OFFSET_BITS=64`**：`fuse_common.h` 用 `#error` 强制要求，故在
   `package_info.defines` 中声明。
6. **运行期能力墙（本包核心新发现）**：`/dev/fuse` **存在但不可访问** ——
   `open("/dev/fuse", O_RDWR)` 返回 `EACCES(13)`，`ls -l /dev/fuse` 也是
   `Permission denied`，而 `os.path.exists()`/`access(F_OK)` 因 stat 失败返回
   **False（假阴性）**；`/proc/modules` 无 `fuse` 行。upstream
   `util/Makefile.am` 的 `install-exec-hook` 会 `chmod u+s fusermount` 与
   `mknod /dev/fuse`，在 OHOS 上都不生效（E046 chmod 不起作用）。
   ⇒ `fuse_mount()` 必然返回 NULL，`fusermount` 的挂载/卸载面不可用；
   可验证面收敛为**库面离线 API** + **CLI 的退出码与 usage**。

## 包内文件

| 路径 | 说明 |
|------|------|
| `lib/libfuse.a` | 主库（静态，R26） |
| `lib/libulockmgr.a` | 用户态锁管理库（静态） |
| `include/fuse.h`、`include/fuse/*.h`、`include/ulockmgr.h` | FUSE 2.x 头文件 |
| `bin/fusermount` | 挂载/卸载辅助工具（setuid 在 OHOS 不生效） |
| `bin/ulockmgr_server` | `ulockmgr` 的用户态服务进程 |

> 上游还会安装 `mount.fuse`(/sbin)、SysV init 脚本(/etc/init.d) 与 udev 规则
> (/etc/udev/rules.d)；OHOS 上 `/etc` 是指向 `/system/etc` 的符号链接、无
> udev/SysV init，故这些 rootfs 专用件在 `package()` 中剥除，不进 Conan 包。

## 参考资料

- 源码仓库：https://github.com/libfuse/libfuse
- FUSE 内核接口：https://www.kernel.org/doc/html/latest/filesystems/fuse.html
- 知识库：E011（HMDFS umask 077）、E007/E072（config.sub/triplet）、E085（musl 缺 pthread_cancel）、E046（chmod 不生效）
