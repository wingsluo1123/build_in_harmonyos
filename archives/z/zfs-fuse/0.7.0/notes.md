# zfs-fuse 0.7.0 适配笔记（OHOS aarch64）

## 编译环境
- 构建系统: custom（SCons，见下）
- 编译日期: 2026-10-13
- 平台: HarmonyOS PC aarch64 (musl)

## 概述
上游 0.7.0 使用 WAF(wscript) 构建，本次适配以 SCons 重写构建
（新增 `src/SConstruct` + 各目录 SConscript 改造），源码仅做平台兼容层修补，
无平台宏（`__OHOS__`）注入——探测均基于 `os.uname()` / musl libc 特性。

## 源码修改清单（patches/ 对应内容）
- `src/SConstruct`（新增）：SCons 构建入口。Python3 移植（os.uname 探测 aarch64）、
  依赖前缀环境变量 OPENSSL_PREFIX/ZLIB_PREFIX/FUSE_PREFIX、CC/AR/RANLIB 可由
  ARGUMENTS/env 覆盖、`-fcommon`、`-D_LARGEFILE64_SOURCE`、`-Dstat64=stat`。
- `src/lib/libsolcompat/ohos_compat.c`（新增）：musl 缺失符号补齐
  （dgettext/gettext/textdomain/bindtextdomain/gethostid/__assert/
  pthread_cancel/pthread_setcancelstate/pthread_yield/major/minor）。
- `src/lib/libzfscommon/ohos_paths.c`（新增）：运行时路径可重定位
  （ZFS_SOCK_DIR/ZPOOL_CACHE_DIR 环境变量，默认 /var/run/zfs、/var/lib/zfs）。
- `src/lib/libsolcompat/include/rpc/types.h`（新增）、`rpc/xdr.h` 改为自包含
  header-only xdrmem 实现（musl 无 rpc/rpc.h）。
- `src/lib/libsolcompat/include/{sys/inttypes.h,unistd_aux.h,sys/types.h}`：
  新 shim 或修补（aarch64 常量、pthread NP 宏映射、statvfs 分支切换）。
- `src/lib/libsolcompat/include/sys/isa_defs.h`：补 aarch64 块。
- `src/lib/libsolcompat/include/devid.h`：补 `#include <sys/types.h>`（dev_t）。
- `src/lib/libsolkerncompat/{fs_subr.c,include/...}`：MAX_CANON/MAX_INPUT、
  statvfs64、与 libsolcompat 同步的 shim。
- `src/lib/libumem/{sol_compat.h,umem.c,SConscript}`：ec_atomic_cas 用
  `__sync_val_compare_and_swap`、CPUHINT() 改 `_thr_self()`、弃 autotools
  改 SCons 直接构建（kernel 变体无消费者且 vmem_init 原型冲突，整体移除）。
- `src/lib/libzpool/{SConscript,include/sys/zfs_context.h}`：去 libaio/rt、
  CPU_SEQID 改 `_thr_self()`。
- `src/lib/libzfs/libzfs_zfsfuse.c`：UNIX socket 改抽象命名空间
  （沙箱文件系统 bind() 返回 EPERM）。
- `src/lib/libzfscommon/include/sys/fs/zfs.h`：ZFS_SOCK_DIR/ZFS_SOCK_NAME
  改函数（zfs_get_sock_dir()/zfs_get_sock_path()，路径可重定位）。
- `src/lib/libnvpair/nvpair.c`：nvs_xdr_nvp_op 解码时对调用方已分配缓冲区
  原地解码（xdr_string DECODE 分支），修复 nvlist_unpack EFAULT。
- `src/zfs-fuse/{SConscript,util.c,zfs_operations.c,zfsfuse_socket.c}`：
  LOCKDIR/LOCKFILE 可重定位（ZFS_LOCK_DIR）、attr/xattr.h→sys/xattr.h、
  ENOATTR→ENODATA、socket 改抽象命名空间、mkdir 用缓存目录函数。
- `src/cmd/stat/common/timestamp.c`：D_FMT 常量修移植。
- `src/cmd/{zdb,ztest}/SConscript` 等：去 libaio/rt 链接。

## 上游测试三步法申报（R51）
- 上游测试清点：无独立 tests/ 目录。上游可执行测试为 `ztest`（用户态池测试器，
  自带 SIGKILL 容错与 zdb 完整性校验）+ `zdb -l/-bc`（label/块指针校验）。
- 实测（本机 aarch64 OHOS）：
  - `ztest -f <dir> -T 25`：exit 0，4 passes，kill rate 100%，完整性校验通过。
  - `ztest -f <dir> -T 10 -V`：exit 0（Pass1-4 全过，16.9s）。
  - `zdb -l <vdev>`：label 解析正常（nvlist/XDR shim 验证）。
- 通过率：2/2（ztest、zdb）= 100%。

## 运行时已知限制
- FUSE 挂载需 /dev/fuse 与可写挂载点；沙箱内 mount 受限（非适配引入）。
- /var 只读 → 运行时路径经 ZFS_SOCK_DIR/ZPOOL_CACHE_DIR/ZFS_LOCK_DIR 环境变量
  重定位（含默认值回退，CI 用默认值即可运行 zdb/ztest 文件池模式）。
---

**编译结束**: 2026-10-13 20:45
**最终状态**: published
