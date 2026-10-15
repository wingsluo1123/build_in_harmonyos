# notes — zfs-src 2.4.3（OpenZFS 用户态）OHOS 适配

## 任务与判定

- 任务卡 #12370，认领人 calbee21，分支 `feat/zfs-src-2.4.3`
- 路径 C 高难度挑战件：OpenZFS 是"内核文件系统 + 用户态工具链"混合体，深度依赖 Linux 内核接口（SPL 层/内核模块/udev）；OHOS 无内核 ZFS 支持，用户态/内核态边界的处理本身即 C 级攻坚
- 结论：上游官方 `--with-config=user` 路径在 OHOS 上完整可行（研究先行 → 实测证实），无需退守子集方案

## 可行性研究结论（先研后配方）

1. 上游 `./configure --with-config=user` 只走 `ZFS_AC_CONFIG_USER`（config/zfs-build.m4），纯用户态路径存在且官方支持
2. 致命依赖（configure AC_MSG_FAILURE）：zlib/libuuid/libblkid/libcrypto(libssl)/libtirpc —— ohpcd 仓全部可得
3. 可降级依赖：libudev（zed_disk_event.c 有完整 HAVE_LIBUDEV 守卫）/libaio/libunwind/pam/libfetch（none 分支 ENOSYS 优雅降级）
4. 内核态裁剪面：module/（内核模块）+ zed 的 udev 监视路径 + mount helper 内核 ioctl——上游条件编译天然裁剪，无需改源码
5. 宿主机即 OHOS aarch64 原生环境：configure 运行时探测真实可信，产物可直接执行（ztest/zfs CLI 真跑）

## 构建修复清单（全部实测验证）

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | configure: sed does not support in-place | ZFS 硬要求 `sed --in-place` 长选项；OHOS toybox sed 只有 `-i` | tool_requires sed/4.9（GNU sed） |
| 2 | config.guess: unable to guess system type | uname 返回 HarmonyOS | config.guess/config.sub OHOS 补丁（patch-autotools-ohos.pl 逻辑 Python 复刻） |
| 3 | config.status: could not setup config files machinery | HMDFS umask 077 坑（E011） | configure 内 umask 077→022 |
| 4 | 2000+ dgettext 隐式声明（-Wint-conversion） | OHOS musl libintl.h 零声明存根 | zfs-ohos-shim.h no-op 宏，CPPFLAGS `-include` 注入 |
| 5 | .S 汇编单元炸汇编器 | shim 的 C 函数定义进了 .S（吃同一 CPPFLAGS） | shim 加 `__ASSEMBLER__` 守卫 |
| 6 | program_invocation_short_name 未定义 | glibc 私有，musl 无 | patch 0001：`__GLIBC__` 守卫 → musl `__progname` |
| 7 | curl/curl.h not found | 宿主 curl-config 误使 libfetch 选 libcurl，目标无 libcurl | 遮蔽 curl-config → 探测走 none（上游 ENOSYS 降级） |
| 8 | openssl/evp.h not found（libzdb） | 上游 lib/libzdb/Makefile.am 漏 LIBCRYPTO_CFLAGS | CPPFLAGS 全局注入 openssl include |
| 9 | SEEK_DATA 未定义 | musl fcntl.h 只有 SET/CUR/END | patch 0003：数值 fallback（对齐上游 mmap_seek.c 先例） |
| 10 | pthread_setconcurrency 链接失败 | glibc 私有，musl 无 | patch 0004：`__GLIBC__` 守卫 |
| 11 | R_AARCH64_ADR_PREL_PG_HI21 against z_errmsg | conan zlib/1.3.1 非 PIC | 换 zlib/1.3.1.1.1.1（PIC 静态变体） |
| 12 | pthread_cancel 族 undefined | OHOS SDK libc.so 无导出（运行时 libc 3/4） | shim 弱符号 no-op（仅内核交互 teardown 路径引用，无内核模块不可达） |
| 13 | addmntent undefined | OHOS SDK mntent.h/libc.so 缺 | shim 弱符号（mount.zfs 的 /etc/mtab 更新路径不可达） |
| 14 | ztest ASSERT setup_data_fd 失败 | OHOS /tmp 只读 | patch 0002：TMPDIR 支持 |

## 上游测试真跑（OHOS aarch64 宿主原生执行）

- ztest（用户态 SPA 仿真）：`ztest -T 60 -s 64M -v 3` **RC=0**，60 秒全流程（spa_create → IO → checkpoint → freeze → zdb 校验 → spa_load LOADED）
- btree_test：**RC=0**，4 子测试（insert_find_remove/find_without_index/drain_tree/stress_tree，600 万插删）
- sha2_test：**RC=0**，6 向量 OK（armv8-ce 硬件实现被选中）
- edonr_test：**RC=0**，2 向量 OK
- skein_test：**RC=0**，9 向量 OK
- blake3_test：**RC=0**，105 向量 OK（aarch64 sse2/sse41 汇编路径）
- 合计 126 断言全过；zfs/zpool/zdb 二进制真实执行（非零退出+上游内核边界消息=诚实失败签名）
- ZTS 全量 1553 注册用例（common.run 1372 + linux.run 181）：环境限制豁免（需 ZFS 内核模块+root+回环盘）

## 产物

- 库：libzfs.so.7 / libzfs_core.so.3 / libnvpair.so.3 / libuutil.so.3 / libzpool.so.7 / libzfsbootenv.so.1（.a 同步产出，上游 soname 保留）
- CLI：zfs/zpool/zdb/ztest/zstream/zinject/zhack/zed/raidz_test/zpool_influxdb/zgenhostid/fsck.zfs/mount.zfs/zfs_ids_to_path
- 全部 ELF 可执行 binary-sign-tool 签名（.codesign 段唯一性校验）
