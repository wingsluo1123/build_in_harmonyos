# util-linux 2.42.2 适配笔记

## 一、结论速览

| 项 | 结果 |
|---|---|
| 源码 | kernel.org 官方 `v2.42/util-linux-2.42.2.tar.xz`，sha256 与官方 `sha256sums.asc` 一致 |
| 构建 | autotools，沿用 2.39/2.42 裁剪：`--disable-all-programs` + `--enable-libblkid/libuuid/libmount` |
| `conan create` | **RC=0**，test_package 探针 `util-linux OK`（1/1） |
| 交付产物 | `libblkid.a` / `libuuid.a` / `libmount.a` + `include/`（无 bin，纯库包） |
| 上游 ts 套件 | 367 项注册测试：**17 FAILED**、224 条 SKIPPED；子测试 **820 项 = 773 通过 / 41 失败 / 6 KNOWN FAILED**，通过率 **94.3%** |

## 二、版本迭代依据

- 本版本为 `2.42` 的**纯版本迭代**（同一上游分支 v2.42 内的补丁版本，2.42.2）。
- 相对 `2.42` 配方只有三处实质差异：`version` 号、`conandata.yml` 的 URL、官方 sha256。
- 另有一处清理：删除了 `--disable-pam` / `--disable-libudev` 两个 **2.42.2 的 `configure` 并不识别**的选项
  （实测 `./configure --help` 只有 `--disable-pam-lastlog2`、`--disable-libmount-udev-support`、`--without-udev`）；
  这两个参数此前是无效果的空参数（configure 会打印 unrecognized options 警告）。
  删除后不会引入 PAM/libudev 依赖：裁剪构建只编三个库且 OHOS sysroot 内无 libudev/pam 头库，
  configure 探测不到即自动关闭；`--disable-all-programs` 也不会构建 lastlog2 等 PAM 模块。
  package_info 仍只声明 `mount/blkid/uuid` 三个自产库，无未声明的外部依赖。
- 配方逻辑（config.guess/config.sub OHOS 识别、umask 077 修复、getusershell/versionsort compat）原样沿用，2.42.2 源码结构与 2.42 一致，无需新增补丁。
- 同族包 `libblkid/2.42.2`、`libuuid/2.42.2` 已在 archives 中存在（独立打包），本包仍是三合一的库集合，供整包消费者使用。

## 三、上游测试清点与实测（R51 三步法）

### 3.1 清点

- `tests/ts/` 下测试组件目录 **91 个**，`tests/run.sh` 注册测试 **367 项**；运行时展开子测试 **820 项**（773 通过 / 41 失败 / 6 KNOWN FAILED）。
- 构建辅助：`make check-programs` 生成 `test_blkid_*`、`test_mkfds` 等消费者程序。

### 3.2 实跑环境

配方是裁剪构建（只编库），ts 套件需要完整工具集，故单独做了一次**完整构建**（非配方裁剪）用于测试：

```bash
# 完整构建（复用 conan 已生成工具链环境）
sh ~/tmp/ul-full-build.sh          # configure（umask 000 补丁）+ make
make -k check-programs             # 测试辅助程序
cd tests && PATH=<shim>:$PATH ./run.sh
```

完整构建期暴露的 OHOS 缺口（**不影响配方出包**，裁剪构建不触发）：

| 缺口 | 现象 | 处置 |
|---|---|---|
| `#!/bin/bash` shebang（12 个 tools 脚本 + ts 脚本） | `make` 生成 errnos.h 报 **Error 126**；ts 脚本 `bad interpreter` 364/367 全挂 | 指向 `/data/service/hnp/bin/bash` |
| `sockaddr_storage` 重复定义 | OHOS sysroot `linux/socket.h:23` 与 `sys/socket.h:377` 双定义 → `lsfd-cmd/sock-xinfo.c`、`lib/netlink.c`、`tests/helpers/test_mkfds.c` 编译失败 | 完整构建用 `--disable-lsfd` 绕开；配方裁剪不编 lsfd 故不受影响 |
| `getutxent()` 缺失 | `term-utils/wall.c:306` 隐式声明 → 指针转换错误 | 完整构建该工具未出包；配方只编库不涉及 |
| `versionsort` 缺失 | `sys-utils/lsmem.c` 未声明标识符（配方已对 libmount 打 compat，lsmem 未覆盖） | 同上，仅完整构建可见 |
| toybox `xargs` 无 `-I` | `run.sh` 依赖 GNU 语义 | 用 busybox 1.37 的 `xargs` 做 shim |
| toybox `sed` 无 `--in-place` | ts 脚本产生 `sed: Unknown option 'in-place'` 噪声（多数用例仍 OK） | 记录为环境差异，不改上游脚本 |

### 3.3 实测结果

```
367 项注册测试 → 17 项 FAILED（run.sh 汇总行 "17 tests of 367 FAILED"）
子测试展开 820 项：773 通过 / 41 失败 / 6 项上游 KNOWN FAILED（预期失败）
通过率 94.3%（773/820，分母含 6 项 KNOWN FAILED；剔除则为 95.0%）
SKIPPED 记录 224 条：无 root 权限 112、相关工具未构建 89（lsfd/ipcs/lsns/col/setpriv 等）、
                     其余 23（ncurses/statmount/sqlite3/mkfs.ext2/pylibmount 等）
```

失败集中在其依赖完整工具集的用例（与交付的三个库无关）：

| 用例 | 失败/总数 | 归因 |
|---|---|---|
| lsblk | 14 条 | 依赖 `--sysroot` 测试树与设备拓扑（无 NVMe/LVM/root） |
| hardlink | 7 条 | 非 root + toybox 工具语义差异 |
| mkswap | 7 条 | 无 root 权限、无 loop 设备 |
| getopt | 6 条 | 输出版本/格式与 GNU getopt 期望差异 |
| script | 4 条 | pty/文本比对差异 |
| fallocate | 3 条 | 文件系统 hole 能力差异 |
| lscpu | 3 条 | aarch64 拓扑与上游期望表不符 |
| kill | 3 条 | 信号解码与 pidfd 支持差异 |
| logger | 2 条 | 日志格式差异 |
| 其余 | fadvise/flock/ionice/misc/setarch/swaplabel/uuidd/chrt 各 1 | 权限/设备/时序相关 |

> 复现统计：`grep -E 'OK \(all [0-9]+ sub-tests|FAILED \([0-9]+ from|KNOWN FAILED \([0-9]+ from' <log>`
> 逐行累加即得 820 / 773 / 41 / 6。上表为按组件归并后的近似分布（明细行按组件合计 57 条，
> 含 KNOWN FAILED 与组内重复计数），组汇总口径以 41 + 6 = 47 为准。

**与交付库直接相关的组件实测**：blkid 组件 11 项中 3 项实跑通过
（`superblocks probing` 134 子测试、`partitions probing` 7、`output formatting` 12），
其余 8 项因无 root（7）或缺 `mkfs.ext2`（1）跳过；`uuidgen` 4/4 通过。

### 3.4 复现命令

```bash
# 上游 ts 全量（完整构建树内）
cd <build>/tests && PATH=<busybox-xargs-shim>:$PATH TMPDIR=<可写目录> ./run.sh
# 仅跑与交付库相关的组件
./run.sh blkid
./run.sh uuid
```

## 四、配方构建（交付口径）

```bash
TMPDIR=~/tmp conan create archives/u/util-linux/2.42.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → RC=0，test_package: ./test_util_linux_probe → util-linux OK
```

本地源码缓存（离线/慢网环境）：把官方 tar 包按 **sha256 命名**放进
`core.sources:download_cache` 指向目录的 `s/` 子目录即可命中，无需联网。

## 五、限制与后续

- 本包为**裁剪构建**：只交付 libblkid/libuuid/libmount，不含 util-linux 命令行工具（lsblk/findmnt/mount 等不出包），因此 CLI 相关的上游用例属于"完整构建实测"，不随包进入 CI。
- 完整构建暴露的 `sockaddr_storage` 双定义属 OHOS sysroot 的 UAPI 头偏差（`linux/socket.h` 不应定义 `struct sockaddr_storage`），若后续要出完整工具集需单独处理（shim 头预定义 `_UAPI_LINUX_SOCKET_H` 守卫）。
- 版本号口径：上游 2.42.2 首次适配，无适配修复后缀。
---

**编译结束**: 2026-10-18 00:17
**最终状态**: built
